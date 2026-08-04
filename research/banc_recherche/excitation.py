"""Excitation électromagnétique : génération de sweep, diagramme de phase,
extraction des fréquences de résonance et du couplage cavité ↔ anche.

L'EM était l'AD9833 sur le firmware ; il passe désormais côté PC (OUTTA +
Behringer). On génère le signal numériquement, on l'émet full-duplex (`audio.py`)
et on analyse la réponse par démodulation cohérente (I/Q).
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from .config import AudioConfig, SweepConfig
from . import audio


def make_sweep(cfg: SweepConfig, samplerate: int) -> np.ndarray:
    """Sinus glissant f0→f1 (chirp) d'amplitude `cfg.amplitude`, mono."""
    n = int(cfg.duration * samplerate)
    t = np.arange(n) / samplerate
    ph = "logarithmic" if cfg.method == "log" else "linear"
    x = signal.chirp(t, cfg.f0, cfg.duration, cfg.f1, method=ph)
    return (cfg.amplitude * x).reshape(-1, 1)


def response(audio_cfg: AudioConfig, sweep_cfg: SweepConfig,
             drive_ch: int = 0, sense_ch: int = 0):
    """Émet le sweep et mesure la réponse de l'anche.

    Renvoie (freqs, H) où `H` est la fonction de transfert complexe estimée par
    corrélation (spectre croisé / autospectre) — module = amplitude, argument =
    phase (→ diagramme de phase).
    """
    out = make_sweep(sweep_cfg, audio_cfg.samplerate)
    rec = audio.play_record(audio_cfg, out)
    drive = out[:, 0]
    sense = rec[:, sense_ch]
    n = min(len(drive), len(sense))
    f, pxy = signal.csd(drive[:n], sense[:n], fs=audio_cfg.samplerate, nperseg=4096)
    _, pxx = signal.welch(drive[:n], fs=audio_cfg.samplerate, nperseg=4096)
    h = pxy / np.where(pxx == 0, np.nan, pxx)
    band = (f >= sweep_cfg.f0) & (f <= sweep_cfg.f1)
    return f[band], h[band]


def resonances(freqs: np.ndarray, h: np.ndarray, n_peaks: int = 4):
    """Fréquences de résonance = pics du module de la fonction de transfert."""
    mag = np.abs(h)
    idx, props = signal.find_peaks(mag, prominence=mag.max() * 0.05)
    order = np.argsort(props["prominences"])[::-1][:n_peaks]
    peaks = sorted(idx[order])
    return [(float(freqs[i]), float(mag[i]), float(np.angle(h[i]))) for i in peaks]
