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
RHO_AIR = 1.204   # kg/m³ à ~20 °C


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
    échantillon : TL(f) = 10·log10(S_in/S_out). Estimation grossière ; voir la
    version 4 micros (matrice de transfert) ci-dessous pour la mesure rigoureuse."""
    f, H, _ = estimate_H12(x_in, x_out, fs, nperseg)
    tl = -20.0 * np.log10(np.abs(H) + 1e-12)     # |P_out/P_in| → atténuation
    return f, tl


# ===========================================================================
# Méthode à QUATRE microphones (matrice de transfert, ASTM E2611).
# 2 micros amont (x1, x2) + 2 micros aval (x3, x4) autour de l'échantillon
# (à x = 0). On décompose le champ en ondes progressives, on obtient p et u de
# part et d'autre, puis la matrice de transfert 2×2 (deux terminaisons) et la
# perte par transmission. Couvre « Acoustic transmittance of valves ».
# ===========================================================================
def decompose(pa, pb, xa: float, xb: float, k):
    """Ondes progressives A (incidente, +x) et B (réfléchie, −x) dans un tube,
    à partir des pressions complexes `pa`,`pb` aux positions `xa`,`xb`.

    p(x) = A·e^{−jkx} + B·e^{+jkx}. `k` peut être un scalaire ou un tableau (freq).
    """
    k = np.asarray(k, dtype="float64")
    det = 2j * np.sin(k * (xb - xa))
    det = np.where(det == 0, np.nan, det)
    A = (pa * np.exp(1j * k * xb) - pb * np.exp(1j * k * xa)) / det
    B = (pb * np.exp(-1j * k * xa) - pa * np.exp(-1j * k * xb)) / det
    return A, B


def waves_to_pu(A, B, rho: float = RHO_AIR, c: float = C_AIR):
    """Pression et vitesse acoustiques à la face (x = 0) depuis les ondes A, B."""
    p = A + B
    u = (A - B) / (rho * c)
    return p, u


def transmission_loss_anechoic(A, C):
    """TL (dB) en terminaison quasi-anéchoïque aval : t = C/A, TL = −20·log10|t|."""
    return -20.0 * np.log10(np.abs(np.asarray(C) / np.asarray(A)) + 1e-12)


def _spectra(sigs, fs, nperseg=4096):
    """Spectres complexes co-cohérents des voies (même base de temps)."""
    n = min(len(s) for s in sigs)
    win = np.hanning(nperseg)
    step = nperseg // 2
    acc = [None] * len(sigs)
    count = 0
    for start in range(0, n - nperseg + 1, step):
        for i, s in enumerate(sigs):
            X = np.fft.rfft(np.asarray(s[start:start + nperseg], dtype="float64") * win)
            acc[i] = X if acc[i] is None else acc[i] + X
        count += 1
    if not count:
        raise ValueError("signal trop court pour nperseg")
    freqs = np.fft.rfftfreq(nperseg, 1.0 / fs)
    return freqs, [a / count for a in acc]


def four_mic_analyze(x1s, x2s, x3s, x4s, positions, fs, rho=RHO_AIR, c=C_AIR,
                     nperseg=4096):
    """Analyse 4 micros (une terminaison) : renvoie (freqs, A,B,C,D, TL, absorption).

    `positions` = (x1, x2, x3, x4) en m, échantillon à x = 0 (amont x < 0, aval x > 0).
    TL suppose la terminaison aval quasi-anéchoïque ; l'absorption amont = 1−|B/A|².
    """
    x1, x2, x3, x4 = positions
    freqs, (P1, P2, P3, P4) = _spectra((x1s, x2s, x3s, x4s), fs, nperseg)
    k = 2 * np.pi * freqs / c
    A, B = decompose(P1, P2, x1, x2, k)     # amont : incidente / réfléchie
    C, D = decompose(P3, P4, x3, x4, k)     # aval : transmise / retour
    tl = transmission_loss_anechoic(A, C)
    absorption = 1.0 - np.abs(B / np.where(A == 0, np.nan, A)) ** 2
    return freqs, A, B, C, D, tl, absorption


def transfer_matrix_two_load(state_a, state_b):
    """Matrice de transfert 2×2 par la méthode **deux terminaisons** (ASTM E2611).

    `state_x` = (p_u, u_u, p_d, u_d) : pressions/vitesses amont et aval pour la
    terminaison x (a puis b). Renvoie (T11, T12, T21, T22).
    """
    pua, uua, pda, uda = state_a
    pub, uub, pdb, udb = state_b
    den = pda * udb - pdb * uda
    den = np.where(den == 0, np.nan, den)
    T11 = (pua * udb - pub * uda) / den
    T12 = (pub * pda - pua * pdb) / den
    T21 = (uua * udb - uub * uda) / den
    T22 = (uub * pda - uua * pdb) / den
    return T11, T12, T21, T22


def tl_from_matrix(T11, T12, T21, T22, rho=RHO_AIR, c=C_AIR):
    """Perte par transmission (dB) depuis la matrice de transfert (section
    constante, terminaison anéchoïque) : TL = 20·log10( |T11 + T12/ρc + ρc·T21 + T22| / 2 )."""
    z = rho * c
    mag = np.abs(T11 + T12 / z + z * T21 + T22) / 2.0
    return 20.0 * np.log10(mag + 1e-12)
