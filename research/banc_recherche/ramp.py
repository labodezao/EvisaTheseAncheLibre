"""Rampes de bifurcation au banc : rampes de pression répétées montée/descente
→ seuils `μ_on`/`μ_off` et **diagramme de bifurcation stochastique**.

Sur le banc à soufflet, une **course** (`STROKE`) est une rampe : **pousser** =
pression croissante (rampe montante → apparition de l'oscillation à `μ_on`),
**tirer** = pression décroissante (rampe descendante → extinction à `μ_off`).
En répétant, le bruit rend les seuils distribués : `stochastic.threshold_stats`
en donne moyenne ± écart-type, et on empile les diagrammes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .config import Config
from . import audio, bifurcation, stochastic
from .bench_link import BenchLink


def amplitude_vs_param(sig, fs, param_t, param_v, win_s=0.03):
    """Aligne l'amplitude (enveloppe RMS de l'audio) sur la base de temps du
    paramètre de contrôle (pression, échantillonnée par la télémétrie).

    `param_t` : instants (s) des échantillons de paramètre ; `param_v` : valeurs.
    Renvoie (param_v, amp) rééchantillonné aux instants du paramètre.
    """
    amp = bifurcation.order_parameter(sig, fs, win_s)
    t_audio = np.arange(amp.size) / fs
    param_t = np.asarray(param_t, dtype="float64")
    param_v = np.asarray(param_v, dtype="float64")
    if param_t.size == 0:
        return param_v, np.array([])
    amp_at = np.interp(param_t, t_audio, amp)
    return param_v, amp_at


@dataclass
class SweepResult:
    stats: stochastic.ThresholdStats
    diagrams: list = field(default_factory=list)   # un BifurcationDiagram par répétition
    mu_on: list = field(default_factory=list)
    mu_off: list = field(default_factory=list)


def _stroke_and_measure(cfg, link, direction, speed):
    """Une course (rampe) : lance STROKE, acquiert audio + pression, renvoie
    (param_pression, amplitude) alignés."""
    link.stroke(direction, speed)
    rec = audio.record(cfg.audio, cfg.doe.acquire_s)
    sig = rec[:, 0]
    frames = link.collect_telem(cfg.doe.acquire_s)
    if not frames:
        return np.array([]), np.array([])
    # instants relatifs (les trames portent un t en ms) + pression p (Pa)
    t = np.array([f.get("t", i) for i, f in enumerate(frames)], dtype="float64")
    t = (t - t[0]) / 1000.0 if t.max() > 100 else np.arange(len(frames)) * (cfg.doe.acquire_s / len(frames))
    p = np.array([f.get("p", np.nan) for f in frames], dtype="float64")
    return amplitude_vs_param(sig, cfg.audio.samplerate, t, p)


def run_threshold_sweep(cfg: Config, link: BenchLink, n_repeats: int = 5,
                        speed: float = 400.0,
                        progress: Callable[[int, int, str], None] | None = None) -> SweepResult:
    """Répète `n_repeats` rampes montée (pousser) + descente (tirer), détecte
    `μ_on`/`μ_off` par rampe et agrège en statistiques + diagrammes."""
    if link is None:
        raise ValueError("run_threshold_sweep requiert un banc connecté (link)")
    link.home()
    mu_on, mu_off, diags = [], [], []
    for k in range(1, n_repeats + 1):
        if progress:
            progress(k, n_repeats, f"rampe {k}/{n_repeats}")
        p_up, a_up = _stroke_and_measure(cfg, link, +1, speed)     # pousser = montée
        p_dn, a_dn = _stroke_and_measure(cfg, link, -1, speed)     # tirer = descente
        if a_up.size and a_dn.size:
            bd = bifurcation.diagram(p_up, a_up, p_dn, a_dn)
            diags.append(bd)
            mu_on.append(bd.mu_on)
            mu_off.append(bd.mu_off)
    link.stop()
    stats = stochastic.threshold_stats(mu_on, mu_off)
    return SweepResult(stats, diags, mu_on, mu_off)
