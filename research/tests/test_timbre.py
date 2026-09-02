import numpy as np

from banc_recherche import timbre


def _sine(f0, sr=44100.0, dur=2.0, amp=1.0, seed=None):
    t = np.arange(int(dur * sr)) / sr
    sig = amp * np.sin(2 * np.pi * f0 * t)
    if seed is not None:
        sig = sig + 0.01 * np.random.default_rng(seed).standard_normal(t.size)
    return sig


def test_stft_and_centroid_recover_sine_frequency():
    sr = 44100.0
    f0 = 1500.0
    y = _sine(f0, sr, dur=1.0)
    S, freqs, hop = timbre.stft_mag(y, sr, n_fft=2048)
    cent = timbre.spectral_centroid(S, freqs)
    assert abs(np.median(cent) - f0) < 20.0    # résolution FFT ~ sr/n_fft


def test_spectral_bands_puts_energy_in_right_band():
    sr = 44100.0
    y = _sine(1500.0, sr, dur=1.0)              # tombe dans (1000, 2000)
    S, freqs, _ = timbre.stft_mag(y, sr)
    bands = timbre.spectral_bands(S, freqs)
    assert bands[(1000, 2000)] > 90.0
    assert bands[(20, 60)] < 1.0


def test_spectral_flatness_tonal_lower_than_noise():
    sr = 44100.0
    tone = _sine(440.0, sr, dur=1.0)
    noise = np.random.default_rng(0).standard_normal(int(sr))
    S_tone, f_tone, _ = timbre.stft_mag(tone, sr)
    S_noise, f_noise, _ = timbre.stft_mag(noise, sr)
    assert np.mean(timbre.spectral_flatness(S_tone)) < np.mean(timbre.spectral_flatness(S_noise)) / 5


def test_hpss_separates_tone_from_clicks():
    sr = 44100.0
    n = int(sr * 2.0)
    t = np.arange(n) / sr

    tone_only = 0.5 * np.sin(2 * np.pi * 440 * t)
    S_tone, _, _ = timbre.stft_mag(tone_only, sr)
    h_pct, p_pct = timbre.hpss_energy_ratio(S_tone)
    assert h_pct > 90.0

    clicks = np.zeros(n)
    clicks[::4410] = 1.0                         # impulsions courtes = large bande
    S_click, _, _ = timbre.stft_mag(clicks, sr)
    h_pct2, p_pct2 = timbre.hpss_energy_ratio(S_click)
    assert p_pct2 > h_pct2


def test_modulation_spectrum_detects_known_rate():
    sr = 44100.0
    f_mod = 5.0
    n = int(sr * 8.0)                                 # long signal -> bonne résolution en fréquence de modulation
    t = np.arange(n) / sr
    mod = 0.5 * (1 + np.cos(2 * np.pi * f_mod * t))
    sig = mod * np.random.default_rng(1).standard_normal(n)
    S, freqs, hop = timbre.stft_mag(sig, sr, n_fft=2048, hop_length=256)
    fps = sr / hop
    peaks = timbre.modulation_spectrum(S, freqs, fps, bands=[(20, 20000, 'large')], fmin=0.5, fmax=15)
    assert abs(peaks['large'][0] - f_mod) < 0.3


def test_correct_metric_octave_picks_true_bpm():
    true_bpm = 90.0
    quarter = true_bpm / 60.0
    peaks = [quarter, 2 * quarter, 4 * quarter]     # noire, croche, double-croche
    candidates = [45.0, 90.0, 120.0, 180.0]
    best_bpm, best_err, errs = timbre.correct_metric_octave(peaks, candidates)
    assert best_bpm == true_bpm
    assert best_err < 1e-6
    assert errs[120.0] > best_err


def test_centroid_regression_recovers_slope():
    rng = np.random.default_rng(2)
    t = np.linspace(0, 100, 500)
    true_slope = 5.0
    y = 1000 + true_slope * t + rng.standard_normal(t.size) * 5
    reg = timbre.centroid_regression(t, y)
    assert abs(reg['slope'] - true_slope) < 0.5
    assert reg['p'] < 0.001
    assert reg['r2'] > 0.9


def test_crest_factor_of_sine_is_about_3db():
    sr = 44100.0
    y = _sine(440.0, sr, dur=1.0)
    cf = timbre.crest_factor_db(y)
    assert abs(cf - 3.01) < 0.1                     # crête/RMS = sqrt(2) pour un sinus


def test_dynamic_range_zero_for_constant_level():
    rms = np.full(200, 0.5)
    assert timbre.dynamic_range_db(rms) == 0.0


def test_dynamic_range_positive_for_varying_level():
    rng = np.random.default_rng(3)
    rms = np.abs(0.1 + 0.4 * rng.random(200))
    assert timbre.dynamic_range_db(rms) > 0.0


def test_beat_stability_zero_for_regular_beats():
    beats = np.arange(0, 20, 0.5)
    assert timbre.beat_stability(beats) < 1e-6


def test_beat_stability_positive_for_irregular_beats():
    rng = np.random.default_rng(4)
    beats = np.cumsum(0.5 + 0.1 * rng.standard_normal(40))
    assert timbre.beat_stability(beats) > 5.0


def test_bourdon_strength_high_for_steady_tone():
    sr = 44100.0
    y = _sine(110.0, sr, dur=2.0)                    # bourdon grave tenu
    S, freqs, _ = timbre.stft_mag(y, sr)
    strength = timbre.bourdon_strength(S, freqs, (60, 250))
    assert strength > 0.8


def test_bourdon_strength_low_for_noise():
    sr = 44100.0
    y = np.random.default_rng(5).standard_normal(int(sr * 2))
    S, freqs, _ = timbre.stft_mag(y, sr)
    strength = timbre.bourdon_strength(S, freqs, (60, 250))
    assert strength < 0.5


def test_bourdon_strength_empty_band_is_zero():
    sr = 44100.0
    y = _sine(440.0, sr, dur=1.0)
    S, freqs, _ = timbre.stft_mag(y, sr)
    assert freqs.max() <= 22050.0
    assert timbre.bourdon_strength(S, freqs, (30000, 40000)) == 0.0   # au-delà de Nyquist -> bande vide


def test_harmonic_partials_recovers_series():
    sr = 44100.0
    f0 = 220.0
    n = int(sr * 2.0)
    t = np.arange(n) / sr
    y = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 6))
    S, freqs, _ = timbre.stft_mag(y, sr, n_fft=16384)   # bonne résolution même au rang 1 (220 Hz)
    partials = timbre.harmonic_partials(S, freqs, f0, n_partials=5)
    for p in partials:
        assert abs(p['cents']) < 30.0


def test_harmonic_partials_nan_outside_window():
    sr = 44100.0
    y = _sine(220.0, sr, dur=1.0)                     # pas d'harmonique 7 dans un sinus pur
    S, freqs, _ = timbre.stft_mag(y, sr, n_fft=4096)
    partials = timbre.harmonic_partials(S, freqs, 220.0, n_partials=8, tol_cents=5.0, min_rel_mag=0.05)
    assert np.isnan(partials[6]['cents'])             # rang 7 (index 6) : rien de significatif, juste la fuite spectrale
