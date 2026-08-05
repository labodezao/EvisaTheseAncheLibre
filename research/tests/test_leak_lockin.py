import numpy as np

from banc_recherche import leak


def test_lockin_extracts_component():
    fs = 2000.0
    t = np.arange(int(4 * fs)) / fs
    f = 5.0
    sig = 0.7 * np.cos(2 * np.pi * f * t) + 3.0 * np.random.default_rng(0).standard_normal(t.size)
    r, _ = leak.lockin(sig, fs, f)
    assert abs(r - 0.7) < 0.1                 # amplitude retrouvée malgré le bruit


def test_lockin_rejects_offband():
    fs = 2000.0
    t = np.arange(int(4 * fs)) / fs
    sig = np.cos(2 * np.pi * 5 * t)
    r_on, _ = leak.lockin(sig, fs, 5.0)
    r_off, _ = leak.lockin(sig, fs, 12.0)     # composante absente à 12 Hz
    assert r_on > 20 * r_off


def _leak_recording(fs, dur, f_mod, hiss_amp, seed=0):
    """Micro : sifflement large bande (bande haute) dont l'amplitude clignote à
    f_mod, + fort bruit ambiant non modulé (basse fréquence)."""
    rng = np.random.default_rng(seed)
    n = int(dur * fs)
    t = np.arange(n) / fs
    hiss = rng.standard_normal(n)
    hiss = leak._bandpass(hiss, fs, 4000, min(9000, fs / 2 * 0.95))
    mod = 0.5 * (1 + np.cos(2 * np.pi * f_mod * t))      # clignote à f_mod
    ambient = 5.0 * leak._bandpass(rng.standard_normal(n), fs, 50, 500)
    return hiss_amp * mod * hiss + ambient


def test_acoustic_leak_strength_discriminates():
    fs = 44100.0
    f_mod = 6.0
    leaky = _leak_recording(fs, 2.0, f_mod, hiss_amp=1.0, seed=1)
    sealed = _leak_recording(fs, 2.0, f_mod, hiss_amp=0.0, seed=2)   # pas de fuite
    s_leak = leak.acoustic_leak_strength(leaky, fs, f_mod)
    s_seal = leak.acoustic_leak_strength(sealed, fs, f_mod)
    assert s_leak > 5 * s_seal                # la fuite ressort malgré le bruit ambiant


def test_leak_map_ranks_leak_first():
    fs = 44100.0
    f_mod = 6.0
    recs = [
        ("bord soufflet", _leak_recording(fs, 1.5, f_mod, 0.0, seed=3)),
        ("soupape #12", _leak_recording(fs, 1.5, f_mod, 1.2, seed=4)),   # la fuite
        ("cire anche", _leak_recording(fs, 1.5, f_mod, 0.1, seed=5)),
    ]
    ranked = leak.leak_map(recs, fs, f_mod)
    assert ranked[0][0] == "soupape #12"


def test_tdoa_sign():
    fs = 48000.0
    rng = np.random.default_rng(0)
    base = leak._bandpass(rng.standard_normal(20000), fs, 3000, 8000)
    shift = 15
    mic1 = base
    mic2 = np.roll(base, shift)                # mic2 décalé de 15 échantillons
    d = leak.tdoa_delay(mic1, mic2, fs)
    # le retard est détecté (le signe = convention, il indique le côté)
    assert abs(abs(d) - shift / fs) < 2 / fs
