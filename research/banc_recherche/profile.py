"""Profil statique d'anche par **balayage d'un capteur de déplacement** monté sur
la table X, et sa **courbure**.

Le capteur n'a pas à être un vibromètre laser (hors de prix) : n'importe quelle
mesure de position par pas convient — **comparateur digital** (dial indicator)
relevé à la main, capteur de distance analogique bon marché (Sharp GP2Y,
inductif), ou même une **méthode photo** (contour de l'anche détecté par
OpenCV). Le firmware `SCAN` lit une entrée analogique à chaque position ; sinon
on charge un simple CSV `position,valeur`. On calcule la **courbure** (dérivée
seconde) et la **déflexion maximale** au repos (chapitre « Static shape »).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ProfileResult:
    position_mm: np.ndarray
    deflection_mm: np.ndarray
    curvature: np.ndarray        # d²y/dx² (1/mm)
    max_deflection: float
    max_curvature: float
    rms_curvature: float


def from_scan(position_mm, raw_value, mm_per_unit: float = 1.0, detrend: bool = True):
    """Construit le profil depuis un balayage. `raw_value` : lecture capteur
    (ex. tension ADC) ; `mm_per_unit` : étalonnage (mm par unité). `detrend`
    retire la pente moyenne (alignement du support) pour isoler la courbure."""
    x = np.asarray(position_mm, dtype="float64")
    y = np.asarray(raw_value, dtype="float64") * mm_per_unit
    order = np.argsort(x)
    x, y = x[order], y[order]
    if detrend and x.size >= 2:
        a, b = np.polyfit(x, y, 1)
        y = y - (a * x + b)
    curv = np.gradient(np.gradient(y, x), x) if x.size >= 3 else np.zeros_like(y)
    return ProfileResult(
        x, y, curv,
        float(np.max(np.abs(y))) if y.size else float("nan"),
        float(np.max(np.abs(curv))) if curv.size else float("nan"),
        float(np.sqrt(np.mean(curv ** 2))) if curv.size else float("nan"))


def parse_scan_lines(lines):
    """Parse les lignes `S position valeur` du firmware → (positions, valeurs)."""
    pos, val = [], []
    for ln in lines:
        p = ln.strip().split()
        if len(p) >= 3 and p[0] == "S":
            try:
                pos.append(float(p[1])); val.append(float(p[2]))
            except ValueError:
                pass
    return np.array(pos), np.array(val)
