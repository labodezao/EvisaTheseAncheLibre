import numpy as np

from banc_recherche.impedance import compute


def test_impedance_basic():
    p = np.full(100, 900.0)      # Pa
    q = np.full(100, 3.0)        # slm cohérents
    r = compute(p, q)
    assert abs(r.impedance - 300.0) < 1e-9
    assert abs(r.pui_hydro - 2700.0) < 1e-9
    assert abs(r.p_mean - 900.0) < 1e-9
    assert abs(r.q_mean - 3.0) < 1e-9


def test_impedance_handles_noise():
    rng = np.random.default_rng(0)
    p = 900.0 + rng.normal(0, 1, 5000)
    q = 3.0 + rng.normal(0, 0.01, 5000)
    r = compute(p, q)
    assert abs(r.impedance - 300.0) < 5.0
