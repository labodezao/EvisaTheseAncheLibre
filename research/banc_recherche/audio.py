"""Acquisition et génération audio via l'interface Behringer (sounddevice).

Remplace l'ancien `pyaudio` de `MesAnche.py`. Full-duplex : on émet le signal
d'excitation EM sur la sortie et on capture simultanément les voies d'entrée
(anche/micro + pression + référence EM), horodatés au même bloc.
"""
from __future__ import annotations

import numpy as np

from .config import AudioConfig

try:
    import sounddevice as sd
except Exception:      # import différé : la GUI peut tourner sans matériel
    sd = None


def list_devices() -> str:
    """Liste les périphériques audio (pour repérer la Behringer)."""
    if sd is None:
        return "sounddevice indisponible"
    return str(sd.query_devices())


def record(cfg: AudioConfig, duration: float) -> np.ndarray:
    """Capture `duration` s sur les voies d'entrée. Renvoie (n, n_in) float32."""
    if sd is None:
        raise RuntimeError("sounddevice indisponible")
    n = int(duration * cfg.samplerate)
    data = sd.rec(n, samplerate=cfg.samplerate, channels=len(cfg.in_channels),
                  device=cfg.device, dtype="float32")
    sd.wait()
    return data


def play_record(cfg: AudioConfig, out: np.ndarray) -> np.ndarray:
    """Full-duplex : émet `out` (n, n_out) et capture en même temps.

    Cœur de l'excitation EM synchrone : la sortie va vers OUTTA/ampli bobine, les
    entrées reviennent de l'anche et des capteurs. Renvoie (n, n_in) float32.
    """
    if sd is None:
        raise RuntimeError("sounddevice indisponible")
    rec = sd.playrec(out.astype("float32"), samplerate=cfg.samplerate,
                     channels=len(cfg.in_channels), device=cfg.device, dtype="float32")
    sd.wait()
    return rec


def to_pascals(cfg: AudioConfig, channel: np.ndarray) -> np.ndarray:
    """Convertit une voie pleine échelle en Pa selon l'étalonnage."""
    return channel * cfg.pa_per_fs


def channel(rec: np.ndarray, idx) -> np.ndarray:
    """Extrait une voie d'un enregistrement multi-canaux (idx borné)."""
    if idx is None or rec.ndim == 1:
        return rec if rec.ndim == 1 else rec[:, 0]
    return rec[:, min(int(idx), rec.shape[1] - 1)]


def accel(cfg: AudioConfig, rec: np.ndarray):
    """Voie accéléromètre si configurée, sinon None."""
    return channel(rec, cfg.accel_channel) if cfg.accel_channel is not None else None
