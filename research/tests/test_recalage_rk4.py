"""Recalage Elmer <-> modèle RK4 : les pièces testables sans Elmer (numpy, scipy)."""
import os
import sys

import numpy as np
import pytest

from banc_recherche.languette import Languette, euler_bernoulli, parametres_modaux
from banc_recherche.reed_model import SECTIONS_DEFAULT, ReedModel

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "fem"))


def test_largeur_moyenne_sur_les_troncons():
    """L'erreur du MATLAB (moyenne divisée par les 5 colonnes au lieu des tronçons)
    n'est pas dans le port Python."""
    sec = np.array([[10e-3, 7800, 4e-3, 0.3e-3, 2.1e11],
                    [10e-3, 7800, 3e-3, 0.2e-3, 2.1e11],
                    [10e-3, 7800, 2e-3, 0.4e-3, 2.1e11]])
    assert ReedModel(sections=sec).b == pytest.approx(3e-3)


def test_option_parametres_elmer_dans_reed_model_et_free_reed():
    pytest.importorskip("scipy")
    from banc_recherche.reed_oscillator import FreeReedModel
    U = Languette.uniforme(30e-3, 3.5e-3, 0.3e-3)
    p = parametres_modaux(U)
    rm = ReedModel(sections=U.matrice(), modal_params=p)
    assert rm.N == 1 and np.sqrt(rm.K[0, 0] / rm.M[0, 0]) / (2 * np.pi) == pytest.approx(p.f_hz)
    fr = FreeReedModel(sections=U.matrice(), modal_params=p)
    assert fr.f_modes[0] == pytest.approx(p.f_hz) and fr.phi_tip[0] == 1.0


def test_reed_model_surestime_la_charniere_de_45_microns():
    """SECTIONS_DEFAULT : Rayleigh-Ritz à 2 modes (reed_model) donne ~102 Hz, la poutre
    exacte ~15,6 Hz (Elmer 15,9 Hz) : la charnière de 45 µm n'est pas représentable sur
    deux modes de cantilever uniforme."""
    pytest.importorskip("scipy")
    import recalage_rk4 as R
    lang = Languette.depuis_matrice(SECTIONS_DEFAULT)
    f_rm, p_rm, _ = R.modal_reed_model(lang)
    eb = euler_bernoulli(lang, 1)[0]
    assert f_rm[0] / eb > 5
    # sur une lame uniforme, les trois s'accordent et la forme est la même
    U = Languette.uniforme(24e-3, 3.5e-3, 0.3e-3)
    f_u, p_u, forme = R.modal_reed_model(U)
    pe = parametres_modaux(U)
    assert f_u[0] == pytest.approx(pe.f_hz, rel=1e-3)
    assert p_u.m_eff == pytest.approx(pe.m_eff, rel=1e-3)
    x = np.linspace(0, U.L, 50)
    from banc_recherche.languette import forme_euler_bernoulli
    assert R.mac(forme(x), forme_euler_bernoulli(U, pe.f_hz, x)) > 0.9999


def test_calage_cavite_sur_un_resonateur_connu():
    pytest.importorskip("scipy")
    import recalage_rk4 as R
    f = np.geomspace(50, 4000, 70)
    w = 2 * np.pi * f
    Ls, a, f1 = 30.0, 8e9, 1200.0
    Z = 1j * w * (Ls + a / ((2 * np.pi * f1) ** 2 - w ** 2))
    Ls_c, a_c, f1_c, m, _ = R.caler_cavite(f, Z, 400.0, 1190.0, 3000.0)
    assert Ls_c == pytest.approx(Ls, rel=1e-3) and a_c == pytest.approx(a, rel=1e-3)
    assert f1_c == pytest.approx(f1, rel=1e-3)


def test_cache_cle_stable_et_relecture(tmp_path, monkeypatch):
    import cache
    monkeypatch.setattr(cache, "DOSSIER", str(tmp_path))
    e = dict(a=1.0, b=[1, 2.0000000000001], c={"x": np.float64(3.0)})
    assert cache.cle("t", e) == cache.cle("t", dict(c={"x": 3.0}, b=[1, 2.0], a=1.0))
    n = []
    calcul = lambda: n.append(1) or dict(v=42)
    assert cache.en_cache("t", e, calcul)["_cache"] == "calculé"
    r = cache.en_cache("t", e, calcul)
    assert r["_cache"] == "lu" and r["v"] == 42 and len(n) == 1


def test_optimisation_outils():
    sys.path.insert(0, os.path.join(ICI, "..", "fem", "sommier"))
    import optimisation_r12 as o
    # kappa et formule de Helmholtz : inverses l'une de l'autre
    k = o.kappa_de(1200.0, 200.0, 12000.0, 8.0)
    assert o.f_helmholtz(200.0, 12000.0, 8.0, k) == pytest.approx(1200.0)
    assert o.trou_de(200.0) == (8.0, 25.0) and o.trou_de(60.0) == (4.0, 15.0)
    assert o.marge_harmoniques(440.0, [440.0]) == pytest.approx(0.0)
    assert o.marge_harmoniques(660.0, [440.0], 1) == pytest.approx(1200 * np.log2(1.5))
    notes = o.lire_notes()
    assert len(notes) == 12 and "à confirmer" in notes[1]["source"]
