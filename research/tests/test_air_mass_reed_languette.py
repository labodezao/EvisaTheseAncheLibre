"""Anche à masse d'air, lot 3 : la vraie lame (`languette.py`) branchée sur
l'excitateur à masse d'air, note jouée SANS `_accorder`.

Renvoie au plan `scripts/excitateur_justesse_plan.py` (2^(7-1) par note, sans
aucun calage). Résumé du plan, écart en cents note jouée / lame :
  R12-grave  -19 à -167 c (médiane -60)    110 Hz  -20 à -239 (-64)
  220 Hz     -5 à -82 (-29)                440 Hz  -1,6 à -26 (-7)
  880 Hz     -0,3 à -9 (-2)                1760 Hz muet sauf 7/64
L'ancien modèle (`live._accorder`) : 1 à 40 c d'écart avant retouche.

Les désaccords connus avec les mesures sont enregistrés (xfail strict), pas
cachés : le jour où le modèle les rattrape, le test le dit.
"""
from pathlib import Path

import numpy as np
import pytest

from banc_recherche.air_mass_reed import (NUMBA, AirMassReedModel, adachi_c4,
                                          from_languette, steel_family)
from banc_recherche.banque_anches import importer
from banc_recherche.languette import parametres_modaux

pytestmark = pytest.mark.skipif(not NUMBA, reason="simulations de 3 s : lent sans numba")

RACINE = Path(__file__).resolve().parents[1]


def _r12_grave(jeu=3e-5, zeta=0.002, K_p=35.0):
    """La lame réelle R12-grave de la banque, comme `r12_grave` du plan."""
    anches, _ = importer(RACINE / "fem" / "anche" / "banque_anches.csv")
    a = [x for x in anches if x.id == "R12-grave"][0]
    lang = a.languette()
    p = from_languette(lang, gap_m=jeu, x_rest_m=float(a.valeur("levee_mm")) * 1e-3,
                       zeta=zeta, K_p=K_p)
    return lang, AirMassReedModel(p)


def test_r12_grave_depuis_la_languette():
    lang, m = _r12_grave()
    mp = parametres_modaux(lang)
    assert m.p.f0_hz == pytest.approx(67.36, abs=0.05)
    assert m.p.mass_kg == pytest.approx(mp.m_eff, rel=1e-9)
    assert m.p.force_area == pytest.approx(mp.gamma, rel=1e-9)


@pytest.mark.parametrize("f_hz, p0, bas, kw", [
    (440.0, 1000.0, -15.0, {}),
    # À 880 Hz le réglage par défaut (levée 0,3 mm, ζ 0,003) a son seuil à
    # 2 kPa : il ne parle pas à 1,5 kPa. Le réglage pris ici est l'un des 30
    # sur 64 du plan qui parlent (levée ∝ longueur, ζ 0,002) : rien n'est calé.
    (880.0, 1500.0, -5.0, dict(lift_exponent=1.0, zeta=0.002)),
])
def test_milieu_de_clavier_sans_retouche(f_hz, p0, bas, kw):
    r = steel_family(f_hz, **kw).played_note(p0, oversample=16)
    msg = f"{f_hz} Hz à {p0} Pa : plays={r['plays']}, cents={r['cents']:.2f}"
    assert r['plays'], msg
    assert bas <= r['cents'] <= 0.0, msg


def _pente_c_par_kpa(m, pressions=(150.0, 300.0, 600.0)):
    """Continuation sur les pressions (3 s chacune), cents / f0 de la lame,
    régression linéaire en c/kPa."""
    state, cents = None, []
    for p in pressions:
        r = m.simulate(3.0, p, oversample=16, state0=state)
        state = r.final_state
        cents.append(1200.0 * np.log2(r.frequency(0.2) / m.p.f0_hz))
    return float(np.polyfit(np.array(pressions) / 1000.0, cents, 1)[0]), cents


@pytest.mark.xfail(strict=True, reason=(
    "désaccord enregistré : les anches graves 62-78 Hz mesurées en 2023 (non "
    "identifiées, data/mesures_2023/rapport_analyse_20261001.md) donnent -8,5 à "
    "-18,7 c/kPa ; le modèle donne ≈ -81 c/kPa de 150 à 600 Pa avec K_p 35 (avec K_p ≈ 2 on "
    "retrouve -18 : le sommier, non mesuré, décide)"))
def test_pente_hauteur_pression_r12_grave():
    _, m = _r12_grave()
    pente, cents = _pente_c_par_kpa(m)
    assert -25.0 <= pente <= -5.0, f"pente {pente:.1f} c/kPa, cents {cents}"


@pytest.mark.xfail(strict=True, reason=(
    "désaccord enregistré : une anche aiguë réelle parle à 1 kPa ; ici le "
    "seuil linéaire de 1760 Hz est > 1,5 kPa (note muette à 1 kPa)"))
def test_1760_hz_parle_a_1_kpa():
    assert steel_family(1760.0).played_note(1000.0, oversample=16)['plays']


def test_critere_joue_sous_le_seuil():
    """Sous le seuil (≈ 106 Pa), l'oscillation lancée plus haut s'éteint."""
    r = AirMassReedModel(adachi_c4(35.0)).played_note(50.0)
    assert r['plays'] is False


def test_pas_adapte_a_la_raideur():
    """Avant la correction du pas : divergence à 0,2 ms pour 1760 Hz, jeu 0,03 mm."""
    m = steel_family(1760.0, gap_m=3e-5)
    r = m.simulate(0.05, 20000.0, oversample=16)   # ne doit pas lever FloatingPointError
    assert np.all(np.isfinite(r.tip))
