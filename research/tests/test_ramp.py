import numpy as np
import pytest

from banc_recherche import ramp


def test_amplitude_vs_param_alignment():
    fs = 8000.0
    t = np.arange(int(2 * fs)) / fs
    env = np.clip((t - 0.5) / 1.0, 0, 1)          # amplitude croît de 0.5 s à 1.5 s
    sig = env * np.sin(2 * np.pi * 200 * t)
    param_t = np.linspace(0, 2, 40)                # pression échantillonnée à 20 Hz
    param_v = 300 + 600 * param_t / 2              # pression croissante
    pv, amp = ramp.amplitude_vs_param(sig, fs, param_t, param_v)
    assert pv.size == amp.size == 40
    # l'amplitude alignée croît globalement avec la pression
    assert amp[-1] > amp[0]


def test_sweep_requires_link():
    from banc_recherche.config import Config
    with pytest.raises(ValueError):
        ramp.run_threshold_sweep(Config(), None)
