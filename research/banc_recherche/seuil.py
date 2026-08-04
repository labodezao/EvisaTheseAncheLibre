"""Seuil d'auto-entretien de l'anche (rampe de pression + hystérésis).

Reprend `mes_seuil_autoentretien.py` : on monte lentement la pression jusqu'au
démarrage de l'oscillation (`p_on`), puis on redescend jusqu'à l'extinction
(`p_off`). L'écart `p_on - p_off` = hystérésis, caractéristique de l'anche.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ThresholdResult:
    p_on: float          # pression de démarrage (montée)
    p_off: float         # pression d'extinction (descente)
    hysteresis: float    # p_on - p_off


def detect(pressure: np.ndarray, amplitude: np.ndarray,
           amp_thresh: float) -> ThresholdResult:
    """Trouve p_on / p_off à partir des traces synchrones pression/amplitude.

    `pressure` et `amplitude` doivent couvrir une rampe montante puis descendante
    (concaténées). `amp_thresh` = seuil d'amplitude marquant l'oscillation.
    """
    pressure = np.asarray(pressure, dtype="float64")
    amplitude = np.asarray(amplitude, dtype="float64")
    peak = int(np.argmax(pressure))          # sommet de la rampe
    up_p, up_a = pressure[:peak + 1], amplitude[:peak + 1]
    dn_p, dn_a = pressure[peak:], amplitude[peak:]

    on_idx = np.where(up_a > amp_thresh)[0]
    off_idx = np.where(dn_a < amp_thresh)[0]
    p_on = float(up_p[on_idx[0]]) if len(on_idx) else float("nan")
    p_off = float(dn_p[off_idx[0]]) if len(off_idx) else float("nan")
    return ThresholdResult(p_on, p_off, p_on - p_off)
