"""Fonction de réponse en fréquence par **balayage sinus exponentiel synchronisé**
(méthode de Farina / Novak — cf. dossier Drive « anches models/frf »).

On émet un sinus glissant exponentiel `f1→f2` ; la convolution de
l'enregistrement par le **filtre inverse** (balayage temporellement retourné et
pondéré) donne la **réponse impulsionnelle** (IR). La FFT de l'IR = FRF
(module + phase). Avantage : les **harmoniques** (distorsion non linéaire de
l'anche) se séparent proprement en amont de l'IR linéaire → mesure de la
non-linéarité, pas seulement des résonances.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Sweep:
    x: np.ndarray            # signal de balayage à émettre
    inverse: np.ndarray      # filtre inverse (pour déconvolution)
    fs: float
    f1: float
    f2: float
    dur: float


def exponential_sweep(f1: float, f2: float, dur: float, fs: float,
                      amplitude: float = 0.5) -> Sweep:
    """Balayage exponentiel + filtre inverse (Farina)."""
    n = int(dur * fs)
    t = np.arange(n) / fs
    L = dur / np.log(f2 / f1)
    phase = 2 * np.pi * f1 * L * (np.exp(t / L) - 1.0)
    x = np.sin(phase)
    # Filtre inverse : balayage retourné, pondéré en amplitude (+6 dB/oct).
    inv = x[::-1] * np.exp(-t / L)
    inv = inv / np.sum(x[::-1] * inv)         # normalisation → IR = δ pour un système unité
    return Sweep(amplitude * x, inv, fs, f1, f2, dur)


def impulse_response(recording, sweep: Sweep) -> np.ndarray:
    """Réponse impulsionnelle = enregistrement ∗ filtre inverse (partie causale)."""
    rec = np.asarray(recording, dtype="float64")
    full = np.convolve(rec, sweep.inverse, mode="full")
    return full


def linear_ir(recording, sweep: Sweep, pre: float = 0.01, post: float = 0.05):
    """Fenêtre l'IR linéaire (autour de la fin du balayage inverse) — sépare la
    réponse linéaire des harmoniques qui la précèdent."""
    full = impulse_response(recording, sweep)
    center = len(sweep.x) - 1            # position de l'IR linéaire
    a = max(0, center - int(pre * sweep.fs))
    b = min(len(full), center + int(post * sweep.fs))
    return full[a:b], center - a


def frf(ir, fs: float):
    """FRF depuis une réponse impulsionnelle : (freqs, complexe H)."""
    ir = np.asarray(ir, dtype="float64")
    H = np.fft.rfft(ir)
    f = np.fft.rfftfreq(ir.size, 1.0 / fs)
    return f, H


def bode(freqs, H):
    """(module dB, phase rad) pour tracé de Bode."""
    mag = 20 * np.log10(np.abs(H) + 1e-12)
    return mag, np.angle(H)


def resonances(freqs, H, n_peaks: int = 5, fmin: float = 20.0):
    """Fréquences de résonance = pics du module de la FRF."""
    from scipy.signal import find_peaks
    mag = np.abs(H)
    band = freqs >= fmin
    idx, props = find_peaks(np.where(band, mag, 0), prominence=mag.max() * 0.05)
    order = np.argsort(props["prominences"])[::-1][:n_peaks]
    return sorted(float(freqs[i]) for i in idx[order])
