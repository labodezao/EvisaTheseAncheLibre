import numpy as np

from banc_recherche.seuil import detect


def test_hysteresis_detection():
    # Rampe montante 0→1000 puis descendante 1000→0.
    up = np.linspace(0, 1000, 500)
    dn = np.linspace(1000, 0, 500)
    pressure = np.concatenate([up, dn])
    # L'anche démarre à 600 Pa (montée) et s'éteint à 400 Pa (descente) : hystérésis.
    amp = np.concatenate([
        (up > 600).astype(float),
        (dn > 400).astype(float),
    ])
    r = detect(pressure, amp, amp_thresh=0.5)
    assert 580 < r.p_on < 620
    assert 380 < r.p_off < 420
    assert r.hysteresis > 0            # p_on > p_off


def test_no_oscillation_gives_nan():
    pressure = np.concatenate([np.linspace(0, 100, 100), np.linspace(100, 0, 100)])
    amp = np.zeros(200)
    r = detect(pressure, amp, amp_thresh=0.5)
    assert np.isnan(r.p_on)
