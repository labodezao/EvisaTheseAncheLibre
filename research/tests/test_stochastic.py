import numpy as np

from banc_recherche import stochastic as st


def _ou(theta, D2, dt, n, seed=0):
    """Ornstein-Uhlenbeck : dx = −θ x dt + √(2 D₂) dW → drift −θx, diffusion D₂."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    s = np.sqrt(2 * D2 * dt)
    for i in range(1, n):
        x[i] = x[i - 1] - theta * x[i - 1] * dt + s * rng.standard_normal()
    return x


def test_kramers_moyal_recovers_ou():
    dt = 0.01
    x = _ou(theta=2.0, D2=0.5, dt=dt, n=200000)
    km = st.kramers_moyal(x, dt, bins=21)
    good = km.counts > 50
    # drift D1(x) ≈ −θ x : pente ≈ −2
    slope = np.polyfit(km.x[good], km.drift[good], 1)[0]
    assert abs(slope + 2.0) < 0.4
    # diffusion D2 ≈ 0.5 (constante)
    assert abs(np.nanmean(km.diffusion[good]) - 0.5) < 0.1


def test_potential_double_well_has_two_minima():
    # Drift bistable D1 = x − x³ (potentiel double puits ±1), D2 constant.
    x = np.linspace(-2, 2, 200)
    km = st.KramersMoyal(x, x - x ** 3, np.full_like(x, 0.2), np.full(200, 100, int))
    xx, phi = st.potential_from_drift(km)
    mins = st.potential_minima(xx, phi)
    centers = xx[mins]
    assert len(mins) == 2
    assert np.any(centers < -0.5) and np.any(centers > 0.5)


def test_early_warning_critical_slowing_down():
    # En approchant le seuil, θ → 0 : variance et AR(1) augmentent.
    dt = 0.01
    thetas = [4.0, 2.0, 1.0, 0.5, 0.25]
    series = [_ou(th, 0.5, dt, 20000, seed=i) for i, th in enumerate(thetas)]
    ew = st.early_warning(range(len(thetas)), series)
    assert st.kendall_tau(ew.param, ew.variance) > 0.5      # variance croît
    assert st.kendall_tau(ew.param, ew.autocorr1) > 0.5     # autocorr croît


def test_threshold_stats():
    ts = st.threshold_stats([6.1, 5.9, 6.0, 6.2], [4.1, 3.9, 4.0, 4.0])
    assert abs(ts.mu_on_mean - 6.05) < 0.1
    assert abs(ts.hysteresis_mean - 2.05) < 0.1
    assert ts.mu_on_std > 0
