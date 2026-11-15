"""Anche à masse d'air : validation contre Adachi et al., Forum Acusticum 2026
(article 000418) et contre les défauts de l'ancien modèle (docs/audit_modele_anche.md).

Toutes les simulations : fs 44100, suréchantillonnage 8, 4 s, régime lu sur les
20 % de fin. Chiffres de l'article en commentaire de chaque test. Les désaccords
connus sont enregistrés (xfail strict ou test qui fixe le comportement), pas cachés.
"""
import math

import numpy as np
import pytest

from banc_recherche.air_mass_reed import (NUMBA, AirMassReedModel, adachi_c4,
                                          steel_family)
from banc_recherche.slot_stack import SlotStack

pytestmark = pytest.mark.skipif(not NUMBA, reason="simulations de 4 s : lent sans numba")

FS, OVS, DUR, FRAC = 44100.0, 8, 4.0, 0.2


def _sim(model, p0, **kw):
    return model.simulate(DUR, p0, fs=FS, oversample=OVS, **kw)


def _continuation(model, pressions):
    """Chaque pression repart de l'état final de la précédente.
    Renvoie [(f, amplitude en m)]."""
    out, state = [], None
    for p in pressions:
        r = _sim(model, p, state0=state)
        state = r.final_state
        out.append((r.frequency(FRAC), r.amplitude(FRAC)))
    return out


@pytest.fixture(scope='module')
def repos_35():
    m = AirMassReedModel(adachi_c4(35.0))
    return {p: _sim(m, p).frequency(FRAC) for p in (200, 400, 600, 800, 1000)}


@pytest.fixture(scope='module')
def repos_150():
    m = AirMassReedModel(adachi_c4(150.0))
    return {p: _sim(m, p).frequency(FRAC) for p in (200, 400, 600, 800, 1000)}


@pytest.fixture(scope='module')
def continuation_35():
    m = AirMassReedModel(adachi_c4(35.0))
    ps = [200, 500, 1000, 1500, 2000, 2500]
    return dict(zip(ps, _continuation(m, ps)))


def _pente(freqs):
    ps = np.array(sorted(freqs)) / 1000.0
    fs = np.array([freqs[p * 1000.0] if (p * 1000.0) in freqs else freqs[int(round(p * 1000))]
                   for p in ps])
    return float(np.polyfit(ps, fs, 1)[0]), float(np.mean(fs))


def _cents(pente, f):
    return 1200.0 * pente / f / math.log(2.0)


# 1 -------------------------------------------------------------------------
def test_frequence_a_1000_pa(repos_35, repos_150):
    # article fig. 6 : 265,1 Hz (K_p = 35), 261,7 Hz (K_p = 150)
    assert repos_35[1000] == pytest.approx(265.1, abs=0.3), repos_35[1000]
    assert repos_150[1000] == pytest.approx(261.7, abs=0.3), repos_150[1000]


# 2 -------------------------------------------------------------------------
def test_pente_hauteur_pression(repos_35, repos_150):
    p35, m35 = _pente(repos_35)
    p150, m150 = _pente(repos_150)
    msg = (f"pentes : K_p=35 {p35:.2f} Hz/kPa ({_cents(p35, m35):.1f} cents/kPa), "
           f"K_p=150 {p150:.2f} Hz/kPa ({_cents(p150, m150):.1f} cents/kPa), "
           f"rapport {p150 / p35:.2f}")
    assert -3.0 <= p35 <= -2.0, msg        # article : -2,5 simulé et mesuré
    assert -6.5 <= p150 <= -5.0, msg       # article : -5,9 simulé, -5,1 mesuré
    assert 1.8 <= p150 / p35 <= 2.6, msg   # mesuré : 2,0


# 3 -------------------------------------------------------------------------
def test_amplitude_par_continuation(continuation_35):
    amps = [continuation_35[p][1] for p in (200, 500, 1000, 1500, 2000, 2500)]
    msg = f"amplitudes (mm) : {[round(a * 1e3, 3) for a in amps]}"
    assert all(b > a for a, b in zip(amps, amps[1:])), msg     # croissante
    assert 0.3e-3 <= amps[0] <= 0.6e-3, msg                     # article fig. 7 : 0,4 mm
    assert 2.5e-3 <= amps[-1] <= 3.5e-3, msg                    # article fig. 7 : 3 mm


def test_enregistre_pas_de_demarrage_a_2000_pa_depuis_le_repos():
    """Enregistré : à 2000 Pa, du repos, l'anche ne parle pas ; l'équilibre y est
    stable, le cycle n'existe que par continuité (hystérésis)."""
    m = AirMassReedModel(adachi_c4(35.0))
    assert m.instability_band()[1] < 2000
    amp = _sim(m, 2000.0).amplitude(FRAC)
    assert amp < 0.05e-3, f"amplitude {amp * 1e3:.4f} mm"


# 4 -------------------------------------------------------------------------
def test_seuil_stabilite_lineaire():
    m = AirMassReedModel(adachi_c4(35.0))
    pth = m.hopf_threshold()
    # article : « environ 200 Pa » (moyennage simplifié) ; ici ≈ 106 Pa
    assert pth is not None and 50.0 <= pth <= 400.0, pth
    a_haut = _sim(m, 1.3 * pth).amplitude(FRAC)
    a_bas = _sim(m, 0.7 * pth).amplitude(FRAC)
    assert a_haut > 0.05e-3, f"seuil {pth:.1f} Pa, amp à 1,3x {a_haut * 1e3:.4f} mm"
    assert a_bas < 0.005e-3, f"seuil {pth:.1f} Pa, amp à 0,7x {a_bas * 1e3:.5f} mm"


# 5 -------------------------------------------------------------------------
def _balayage_seuil(K_p):
    m = AirMassReedModel(adachi_c4(K_p))
    pth = m.hopf_threshold()
    mult = [2, 4, 8, 16, 32]
    res = _continuation(m, [k * pth for k in mult])
    return pth, dict(zip(mult, res))


@pytest.fixture(scope='module')
def seuil_35():
    return _balayage_seuil(35.0)


@pytest.fixture(scope='module')
def seuil_0():
    return _balayage_seuil(0.0)


def test_amplitude_bornee_par_le_clapet(seuil_35):
    pth, r = seuil_35
    a16, a32 = r[16][1], r[32][1]
    msg = (f"p_th {pth:.1f} Pa ; amp (mm) : "
           f"{ {k: round(v[1] * 1e3, 3) for k, v in r.items()} }")
    assert a16 < 4e-3, msg                 # ancien modèle : 47 mm à 16x
    assert a32 / a16 < 1.7, msg


def test_sans_clapet_amplitude_non_bornee(seuil_0):
    pth, r = seuil_0
    a16, a32 = r[16][1], r[32][1]
    msg = (f"p_th {pth:.1f} Pa ; amp (mm) : "
           f"{ {k: round(v[1] * 1e3, 3) for k, v in r.items()} }")
    assert a32 / a16 > 1.8, msg
    # pas de baisse de hauteur sans clapet
    assert abs(r[16][0] - 267.6) < 0.1, f"f à 16x : {r[16][0]:.2f} Hz"


# 6 -------------------------------------------------------------------------
# Rien n'est mesuré : c'est une loi de réglage balayée
# (scripts/excitateur_seuil_plan.py, plan 2^6), lames d'acier nominales.
def _seuils(**kw):
    out = {}
    for f in (100.0, 900.0):
        m = steel_family(f, **kw)
        out[f] = m.hopf_threshold(p_lo=0.1, p_hi=1e5, n_scan=70)
    return out


def test_seuil_selon_la_note_reglage_constant():
    s = _seuils()
    assert s[100.0] is not None and s[900.0] is not None, s
    dec = math.log10(s[900.0] / s[100.0])
    msg = f"seuils : 100 Hz {s[100.0]:.1f} Pa, 900 Hz {s[900.0]:.1f} Pa, {dec:.2f} décades"
    # ancien modèle : 3,0 décades (1,8 Pa à 102 Hz, 1781 Pa à 880 Hz)
    assert 1.5 <= dec <= 2.6, msg
    assert dec < 3.0, msg


def test_seuil_selon_la_note_reglage_proportionnel():
    s = _seuils(lift_440_m=0.5e-3, lift_exponent=1, gap_m=3e-5, zeta=0.002,
                K_p=150, thickness_m=0.2e-3)
    assert s[100.0] is not None and s[900.0] is not None, s
    dec = math.log10(s[900.0] / s[100.0])
    msg = f"seuils : 100 Hz {s[100.0]:.1f} Pa, 900 Hz {s[900.0]:.1f} Pa, {dec:.2f} décades"
    assert dec < 1.0, msg
    assert 30.0 <= s[100.0] <= 1000.0 and 30.0 <= s[900.0] <= 1000.0, msg


# 7 -------------------------------------------------------------------------
def test_sens_de_montage_par_la_pile():
    base = adachi_c4(35.0)
    droit = AirMassReedModel(base.with_(
        stack=SlotStack.accordion(1.0e-3, 0.3e-3, tongue_m=0.3e-3), x_rest_m=0.3e-3))
    a = _sim(droit, 1000.0).amplitude(FRAC)
    assert a > 1e-3, f"sens normal : {a * 1e3:.3f} mm"
    inverse = AirMassReedModel(base.with_(
        stack=SlotStack.accordion(1.0e-3, 0.3e-3, tongue_m=0.3e-3, reverse=True),
        x_rest_m=0.3e-3))
    assert inverse.instability_band() == (None, None)
    b = _sim(inverse, 1000.0).amplitude(FRAC)
    assert b < 1e-6, f"sens inverse : {b:.3e} m"


# 8 -------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason=(
    "le modèle à masse d'air 1D garde la contradiction : la lame centrée a une "
    "section constante (le jeu) tant qu'elle reste dans la pile, et quand elle en "
    "sort des deux côtés la sortie aval freine autant que l'amont entretient. "
    "Désaccord enregistré, pas caché."))
def test_sandwich_joue_dans_les_deux_sens():
    """Essai réel d'Ewen : la lame en sandwich joue dans les deux sens."""
    m = AirMassReedModel(adachi_c4(35.0).with_(
        stack=SlotStack.sandwich(0.9e-3, 0.9e-3, tongue_m=0.3e-3), x_rest_m=0.0))
    st = m.rest_state()
    st[0] = 1.5e-3                          # pichenette
    r = _sim(m, 1000.0, state0=st)
    assert r.amplitude(FRAC) > 0.3e-3, f"amplitude {r.amplitude(FRAC) * 1e3:.4f} mm"
