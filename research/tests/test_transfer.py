import numpy as np

from banc_recherche.transfer import (
    reflection_impedance, decompose, transfer_matrix_two_load, tl_from_matrix, C_AIR,
)


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


# ---- Méthode 4 microphones -------------------------------------------------
def test_wave_decomposition_roundtrip():
    xa, xb = -0.10, -0.07          # deux micros amont
    f = np.linspace(200, 3000, 40)
    k = 2 * np.pi * f / C_AIR
    A0, B0 = 1.0 + 0j, 0.3 - 0.2j
    pa = A0 * np.exp(-1j * k * xa) + B0 * np.exp(1j * k * xa)
    pb = A0 * np.exp(-1j * k * xb) + B0 * np.exp(1j * k * xb)
    A, B = decompose(pa, pb, xa, xb, k)
    assert np.allclose(A, A0, atol=1e-9)
    assert np.allclose(B, B0, atol=1e-9)


def test_transfer_matrix_two_load_roundtrip():
    T11, T12, T21, T22 = 1.2 + 0.1j, 300 + 50j, 1e-4j, 0.9 - 0.05j
    # deux terminaisons aval distinctes
    pda, uda = 1.0 + 0j, 0.002 + 0j
    pdb, udb = 1.0 + 0j, -0.001 + 0.0005j
    pua = T11 * pda + T12 * uda; uua = T21 * pda + T22 * uda
    pub = T11 * pdb + T12 * udb; uub = T21 * pdb + T22 * udb
    R = transfer_matrix_two_load((pua, uua, pda, uda), (pub, uub, pdb, udb))
    assert np.allclose(R, (T11, T12, T21, T22), atol=1e-9)


def test_tl_identity_is_zero():
    # Matrice identité = pas d'échantillon → TL ≈ 0 dB.
    tl = tl_from_matrix(1.0, 0.0, 0.0, 1.0)
    assert abs(tl) < 1e-6
