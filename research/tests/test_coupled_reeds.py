"""Deux anches d'une note, leurs chambres, la table d'harmonie, le clapet.

Numpy seul ; simulations courtes (quelques dixièmes de seconde utiles).
"""
import numpy as np
import pytest

from banc_recherche.coupled_reeds import (CoupledReedsModel, Orifice, Voicing,
                                          dominant_frequency)

FS, OVER = 8000.0, 24          # assez fin pour la raideur du réseau, assez vite pour les tests
PROPRE = dict(supply_resistance=0.0, hole_resistance=5e6)   # démarrage propre à chaque anche (défaut)
PARTAGE = dict(supply_resistance=5e6, hole_resistance=0.0)  # même résistance, au clapet


def _run(dur=0.8, P=300.0, **kw):
    voicing = kw.pop('voicing', Voicing())
    assert voicing.hole_resistance > 0 or voicing.supply_resistance > 0
    m = CoupledReedsModel(voicing=voicing, **kw)
    return m, m.simulate(dur, supply_pa=P, fs=FS, oversample=OVER)


def test_l_air_se_conserve_et_se_partage_egalement():
    """Ce qui entre par les anches ressort par le clapet ; deux anches
    identiques prennent chacune la moitié."""
    _, r = _run()
    c = r.consumption(0.4)
    assert c['reed'][0] > 0
    assert abs(c['reed'][0] - c['reed'][1]) < 0.01 * c['reed'][0]
    assert abs(sum(c['reed']) - c['pallet']) < 0.03 * c['pallet']


def test_une_anche_bloquee_ne_consomme_rien_et_l_autre_joue():
    m, r = _run(muted=(False, True))
    st = r.steady(0.4)
    assert np.ptp(r.tips[1][st]) == 0.0
    assert r.consumption(0.4)['reed'][1] == 0.0
    assert np.ptp(r.tips[0][st]) > 0.5e-3            # auto-oscillation (> 0,5 mm)
    f = dominant_frequency(r.tips[0][st], r.fs)
    # La note de sa lame, relevée par le ressort d'air de la chambre : +61 ¢
    # ici, comme `FreeReedModel` (+49 ¢ au seuil pour la même anche). C'est
    # un décalage physique, pas une erreur — il se mesure à l'accordeur.
    assert 0 < 1200 * np.log2(f / m.f_reeds[0]) < 80


def test_deux_anches_consomment_moins_que_deux_fois_une():
    """Elles se partagent le passage commun : l'air ne double pas."""
    _, seule = _run(muted=(False, True))
    _, deux = _run()
    q1 = seule.consumption(0.4)['pallet']
    q2 = deux.consumption(0.4)['pallet']
    assert q1 < q2 < 2 * q1


def test_le_placement_du_demarrage_decide_du_couplage():
    """Même résistance de démarrage, deux placements, deux mondes.

    Partagée au clapet, elle soude les anches : même désaccordées de 20 ¢,
    elles jouent à l'unisson — ce qu'aucune musette ne fait. Propre à chaque
    chambre, elles battent à l'écart de leurs lames. C'est ce qui dit que
    l'excitation d'une anche lui est propre, et que le canal commun ne les
    couple que faiblement.
    """
    m_s, partagee = _run(dur=1.5, detune_cents=20.0, voicing=Voicing(**PARTAGE))
    m_p, propre = _run(dur=1.5, detune_cents=20.0)
    gap = m_p.f_reeds[1] - m_p.f_reeds[0]
    assert abs(partagee.beat_hz(0.6)) < 0.05
    assert abs(propre.beat_hz(0.6) - gap) < 0.1 * gap


def test_rayonnement_et_rendement_sont_physiques():
    """Le son sort par le clapet : puissance positive, rendement petit
    (une anche libre transforme une infime part du souffle en son)."""
    _, r = _run()
    assert r.radiated_power(0.4) > 0
    assert 0 < r.efficiency(0.4) < 1e-2
    assert np.isfinite(r.radiated).all()


def test_orifice():
    o = Orifice(1e-4, 0.01, cd=0.5)
    assert o.inertance(1.2) == pytest.approx(1.2 * 0.01 / 1e-4)
    assert o.loss(-1e-4, 1.2) == pytest.approx(-o.loss(1e-4, 1.2))


def test_parametres_invalides():
    with pytest.raises(ValueError):
        CoupledReedsModel(direction='souffler')
