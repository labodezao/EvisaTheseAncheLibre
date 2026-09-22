"""Garde-fous du modèle d'anche libre alimenté en débit.

Ces tests figent des propriétés **physiques**, pas seulement numériques :
conservation de la masse, bornes et asymétrie de l'ouverture, amortissement
valide, et surtout l'**auto-oscillation** — existence d'une bande de débit
instable, bornée en bas (seuil de démarrage) et en haut (étouffement quand la
languette est soufflée hors de la fente et cesse de moduler le débit).

`instability_band` est appelée avec un balayage grossier (`n_scan=14`) : on
teste la présence et l'ordre des seuils, pas leur précision — sinon la suite
passe de 2 à 80 secondes.
"""
import os

import numpy as np
import pytest

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
    """À l'équilibre, ce qui sort égale ce que la source **fournit réellement**.

    Ce n'est pas la consigne `q₀` : la source a une impédance interne finie et
    débite `q₀ − p/R`. Confondre les deux ferait croire à une fuite.
    """
    rm = _rm()
    for q_in in (1e-5, 5e-5):
        st = rm.equilibrium(q_in)
        p = st[2 * rm.N]
        tip = float(rm.phi_tip @ st[rm.N:2 * rm.N])
        q_out = rm._flow_out(p, float(rm.opening(tip)))
        q_fourni = rm.source_flow(q_in, p)
        assert abs(q_out - q_fourni) / q_fourni < 1e-6


def test_source_ideale_fournit_la_consigne():
    """Impédance infinie = source de débit idéale : elle fournit exactement la
    consigne, quelle que soit la pression."""
    from banc_recherche.reed_oscillator import Source
    rm = _rm(source=Source(impedance_pa_s_m3=float("inf")))
    assert rm.source_flow(1e-5, 500.0) == 1e-5
    st = rm.equilibrium(1e-5)
    tip = float(rm.phi_tip @ st[rm.N:2 * rm.N])
    q_out = rm._flow_out(st[2 * rm.N], float(rm.opening(tip)))
    assert abs(q_out - 1e-5) / 1e-5 < 1e-6


def test_source_molle_debite_moins_sous_pression():
    """Une source réelle débite moins quand la pression monte — c'est cette
    pente qui borne l'amplitude de l'anche."""
    from banc_recherche.reed_oscillator import Source
    rm = _rm(source=Source(impedance_pa_s_m3=2.0e8))
    assert rm.source_flow(1e-5, 0.0) == 1e-5
    assert rm.source_flow(1e-5, 500.0) < 1e-5


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


def test_hors_bande_l_ecoulement_decouple_completement():
    """Au-dessus de l'étouffement, l'écoulement ne dissipe pas : il **lâche**.

    La languette est soufflée hors de la fente, l'ouverture sature, donc
    `∂h/∂y = 0` : le déplacement ne module plus rien. Et comme une anche
    libre ne comprime pas sa chambre (`Slot.sweep_coupling = 0`), il ne reste
    aucun chemin de `ẏ` vers `p`. L'anche est rendue à elle-même et décroît à
    son propre amortissement, `-ζω₁`, à la virgule près.

    Ce test affirmait l'inverse — « l'écoulement dissipe quinze fois plus que
    l'anche », ≈ -40 s⁻¹ contre -2,6. Ces 40 s⁻¹ étaient produits par le
    terme de balayage fantôme, pas par l'écoulement. En le retirant, le taux
    tombe pile sur `-ζω₁`. L'ancien chiffre mesurait un bug.
    """
    rm = _rm()
    _, haut = rm.instability_band(n_scan=14)
    assert haut is not None
    q_trop = haut[0] * 5.0
    r, _, _ = rm.growth_rate(q_trop)
    assert r < 0
    assert abs(r - (-rm.zeta * rm.omega[0])) < 1e-6 * rm.omega[0]


def test_bande_d_instabilite_existe():
    """L'anche s'auto-entretient : il existe une bande de débit où l'équilibre
    est instable. Bornée EN BAS (pas assez d'énergie pour démarrer) et EN HAUT
    (languette soufflée hors de la fente, l'ouverture sature, ∂h/∂y = 0 : elle
    ne module plus le débit) — l'étouffement quand on pousse trop fort."""
    rm = _rm()
    bas, haut = rm.instability_band(n_scan=14)
    assert bas is not None, "le modèle doit démarrer quelque part"
    assert haut is not None, "et s'étouffer quand on pousse trop fort"
    q_on, p_on, f_on = bas
    q_off, p_off, _ = haut
    assert q_off > q_on
    assert 1.0 < p_on < 500.0          # seuil de démarrage d'ordre physique
    assert p_off > p_on


def test_la_note_est_celle_de_la_lame():
    """Une anche libre chante **la note de sa lame**. C'est tout le métier de
    l'accordeur : on lime la languette, la note suit. Le modèle doit donc
    tomber à quelques dizaines de cents de la fréquence propre — pas à une
    tierce.

    Ce test a longtemps toléré `1.0 < f_on/f_anche < 1.4`, soit jusqu'à
    +580 cents, et laissait passer un modèle qui sortait +267 cents (une
    tierce mineure au-dessus). La borne lâche cachait le terme de balayage
    fantôme corrigé dans `Slot.sweep_coupling`. Une borne large ne teste
    rien : c'est la leçon à retenir de ce garde-fou.
    """
    rm = _rm()
    bas, _ = rm.instability_band(n_scan=14)
    assert bas is not None
    cents = 1200 * np.log2(bas[2] / rm.f_modes[0])
    assert -50.0 < cents < 80.0, f"note à {cents:+.0f} cents de la lame"


def test_saturation_de_l_ouverture_eteint_l_oscillation():
    """Mécanisme de l'étouffement : au-dessus du seuil haut la languette est
    soufflée hors de la fente, l'ouverture sature, et l'équilibre redevient
    stable."""
    rm = _rm()
    _, haut = rm.instability_band(n_scan=14)
    assert haut is not None
    q_trop = haut[0] * 3.0
    assert rm.growth_rate(q_trop)[0] < 0
    st = rm.equilibrium(q_trop)
    tip = float(rm.phi_tip @ st[rm.N:2 * rm.N])
    assert float(rm.opening(tip)) >= rm.slot.max_open_m - 1e-12


def test_la_chambre_geometrique_suffit_a_demarrer():
    """Il fallait auparavant gonfler le volume à 40 cm³ pour obtenir un
    démarrage — cinq fois la chambre réelle. Ce n'était pas de la physique
    mais le symptôme du balayage fantôme : une fois celui-ci retiré, la
    chambre qu'on peut mesurer au pied à coulisse (35×15×15 mm) suffit.
    """
    from banc_recherche.reed_oscillator import Chamber
    rm = FreeReedModel(n_modes=2, zeta=0.004, chamber=Chamber(volume_m3=7.9e-6))
    assert rm.instability_band(n_scan=14)[0] is not None


def test_la_languette_libre_ne_comprime_pas_la_chambre():
    """La distinction anche libre / anche battante, dans un seul coefficient.

    Une anche battante est plaquée sur la table : elle ferme l'ouverture,
    c'est un piston dans la paroi, son balayage comprime l'air. Une anche
    libre est *dans* sa fente : ce qu'elle déplace transite par la fente
    elle-même. Compter son balayage revient à compter son déplacement deux
    fois — `opening()` le prend déjà en charge.

    Le prix de l'erreur, mesuré : une raideur d'air parasite qui remontait la
    note de **+267 cents** et interdisait le démarrage avec la chambre
    réelle. On fige ici les deux symptômes.
    """
    rm = _rm()
    assert rm.slot.sweep_coupling == 0.0, "une anche libre ne comprime pas"

    battante = _rm(slot=Slot(sweep_coupling=1.0))
    bas_libre, _ = rm.instability_band(n_scan=14)
    bas_battante, _ = battante.instability_band(n_scan=14)
    assert bas_libre is not None
    assert bas_battante is None, (
        "avec le balayage compté, la chambre réelle ne démarrait plus")


@pytest.mark.skipif(not os.environ.get("BANC_TESTS_LENTS"),
                    reason="~40 s : lancer avec BANC_TESTS_LENTS=1")
def test_hysterese_sous_critique():
    """La bifurcation est **sous-critique** : en repartant d'un cycle établi et
    en baissant la consigne, l'oscillation persiste EN DESSOUS du seuil de
    démarrage. C'est `p_on > p_off`, ce que mesure `seuil.py` au banc par
    rampe montante puis descendante — et ce que font les anches réelles.

    Coûteux (il faut établir un cycle limite) : hors suite par défaut, qui
    tient en quelques secondes.

    ⚠️ Ne pas y réinscrire de chiffres de référence sans les avoir remesurés.
    Les précédents (p_on 25,8 Pa, p_off 19,4 Pa, rapport 1,33) dataient du
    modèle d'avant `Slot.sweep_coupling` et d'avant la dichotomie de
    `equilibrium` ; ils ne valent plus rien. Le test vérifie la **propriété**
    — le cycle survit sous le seuil de démarrage, donc la bifurcation est
    sous-critique — et c'est elle qui compte pour la thèse, pas la valeur.
    """
    rm = _rm()
    h = rm.extinction_threshold(mults=(0.90,), dur=1.0, oversample=8, start_mult=2.5)
    assert np.isfinite(h["p_on"]) and h["p_on"] > 0
    assert np.isfinite(h["p_off"]), "le cycle doit survivre sous le seuil de démarrage"
    assert h["p_off"] < h["p_on"]
    assert h["ratio"] > 1.0
