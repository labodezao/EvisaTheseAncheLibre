"""Trou de table et soupape d'une grosse basse (BB95) : les pièces testables sans Elmer."""
import math
import os
import sys

import numpy as np
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "fem", "sommier"))
sys.path.insert(0, os.path.join(ICI, "..", "fem"))

import trou_soupape_bb95 as elm  # noqa: E402


def test_formules_de_la_note():
    """Les constantes localisées redonnent la table § 3.1 de la note (12x12, 40 cm³ : 823 Hz)."""
    n = elm.formules_note((12.0, 12.0), 3.0, V_cm3=40.0)
    assert n["f_H_Hz"] == pytest.approx(823, rel=0.01)
    assert n["levee_critique_mm"] == pytest.approx(3.0)
    assert n["A_rideau_mm2"] == pytest.approx(144.0)


def test_ajustement_retrouve_le_reseau():
    """Z(f) d'un réseau connu, bruité à 1 % : l'ajustement retrouve L, C, R à 2 %."""
    pytest.importorskip("scipy")
    f = np.array(elm.FREQS, float)
    L_s, C, R, L = 3.0, 40e-6 / (1.2 * 343 ** 2), 3e4, 130.0
    rng = np.random.default_rng(0)
    Z = elm.z_reseau(f, L_s, C, R, L) * (1 + 0.01 * rng.normal(size=f.size))
    fit = elm.ajuster(f, Z)
    assert fit["L_trou_kg_m4"] == pytest.approx(L, rel=0.02)
    assert fit["C_m3_Pa"] == pytest.approx(C, rel=0.02)
    assert fit["R_Pa_s_m3"] == pytest.approx(R, rel=0.05)
    assert fit["f_H_Hz"] == pytest.approx(1 / (2 * math.pi * math.sqrt(L * C)), rel=0.01)


def test_lame_accordee_et_reglage():
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.lame_basse(41.2, profil="grattee")
    assert info["f1_Hz"] == pytest.approx(41.2, rel=1e-4)
    assert info["f_nue_Hz"] > 41.2                        # sans masse, ce n'est pas une basse
    assert 0.5 < info["masse_bout_g"] < 20
    assert st.clearance_m == pytest.approx(0.05e-3)       # jeu d'Ewen
    assert st.plate_m == pytest.approx(2.5e-3)
    lame_u, _, info_u = J.lame_basse(41.2, profil="uniforme")
    assert info_u["k_eff_N_m"] > 3 * info["k_eff_N_m"]    # la lame uniforme de 1 mm est bien plus raide


def test_reseau_de_repli_et_pertes_en_serie():
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.lame_basse(41.2, profil="grattee")
    r = J.reseau_note("12x12", 3.0)
    mod = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r)
    # trou et rideau en série : perte > perte du trou seul
    perte_trou = 1.2 / 2 / (J.CD * mod.A_trou) ** 2
    assert mod.perte > perte_trou
    d, q_r = mod.deriv((0.0, 0.0, 0.0, 0.0), 1000.0)
    assert q_r > 0 and d[1] > 0                            # la pression pousse la lame dans la fente
    sans = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, sans_trou=True)
    assert sans.perte == 0.0


def test_mesures_sur_une_oscillation_de_synthese():
    import trou_soupape_jeu as J
    fs, f1 = 8000.0, 41.2
    t = np.arange(int(1.2 * fs)) / fs
    env = np.minimum(1.0, t / 0.2)
    x = 1e-3 * env * np.sin(2 * np.pi * f1 * t)
    q = 1e-3 * (1 + np.maximum(0, np.sin(2 * np.pi * f1 * t)))
    sim = dict(t=t, x=x, p_ch=100 * (1 + 0.5 * np.sin(2 * np.pi * f1 * t)), q_r=q, q_h=q, fs=fs, P=2000.0)
    m = J.mesures(sim, f1)
    assert m["joue"] and m["f_jeu_Hz"] == pytest.approx(f1, rel=0.01)
    assert m["amplitude_bout_mm"] == pytest.approx(1.0, rel=0.02)
    assert m["p_ch_crete_pct"] == pytest.approx(7.5, rel=0.02)
    assert 0.1 < m["attaque_10_90_s"] < 0.2
