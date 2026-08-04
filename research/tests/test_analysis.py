import numpy as np

from banc_recherche.analysis import envelope, attack


def _tone_with_attack(sr=48000, dur=1.0, onset=0.2, rise=0.05, f=440.0):
    t = np.arange(int(dur * sr)) / sr
    tone = np.sin(2 * np.pi * f * t)
    env = np.clip((t - onset) / rise, 0.0, 1.0)   # rampe linéaire après l'onset
    return tone * env


def test_envelope_tracks_amplitude():
    sr = 48000
    sig = _tone_with_attack(sr=sr)
    env = envelope(sig, sr)
    assert env[:int(0.15 * sr)].mean() < 0.05      # silence avant onset
    assert env[int(0.6 * sr):].mean() > 0.5        # établi ensuite


def test_attack_tresp_positive():
    sr = 48000
    sig = _tone_with_attack(sr=sr, onset=0.2, rise=0.05)
    r = attack(sig, sr)
    assert r.onset_s > 0.15 and r.onset_s < 0.25
    assert 0 < r.tresp_ms < 100          # montée de l'ordre de la dizaine de ms
    assert r.steady_amp > 0.3
