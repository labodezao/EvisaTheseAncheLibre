import numpy as np

from banc_recherche import modal, phase_space, frf, reed_model, material


# ---- Analyse modale (multi-tronçon) ----------------------------------------
def test_modal_single_section_matches_material():
    # Un seul tronçon uniforme → doit retrouver les fréquences d'Euler-Bernoulli
    # (identiques à material.resonance_frequency).
    L, rho, b, h, E = 0.020, 7800.0, 0.005, 0.0005, 2.1e11
    sec = [[L, rho, b, h, E]]
    f = modal.natural_frequencies_np(sec, n_modes=3)
    for mode in (1, 2, 3):
        f_ref = material.resonance_frequency(E, L, h, rho, mode)
        assert abs(f[mode - 1] - f_ref) / f_ref < 0.02


def test_modal_increases_with_mode():
    f = modal.natural_frequencies_np(reed_model.SECTIONS_DEFAULT, n_modes=2)
    assert f[1] > f[0] > 0


# ---- Espace des phases (double intégration accéléromètre) ------------------
def test_phase_space_from_acceleration():
    fs = 4000.0
    f0 = 200.0
    t = np.arange(int(1.0 * fs)) / fs
    x0 = 1e-3
    x = x0 * np.sin(2 * np.pi * f0 * t)
    a = -(2 * np.pi * f0) ** 2 * x               # accélération de x(t)
    ps = phase_space.from_acceleration(a, fs, hp_hz=20)
    # amplitudes retrouvées (loin des bords)
    assert abs(np.max(np.abs(ps.position[200:-200])) - x0) / x0 < 0.05
    assert abs(np.max(np.abs(ps.velocity[200:-200])) - 2 * np.pi * f0 * x0) / (2 * np.pi * f0 * x0) < 0.05


def test_delay_embedding_shape():
    x = np.sin(np.linspace(0, 50, 1000))
    emb = phase_space.delay_embedding(x, delay=5, dim=3)
    assert emb.shape[1] == 3 and emb.shape[0] == 1000 - 2 * 5


# ---- FRF swept-sine (Farina) -----------------------------------------------
def test_sweep_selfdeconvolves_to_impulse():
    # Convoluer le balayage par son filtre inverse → impulsion nette à la fin.
    fs = 8000.0
    sw = frf.exponential_sweep(50, 2000, 1.0, fs)
    ir = frf.impulse_response(sw.x / 0.5, sw)     # système = gain unité
    peak = int(np.argmax(np.abs(ir)))
    # le pic est proche de la fin du balayage
    assert abs(peak - (len(sw.x) - 1)) < 0.02 * fs
    # et c'est un vrai pic (net devant le reste)
    assert np.abs(ir[peak]) > 10 * np.median(np.abs(ir))


# ---- Modèle non linéaire (RK4) ---------------------------------------------
def test_reed_free_oscillation_at_natural_frequency():
    # Sans débit : oscillation libre au voisinage de la 1re fréquence propre.
    rm = reed_model.ReedModel(n_modes=2, zeta=0.0)
    f0 = modal.natural_frequencies_np(rm.sec, n_modes=2)[0]
    fs = max(20000.0, 8 * f0)
    res = rm.simulate(dur=0.05, fs=fs, q_in=0.0, q0=[1e-4, 0.0])
    x = res.position - res.position.mean()
    X = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    fr = np.fft.rfftfreq(x.size, 1 / fs)
    fpk = fr[np.argmax(X)]
    assert abs(fpk - f0) / f0 < 0.1
    assert np.all(np.isfinite(res.position))


def test_reed_simulation_bounded():
    rm = reed_model.ReedModel(n_modes=2)
    res = rm.simulate(dur=0.02, fs=20000.0, q_in=3e-5)
    assert np.all(np.isfinite(res.position))
    assert np.max(np.abs(res.position)) < 1.0     # reste physique (borné)
