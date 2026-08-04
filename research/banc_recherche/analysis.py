"""Analyse acoustique façon Praat (via parselmouth) : temps de réponse `Tresp`,
enveloppe d'attaque, formants F1–F4 (modes de cavité), pitch de référence.

Reprend `Data_analysis.py` et `enveloppepraat.py` en supprimant l'appel externe
à Praat lancé à la main : tout passe par `parselmouth`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import parselmouth
except Exception:      # la GUI reste utilisable sans Praat installé
    parselmouth = None


@dataclass
class AttackResult:
    tresp_ms: float          # temps de montée à 90 % de l'amplitude établie
    onset_s: float           # instant de début d'oscillation
    steady_amp: float        # amplitude établie (RMS)


def _sound(sig: np.ndarray, sr: int):
    if parselmouth is None:
        raise RuntimeError("parselmouth (Praat) indisponible")
    return parselmouth.Sound(sig.astype("float64"), sampling_frequency=sr)


def envelope(sig: np.ndarray, sr: int, smooth_ms: float = 5.0) -> np.ndarray:
    """Enveloppe d'amplitude (RMS glissant) — reprise d'`enveloppepraat.py`."""
    win = max(1, int(smooth_ms * 1e-3 * sr))
    sq = np.convolve(sig.astype("float64") ** 2, np.ones(win) / win, mode="same")
    return np.sqrt(sq)


def attack(sig: np.ndarray, sr: int, thresh: float = 0.1) -> AttackResult:
    """Mesure `Tresp` : de l'onset (seuil) à 90 % de l'amplitude établie."""
    env = envelope(sig, sr)
    steady = float(np.median(env[int(0.6 * len(env)):])) if len(env) else 0.0
    if steady <= 0:
        return AttackResult(float("nan"), float("nan"), 0.0)
    onset_idx = int(np.argmax(env > thresh * steady))
    reach = np.where(env[onset_idx:] >= 0.9 * steady)[0]
    tresp = (reach[0] / sr * 1000.0) if len(reach) else float("nan")
    return AttackResult(tresp, onset_idx / sr, steady)


def formants(sig: np.ndarray, sr: int, n: int = 4, max_hz: float = 5500.0):
    """Formants F1..Fn (modes de cavité) — valeurs médianes sur la tenue."""
    snd = _sound(sig, sr)
    fo = snd.to_formant_burg(max_number_of_formants=n, maximum_formant=max_hz)
    out = []
    for k in range(1, n + 1):
        vals = [fo.get_value_at_time(k, t) for t in fo.ts()]
        vals = [v for v in vals if v is not None and not np.isnan(v)]
        out.append(float(np.median(vals)) if vals else float("nan"))
    return out


def pitch_hz(sig: np.ndarray, sr: int, fmin: float = 50.0, fmax: float = 2000.0) -> float:
    """Pitch de référence (médiane) via Praat — repère grossier ; l'accordeur web
    reste la mesure fine (zoom hétérodyne / Matrix Pencil)."""
    snd = _sound(sig, sr)
    p = snd.to_pitch(pitch_floor=fmin, pitch_ceiling=fmax)
    vals = p.selected_array["frequency"]
    vals = vals[vals > 0]
    return float(np.median(vals)) if len(vals) else float("nan")
