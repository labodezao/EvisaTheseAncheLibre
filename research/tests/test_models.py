import pytest
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
    # f0 = 15,59 Hz (vraie lame en tronçons, corrigé le 22/11/2026 ; 102,1 Hz avant) :
    # fenêtre de 2 s -> résolution 0,5 Hz (1 Hz au moins), ~31 périodes.
    res = rm.simulate(dur=2.0, fs=fs, q_in=0.0, q0=[1e-4, 0.0])
    x = res.position - res.position.mean()
    X = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    fr = np.fft.rfftfreq(x.size, 1 / fs)
    fpk = fr[np.argmax(X)]
    assert fr[1] - fr[0] <= 1.0
    assert f0 == pytest.approx(15.59, abs=0.05)
    assert abs(fpk - f0) / f0 < 0.05
    assert np.all(np.isfinite(res.position))


def test_reed_simulation_bounded():
    rm = reed_model.ReedModel(n_modes=2)
    res = rm.simulate(dur=0.02, fs=20000.0, q_in=3e-5)
    assert np.all(np.isfinite(res.position))
    # Lame par défaut à 15,59 Hz (charnière 45 µm), 43 fois plus souple en raideur
    # modale que l'ancienne base fausse (102,1 Hz) : la position max passe de 0,115 à
    # 1,082 à forçage égal (pression de cavité jusqu'à 6,6 bar, aucune butée dans le
    # modèle). Ce n'est pas numérique : fs x4 donne 1,0819 contre 1,0820. Borne = « pas de
    # divergence » (1,72 sur 1 s, plateau), pas une amplitude physique.
    assert np.max(np.abs(res.position)) < 2.0
    res4 = rm.simulate(dur=0.02, fs=80000.0, q_in=3e-5)
    assert np.max(np.abs(res4.position)) == pytest.approx(np.max(np.abs(res.position)), rel=1e-2)
