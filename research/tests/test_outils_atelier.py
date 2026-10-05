import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import outils_atelier as oa  # noqa: E402


def test_levee_utile_rideau_egal_trou():
    aire, per = oa.lire_trou("20x15")
    assert (aire, per) == (300, 70)
    assert oa.levee_utile_mm(aire, per) == pytest.approx(300 / 70)
    aire, per = oa.lire_trou("d12")                  # trou rond : h = d / 4
    assert oa.levee_utile_mm(aire, per) == pytest.approx(3.0)


def test_fente_en_h_cube_et_lineaire_en_pression():
    q1 = oa.fuite_fente_lpm(0.02, 100, 5, 500)
    assert oa.fuite_fente_lpm(0.04, 100, 5, 500) == pytest.approx(8 * q1)
    assert oa.fuite_fente_lpm(0.02, 100, 5, 1000) == pytest.approx(2 * q1)
    assert oa.fuite_fente_lpm(oa.jeu_max_mm(q1, 100, 5, 500), 100, 5, 500) == pytest.approx(q1)
    assert oa.reynolds_fente(0.05, 100, 5, 500) < 10   # Poiseuille valide


def test_ressort_et_decollement_sont_inverses():
    f = oa.force_ressort_g(300, 3000, marge=1.0)
    assert oa.pression_decollement_pa(f, 300) == pytest.approx(3000)


def test_chute_du_livret():
    q, d = oa.chute(10, 60, 600)
    assert q == pytest.approx(10)
    assert d == pytest.approx(3.3, abs=0.05)


def test_gazometre_150_cm2():
    m, v = oa.gazometre(150, 500)
    assert v == pytest.approx(6.67, abs=0.01)
    assert m == pytest.approx(0.765, abs=0.005)


def test_fenetre_soufflet_et_battement():
    smin, smax = oa.fenetre_soufflet(40, 1000, 2, 2, 0.4, 4)
    assert smax == pytest.approx(0.04)
    assert smin == pytest.approx(4 / 60000 * 4 / 0.4)
    assert oa.battement_hz(440, 1200) == pytest.approx(440)
