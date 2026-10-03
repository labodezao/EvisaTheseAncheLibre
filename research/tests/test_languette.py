"""La languette : Euler-Bernoulli exact, Rayleigh-Ritz (km.py étendu), pont vers coupled_reeds."""
import os

import numpy as np
import pytest

from banc_recherche import material
from banc_recherche.languette import (Languette, Troncon, euler_bernoulli, fleche_statique,
                                      forme_euler_bernoulli, parametres_modaux, rayleigh_ritz)

ICI = os.path.dirname(os.path.abspath(__file__))
MATRIX = os.path.join(ICI, "..", "reedgui", "matrix.txt")
U = Languette.uniforme(30e-3, 3.5e-3, 0.3e-3)


def test_euler_bernoulli_poutre_uniforme_redonne_la_formule():
    f = euler_bernoulli(U, 4)
    for n in range(4):
        assert f[n] == pytest.approx(material.resonance_frequency(2.1e11, 30e-3, 0.3e-3, 7800, n + 1), rel=2e-6)


def test_rayleigh_ritz_exact_sur_poutre_uniforme_meme_avec_beaucoup_de_modes():
    for n_base in (5, 20, 40):
        f = rayleigh_ritz(U, 5, n_base=n_base)[0]
        assert f == pytest.approx(euler_bernoulli(U, 5), rel=1e-6)


def test_deformee_et_parametres_modaux_poutre_uniforme():
    p = parametres_modaux(U)
    assert p.m_eff / U.masse() == pytest.approx(0.25, rel=1e-4)          # masse modale = m/4
    EI = 2.1e11 * 3.5e-3 * 0.3e-3 ** 3 / 12
    assert p.k_eff / (3 * EI / 30e-3 ** 3) == pytest.approx(1.0302, rel=1e-3)
    x = np.linspace(0, 30e-3, 5)
    assert forme_euler_bernoulli(U, p.f_hz, x)[-1] == pytest.approx(1.0)
    assert p.phi_moyen == pytest.approx(0.3915, abs=1e-3)


def test_fleche_statique():
    EI = 2.1e11 * 3.5e-3 * 0.3e-3 ** 3 / 12
    assert fleche_statique(U, [30e-3])[0] == pytest.approx(30e-3 ** 3 / (3 * EI), rel=1e-5)


def test_matrix_txt_reedgui_trois_methodes():
    """L'anche d'Ewen (2020) : km.py à 2 modes surestime de 50 %, Rayleigh-Ritz converge
    vers Euler-Bernoulli exact par le haut. (Elmer : 67,7 Hz, voir fem/anche/resultats.)"""
    R = Languette.depuis_matrice(MATRIX)
    eb = euler_bernoulli(R, 3)
    assert eb[0] == pytest.approx(67.36, abs=0.02)
    km2 = rayleigh_ritz(R, 2, n_base=2)[0]
    assert km2[0] / eb[0] > 1.4
    f5, f20 = rayleigh_ritz(R, 3, n_base=5)[0], rayleigh_ritz(R, 3, n_base=20)[0]
    assert eb[0] < f20[0] < f5[0]


def test_troncon_variable_et_adoucissement():
    # une languette qui s'affine : la largeur compte
    a = Languette([Troncon(30e-3, (4e-3, 2e-3), 0.3e-3)])
    b = Languette.uniforme(30e-3, 3e-3, 0.3e-3)
    assert euler_bernoulli(a, 1)[0] > euler_bernoulli(b, 1)[0] * 1.05
    # adoucir une marche : même longueur, fréquence presque inchangée
    R = Languette.depuis_matrice(MATRIX)
    Ra = R.adoucie()
    assert Ra.L == pytest.approx(R.L)
    assert euler_bernoulli(Ra, 1)[0] == pytest.approx(euler_bernoulli(R, 1)[0], rel=5e-3)


def test_masse_ponctuelle_baisse_la_frequence():
    m = Languette([Troncon(30e-3, 3.5e-3, 0.3e-3)], masses=[(29e-3, 0.1e-3)])
    assert euler_bernoulli(m, 1)[0] < 0.8 * euler_bernoulli(U, 1)[0]
    assert rayleigh_ritz(m, 1, n_base=10)[0][0] == pytest.approx(euler_bernoulli(m, 1)[0], rel=5e-3)


def test_languette_modale_branchee_dans_coupled_reeds():
    pytest.importorskip("scipy")
    from banc_recherche.coupled_reeds import CoupledReedsModel
    from banc_recherche.languette import LanguetteModale, reglage
    p = parametres_modaux(U)
    lm = [LanguetteModale(p, U.L, 3.56e-3) for _ in range(2)]
    st = reglage(0.45e-3, 1.2e-3, 0.3e-3, 3.56e-3, 3.5e-3, p.phi_moyen)
    m = CoupledReedsModel(reeds=lm, settings=[st, st], muted=(False, True))
    assert m.f_reeds[0] == pytest.approx(p.f_hz, rel=1e-9)
