"""Plan d'expériences automatique (DOE) — reprise de `Mesures.py`.

Grille factorielle Section × Pression × Clapet × Position. Pour chaque point :
positionne les axes (air via `BenchLink`), asservit la pression, stabilise,
capture l'audio (`audio`) synchronisé avec la pression/débit, analyse
(`analysis`, `impedance`) et stocke (`storage`).
"""
from __future__ import annotations

import time
from itertools import product
from typing import Callable, Iterator

import numpy as np

from .config import Config
from . import audio, analysis, impedance
from .bench_link import BenchLink
from .storage import Point, Store, export_csv


def grid(cfg: Config):
    """Itère la grille complète (section, pression, clapet, position)."""
    d = cfg.doe
    return product(d.sections_mm, d.pressures_pa, d.clapets_deg, d.positions)


def run(cfg: Config, link: BenchLink | None = None,
        progress: Callable[[int, int, str], None] | None = None) -> Iterator[Point]:
    """Exécute le DOE et *yield* chaque `Point` mesuré.

    `link` : lien ESP32 ouvert (air). Si None, on suppose la pneumatique pilotée
    à la main (mode dégradé). `progress(k, total, msg)` : rappel d'avancement.
    """
    combos = list(grid(cfg))
    total = len(combos)
    store = Store(cfg.hdf5_path)
    points: list[Point] = []
    try:
        for k, (sec, pa, clap, pos) in enumerate(combos, 1):
            if progress:
                progress(k, total, f"S={sec} P={pa} C={clap}° pos={pos}")
            if link:
                link.section(sec)
                link.clap(clap)
                link.pressure(pa)
                if pos >= 0:
                    link.press_btn(pos, True)
            time.sleep(cfg.doe.settle_s)

            # Acquisition synchrone : audio (Behringer) + pneumatique. Si le banc
            # ESP32 est connecté, on tire P/Q de sa télémétrie ; sinon on retombe
            # sur les voies audio (montage tout-analogique dans la Behringer).
            if link is not None:
                if hasattr(link, "send"):
                    link.send(f"ACQUIRE {cfg.doe.acquire_s}")
                rec = audio.record(cfg.audio, cfg.doe.acquire_s)
                sig = rec[:, 0]
                frames = link.collect_telem(cfg.doe.acquire_s)
                p_mean, q_mean = link.mean_pq(frames)
                p_ch = np.array([f.get("p", np.nan) for f in frames], dtype="float64")
                q_ch = np.array([f.get("q", np.nan) for f in frames], dtype="float64")
            else:
                rec = audio.record(cfg.audio, cfg.doe.acquire_s)
                sig = rec[:, 0]
                p_ch = audio.to_pascals(cfg.audio, rec[:, min(1, rec.shape[1] - 1)])
                q_ch = rec[:, min(2, rec.shape[1] - 1)]

            imp = impedance.compute(p_ch, q_ch)
            # Analyse acoustique fine (Praat) si dispo, sinon repli sur l'enveloppe.
            try:
                pr = analysis.praat_calcs(sig, cfg.audio.samplerate)
                tresp_ms = pr.tresp_s * 1000.0
                f0 = pr.mean_fund_hz
                forms = (pr.f1, pr.f2, pr.f3, pr.f4)
            except Exception:
                atk = analysis.attack(sig, cfg.audio.samplerate)
                tresp_ms, f0, forms = atk.tresp_ms, float("nan"), ()

            pt = Point(idx=k, section_mm=sec, pressure_pa=pa, clapet_deg=clap,
                       position=pos, f0_hz=f0, tresp_ms=tresp_ms,
                       impedance=imp.impedance, pui_hydro=imp.pui_hydro,
                       formants=tuple(forms), audio=sig.astype(np.float32),
                       pressure=p_ch.astype(np.float32), flow=q_ch.astype(np.float32))
            store.write(pt)
            points.append(pt)
            if link and pos >= 0:
                link.press_btn(pos, False)
            yield pt
    finally:
        if link:
            link.stop()
        export_csv(points, cfg.csv_path)
        store.close()
