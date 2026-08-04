"""Méthode à **deux microphones** (tube d'impédance, ISO 10534-2).

Avec l'excitation EM comme source et deux micros de mesure espacés de `s`, on
mesure la fonction de transfert H12 = P2/P1, d'où on tire le **coefficient de
réflexion** `R`, l'**impédance acoustique normalisée** `Z/ρc` et l'**absorption**
`α = 1 − |R|²` de l'échantillon (cavité, clapet, sourdine).

Couvre les chapitres « Pressure and Flow : impedance », « inverse problem
solving » et « Acoustic transmittance of valves » du manuscrit.
"""
from __future__ import annotations

import numpy as np

C_AIR = 343.0     # m/s à ~20 °C ; ajuster selon température (voir speed_of_sound)


def speed_of_sound(temp_c: float = 20.0) -> float:
    return 331.3 * np.sqrt(1.0 + temp_c / 273.15)


def estimate_H12(x1: np.ndarray, x2: np.ndarray, fs: float, nperseg: int = 4096):
    """Fonction de transfert H12 = P2/P1 par moyenne de périodogrammes croisés
    (numpy seul). Renvoie (freqs, H12 complexe, cohérence)."""
    x1 = np.asarray(x1, dtype="float64")
    x2 = np.asarray(x2, dtype="float64")
    n = min(len(x1), len(x2))
    x1, x2 = x1[:n], x2[:n]
    win = np.hanning(nperseg)
    step = nperseg // 2
    S11 = S22 = S12 = None
    count = 0
    for start in range(0, n - nperseg + 1, step):
        a = np.fft.rfft(x1[start:start + nperseg] * win)
        b = np.fft.rfft(x2[start:start + nperseg] * win)
        s11 = (a.conj() * a).real
        s22 = (b.conj() * b).real
        s12 = a.conj() * b
        S11 = s11 if S11 is None else S11 + s11
        S22 = s22 if S22 is None else S22 + s22
        S12 = s12 if S12 is None else S12 + s12
        count += 1
    if not count:
        raise ValueError("signal trop court pour nperseg")
    freqs = np.fft.rfftfreq(nperseg, 1.0 / fs)
    H12 = S12 / np.where(S11 == 0, np.nan, S11)
    coherence = (np.abs(S12) ** 2) / np.where(S11 * S22 == 0, np.nan, S11 * S22)
    return freqs, H12, coherence


def reflection_impedance(freqs: np.ndarray, H12: np.ndarray, spacing: float,
                         x1_dist: float, c: float = C_AIR):
    """Coefficient de réflexion, impédance normalisée et absorption (ISO 10534-2).

    `spacing` = écart entre les deux micros (m) ; `x1_dist` = distance du micro 1
    (le plus loin) à l'échantillon (m). Renvoie (R, Z_norm, absorption) complexes/réels.
    """
    freqs = np.asarray(freqs, dtype="float64")
    k = 2.0 * np.pi * freqs / c
    H_I = np.exp(-1j * k * spacing)     # onde incidente
    H_R = np.exp(+1j * k * spacing)     # onde réfléchie
    denom = H_R - H12
    R = (H12 - H_I) / np.where(denom == 0, np.nan, denom) * np.exp(2j * k * x1_dist)
    Z_norm = (1.0 + R) / np.where((1.0 - R) == 0, np.nan, (1.0 - R))
    absorption = 1.0 - np.abs(R) ** 2
    return R, Z_norm, absorption


def transmission_loss(x_in: np.ndarray, x_out: np.ndarray, fs: float,
                      nperseg: int = 4096):
    """Perte par transmission simplifiée (niveau) entre amont et aval d'un
    échantillon : TL(f) = 10·log10(S_in/S_out). Estimation grossière ; la
    version 4 micros (matrice de transfert) viendra si besoin."""
    f, H, _ = estimate_H12(x_in, x_out, fs, nperseg)
    tl = -20.0 * np.log10(np.abs(H) + 1e-12)     # |P_out/P_in| → atténuation
    return f, tl
