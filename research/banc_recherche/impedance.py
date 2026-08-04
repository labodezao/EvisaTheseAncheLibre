"""Impédance (P/Q) et puissance hydraulique (P·Q).

Reprend le cœur numérique de `Data_analysis.py` : à partir de la pression `p`
(Pa) et du débit `q` (m³/s ou slm cohérents), on calcule l'impédance et la
puissance, moyennées sur la tenue.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ImpedanceResult:
    impedance: float     # Z = P/Q (moyenne)
    pui_hydro: float     # P·Q (moyenne)
    p_mean: float
    q_mean: float


def compute(p: np.ndarray, q: np.ndarray) -> ImpedanceResult:
    p = np.asarray(p, dtype="float64")
    q = np.asarray(q, dtype="float64")
    p_mean = float(np.nanmean(p)) if p.size else float("nan")
    q_mean = float(np.nanmean(q)) if q.size else float("nan")
    z = p_mean / q_mean if q_mean not in (0.0, float("nan")) else float("nan")
    return ImpedanceResult(z, p_mean * q_mean, p_mean, q_mean)
