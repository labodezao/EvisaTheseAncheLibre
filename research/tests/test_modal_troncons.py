"""`modal.assemble` sur une lame à tronçons : fréquences contre l'équation transcendante exacte
de la poutre encastrée-libre à deux tronçons (indépendante du code testé).

Cause de l'ancienne erreur (22/11/2026) : la base de modes du cantilever UNIFORME (Rayleigh-
Ritz) converge mal quand la raideur saute (+153 % avec 1 mode, +3 à +11 % avec 6)."""
import numpy as np
import pytest

from banc_recherche import modal

E, RHO, B, L = 100e9, 8500.0, 3e-3, 24e-3


def _secs(a_mm, t1_mm, t2_mm=0.8):
    return [[a_mm * 1e-3, RHO, B, t1_mm * 1e-3, E], [L - a_mm * 1e-3, RHO, B, t2_mm * 1e-3, E]]


def _exact(sec, n_roots=2):
    """Racines de det = 0 (continuité de flèche, pente, moment, effort tranchant au saut ;
    encastré en 0, libre en L) : plus petite valeur singulière du système 8x8."""
    (l1, r1, b1, t1, e1), (l2, r2, b2, t2, e2) = sec
    EI1, EI2 = e1 * b1 * t1 ** 3 / 12, e2 * b2 * t2 ** 3 / 12
    m1, m2 = r1 * b1 * t1, r2 * b2 * t2

    def base(k, x):
        c, s, ch, sh = np.cos(k * x), np.sin(k * x), np.cosh(k * x), np.sinh(k * x)
        return np.array([[c, s, ch, sh], [-k * s, k * c, k * sh, k * ch],
                         [-k * k * c, -k * k * s, k * k * ch, k * k * sh],
                         [k ** 3 * s, -k ** 3 * c, k ** 3 * sh, k ** 3 * ch]])

    def sv(f):
        w = 2 * np.pi * f
        k1, k2 = (m1 * w * w / EI1) ** .25, (m2 * w * w / EI2) ** .25
        A0, B1, C0, C1 = base(k1, 0.0), base(k1, l1), base(k2, 0.0), base(k2, l2)
        Mx = np.zeros((8, 8))
        Mx[0:2, 0:4] = A0[0:2]
        Mx[2:4, 0:4], Mx[2:4, 4:8] = B1[0:2], -C0[0:2]
        Mx[4, 0:4], Mx[4, 4:8] = EI1 * B1[2], -EI2 * C0[2]
        Mx[5, 0:4], Mx[5, 4:8] = EI1 * B1[3], -EI2 * C0[3]
        Mx[6, 4:8], Mx[7, 4:8] = C1[2], C1[3]
        return np.linalg.svd(Mx, compute_uv=False)[-1]

    from scipy.optimize import minimize_scalar
    fs = np.linspace(100, 8000, 3000)
    v = np.array([sv(f) for f in fs])
    out = []
    for i in range(1, len(fs) - 1):
        if v[i] < v[i - 1] and v[i] < v[i + 1]:
            out.append(minimize_scalar(sv, bounds=(fs[i - 1], fs[i + 1]), method="bounded",
                                       options={"xatol": 1e-7}).x)
        if len(out) == n_roots:
            break
    return out


@pytest.mark.parametrize("a_mm,t1_mm", [(6, 0.2655), (10, 0.2861), (14, 0.2888)])
def test_deux_epaisseurs_un_et_six_modes(a_mm, t1_mm):
    sec = _secs(a_mm, t1_mm)
    ex = _exact(sec)
    assert ex[0] == pytest.approx(175.0, rel=0.005)          # la fréquence visée, éléments finis de poutre
    for n in (1, 6):
        M, K = modal.assemble(sec, n)
        f = np.sqrt(np.diag(K) / np.diag(M)) / (2 * np.pi)
        assert f[0] == pytest.approx(ex[0], rel=2e-4)
        if n >= 2:
            assert f[1] == pytest.approx(ex[1], rel=2e-4)    # mode 2
    # les fréquences propres de M, K sont les mêmes, quel que soit n
    f6 = modal.natural_frequencies(sec, 6)
    assert f6[0] == pytest.approx(ex[0], rel=2e-4) and f6[1] == pytest.approx(ex[1], rel=2e-4)


def test_uniforme_formule_et_tronconnage_neutre():
    t = 0.8e-3
    attendu = 0.1615 * t / L ** 2 * np.sqrt(E / RHO)
    une = modal.natural_frequencies([[L, RHO, B, t, E]], 3)
    deux = modal.natural_frequencies(_secs(9, 0.8), 3)       # même lame coupée en deux tronçons
    assert une[0] == pytest.approx(attendu, rel=5e-4)         # 0.1615 est arrondi à 4 chiffres
    assert une == pytest.approx(deux, rel=1e-6)
    beta = (1.87510407, 4.69409113, 7.85475744)
    exact = [b ** 2 / (2 * np.pi * L ** 2) * np.sqrt(E * B * t ** 3 / 12 / (RHO * B * t)) for b in beta]
    assert une == pytest.approx(exact, rel=2e-6)


def test_base_gamma_tip_coherents():
    sec = _secs(6, 0.2655)
    M, K = modal.assemble(sec, 2)
    gam, tip = modal.mode_gamma_tip(sec, 2)
    assert np.allclose(M, np.diag(np.diag(M))) and np.allclose(K, np.diag(np.diag(K)))
    assert tip == pytest.approx(modal.mode_shapes(sec, [L], 2)[:, 0], rel=1e-9)
    assert tip[0] == pytest.approx(2.0, rel=1e-3)             # normalisation du cantilever uniforme
    x = np.linspace(0, L, 4001)
    psi = modal.mode_shapes(sec, x, 2)
    assert gam[0] == pytest.approx(B * modal._trapz(psi[0], x), rel=1e-4)
