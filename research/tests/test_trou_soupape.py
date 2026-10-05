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


def test_lame_nue_de_re_diese():
    """Lame nue 74 x 8 x 1 mm (Ewen, 05/10/2026) : 153,1 Hz, accordée sur ré# (155,56 Hz) par
    0,6 mm de longueur libre en moins ; levée de l'anche 1 mm ; pas de masse au bout."""
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.lame_nue()
    assert info["f_74mm_Hz"] == pytest.approx(153.07, abs=0.05)
    assert info["f1_Hz"] == pytest.approx(155.56, rel=1e-4)
    assert info["L_libre_mm"] == pytest.approx(73.40, abs=0.02)
    assert info["m_eff_g"] == pytest.approx(0.25 * 7850 * 73.4e-3 * 8e-3 * 1e-3 * 1e3, rel=0.01)   # m/4
    assert st.lift_m == pytest.approx(1.0e-3)              # levée de l'ANCHE au repos
    assert st.clearance_m == pytest.approx(0.05e-3)
    assert info["fleche_2kPa_mm"] < 1.0                     # à 2 kPa la lame ne se plaque pas en statique


def test_ajustement_L_de_la_levee():
    import trou_soupape_jeu as J
    h = np.array([1.0, 2.0, 3.0, 4.0, 6.0])
    L0, a = J.ajuste_L(h, 145.0 + 170.0 / h)
    assert L0 == pytest.approx(145.0) and a == pytest.approx(170.0)


def test_reseau_de_repli_pertes_en_serie_et_balayage():
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.lame_nue()
    r = J.reseau_note("12x12", 3.0)
    mod = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r)
    perte_trou = 1.2 / 2 / (J.CD * mod.A_trou) ** 2
    assert mod.perte > perte_trou                          # trou et rideau en série
    assert mod.perte_de(1e-3) > mod.perte_de(3e-3)         # la soupape qui s'ouvre perd moins
    d, q_r = mod.deriv((0.0, 0.0, 0.0, 0.0, 0.0), 1000.0)
    assert q_r > 0 and d[1] > 0                            # la pression pousse la lame dans la fente
    d1, _ = mod.deriv((0.0, 1.0, 0.0, 0.0, 0.0), 1000.0)        # la lame avance : elle remplit la chambre
    assert d1[2] > d[2]
    sans = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, sans_trou=True)
    assert sans.perte == 0.0


def test_masse_du_reseau():
    """Sous la résonance du trou, la masse vue par la lame est g².L (le trou porte le débit balayé)."""
    import trou_soupape_jeu as J
    g, L, C = 2.3e-4, 150.0, 43e-6 / (1.2 * 343 ** 2)
    m, R = J.masse_reseau(g, dict(L=L, C=C, R=0.0), 155.0)
    f_H = 1 / (2 * math.pi * math.sqrt(L * C))
    assert m == pytest.approx(g * g * L / (1 - (155.0 / f_H) ** 2), rel=1e-6)


def test_mesures_sur_une_oscillation_de_synthese():
    import trou_soupape_jeu as J
    fs, f1 = 8000.0, 155.56
    t = np.arange(int(1.2 * fs)) / fs
    env = np.minimum(1.0, t / 0.2)
    x = 1e-3 * env * np.sin(2 * np.pi * f1 * t)
    q = 1e-3 * (1 + np.maximum(0, np.sin(2 * np.pi * f1 * t)))
    sim = dict(t=t, x=x, p_ch=100 * (1 + 0.5 * np.sin(2 * np.pi * f1 * t)), q_r=q, q_h=q, fs=fs, P=2000.0)
    m = J.mesures(sim, f1)
    assert m["joue"] and m["f_jeu_Hz"] == pytest.approx(f1, rel=0.01)
    assert m["amplitude_bout_mm"] == pytest.approx(1.0, rel=0.02)
    assert m["p_ch_crete_pct"] == pytest.approx(7.5, rel=0.02)
    assert 15 < m["t_parle_10_ms"] < 30                    # 10 % de l'enveloppe à 20 ms
    assert 175 < m["t_parle_90_ms"] < 195                  # 90 % à 180 ms
    assert m["periodes_90"] == pytest.approx(m["t_parle_90_ms"] * 1e-3 * m["f_jeu_Hz"])


def test_couplage_deformee_et_masse_ajoutee_d_une_bande():
    import couplage_lame_air as C
    assert C.psi(0.0) == pytest.approx(0.0, abs=1e-12) and C.psi(1.0) == pytest.approx(1.0, rel=1e-6)
    m = 7850 * 74e-3 * 8e-3 * 1e-3
    assert C.masse_modale() == pytest.approx(m / 4, rel=1e-3)
    t = C.theorie_bande()
    assert t["m_a_sur_m"] == pytest.approx(math.pi * 1.2 * 8e-3 / (4 * 7850 * 1e-3), rel=1e-3)


def test_couplage_mode_couple():
    """Masse ajoutée constante : f = f_vide / sqrt(1 + m_a/m) ; R_a donne zeta."""
    import couplage_lame_air as C
    f = np.array([140.0, 153.07, 170.0])
    m = C.masse_modale()
    Zm = 1e-3 * 1j * 2 * np.pi * f * (0.01 * m) / 1e-3 + 1e-4
    r = C.mode_couple(f, Zm)
    assert r["f_couple_Hz"] == pytest.approx(153.07 / math.sqrt(1.01), rel=1e-6)
    assert r["zeta_air"] == pytest.approx(1e-4 / (2 * 1.01 * m * 2 * math.pi * r["f_couple_Hz"]), rel=1e-6)


def test_source_de_debit_sans_chambre():
    """Le débit q0 remplit le volume amont tant que la lame est fermée ; la lame qui entre dans la
    fente agrandit ce volume (la pression amont baisse)."""
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.la_lame()
    mod = J.SourceDebit(lame, st, 1e-3, 5.0)
    d0, _ = mod.deriv((0.0, 0.0, 0.0, 0.0, 0.0))
    assert d0[2] > 0                                     # q0 > fuite : la pression monte
    d1, _ = mod.deriv((0.0, 1.0, 0.0, 0.0, 0.0))
    assert d1[2] < d0[2]                                 # volume balayé
    assert J.R_RAYONNEMENT < 1000                        # pas l'artefact rho.c/S de la boîte


# --- Corrections de l'audit Fable (§ 4) et coupe 2D (05/10/2026) ------------------------------------
def test_modele_corrige_phase_perte_et_inertie():
    """Les phases de la lame, la perte bornée (max < somme), et l'état « débit » : la force reçoit
    -Lambda_F.dq/dt (la lame qui ferme fait baisser le débit : surpression, force vers l'aval)."""
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.la_lame()
    r = J.reseau_note("12x12", 3.0)
    m_somme = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r)
    m_max = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, perte_mode="max")
    assert m_max.perte < m_somme.perte
    phi = m_somme.cr.phi[0]
    assert m_somme.phase(0.0) == "entree"
    assert m_somme.phase((st.lift_m + 0.5 * st.plate_m) / phi) == "plaquette"
    assert m_somme.phase((st.lift_m + st.tongue_m + 2 * st.plate_m) / phi) == "sortie"
    sans = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, inertie=True)
    avec = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, inertie=True, lambda_f={"entree": 5e-3})
    s = (0.0, 0.0, 0.0, 0.0, 2e-3)          # débit au-dessus du débit d'équilibre : dq/dt < 0
    d0, q0 = sans.deriv(s, 1000.0)
    d1, q1 = avec.deriv(s, 1000.0)
    assert q0 == q1 == 2e-3 and d0[4] < 0
    assert d1[1] > d0[1]                     # -Lambda_F.dq/dt > 0 : poussée vers la fente
    frein = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, inertie=True, c_jet={"entree": 1e-4})
    d2, _ = frein.deriv((0.0, 1.0, 0.0, 0.0, 2e-3), 1000.0)
    d3, _ = sans.deriv((0.0, 1.0, 0.0, 0.0, 2e-3), 1000.0)
    assert d2[1] < d3[1]                     # c_jet.v_jet freine la lame qui avance


def test_source_generale_sept_etats():
    pytest.importorskip("scipy")
    import trou_soupape_jeu as J
    lame, st, info = J.la_lame()
    r = J.reseau_note("12x12", 3.0)
    m = J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, inertie=True, L_s=30.0, V_amont_cm3=40.0)
    d, q = m.deriv((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 1000.0)
    assert len(d) == 7 and d[6] > 0          # la source pousse : le débit de source monte
    with pytest.raises(ValueError):
        J.BasseTrouSoupape(lame, st, "12x12", 3.0, r, R_s=1e5)


def test_coupe_2d_theorie_et_decomposition():
    """Débits de référence, décomposition en phase / quadrature, et le loin 3D (sans Elmer)."""
    import coupe_2d_lame as C
    th = C.theorie_stationnaire("plaquette", 2000.0)
    assert th["q_poiseuille"] == pytest.approx(2 * 2000 * (0.05e-3) ** 3 / (12 * C.MU * 1e-3), rel=1e-9)
    assert th["q_poiseuille_pertes"] < th["q_poiseuille"]
    th = C.theorie_stationnaire("entree", 2000.0)
    assert th["q_bernoulli_0611"] == pytest.approx(2 * 0.611 * math.hypot(0.5e-3, 0.05e-3) * math.sqrt(2 * 2000 / 1.2), rel=1e-9)
    w, Y, t0 = 2 * math.pi * 155, 2e-5, 0.01
    t = np.linspace(0, t0 + 5 / 155, 2000)
    y = 3.0 + 0.5 * t + 0.2 * np.sin(w * (t - t0)) - 0.05 * np.cos(w * (t - t0)) + 0.01 * np.sin(2 * w * (t - t0))
    r = C.decomposer(t, y, t0, Y, w, 3)
    assert r["A_s"] == pytest.approx(0.2, abs=1e-6) and r["A_c"] == pytest.approx(-0.05, abs=1e-6)
    a, b = C.correction_3d(10.0), C.correction_3d(40.0)
    assert a["J_m"] > b["J_m"]                                   # domaine 2D plus grand : moins à corriger
    assert a["R_equivalent_mm"] == pytest.approx(b["R_equivalent_mm"])
    assert 20 < a["R_equivalent_mm"] < 80                        # de l'ordre de la longueur de la lame
    assert a["int_psi2_mm"] == pytest.approx(74.0 / 4, rel=1e-3)
