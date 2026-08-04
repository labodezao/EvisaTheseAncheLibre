import numpy as np

from banc_recherche import leak


def test_recovers_time_constant():
    tau0, p0 = 12.0, 900.0
    t = np.linspace(0, 30, 300)
    p = p0 * np.exp(-t / tau0)
    r = leak.fit_decay(t, p)
    assert abs(r.tau - tau0) / tau0 < 1e-6
    assert abs(r.p0 - p0) / p0 < 1e-6
    assert abs(r.half_life - tau0 * np.log(2)) < 1e-6


def test_conductance_with_volume():
    tau0, p0, vol = 20.0, 800.0, 5e-4
    t = np.linspace(0, 40, 200)
    p = p0 * np.exp(-t / tau0)
    r = leak.fit_decay(t, p, volume_m3=vol)
    assert abs(r.conductance - vol / tau0) / (vol / tau0) < 1e-6


def test_no_leak_gives_inf_tau():
    t = np.linspace(0, 30, 100)
    p = np.full_like(t, 900.0)          # pression constante = pas de fuite
    r = leak.fit_decay(t, p)
    assert not np.isfinite(r.tau)
