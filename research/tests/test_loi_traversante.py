"""Loi de passage « traversante » de l'anche libre (accordéon).

Audit du 23/11/2026. L'ouverture écrêtée `clip(y + h0, fuite, max_open)` ferme
l'anche la moitié de la période (débit haché, centroïde 9 kHz contre 1,5 kHz
sur l'enregistrement) et sa butée haute couche l'anche à forte pression (les
notes aiguës s'éteignent). La loi traversante est celle de
`coupled_reeds.ReedSetting.gap` : section = largeur x racine(gap² + jeu²),
sans butée haute. Réglage « e3 » d'un plan fractionné hors moteur.

Ce fichier garde aussi l'ancienne loi (`loi='ecretee'`), qui n'a rien perdu.
La partie Python n'a besoin que de numpy ; ce qui passe par le noyau C saute
sans compilateur.
"""
import ctypes

import numpy as np
import pytest

from banc_recherche import coupled_reeds, embedded as emb, hybrid, live
from banc_recherche.soufflet import pression_demandee

SR = 48000.0

sans_compilateur = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")


def f_de(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _rendre_c(n, e, loi, duree=1.0, sortie=emb.SORTIE_RAYONNEE,
              source_impedance=None):
    """Une note, pression constante `pression_demandee(e)`, par le noyau C.
    `source_impedance` : fixée à la voix si donnée, sinon la loi de la note."""
    kw = {} if source_impedance is None else {'source_impedance': source_impedance}
    v = hybrid.accordeon(f_de(n), loi=loi, **kw)
    p = emb.params_from_voice(v, samplerate=SR, name='accordeon', sortie=sortie)
    cp, garde = live._to_c_params(p)
    niveau = float(pression_demandee(e)) / v.exciter.source_impedance
    voix = live.Voice()
    voix.note_on(cp, n, niveau)
    sortie_c = np.empty(int(duree * SR), np.float32)
    bloc = np.zeros(512, np.float32)
    lib = live.engine_library()
    for i in range(0, len(sortie_c), 512):
        bloc[:] = 0.0
        lib.hv_render(ctypes.byref(voix.params), ctypes.byref(voix.state),
                      ctypes.c_float(niveau), bloc, 512)
        sortie_c[i:i + 512] = bloc[:min(512, len(sortie_c) - i)]
    return sortie_c.astype(float), garde


def _niveau_db(x, fin=0.2):
    x = np.asarray(x, float)[-int(fin * SR):]
    return 20 * np.log10(max(np.sqrt(np.mean((x - x.mean()) ** 2)), 1e-30))


def _centroide(x, fin=0.2):
    x = np.asarray(x, float)[-int(fin * SR):]
    x = x - x.mean()
    a = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 16))
    fr = np.fft.rfftfreq(1 << 16, 1 / SR)
    return float((fr * a).sum() / a.sum())


# -- la loi elle-même ----------------------------------------------------------

def test_l_accordeon_prend_la_loi_traversante_et_le_reglage_e3():
    ex = hybrid.accordeon(110.0).exciter
    assert ex.loi == 'traversante'
    assert ex.q == 60.0
    assert ex.plate_m == pytest.approx(1.2e-3)
    assert ex.tongue_m == pytest.approx(0.4e-3)
    assert ex.clearance_m == pytest.approx(15e-6)
    assert ex.rest_offset_m == pytest.approx(0.10e-3)


def test_les_cotes_de_la_fente_suivent_la_note_comme_les_autres():
    r = 220.0 / 110.0
    ex = hybrid.accordeon(220.0).exciter
    assert ex.plate_m == pytest.approx(1.2e-3 / r)
    assert ex.tongue_m == pytest.approx(0.4e-3 / r)
    assert ex.clearance_m == pytest.approx(15e-6 / r)


def test_l_ancienne_loi_reste_disponible_telle_quelle():
    ex = hybrid.accordeon(110.0, loi='ecretee').exciter
    assert ex.loi == 'ecretee' and ex.q == 125.0
    for y in (-3e-4, 0.0, 2e-4, 9e-4):
        attendu = float(np.clip(y + ex.rest_offset_m, ex.leak_m, ex.max_open_m))
        assert ex.opening(np.array([y, 0.0])) == attendu


def test_la_loi_par_defaut_de_l_excitateur_nu_est_l_ancienne():
    """Les autres usages de `FreeReedExciter` ne changent pas."""
    assert hybrid.FreeReedExciter().loi == 'ecretee'


def test_une_loi_inconnue_est_refusee():
    with pytest.raises(ValueError):
        hybrid.FreeReedExciter(loi='inventee')
    with pytest.raises(ValueError):
        hybrid.accordeon(110.0, loi='inventee')


def test_le_gap_du_moteur_est_celui_de_coupled_reeds():
    """Même loi que `ReedSetting.gap`, lue dans le sens du moteur (y > 0 ouvre,
    donc déplacement `-y` pour `coupled_reeds`)."""
    ex = hybrid.accordeon(110.0).exciter
    st = coupled_reeds.ReedSetting(lift_m=ex.rest_offset_m, plate_m=ex.plate_m,
                                   tongue_m=ex.tongue_m,
                                   clearance_m=ex.clearance_m)
    for y in np.linspace(-2.5e-3, 1.5e-3, 81):
        assert ex.gap(y) == pytest.approx(st.gap(-y), abs=1e-15)


def test_la_languette_traverse_sa_fente_sans_butee_haute():
    ex = hybrid.accordeon(110.0).exciter
    h0, c = ex.rest_offset_m, ex.clearance_m
    # au repos : levée h0 (la fente tient le jeu en plus, en quadrature)
    assert ex.opening(np.array([0.0, 0.0])) == pytest.approx(np.hypot(h0, c))
    # dans la fente : il ne reste que le jeu latéral
    assert ex.opening(np.array([-(h0 + 0.5 * ex.tongue_m), 0.0])) == \
        pytest.approx(c)
    # ressortie de l'autre côté : le passage se rouvre
    sortie = -(h0 + ex.tongue_m + ex.plate_m + 2e-4)
    assert ex.opening(np.array([sortie, 0.0])) == pytest.approx(np.hypot(2e-4, c))
    # aucune butée haute : plus ouverte que `max_open_m`
    assert ex.opening(np.array([5 * ex.max_open_m, 0.0])) > 5 * ex.max_open_m


# -- elle parle, de 0,3 à 1,0, sur toute la tessiture (noyau C) -----------------

@sans_compilateur
@pytest.mark.parametrize("note", [45, 52, 57, 64, 69, 76, 84])
def test_la_loi_traversante_parle_de_0_3_a_1_0(note):
    for e in (0.3, 0.5, 0.8, 1.0):
        x, _ = _rendre_c(note, e, 'traversante')
        assert _niveau_db(x) > -70.0, f"muette : note {note}, expression {e}"


@sans_compilateur
def test_la_loi_traversante_ne_s_eteint_pas_a_forte_pression():
    """Là où l'écrêtée couche l'anche (niveau nul, mesuré à -600 dB), la
    traversante reste à son niveau : c'est la butée haute qui était fautive."""
    for note, e in ((69, 0.8), (69, 1.0), (76, 0.8), (84, 1.0)):
        ancienne, _ = _rendre_c(note, e, 'ecretee')
        nouvelle, _ = _rendre_c(note, e, 'traversante')
        assert _niveau_db(ancienne) < -80.0, f"l'ancienne parle : {note} {e}"
        assert _niveau_db(nouvelle) > -60.0, f"s'éteint : {note} {e}"


@sans_compilateur
@pytest.mark.parametrize("note, e", [(57, 0.5), (57, 0.8), (69, 0.5), (76, 0.5)])
def test_le_centroide_de_la_traversante_est_plus_bas_que_celui_de_l_ecretee(note, e):
    trav, _ = _rendre_c(note, e, 'traversante')
    ecre, _ = _rendre_c(note, e, 'ecretee')
    assert _centroide(trav) < 0.7 * _centroide(ecre)


@sans_compilateur
def test_le_niveau_monte_avec_la_pression():
    niv = [_niveau_db(_rendre_c(57, e, 'traversante')[0])
           for e in (0.3, 0.5, 0.8, 1.0)]
    assert all(b > a + 3.0 for a, b in zip(niv, niv[1:]))


# -- le noyau C et la référence Python donnent le même son ----------------------

def _params(note, loi='traversante', sortie=None):
    # R = 2e8 fixe : ces tests posent un niveau en m³/s calculé pour 2e8
    return emb.params_from_voice(hybrid.accordeon(f_de(note), loi=loi,
                                                  source_impedance=2.0e8),
                                 samplerate=SR, name='accordeon', sortie=sortie)


def test_les_parametres_embarques_portent_la_loi():
    p = _params(57)
    assert p.loi == 'traversante' and p.reed_q == 60.0
    assert p.plate_m > 0 and p.tongue_m > 0 and p.clearance_m > 0
    assert _params(57, loi='ecretee').loi == 'ecretee'


def test_la_table_c_exportee_porte_la_loi():
    assert ".free_law = 1," in emb.to_c_params(_params(57))
    assert ".free_law = 0," in emb.to_c_params(_params(57, loi='ecretee'))
    assert "HV_LAW_THROUGH" in emb.to_c_engine()['hybrid_voice.h']


@sans_compilateur
@pytest.mark.parametrize("note, e", [(45, 0.8), (57, 0.5), (69, 1.0), (76, 0.3)])
@pytest.mark.parametrize("sortie", [emb.SORTIE_RAYONNEE, emb.SORTIE_PRESSION])
def test_le_noyau_c_suit_la_reference_python_en_loi_traversante(note, e, sortie):
    p = _params(note, sortie=sortie)
    niveau = float(pression_demandee(e)) / 2.0e8
    cp, garde = live._to_c_params(p)
    v = live.Voice()
    v.note_on(cp, note, niveau)
    bloc = np.zeros(256, np.float32)
    morceaux = []
    for _ in range(2):
        v.render(bloc, glide=1.0)
        morceaux.append(bloc.copy())
    c = np.concatenate(morceaux).astype(float)
    py, _ = emb.RealtimeVoice(p).render(512, niveau)
    # float32 contre float64 pendant la montée d'amplitude : l'écart relatif y
    # est amplifié (jusqu'à 3e-2 mesuré ici, 1e-1 pour l'ancienne loi sur le
    # même banc). Ce qui prouve le portage, c'est le test suivant (niveau et
    # timbre sur 0,6 s) ; celui-ci attrape un noyau qui n'applique pas la loi.
    assert np.max(np.abs(c - py)) < 5e-2 * np.std(py)


@sans_compilateur
@pytest.mark.parametrize("note, e", [(57, 0.5), (69, 0.8)])
def test_le_noyau_c_et_python_ont_meme_niveau_et_meme_hauteur(note, e):
    """Plus longtemps, le déphasage s'accumule (float32 : un à trois cents) et
    le point à point ne tient plus : on compare ce qu'on entend, niveau et
    hauteur."""
    p = _params(note)
    niveau = float(pression_demandee(e)) / 2.0e8
    py, _ = emb.RealtimeVoice(p).render(int(0.6 * SR), niveau)
    c, _ = _rendre_c(note, e, 'traversante', duree=0.6, source_impedance=2.0e8)
    assert abs(_niveau_db(py) - _niveau_db(c)) < 0.5
    assert abs(_centroide(py) - _centroide(c)) < 0.1 * _centroide(py)
