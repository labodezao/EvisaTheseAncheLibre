"""Deux anches d'une note, leurs chambres, la table d'harmonie, le clapet.

Anches fermées par le souffle (accordéon), lames d'acier réalistes, aucun
paramètre calé. Numpy seul ; simulations courtes.
"""
import numpy as np
import pytest

from banc_recherche.coupled_reeds import (CoupledReedsModel, Orifice, ReedSetting,
                                          dominant_frequency, pair, steel_reed)

FS, OVER, P = 8000.0, 24, 1000.0


def _sim(m, dur=0.6):
    return m.simulate(dur, supply_pa=P, fs=FS, oversample=OVER)


@pytest.fixture(scope='module')
def seule():
    m = pair(440.0, muted=(False, True))
    return m, _sim(m, 1.0)


@pytest.fixture(scope='module')
def deux():
    m = pair(440.0)
    return m, _sim(m, 1.0)


def test_la_section_se_ferme_puis_se_rouvre():
    """Levée au-dessus de la plaque → dedans (jeu seul) → ressortie."""
    st = ReedSetting(lift_m=0.5e-3, plate_m=1.2e-3, tongue_m=0.4e-3)
    assert st.gap(0.0) == pytest.approx(0.5e-3)
    assert st.gap(0.8e-3) == 0.0                       # dans la fente
    assert st.gap(0.5e-3 + 0.4e-3 + 1.2e-3 + 0.3e-3) == pytest.approx(0.3e-3)


def test_une_anche_fermee_par_le_souffle_demarre_seule(seule):
    """Sans aucune résistance calée : la languette s'entretient d'elle-même,
    un peu SOUS la note de sa lame (la note baisse quand on pousse)."""
    m, r = seule
    st = r.steady(0.5)
    assert np.ptp(r.tips[0][st]) > 0.3e-3
    assert np.ptp(r.tips[1][st]) == 0.0
    assert r.consumption(0.5)['reed'][1] == 0.0
    c = 1200 * np.log2(dominant_frequency(r.tips[0][st], r.fs) / m.f_reeds[0])
    assert -30 < c < 0


def test_la_loi_ouverte_par_le_souffle_ne_demarre_pas():
    """L'ancienne géométrie (le souffle OUVRE le passage) dans le même réseau,
    sans résistance calée : rien ne s'entretient. C'était l'erreur du modèle
    à une anche, qui ne démarrait que grâce à une résistance de source ajustée."""
    r1, _ = steel_reed(440.0)
    r2, _ = steel_reed(440.0)
    m = CoupledReedsModel(reeds=[r1, r2], setting=None, muted=(False, True))
    r = _sim(m)
    t = r.t
    a1 = np.ptp(r.tips[0][(t > 0.1) & (t < 0.15)])
    a2 = np.ptp(r.tips[0][t > 0.55])
    assert a2 < a1                                     # ça s'amortit


def test_l_air_se_conserve_et_se_partage_egalement(deux):
    _, r = deux
    c = r.consumption(0.5)
    assert abs(c['reed'][0] - c['reed'][1]) < 0.01 * c['reed'][0]
    assert abs(sum(c['reed']) - c['pallet']) < 0.03 * c['pallet']


def test_deux_anches_consomment_presque_deux_fois_une(seule, deux):
    """Canal et clapet communs ne freinent presque pas : l'air double, à
    quelques pour cent près (−4 % mesuré). Le « ×1,56 » du premier jet venait
    de la résistance calée, pas de l'acoustique."""
    q1 = seule[1].consumption(0.5)['pallet']
    q2 = deux[1].consumption(0.5)['pallet']
    assert 1.8 * q1 < q2 < 2.02 * q1


def test_voix_collees_pres_de_l_unisson_battement_au_dela():
    """À 1 ¢ les deux voix se verrouillent (le canal et le clapet communs les
    couplent) ; à 20 ¢ elles battent à l'écart de leurs lames."""
    proche = pair(440.0, detune_cents=1.0)
    loin = pair(440.0, detune_cents=20.0)
    rp = proche.simulate(1.5, supply_pa=P, fs=FS, oversample=OVER)
    rl = loin.simulate(1.5, supply_pa=P, fs=FS, oversample=OVER)
    gap = loin.f_reeds[1] - loin.f_reeds[0]
    assert abs(rp.beat_hz(0.6)) < 0.02
    assert abs(rl.beat_hz(0.6) - gap) < 0.05 * gap


def test_rayonnement_physique(deux):
    _, r = deux
    assert r.radiated_power(0.5) > 0
    assert 0 < r.efficiency(0.5) < 0.1
    assert np.isfinite(r.radiated).all()


def test_orifice_et_parametres():
    o = Orifice(1e-4, 0.01, cd=0.5)
    assert o.inertance(1.2) == pytest.approx(1.2 * 0.01 / 1e-4)
    assert o.loss(-1e-4, 1.2) == pytest.approx(-o.loss(1e-4, 1.2))
    with pytest.raises(ValueError):
        CoupledReedsModel(direction='souffler')


# --- pile de supports des deux côtés (slot_stack) ---------------------------

from banc_recherche.slot_stack import SlotStack  # noqa: E402


def _pile(stack, P=1000.0, dur=0.5):
    r1, _ = steel_reed(440.0)
    r2, _ = steel_reed(440.0)
    m = CoupledReedsModel(reeds=[r1, r2], stacks=[stack, stack], muted=(False, True))
    r = m.simulate(dur, supply_pa=P, fs=FS, oversample=OVER)
    x, t = r.tips[0], r.t
    return np.ptp(x[(t > 0.08) & (t < 0.11)]), np.ptp(x[t > dur - 0.04])


def test_pile_geometrie():
    s = SlotStack.sandwich(0.5e-3, 1.5e-3, tongue_m=0.3e-3)
    assert s.columns(0.0) == pytest.approx((0.5e-3, 1.5e-3))
    assert s.passage(0.0) == (0.0, pytest.approx(0.3e-3))      # dans la pile : le jeu seul
    f = s.flipped()
    assert f.columns(0.0) == pytest.approx((1.5e-3, 0.5e-3))
    a = SlotStack.accordion(0.9e-3, 0.45e-3, tongue_m=0.3e-3)
    assert a.passage(0.0)[0] == pytest.approx(0.45e-3)          # levée au-dessus de la plaque


def test_pile_accordeon_joue_dans_le_bon_sens_seulement():
    a1, a2 = _pile(SlotStack.accordion(0.9e-3, 0.45e-3))
    b1, b2 = _pile(SlotStack.accordion(0.9e-3, 0.45e-3, reverse=True))
    assert a2 > a1 and a2 > 0.3e-3
    assert b2 < b1


@pytest.mark.xfail(strict=True, reason=(
    "Ewen, essai réel : l'anche en sandwich joue dans les deux sens. Le modèle "
    "1D instantané ne sait pas la faire jouer — il lui manque le retard de "
    "l'écoulement au bord de la languette. Désaccord enregistré, pas caché "
    "(docs/audit_deux_anches.md §7)."))
def test_sandwich_contredit_le_modele():
    a1, a2 = _pile(SlotStack.sandwich(0.9e-3, 0.9e-3))
    assert a2 > 0.3e-3
