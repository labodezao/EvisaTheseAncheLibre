"""Propriétés matériau de l'anche à partir d'un essai de résonance en cantilever.

Une lamelle bridée (`CLAMP`) excitée EM résonne à `f_n`. Pour une poutre
d'Euler-Bernoulli à section rectangulaire, on remonte au **module d'Young** `E` :

    f_n = (β_n² · t) / (2π · L²) · sqrt(E / (12 ρ))

où β₁L = 1.875, β₂L = 4.694, β₃L = 7.855 (encastré-libre). La largeur se
simplifie. Couvre le chapitre « Material of reeds ».
"""
from __future__ import annotations

import numpy as np

# Racines de l'équation caractéristique encastré-libre (β_n · L).
BETA_L = (1.875104, 4.694091, 7.854757, 10.995541)


def youngs_modulus(f_n: float, length: float, thickness: float, density: float,
                   mode: int = 1) -> float:
    """Module d'Young `E` (Pa) depuis la fréquence de résonance `f_n` (Hz).

    `length`, `thickness` en m ; `density` en kg/m³. `mode` = 1..4.
    """
    bl = BETA_L[mode - 1]
    # f_n = (bl² t)/(2π L²) · sqrt(E/(12 ρ))  →  E = 12 ρ · (2π f_n L² /(bl² t))²
    return 12.0 * density * (2.0 * np.pi * f_n * length ** 2 / (bl ** 2 * thickness)) ** 2


def resonance_frequency(E: float, length: float, thickness: float, density: float,
                        mode: int = 1) -> float:
    """Fréquence de résonance attendue (Hz) — utile pour vérifier / prédire."""
    bl = BETA_L[mode - 1]
    return (bl ** 2 * thickness) / (2.0 * np.pi * length ** 2) * np.sqrt(E / (12.0 * density))


def density_from_mass(mass_kg: float, length: float, width: float, thickness: float) -> float:
    """Masse volumique d'une lamelle rectangulaire (kg/m³)."""
    vol = length * width * thickness
    return mass_kg / vol if vol > 0 else float("nan")
