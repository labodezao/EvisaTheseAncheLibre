import numpy as np

from banc_recherche import ringdown


def _decaying(f=200.0, alpha=5.0, fs=8000.0, dur=2.0):
    t = np.arange(int(dur * fs)) / fs
    return np.exp(-alpha * t) * np.sin(2 * np.pi * f * t), fs


def test_recovers_frequency_and_damping():
    sig, fs = _decaying(f=200.0, alpha=5.0)
    r = ringdown.estimate(sig, fs)
    assert abs(r.freq_hz - 200.0) < 2.0
    assert abs(r.alpha - 5.0) / 5.0 < 0.15          # ±15 %
    q_expected = np.pi * 200.0 / 5.0                # Q = ω0/(2α) = πf/α
    assert abs(r.q - q_expected) / q_expected < 0.2


def test_envelope_is_monotone_after_peak():
    sig, fs = _decaying()
    env = ringdown.analytic_envelope(sig)
    peak = int(np.argmax(env))
    tail = env[peak + 100:]
    # tendance décroissante : la moyenne de la 1re moitié > 2e moitié
    assert tail[:len(tail)//2].mean() > tail[len(tail)//2:].mean()
