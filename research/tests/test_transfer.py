import numpy as np

from banc_recherche.transfer import reflection_impedance, C_AIR


def test_recovers_known_reflection():
    # Coefficient de réflexion imposé → construit H12 → doit être retrouvé.
    f = np.linspace(100, 3000, 50)
    s, x1 = 0.03, 0.10
    R0 = 0.4 + 0.2j
    k = 2 * np.pi * f / C_AIR
    H_I = np.exp(-1j * k * s)
    H_R = np.exp(1j * k * s)
    A = R0 * np.exp(-2j * k * x1)
    H12 = (H_I + A * H_R) / (1 + A)
    R, Z, alpha = reflection_impedance(f, H12, s, x1)
    assert np.allclose(R, R0, atol=1e-9)
    assert np.allclose(alpha, 1 - abs(R0) ** 2, atol=1e-9)


def test_rigid_wall_full_reflection():
    f = np.linspace(100, 3000, 20)
    s, x1 = 0.03, 0.10
    R0 = 1.0 + 0j                     # paroi rigide : α ≈ 0
    k = 2 * np.pi * f / C_AIR
    H_I, H_R = np.exp(-1j * k * s), np.exp(1j * k * s)
    A = R0 * np.exp(-2j * k * x1)
    H12 = (H_I + A * H_R) / (1 + A)
    _, _, alpha = reflection_impedance(f, H12, s, x1)
    assert np.allclose(alpha, 0.0, atol=1e-9)
