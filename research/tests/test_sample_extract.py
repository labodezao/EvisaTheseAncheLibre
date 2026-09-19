import numpy as np

from banc_recherche import sample_extract as sx
from banc_recherche import synth_export as se


SR = 22050.0


def _tone(f0, dur=1.5, sr=SR, partials=(1.0,), fm_rate=0.0, fm_cents=0.0):
    """Son harmonique synthétique, vibrato optionnel."""
    t = np.arange(int(dur * sr)) / sr
    if fm_rate > 0:
        # modulation de hauteur en cents -> phase intégrée
        dev = (fm_cents / 1200.0) * np.sin(2 * np.pi * fm_rate * t)
        phase = 2 * np.pi * f0 * np.cumsum(2 ** dev) / sr
    else:
        phase = 2 * np.pi * f0 * t
    y = np.zeros_like(t)
    for k, amp in enumerate(partials, start=1):
        y += amp * np.sin(k * phase)
    return y / (np.max(np.abs(y)) or 1.0)


# ---- hauteur ---------------------------------------------------------------

def test_detect_f0_recovers_sine():
    y = _tone(220.0)
    f0, times = sx.detect_f0(y, SR)
    good = f0[np.isfinite(f0)]
    assert good.size > 10
    assert abs(np.median(good) - 220.0) < 2.0


def test_detect_f0_nan_on_silence():
    y = np.zeros(int(SR))
    f0, _ = sx.detect_f0(y, SR)
    assert np.all(~np.isfinite(f0))


def test_vibrato_recovers_rate_and_depth():
    y = _tone(330.0, dur=3.0, fm_rate=5.0, fm_cents=50.0)
    f0, times = sx.detect_f0(y, SR)
    vib = sx.vibrato(f0, times)
    assert abs(vib['f0_median_hz'] - 330.0) < 5.0
    assert abs(vib['rate_hz'] - 5.0) < 1.0
    assert 20.0 < vib['depth_cents'] < 120.0     # ordre de grandeur des 50 cents crête


def test_vibrato_absent_on_steady_tone():
    y = _tone(440.0, dur=2.0)
    f0, times = sx.detect_f0(y, SR)
    assert sx.vibrato(f0, times)['depth_cents'] < 10.0


# ---- partiels --------------------------------------------------------------

def test_partial_envelopes_recovers_relative_levels():
    y = _tone(200.0, dur=2.0, partials=(1.0, 0.5, 0.25))
    amps, times = sx.partial_envelopes(y, SR, 200.0, n_partials=3)
    means = amps.mean(axis=1)
    assert means[0] > means[1] > means[2] > 0
    assert abs(means[1] / means[0] - 0.5) < 0.15
    assert abs(means[2] / means[0] - 0.25) < 0.15


def test_attack_times_orders_partials():
    sr = SR
    t = np.arange(int(2.0 * sr)) / sr
    # fondamental tout de suite, harmonique 2 qui n'entre qu'à 1 s
    y = np.sin(2 * np.pi * 200 * t)
    y[t >= 1.0] += np.sin(2 * np.pi * 400 * t[t >= 1.0])
    amps, times = sx.partial_envelopes(y, sr, 200.0, n_partials=2)
    at = sx.attack_times(amps, times)
    assert at[0] < 0.5
    assert at[1] > 0.9


# ---- enveloppes ------------------------------------------------------------

def test_compress_envelope_keeps_endpoints_and_limit():
    t = np.linspace(0, 1, 500)
    env = np.sin(2 * np.pi * 3 * t) ** 2
    bp = sx.compress_envelope(t, env, max_points=6)
    assert len(bp) <= 6
    assert bp[0][0] == 0.0
    assert abs(bp[-1][0] - 1.0) < 1e-9


def test_compress_envelope_ramp_is_two_points():
    t = np.linspace(0, 1, 200)
    bp = sx.compress_envelope(t, t, max_points=8)
    assert len(bp) == 2                     # une droite ne demande que ses extrémités


def test_adsr_on_synthetic_envelope():
    sr = 100.0
    t = np.arange(0, 3, 1 / sr)
    env = np.piecewise(
        t, [t < 0.2, (t >= 0.2) & (t < 0.6), (t >= 0.6) & (t < 2.5), t >= 2.5],
        [lambda x: x / 0.2,
         lambda x: 1 - 0.5 * (x - 0.2) / 0.4,
         lambda x: 0.5,
         lambda x: 0.5 * np.maximum(0.0, 1 - (x - 2.5) / 0.5)])
    a = sx.adsr_from_envelope(t, env)
    assert abs(a['attack_s'] - 0.2) < 0.05
    assert abs(a['sustain_level'] - 0.5) < 0.1
    assert a['release_s'] > 0.1


# ---- résonateur & source ---------------------------------------------------

def _formant_tone(f0, f_res, q_res, n_partials=24, dur=1.5, sr=SR):
    """Son harmonique dont les partiels suivent une résonance centrée sur
    `f_res` : les raies sont à n·f0, l'enveloppe culmine à f_res."""
    t = np.arange(int(dur * sr)) / sr
    y = np.zeros_like(t)
    for n in range(1, n_partials + 1):
        f = n * f0
        if f >= sr / 2 * 0.9:
            break
        r = f / f_res
        amp = 1.0 / np.sqrt((1 - r ** 2) ** 2 + (r / q_res) ** 2)
        y += amp * np.sin(2 * np.pi * f * t)
    return y / (np.max(np.abs(y)) or 1.0)


def test_spectral_envelope_removes_harmonic_comb():
    """L'enveloppe cepstrale doit gommer le peigne : son ondulation doit être
    bien plus faible que celle du spectre brut."""
    from banc_recherche import timbre
    y = _formant_tone(220.0, 1500.0, 3.0)
    S, freqs, _ = timbre.stft_mag(y, SR, n_fft=4096)
    raw = S.mean(axis=1)
    env = sx.spectral_envelope(S, freqs, f0_hz=220.0)

    band = (freqs > 300) & (freqs < 4000)
    ripple_raw = np.std(np.log(np.maximum(raw[band], raw.max() * 1e-8)))
    ripple_env = np.std(np.log(np.maximum(env[band], env.max() * 1e-8)))
    assert ripple_env < ripple_raw / 2


def test_resonator_peaks_find_body_not_partials():
    """Le pic dominant doit être la résonance (1500 Hz), pas le fondamental
    ni un harmonique — c'est tout l'intérêt d'un résonateur : il ne bouge pas
    avec la note."""
    from banc_recherche import timbre
    f0, f_res = 220.0, 1500.0
    y = _formant_tone(f0, f_res, 3.0)
    S, freqs, _ = timbre.stft_mag(y, SR, n_fft=4096)
    peaks = sx.resonator_peaks(S, freqs, n_peaks=4, f0_hz=f0)
    assert peaks
    best = max(peaks, key=lambda p: p['gain_db'])
    assert abs(best['freq_hz'] - f_res) < 250.0
    assert abs(best['freq_hz'] - f0) > 500.0


def test_resonator_invariant_across_notes():
    """Deux notes différentes jouées dans le même corps doivent donner la même
    résonance (à la tolérance près) — sinon ce n'est pas un résonateur."""
    from banc_recherche import timbre
    f_res = 1200.0
    found = []
    for f0 in (196.0, 330.0):
        y = _formant_tone(f0, f_res, 3.0)
        S, freqs, _ = timbre.stft_mag(y, SR, n_fft=4096)
        peaks = sx.resonator_peaks(S, freqs, n_peaks=4, f0_hz=f0)
        assert peaks
        found.append(max(peaks, key=lambda p: p['gain_db'])['freq_hz'])
    assert abs(found[0] - found[1]) < 250.0


def test_adsr_attack_small_on_steady_tone():
    """Un son tenu n'a pas une attaque de plusieurs secondes."""
    t = np.linspace(0, 3, 600)
    env = np.ones_like(t)
    env[:20] = np.linspace(0, 1, 20)
    assert sx.adsr_from_envelope(t, env)['attack_s'] < 0.3


def test_resonator_peaks_finds_known_resonance():
    from scipy import signal
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(int(SR * 2))
    b, a = signal.iirpeak(800.0 / (SR / 2), Q=12.0)
    y = signal.lfilter(b, a, noise)
    from banc_recherche import timbre
    S, freqs, _ = timbre.stft_mag(y, SR, n_fft=4096)
    peaks = sx.resonator_peaks(S, freqs, n_peaks=3)
    assert peaks
    assert min(abs(p['freq_hz'] - 800.0) for p in peaks) < 60.0


def test_source_slope_negative_for_decaying_spectrum():
    # spectre en 1/n (dent de scie) : exactement -6,02 dB par octave de rang
    y = _tone(200.0, dur=1.5, partials=tuple(1.0 / n for n in range(1, 7)))
    amps, _ = sx.partial_envelopes(y, SR, 200.0, n_partials=6)
    slope = sx.source_slope(amps)
    assert slope < 0                        # spectre décroissant = pente négative
    assert abs(slope - (-6.02)) < 1.5


# ---- modèle complet --------------------------------------------------------

def test_extract_end_to_end():
    y = _tone(220.0, dur=2.0, partials=(1.0, 0.5, 0.3))
    m = sx.extract(y, SR, name="test", n_partials=6)
    assert abs(m.f0_hz - 220.0) < 3.0
    assert m.samplerate == int(SR)
    assert len(m.partial_levels_db) == 6
    assert len(m.partial_envelopes) == 6
    assert m.partial_levels_db[0] == 0.0 or abs(m.partial_levels_db[0]) < 1e-6
    assert m.partial_levels_db[1] < 0      # harmonique 2 plus faible que le fondamental
    assert m.duration_s > 1.9


def test_extract_gives_up_cleanly_on_noise_without_pitch():
    y = np.zeros(int(SR))
    m = sx.extract(y, SR, name="silence")
    assert not np.isfinite(m.f0_hz)
    assert m.n_partials == 0               # on n'invente pas de partiels


# ---- export ----------------------------------------------------------------

def test_biquad_unity_when_no_gain():
    bq = se.biquad_peaking(1000.0, 2.0, 0.0, SR)
    assert abs(bq['b0'] - 1.0) < 1e-9
    assert abs(bq['b1'] - bq['a1']) < 1e-9
    assert abs(bq['b2'] - bq['a2']) < 1e-9


def test_biquad_boosts_at_center_frequency():
    from scipy import signal
    bq = se.biquad_peaking(1000.0, 4.0, 12.0, SR)
    b = [bq['b0'], bq['b1'], bq['b2']]
    a = [1.0, bq['a1'], bq['a2']]
    w, h = signal.freqz(b, a, worN=[2 * np.pi * 1000.0 / SR])
    gain_db = 20 * np.log10(abs(h[0]))
    assert abs(gain_db - 12.0) < 0.5


def test_to_q15_saturates():
    assert se.to_q15(0.0) == 0
    assert se.to_q15(1.0) == 32767
    assert se.to_q15(5.0) == 32767
    assert se.to_q15(-5.0) == -32768


def test_json_roundtrip():
    import json
    y = _tone(220.0, dur=1.0, partials=(1.0, 0.4))
    m = sx.extract(y, SR, name="json", n_partials=4)
    data = json.loads(se.to_json(m))
    assert data['_format'].startswith('banc_recherche.sample_model')
    assert abs(data['f0_hz'] - 220.0) < 3.0


def test_c_header_has_guard_and_tables():
    y = _tone(220.0, dur=1.0, partials=(1.0, 0.4))
    m = sx.extract(y, SR, name="Anche Basse", n_partials=4)
    src = se.to_c_header(m, fixed_point=True)
    assert "#ifndef ANCHE_BASSE_MODEL_H" in src
    assert "#endif" in src
    assert "biquad_f32_t" in src and "biquad_q15_t" in src
    assert "anche_basse_partial_db" in src
    assert "nan" not in src.lower()          # aucun nan ne doit fuir dans du C


def test_c_header_survives_model_without_pitch():
    m = sx.extract(np.zeros(int(SR)), SR, name="vide")
    src = se.to_c_header(m)
    assert "#ifndef VIDE_MODEL_H" in src
    assert "nan" not in src.lower()


def test_wavetable_shape_and_normalisation():
    y = _tone(220.0, dur=1.0, partials=(1.0, 0.5, 0.25))
    m = sx.extract(y, SR, name="wt", n_partials=6)
    wave = se.to_wavetable(m, table_size=128)
    assert wave.shape == (128,)
    assert abs(np.max(np.abs(wave)) - 1.0) < 1e-6
    assert se.wavetable_to_c(wave, "wt").count(",") > 100


def test_dream_adapter_refuses_to_invent_protocol():
    import pytest
    m = sx.extract(_tone(220.0, dur=0.5), SR, name="dream")
    with pytest.raises(NotImplementedError):
        se.DreamAdapter(m).to_sysex()
