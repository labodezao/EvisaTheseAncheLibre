"""Plan d'expériences automatique (DOE) — reprise de `Mesures.py`.

Deux modes selon la source d'air du banc :

- **Pression** (turbine/asservissement) : grille Section × Pression × Clapet ×
  Position ; on asservit la pression, on stabilise, on mesure.
- **Soufflet** (`use_stroke`, banc **sans soufflerie**) : grille Section ×
  Vitesse × Clapet ; chaque point est mesuré en **poussant puis en tirant**
  (`STROKE`), remplissant les deux sens de pression (l'ancien `P_pos`). La mesure
  se fait pendant la course, la pression venant du mouvement du soufflet.

Pour chaque point : positionne les axes (`BenchLink`), acquiert l'audio
(`audio`) synchronisé avec la pression/débit, analyse (`analysis`, `impedance`)
et stocke (`storage`).
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
    """Itère la grille complète. En mode soufflet : Section × Vitesse × Clapet ×
    Sens ; sinon : Section × Pression × Clapet × Position."""
    d = cfg.doe
    if d.use_stroke:
        return product(d.sections_mm, d.stroke_speeds, d.clapets_deg, d.stroke_directions)
    return product(d.sections_mm, d.pressures_pa, d.clapets_deg, d.positions)


def _acquire(cfg: Config, link: BenchLink | None):
    """Acquisition synchrone audio + pneumatique. Renvoie (sig, p_ch, q_ch)."""
    if link is not None:
        if hasattr(link, "send"):
            link.send(f"ACQUIRE {cfg.doe.acquire_s}")
        rec = audio.record(cfg.audio, cfg.doe.acquire_s)
        sig = rec[:, 0]
        frames = link.collect_telem(cfg.doe.acquire_s)
        p_ch = np.array([f.get("p", np.nan) for f in frames], dtype="float64")
        q_ch = np.array([f.get("q", np.nan) for f in frames], dtype="float64")
    else:
        rec = audio.record(cfg.audio, cfg.doe.acquire_s)
        sig = rec[:, 0]
        p_ch = audio.to_pascals(cfg.audio, rec[:, min(1, rec.shape[1] - 1)])
        q_ch = rec[:, min(2, rec.shape[1] - 1)]
    return sig, p_ch, q_ch


def _analyse(cfg: Config, sig, p_ch, q_ch, **point_kw) -> Point:
    """Analyse acoustique (Praat sinon enveloppe) + impédance → `Point`."""
    imp = impedance.compute(p_ch, q_ch)
    try:
        pr = analysis.praat_calcs(sig, cfg.audio.samplerate)
        tresp_ms, f0 = pr.tresp_s * 1000.0, pr.mean_fund_hz
        forms = (pr.f1, pr.f2, pr.f3, pr.f4)
    except Exception:
        atk = analysis.attack(sig, cfg.audio.samplerate)
        tresp_ms, f0, forms = atk.tresp_ms, float("nan"), ()
    return Point(f0_hz=f0, tresp_ms=tresp_ms, impedance=imp.impedance,
                 pui_hydro=imp.pui_hydro, formants=tuple(forms),
                 audio=sig.astype(np.float32), pressure=p_ch.astype(np.float32),
                 flow=q_ch.astype(np.float32), **point_kw)


def run(cfg: Config, link: BenchLink | None = None,
        progress: Callable[[int, int, str], None] | None = None) -> Iterator[Point]:
    """Exécute le DOE et *yield* chaque `Point` mesuré.

    `link` : lien ESP32 ouvert (air). Si None, pneumatique pilotée à la main
    (mode dégradé). `progress(k, total, msg)` : rappel d'avancement.
    """
    d = cfg.doe
    combos = list(grid(cfg))
    total = len(combos)
    store = Store(cfg.hdf5_path)
    points: list[Point] = []
    if link is not None and d.use_stroke:
        link.home()          # part de la butée : pousser depuis 0, tirer depuis le bout
    try:
        for k, combo in enumerate(combos, 1):
            if d.use_stroke:
                sec, speed, clap, direction = combo
                pos = 0 if direction > 0 else 1          # P_pos : pousser=0, tirer=1
                if progress:
                    progress(k, total, f"S={sec} v={speed} C={clap}° {'pousser' if direction>0 else 'tirer'}")
                if link:
                    link.section(sec)
                    link.clap(clap)
                    if d.button >= 0:
                        link.press_btn(d.button, True)
                    link.stroke(direction, speed)        # lance la passe
                    time.sleep(0.2)                      # laisse la pression monter
                sig, p_ch, q_ch = _acquire(cfg, link)
                pt = _analyse(cfg, sig, p_ch, q_ch, idx=k, section_mm=sec,
                              pressure_pa=float("nan"), clapet_deg=clap, position=pos)
                if link and d.button >= 0:
                    link.press_btn(d.button, False)
            else:
                sec, pa, clap, pos = combo
                if progress:
                    progress(k, total, f"S={sec} P={pa} C={clap}° pos={pos}")
                if link:
                    link.section(sec)
                    link.clap(clap)
                    link.pressure(pa)
                    if pos >= 0:
                        link.press_btn(pos, True)
                time.sleep(d.settle_s)
                sig, p_ch, q_ch = _acquire(cfg, link)
                pt = _analyse(cfg, sig, p_ch, q_ch, idx=k, section_mm=sec,
                              pressure_pa=pa, clapet_deg=clap, position=pos)
                if link and pos >= 0:
                    link.press_btn(pos, False)
            store.write(pt)
            points.append(pt)
            yield pt
    finally:
        if link:
            link.stop()
        export_csv(points, cfg.csv_path)
        store.close()
