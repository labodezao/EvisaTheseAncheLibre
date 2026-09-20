"""Garde-fous du modèle d'anche libre alimenté en débit.

Ces tests figent des propriétés **physiques** : conservation de la masse,
bornes de l'ouverture, asymétrie de l'anche libre, amortissement valide.
Ils ne prétendent pas que le modèle auto-oscille — il ne le fait pas encore,
et `test_pas_d_auto_oscillation_revendiquee` le consigne explicitement pour
qu'on s'en aperçoive le jour où ça change.
"""
import numpy as np

from banc_recherche.reed_oscillator import FreeReedModel, Chamber, Slot


def _rm(**k):
    return FreeReedModel(n_modes=2, zeta=0.004, **k)


def test_amortissement_symetrique_et_dissipatif():
    rm = _rm()
    assert np.allclose(rm.C, rm.C.T, atol=1e-12)
    assert np.min(np.linalg.eigvalsh(rm.C)) > -1e-12


def test_ouverture_bornee():
    rm = _rm()
    s = rm.slot
    for tip in (-1e-2, -1e-4, 0.0, 1e-4, 1e-2):
        h = float(rm.opening(tip))
        assert s.leak_m - 1e-15 <= h <= s.max_open_m + 1e-15


def test_ouverture_asymetrique():
    """Anche libre : seul le déplacement qui dégage la fente ouvre. Une
    ouverture symétrique doublerait la fréquence de la note."""
    rm = _rm()
    ouvert = float(rm.opening(+3e-4))
    ferme = float(rm.opening(-3e-4))
    assert ouvert > ferme
    assert ferme == rm.slot.leak_m          # côté fermé : fuite résiduelle seule


def test_pas_de_debit_inverse():
    """La soupape bloque le retour d'air : débit nul en dépression."""
    rm = _rm()
    assert rm._flow_out(-500.0, 2e-4) == 0.0
    assert rm._flow_out(500.0, 2e-4) > 0.0


def test_equilibre_conserve_la_masse():
    """À l'équilibre, ce qui sort doit égaler ce qui entre."""
    rm = _rm()
    for q_in in (1e-5, 5e-5):
        st = rm.equilibrium(q_in)
        tip = float(rm.phi_tip @ st[rm.N:2 * rm.N])
        q_out = rm._flow_out(st[2 * rm.N], float(rm.opening(tip)))
        assert abs(q_out - q_in) / q_in < 1e-6


def test_equilibre_est_un_point_fixe():
    """La dérivée doit s'annuler à l'équilibre (hors bruit numérique)."""
    rm = _rm()
    st = rm.equilibrium(5e-5)
    d = rm.deriv(st, 5e-5)
    assert np.max(np.abs(d[:2 * rm.N])) < 1e-6


def test_simulation_reste_physique():
    """Pas de divergence, et des valeurs d'accordéon : course sous le
    millimètre, surpression raisonnable, ouverture dans ses bornes."""
    rm = _rm()
    r = rm.simulate(0.05, fs=44100.0, q_in=5e-5, oversample=8)
    assert np.isfinite(r.pressure).all() and np.isfinite(r.tip).all()
    assert np.ptp(r.tip) < 1.5e-3
    assert 0.0 < r.pressure.max() < 5000.0
    assert (r.opening >= rm.slot.leak_m - 1e-15).all()
    assert (r.opening <= rm.slot.max_open_m + 1e-15).all()


def test_l_ecoulement_dissipe_plus_que_l_anche_seule():
    """Constat central de l'analyse de stabilité : le couplage à l'écoulement
    **ajoute** de l'amortissement au lieu d'en retirer. À 5e-5 m³/s le taux de
    croissance vaut ≈ -40 s⁻¹, soit une quinzaine de fois l'amortissement
    propre de l'anche (-ζω ≈ -2,6 s⁻¹). C'est précisément pour cela que le
    modèle ne s'auto-entretient pas : la boucle est à rétroaction négative."""
    rm = _rm()
    r, _, _ = rm.growth_rate(5e-5)
    amortissement_propre = -rm.zeta * rm.omega[0]
    assert r < 0
    assert r < 5 * amortissement_propre        # nettement plus amorti (r plus négatif)


def test_pas_d_auto_oscillation_revendiquee():
    """CONSTAT, à faire évoluer : sur toute la plage de débit testée,
    l'équilibre reste stable. Le modèle ne s'auto-entretient pas encore.
    Si ce test échoue un jour, c'est une bonne nouvelle — mettre à jour
    docs/audit_modele_anche.md."""
    rm = _rm()
    for q_in in (1e-6, 1e-5, 1e-4, 1e-3):
        assert rm.growth_rate(q_in)[0] < 0.0
    assert rm.hopf_threshold() is None
