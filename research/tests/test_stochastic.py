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


# ---- Stuart-Landau (coefficient de Landau complexe) ------------------------
def test_stuart_landau_recovers_coefficients():
    mu0, w0, a0, b0 = 0.5, 2 * np.pi * 20, 1.0, 0.3
    dt, n = 1e-4, 40000
    z = np.zeros(n, dtype="complex128")
    z[0] = 0.01 + 0j
    for i in range(1, n):
        zi = z[i - 1]
        z[i] = zi + dt * ((mu0 + 1j * w0) * zi - (a0 + 1j * b0) * abs(zi) ** 2 * zi)
    sl = st.fit_complex_amplitude(z, dt)
    assert abs(sl.mu - mu0) < 0.02
    assert abs(sl.omega - w0) / w0 < 0.01
    assert abs(sl.a - a0) < 0.05
    assert abs(sl.b - b0) < 0.05
    assert abs(sl.r_limit - np.sqrt(mu0 / a0)) < 0.02


def test_analytic_signal_of_sine():
    fs = 2000.0
    t = np.arange(4000) / fs
    z = st.analytic_signal(np.sin(2 * np.pi * 50 * t))
    # amplitude ≈ 1 loin des bords
    assert abs(np.median(np.abs(z)[200:-200]) - 1.0) < 0.05


# ---- Résonance cohérente ---------------------------------------------------
def test_spectral_coherence_pure_vs_noisy():
    fs = 2000.0
    t = np.arange(8000) / fs
    rng = np.random.default_rng(0)
    pure = np.sin(2 * np.pi * 60 * t)
    noisy = pure + 3.0 * rng.standard_normal(t.size)
    assert st.coherence_measure(pure, fs) > st.coherence_measure(noisy, fs)


def test_coherence_resonance_picks_max():
    fs = 2000.0
    t = np.arange(6000) / fs
    rng = np.random.default_rng(1)
    base = np.sin(2 * np.pi * 50 * t)
    # cohérence maximale au niveau intermédiaire (index 1)
    series = [base + 5 * rng.standard_normal(t.size),      # très bruité
              base + 0.2 * rng.standard_normal(t.size),    # propre
              base + 8 * rng.standard_normal(t.size)]      # très bruité
    cr = st.coherence_resonance([0.1, 0.5, 1.0], series, fs)
    assert cr.optimal_noise == 0.5


# ---- Temps de résidence / Kramers ------------------------------------------
def test_residence_times():
    state = [0, 0, 1, 1, 1, 0, 0, 0, 1]
    r = st.residence_times(state, dt=1.0)
    assert r[0] == [2.0, 3.0]
    assert r[1] == [3.0, 1.0]


def test_kramers_rate_double_well():
    # U = −x²/2 + x⁴/4 : ΔU = 1/4, U''(min)=2, |U''(barrière)|=1.
    x = np.linspace(-2, 2, 400)
    phi = -x ** 2 / 2 + x ** 4 / 4
    phi = phi - phi.min()
    D = 0.1
    r = st.kramers_from_potential(x, phi, D)
    expected = (np.sqrt(2 * 1) / (2 * np.pi)) * np.exp(-0.25 / D)
    assert abs(r - expected) / expected < 0.1
