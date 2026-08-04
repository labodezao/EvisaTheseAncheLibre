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


@dataclass
class PraatResult:
    """Port fidèle de `Data_analysis.PraatCalcs` : ce que l'ancienne chaîne
    calculait par point de mesure (Tresp, formants moyens, pitch, intensité)."""
    tresp_s: float
    t_zero_s: float
    mean_fund_hz: float
    f1: float
    f2: float
    f3: float
    f4: float
    hnr_db: float
    # séries pour tracé
    pitch_t: np.ndarray
    pitch_hz: np.ndarray
    env_t: np.ndarray
    env: np.ndarray
    intensity_t: np.ndarray
    intensity_db: np.ndarray


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


def praat_calcs(sig: np.ndarray, sr: int, f0min: float = 40.0,
                f0max: float = 2000.0) -> PraatResult:
    """Port fidèle de `Data_analysis.PraatCalcs` (cœur scientifique de la thèse).

    - trim des `sr/3` premiers échantillons (bruit de mise en route) ;
    - enveloppe d'amplitude Praat (IntensityTier → AmplitudeTier → Hann band) ;
    - `t_zero` = 1er pic d'enveloppe dans [0.50, 0.85] s (son du clapet) ;
    - `Tresp` = temps du 1er pic établi après `t_zero + offset` − `t_zero` ;
    - formants F1–F4 (burg) moyennés après `t_zero`, pitch, HNR.
    """
    from parselmouth.praat import call
    from scipy import signal as _sig

    offset_peaks = 8000
    snd0 = _sound(sig, sr)
    samplerate = call(snd0, "Get sampling frequency")
    offset_t0 = int(samplerate / 3)
    snd = parselmouth.Sound(snd0.values.T.flatten()[offset_t0:], sampling_frequency=samplerate)
    sound_data = snd.values.T.flatten()

    duration = call(snd, "Get total duration")
    intensity = call(snd, "To Intensity", 50, 1 / samplerate)
    int_tier = call(intensity, "Down to IntensityTier")
    amp = call(int_tier, "To AmplitudeTier")
    tabreal = call(amp, "Down to TableOfReal")
    mat = call(tabreal, "To Matrix")
    tmat = call(mat, "Transpose")
    datas = call(tmat, "To Sound (slice)", 2)
    call(datas, "Scale times to", 0, duration)
    raw_env = call(datas, "Resample", samplerate, 5)
    env = call(raw_env, "Filter (pass Hann band)", 0, 60, 5)
    env_data = np.asarray(env.values.T.flatten())
    env_time = np.asarray(env.xs())
    int_data = np.asarray(intensity.values.T.flatten())
    int_time = np.asarray(intensity.xs())

    pitch = call(snd, "To Pitch", 0, f0min, f0max)
    pitch_values = np.asarray(pitch.selected_array["frequency"])
    pitch_time = np.asarray(pitch.xs())
    pitch_values[pitch_values == 0] = np.nan
    harmonicity = call(snd, "To Harmonicity (cc)", 0.01, f0min, 0.1, 1.0)
    hnr = call(harmonicity, "Get mean", 0, 0)

    formants_obj = call(snd, "To Formant (burg)", 0.0001, 5, f0max, 0.03, 12)
    point_proc = call(snd, "To PointProcess (periodic, cc)", 20, 5000)
    n_points = int(call(point_proc, "Get number of points"))
    f_lists = [[], [], [], []]
    t_list = []
    for point in range(1, n_points + 1):
        t = call(point_proc, "Get time from index", point)
        t_list.append(t)
        for k in range(4):
            f_lists[k].append(call(formants_obj, "Get value at time", k + 1, t, "Hertz", "Linear"))
    t_arr = np.asarray(t_list)
    f_arr = [np.asarray(fl) for fl in f_lists]

    # Tresp : 1er pic d'enveloppe dans [0.50, 0.85] s (extinction du clapet).
    peaks, _ = _sig.find_peaks(env_data, height=0.45 * np.max(np.abs(env_data)))
    i = 0
    if len(peaks):
        while env_time[peaks[i]] < 0.50 or env_time[peaks[i]] > 0.85:
            if i < peaks.shape[0] - 1:
                i += 1
            else:
                i = 0
                break
    t_zero_idx = peaks[i] if len(peaks) else 0
    t_zero = float(env_time[t_zero_idx]) if len(env_time) else 0.0

    tresp = float("nan")
    tail = env_data[t_zero_idx + offset_peaks:]
    if len(tail):
        thr = 0.95 * np.nanmean(env_data[-int(len(env_data[t_zero_idx:]) / 2):])
        pk2, _ = _sig.find_peaks(tail, height=thr)
        if len(pk2):
            tresp = float(env_time[pk2[0] + t_zero_idx + offset_peaks] - t_zero)

    mean_fund = float(np.nanmean(pitch_values[np.argwhere(pitch_time > t_zero)].flatten())) \
        if len(pitch_values) else float("nan")
    fmeans = []
    for fl in f_arr:
        idx = np.argwhere(t_arr > t_zero).flatten().astype(int)
        fmeans.append(float(np.nanmean(fl[idx])) if len(fl) and len(idx) > 1 else 0.0)

    return PraatResult(
        tresp_s=tresp, t_zero_s=t_zero, mean_fund_hz=mean_fund,
        f1=fmeans[0], f2=fmeans[1], f3=fmeans[2], f4=fmeans[3], hnr_db=float(hnr),
        pitch_t=pitch_time, pitch_hz=pitch_values, env_t=env_time, env=env_data,
        intensity_t=int_time, intensity_db=int_data)
