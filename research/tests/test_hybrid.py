"""Modèle hybride généralisé : résonateur, excitateurs, moteur temps réel.

Les tests lents (simulations complètes) sont derrière `BANC_TESTS_LENTS=1` :
une voix coûte quelques secondes, et une suite qu'on n'ose plus lancer ne
sert à rien.
"""
import os

import numpy as np
import pytest

from banc_recherche import hybrid, embedded as emb, identify as idf

LENT = pytest.mark.skipif(not os.environ.get('BANC_TESTS_LENTS'),
                          reason="lent : BANC_TESTS_LENTS=1 pour l'activer")

SR = 44100.0


def _ton(f0, dur=0.5, sr=SR, rangs=(1.0,)):
    t = np.arange(int(dur * sr)) / sr
    return sum(a * np.sin(2 * np.pi * f0 * (k + 1) * t)
               for k, a in enumerate(rangs))


# =============================================================================
# Résonateur
# =============================================================================

def test_bore_modes_cylindrique_ne_donne_que_les_impairs():
    m = hybrid.bore_modes(100.0, n_modes=5, kind='cylindrique')
    assert [round(x.freq_hz) for x in m] == [100, 300, 500, 700, 900]


def test_bore_modes_conique_donne_la_serie_complete():
    m = hybrid.bore_modes(100.0, n_modes=5, kind='conique')
    assert [round(x.freq_hz) for x in m] == [100, 200, 300, 400, 500]


def test_bore_modes_refuse_une_perce_inconnue():
    with pytest.raises(ValueError):
        hybrid.bore_modes(100.0, kind='rectangulaire')


def test_z_char_decroit_avec_le_carre_du_diametre():
    # doubler le diamètre quadruple la section, donc divise Z_c par quatre
    assert hybrid.z_char(5e-3) / hybrid.z_char(10e-3) == pytest.approx(4.0)
    # une bombarde oppose bien plus qu'une clarinette : c'est tout son caractère
    assert hybrid.z_char(5e-3) > 5 * hybrid.z_char(14.6e-3)


def test_string_modes_eteint_le_mode_au_noeud_d_archet():
    """À β = 1/7, l'archet touche le nœud du 7ᵉ mode : il ne peut pas l'exciter."""
    m = hybrid.string_modes(100.0, n_modes=10, beta=1.0 / 7.0)
    pics = {round(x.freq_hz): x.peak for x in m}
    assert pics[700] < 1e-6 * max(pics.values())


def test_string_modes_amortit_les_aigus_quand_on_le_demande():
    plat = hybrid.string_modes(100.0, 8, q=500.0, q_decay=0.0)
    penche = hybrid.string_modes(100.0, 8, q=500.0, q_decay=1.0)
    assert plat[-1].q == pytest.approx(plat[0].q)
    assert penche[-1].q < 0.2 * penche[0].q


def test_string_modes_inharmonicite_etire_les_aigus():
    droit = hybrid.string_modes(100.0, 6, inharmonicity=0.0)
    raide = hybrid.string_modes(100.0, 6, inharmonicity=1e-3)
    assert raide[-1].freq_hz > droit[-1].freq_hz
    assert raide[0].freq_hz == pytest.approx(droit[0].freq_hz, rel=1e-3)


def test_resonator_sans_mode_ni_cavite_ne_repond_rien():
    r = hybrid.Resonator()
    assert r.n_state == 0
    assert r.response(np.zeros(0)) == 0.0


def test_compliance_repond_au_continu_la_ou_un_mode_ne_repond_pas():
    """Toute la différence entre une chambre fermée et un tuyau ouvert.

    Sous un débit **constant**, la pression d'une cavité monte sans cesse —
    c'est le ressort d'air qu'on comprime. Celle d'un tuyau ouvert reste
    bornée : souffler continûment dans une clarinette n'y installe aucune
    surpression statique. C'est pour cette raison, et pour elle seule, qu'une
    anche libre impose sa hauteur là où une anche de clarinette la reçoit.
    """
    def integre(res, drive, dt, n):
        s = np.zeros(res.n_state)
        trace = np.empty(n)
        for i in range(n):
            s = s + res.deriv(s, drive=drive) * dt
            trace[i] = res.response(s)
        return trace

    cav = integre(hybrid.Resonator(compliance=hybrid.chamber_compliance(40e-6)),
                  1e-6, 1e-6, 4000)
    # sous débit constant la pression monte **linéairement** : p(4t) = 4·p(t)
    assert cav[999] > 0
    assert cav[3999] / cav[999] == pytest.approx(4.0, rel=0.02)

    tuy = integre(hybrid.Resonator(hybrid.bore_modes(200.0, 4)), 1e-6, 1e-7, 4000)
    seconde_moitie = np.abs(tuy[len(tuy) // 2:]).max()
    assert seconde_moitie < 5 * np.abs(tuy[:len(tuy) // 2]).max()   # borné


def test_chamber_compliance_croit_avec_le_volume():
    assert (hybrid.chamber_compliance(80e-6)
            == pytest.approx(2 * hybrid.chamber_compliance(40e-6)))


# =============================================================================
# Détection de hauteur — les deux pièges dans lesquels je suis tombé
# =============================================================================

@pytest.mark.parametrize("f0", [110.0, 147.0, 440.0])
def test_playing_frequency_sur_signaux_connus(f0):
    t = np.arange(int(0.3 * SR)) / SR
    for sig in (np.sin(2 * np.pi * f0 * t),
                np.sign(np.sin(2 * np.pi * f0 * t)),
                2 * ((f0 * t) % 1) - 1):
        assert hybrid.playing_frequency(sig, SR) == pytest.approx(f0, rel=2e-3)


def test_playing_frequency_ne_tombe_pas_l_octave_en_dessous():
    """Régression : un signal riche corrèle presque autant à 2 ou 3 périodes.

    Mesuré sur le violon, ac valait 0,8800 à trois périodes contre 0,8781 à
    une seule — 0,2 % d'écart faisait annoncer f0/3.
    """
    t = np.arange(int(0.3 * SR)) / SR
    riche = sum(np.sin(2 * np.pi * 220.0 * k * t) / k for k in range(1, 16))
    assert hybrid.playing_frequency(riche, SR) == pytest.approx(220.0, rel=2e-3)


def test_playing_frequency_ignore_le_lobe_principal():
    """Régression : près du retard zéro l'autocorrélation vaut encore ~1.

    Un `argmax` brut y trouvait son maximum et renvoyait `nan` ou n'importe
    quelle fréquence aiguë.
    """
    t = np.arange(int(0.3 * SR)) / SR
    carre = np.sign(np.sin(2 * np.pi * 147.0 * t))
    assert hybrid.playing_frequency(carre, SR, fmax=8000.0) == pytest.approx(147.0, rel=3e-3)


def test_playing_frequency_avoue_son_ignorance():
    assert np.isnan(hybrid.playing_frequency(np.zeros(4096), SR))
    assert np.isnan(hybrid.playing_frequency(np.ones(10), SR))


# =============================================================================
# Excitateurs
# =============================================================================

def test_anche_simple_se_ferme_sous_la_pression():
    """Une anche battante cède à la pression : c'est l'inverse de l'anche libre."""
    ex = hybrid.SingleReedExciter()
    d, q = ex.deriv(np.zeros(2), response=0.0, level=ex.closing_pressure_pa * 0.5)
    assert d[1] < 0                      # poussée vers la fermeture
    assert q > 0                         # mais elle laisse encore passer


def test_anche_simple_ne_debite_plus_une_fois_plaquee():
    ex = hybrid.SingleReedExciter()
    _, q = ex.deriv(np.array([-ex.rest_opening_m * 2, 0.0]), 0.0, 3000.0)
    assert q == pytest.approx(0.0)


def test_anche_libre_s_ouvre_sous_la_pression():
    """Signe opposé à l'anche battante — l'asymétrie qui fait l'accordéon."""
    ex = hybrid.FreeReedExciter()
    d, _ = ex.deriv(np.zeros(2), response=200.0, level=0.0)
    assert d[1] > 0


def test_anche_libre_interdit_le_debit_inverse():
    """La soupape de cuir : pas de retour à travers la fente."""
    ex = hybrid.FreeReedExciter(source_impedance=float('inf'))
    _, net = ex.deriv(np.zeros(2), response=-500.0, level=0.0)
    assert net == pytest.approx(0.0)


def test_frottement_archet_s_effondre_avec_le_glissement():
    """La pente négative de μ(v) : ce qui rend l'archet capable d'entretenir."""
    ex = hybrid.BowExciter()
    lent = ex.friction(0.001)
    vite = ex.friction(1.0)
    assert lent > vite > 0
    assert lent == pytest.approx(ex.mu_static, rel=0.05)
    assert ex.friction(-0.5) == pytest.approx(-ex.friction(0.5))


def test_build_refuse_un_instrument_inconnu():
    with pytest.raises(ValueError, match="inconnu"):
        hybrid.build('theremine')


def test_tous_les_instruments_se_construisent():
    for nom in hybrid.INSTRUMENTS:
        v = hybrid.build(nom)
        assert isinstance(v, hybrid.HybridVoice)
        assert nom in hybrid.FAMILIES


# =============================================================================
# Descripteurs d'identification
# =============================================================================

def test_odd_even_separe_cylindrique_et_conique():
    impairs = np.array([0., -60., -8., -60., -16., -60., -24., -60.])
    complet = np.array([0., -3., -6., -9., -12., -15., -18., -21.])
    assert idf.odd_even_ratio(impairs) > 20
    assert abs(idf.odd_even_ratio(complet)) < 10
    assert idf.bore_kind_from_sound(impairs) == 'cylindrique'
    assert idf.bore_kind_from_sound(complet) == 'conique'


def test_position_d_archet_lue_dans_le_creux():
    niv = -3.0 * np.arange(12)
    niv[6] -= 30.0                       # 7ᵉ partiel éteint -> β = 1/7
    assert idf.bow_position_from_sound(niv) == pytest.approx(1.0 / 7.0)


def test_position_d_archet_avoue_quand_il_n_y_a_pas_de_creux():
    assert np.isnan(idf.bow_position_from_sound(-3.0 * np.arange(12)))


def test_pente_spectrale_sur_une_dent_de_scie():
    """1/n en amplitude, c'est −6 dB par octave de rang."""
    n = np.arange(1, 17, dtype='float64')
    assert idf.spectral_decay(20 * np.log10(1.0 / n)) == pytest.approx(-6.0, abs=0.1)


def test_harmonic_levels_retrouve_des_rangs_imposes():
    y = _ton(200.0, rangs=(1.0, 0.5, 0.25))
    niv = idf.harmonic_levels(y, SR, 200.0, n_partials=3)
    assert niv[0] == pytest.approx(0.0, abs=0.5)
    assert niv[1] == pytest.approx(-6.0, abs=1.5)
    assert niv[2] == pytest.approx(-12.0, abs=1.5)


def test_identify_refuse_un_instrument_inconnu():
    with pytest.raises(ValueError):
        idf.identify(_ton(200.0), SR, 'kazoo', f0_hz=200.0, fit_level=False)


def test_identify_refuse_un_son_sans_hauteur():
    with pytest.raises(ValueError, match="hauteur"):
        idf.identify(np.zeros(8192), SR, 'violon', fit_level=False)


def test_identify_separe_le_mesure_du_suppose():
    """Le cœur de l'honnêteté du module : ne jamais présenter l'un pour l'autre."""
    y = _ton(220.0, rangs=(1.0, 0.5, 0.33, 0.25, 0.2, 0.17, 0.02, 0.12))
    ident = idf.identify(y, SR, 'violon', f0_hz=220.0, fit_level=False)
    assert ident.mesure and ident.suppose
    assert not (set(ident.mesure) & set(ident.suppose))
    assert 'masse de corde' in ident.suppose
    texte = ident.rapport()
    assert 'MESURÉ' in texte and 'SUPPOSÉ' in texte


# =============================================================================
# Moteur temps réel et export C
# =============================================================================

def test_biquad_passe_bande_a_le_bon_sommet():
    fs, f0, q, pic = 48000.0, 1000.0, 20.0, 7.5
    b0, b1, b2, a1, a2 = emb.biquad_bandpass(f0, q, pic, fs)
    w = 2 * np.pi * f0 / fs
    z = np.exp(-1j * w)
    h = abs((b0 + b1 * z + b2 * z ** 2) / (1 + a1 * z + a2 * z ** 2))
    assert h == pytest.approx(pic, rel=0.02)


def test_biquad_passe_bande_annule_le_continu():
    """Un tuyau ouvert n'accumule pas de pression statique."""
    b0, b1, b2, a1, a2 = emb.biquad_bandpass(500.0, 30.0, 1.0, 48000.0)
    assert (b0 + b1 + b2) / (1 + a1 + a2) == pytest.approx(0.0, abs=1e-9)


def test_biquad_passe_bas_a_le_bon_gain_continu():
    g = -3.7
    b0, b1, b2, a1, a2 = emb.biquad_lowpass(2500.0, 4.0, g, 48000.0)
    assert (b0 + b1 + b2) / (1 + a1 + a2) == pytest.approx(g, rel=1e-6)


def test_biquad_refuse_au_dela_de_nyquist():
    assert emb.biquad_bandpass(30000.0, 10.0, 1.0, 48000.0) is None


def test_archet_sureechantillonne_plus_que_l_anche():
    """Mesuré : à K=4 le violon décroche à 91 Hz au lieu de 440."""
    assert emb.OVERSAMPLE_MIN[emb.FAMILY_BOW] > emb.OVERSAMPLE_MIN[emb.FAMILY_SINGLE_REED]
    p = emb.params_from_voice(hybrid.build('violon', 440.0))
    assert p.oversample == emb.OVERSAMPLE_MIN[emb.FAMILY_BOW]


def test_params_from_voice_couvre_les_trois_familles():
    attendu = {'clarinette': emb.FAMILY_SINGLE_REED,
               'bombarde': emb.FAMILY_SINGLE_REED,
               'accordeon': emb.FAMILY_FREE_REED,
               'violon': emb.FAMILY_BOW}
    for nom, fam in attendu.items():
        assert emb.params_from_voice(hybrid.build(nom)).family == fam


def test_litteraux_c_valides():
    """Régression : `%g` rend `0` pour zéro, et `0f` ne compile pas en C."""
    assert emb._f(0.0) == '0.0f'
    assert emb._f(float('nan')) == '0.0f'
    assert emb._f(float('inf')) == '0.0f'
    for v in (1.0, -2.5, 1e-9, 1e12, 0.0):
        s = emb._f(v)
        assert s.endswith('f')
        assert 'e' in s or 'E' in s or '.' in s


def test_identifiant_c_translittere_les_accents():
    """« accordéon » doit donner `accordeon`, pas `accord_on` ni un é brut."""
    assert emb._ident('accordéon') == 'accordeon'
    assert emb._ident('vielle à roue') == 'vielle_a_roue'
    assert emb._ident('') == 'voice'
    assert emb._ident('3cordes')[0].isalpha()


def test_export_c_produit_du_c_plausible():
    p = emb.params_from_voice(hybrid.build('clarinette', 147.0))
    src = emb.to_c_params(p)
    assert '#ifndef CLARINETTE_PARAMS_H' in src
    assert src.count('{') == src.count('}')
    assert ' 0f' not in src and ',0f' not in src
    moteur = emb.to_c_engine()
    assert set(moteur) == {'hybrid_voice.h', 'hybrid_voice.c'}
    assert 'malloc' not in moteur['hybrid_voice.c']      # temps réel : pas d'alloc
    assert 'printf' not in moteur['hybrid_voice.c']


def test_cout_cpu_croit_avec_le_nombre_de_modes():
    petit = emb.params_from_voice(hybrid.build('clarinette'))
    petit.modes = petit.modes[:4]
    gros = emb.params_from_voice(hybrid.build('clarinette'))
    assert (emb.cpu_estimate(petit)['mflops_per_voice']
            < emb.cpu_estimate(gros)['mflops_per_voice'])
    assert emb.cpu_estimate(gros, mcu_mflops=480.0)['voices'] > 1.0


def test_voix_temps_reel_demarre_et_reste_bornee():
    p = emb.params_from_voice(hybrid.build('clarinette', 147.0))
    a, _ = emb.RealtimeVoice(p).render(2048, 2500.0)
    assert np.all(np.isfinite(a))
    assert np.ptp(a) > 1.0


# -- les lents ----------------------------------------------------------------

@LENT
@pytest.mark.parametrize("nom,f0,lvl", [('clarinette', 147.0, 2500.0),
                                        ('saxophone', 233.0, 2200.0),
                                        ('vielle', 196.0, 1.2)])
def test_le_temps_reel_rejoint_le_modele_continu(nom, f0, lvl):
    """Le portage discret doit donner la **même note** que les équations."""
    v = hybrid.build(nom, f0)
    ref = v.simulate(0.3, fs=22050.0, level=lvl, oversample=8, settle=0.2)
    f_ref = hybrid.playing_frequency(ref.response, ref.fs)

    p = emb.params_from_voice(v, samplerate=48000.0)
    a, _ = emb.RealtimeVoice(p).render(int(0.5 * 48000), lvl)
    f_rt = hybrid.playing_frequency(a[int(0.3 * 48000):], 48000.0)

    assert abs(1200 * np.log2(f_rt / f_ref)) < 10.0     # moins d'un dixième de ton


@LENT
def test_clarinette_sonne_creux_et_saxophone_plein():
    """La perce décide du timbre, pas l'anche : même excitateur des deux côtés."""
    ecarts = {}
    for nom, f0, lvl in [('clarinette', 147.0, 2500.0), ('saxophone', 233.0, 2200.0)]:
        r = hybrid.build(nom, f0).simulate(0.3, fs=22050.0, level=lvl,
                                           oversample=8, settle=0.2)
        niv = idf.harmonic_levels(r.response, r.fs, f0, 10)
        ecarts[nom] = idf.odd_even_ratio(niv)
    assert ecarts['clarinette'] > 20.0
    assert ecarts['saxophone'] < 12.0


@LENT
def test_la_corde_frottee_suit_la_loi_de_helmholtz():
    """Vitesse de glissement = v_archet·(1−β)/β. Prédiction, pas réglage."""
    for nom, f0, beta in [('violon', 440.0, 1.0 / 7.0), ('vielle', 196.0, 1.0 / 9.0)]:
        v = hybrid.build(nom, f0)
        r = v.simulate(0.25, fs=22050.0, level=0.3, oversample=8, settle=0.15)
        attendu = v.exciter.bow_speed * (1 - beta) / beta
        assert np.max(np.abs(r.response)) == pytest.approx(attendu, rel=0.35)


@LENT
def test_identification_retrouve_la_perce_et_l_archet():
    """Bouclage : on synthétise, on oublie, on réidentifie."""
    r = hybrid.build('clarinette', 147.0).simulate(
        0.4, fs=22050.0, level=2500.0, oversample=8, settle=0.25)
    niv = idf.harmonic_levels(r.response, r.fs, 147.0, 16)
    assert idf.bore_kind_from_sound(niv) == 'cylindrique'

    r = hybrid.build('violon', 440.0).simulate(
        0.4, fs=22050.0, level=0.25, oversample=8, settle=0.25)
    niv = idf.harmonic_levels(r.response, r.fs, 440.0, 16)
    assert idf.bow_position_from_sound(niv) == pytest.approx(1.0 / 7.0)


# =============================================================================
# Perce réelle : pertes visco-thermiques, coupure, registre, justesse
# =============================================================================

def test_pertes_viscothermiques_suivent_racine_de_f():
    """Couche limite en 1/√f : `Q ∝ √f` et `Z ∝ 1/√f`, sans paramètre libre."""
    m = hybrid.bore_modes(100.0, n_modes=4, kind='conique', q=30.0, z_peak=1e7)
    for i, mode in enumerate(m):
        r = i + 1.0
        assert mode.q == pytest.approx(30.0 * np.sqrt(r), rel=1e-6)
        assert mode.peak == pytest.approx(1e7 / np.sqrt(r), rel=1e-6)


def test_la_coupure_de_reseau_eteint_les_aigus():
    """Benade : au-dessus de la coupure le réseau de trous laisse fuir.

    C'est ce mécanisme-là qui éteint les aigus d'un instrument à vent, pas la
    viscosité — qui les rend au contraire plus sélectifs.
    """
    libre = hybrid.bore_modes(200.0, 8, 'conique', z_peak=1e7)
    coupe = hybrid.bore_modes(200.0, 8, 'conique', z_peak=1e7, cutoff_hz=600.0)
    assert coupe[0].peak == pytest.approx(libre[0].peak, rel=0.05)   # sous la coupure
    assert coupe[-1].peak < 0.1 * libre[-1].peak                     # bien au-dessus


def test_les_modes_negligeables_sont_ecartes():
    """Un mode inaudible coûte un biquad sur la carte sans rien apporter."""
    beaucoup = hybrid.bore_modes(200.0, 16, 'conique', z_peak=1e7,
                                 cutoff_hz=500.0, prune_db=30.0)
    assert len(beaucoup) < 16
    pics = [m.peak for m in beaucoup]
    assert min(pics) >= max(pics) * 10 ** (-30.0 / 20.0)


def test_le_registre_donne_la_douzieme_ou_l_octave():
    """La perce décide du registre, et le modèle le retrouve seul.

    Cylindrique : résonances f0, 3f0, 5f0 → étouffer la première laisse 3f0,
    la douzième. Conique : f0, 2f0, 3f0 → l'octave. C'est ce qui sépare le
    doigté d'une clarinette de celui d'un saxophone.
    """
    for kind, attendu in (('cylindrique', 3.0), ('conique', 2.0)):
        modes = hybrid.bore_modes(200.0, 6, kind)
        ouvert = hybrid.register_vent(modes, kill=1)
        fort = max(range(len(ouvert)), key=lambda i: ouvert[i].peak)
        assert ouvert[fort].freq_hz / modes[0].freq_hz == pytest.approx(attendu)
        assert ouvert[0].peak < 0.1 * modes[0].peak


# -- le pont vers un calcul de perce (Tutti) ----------------------------------

def test_modes_from_cents_et_retour():
    """Aller-retour exact : la justesse entrée est la justesse relue."""
    cents = [0.0, -12.0, 7.0, 3.0, -5.0]
    m = hybrid.modes_from_cents(147.0, cents, kind='cylindrique')
    assert hybrid.inharmonicity_cents(m) == pytest.approx(cents, abs=1e-6)


def test_un_ecart_en_cents_est_un_rapport_pas_une_difference():
    """Piège classique : +1200 cents doit doubler la fréquence."""
    m = hybrid.modes_from_cents(100.0, [0.0, 1200.0], kind='conique')
    assert m[1].freq_hz == pytest.approx(400.0)      # 2·100 Hz, une octave au-dessus


def test_modes_from_partials_accepte_une_perce_quelconque():
    """Aucune série idéale imposée : on prend les résonances telles quelles."""
    mesure = [143.0, 431.0, 742.0, 1015.0]
    m = hybrid.modes_from_partials(mesure, q=40.0, z_peak=5e7)
    assert [round(x.freq_hz) for x in m] == mesure
    assert m[1].q > m[0].q                           # visco-thermique appliquée
    assert m[1].peak < m[0].peak


def test_modes_from_partials_accepte_des_Q_et_sommets_mesures():
    """Avec une mesure d'impédance complète, plus rien n'est supposé."""
    m = hybrid.modes_from_partials([100.0, 300.0], qs=[11.0, 22.0],
                                   peaks=[3e7, 1e7])
    assert [x.q for x in m] == [11.0, 22.0]
    assert [x.peak for x in m] == [3e7, 1e7]


def test_modes_from_partials_trie_et_refuse_le_vide():
    m = hybrid.modes_from_partials([300.0, 100.0, 200.0])
    assert [round(x.freq_hz) for x in m] == [100, 200, 300]
    with pytest.raises(ValueError):
        hybrid.modes_from_partials([0.0, -5.0, float('nan')])


def test_inharmonicity_devine_la_serie():
    conique = hybrid.bore_modes(100.0, 4, 'conique')
    cylindrique = hybrid.bore_modes(100.0, 4, 'cylindrique')
    assert hybrid.inharmonicity_cents(conique) == pytest.approx(np.zeros(4), abs=1e-6)
    assert hybrid.inharmonicity_cents(cylindrique) == pytest.approx(np.zeros(4), abs=1e-6)


@LENT
def test_la_hauteur_du_registre_suit_la_deuxieme_resonance():
    """La prédiction qui rend un calcul de perce utile ici.

    Au registre, c'est la **deuxième** résonance qui fait la note : la
    désaccorder de n cents décale la note jouée de n cents. C'est exactement
    le problème de justesse sur lequel travaille un facteur, et c'est ce qu'un
    calcul de perce (Tutti) sait chiffrer.
    """
    ex = hybrid.SingleReedExciter()
    z = 20 * hybrid.z_char(14.6e-3)

    def joue(c2):
        modes = hybrid.modes_from_cents(147.0, [0.0, c2] + [0.0] * 6,
                                        kind='cylindrique', q=40.0, z_peak=z,
                                        cutoff_hz=1500.0)
        v = hybrid.HybridVoice(ex, hybrid.Resonator(hybrid.register_vent(modes)))
        r = v.simulate(0.3, fs=22050.0, level=2500.0, oversample=8, settle=0.2)
        return hybrid.playing_frequency(r.response, r.fs)

    ref = joue(0.0)
    for c2 in (-20.0, 20.0, 40.0):
        ecart = 1200 * np.log2(joue(c2) / ref)
        assert abs(ecart - c2) < 5.0        # suivi au cent près, 5 de tolérance


def test_le_moteur_par_defaut_de_chaque_vent_est_celui_qui_joue_juste():
    """Choix mesuré, pas de principe : la clarinette (cylindre) joue juste
    par TUTT ; les coniques idéalisées à un tronçon y sautent à l'octave sur
    une partie de la tessiture (fondamental trop faible, cf. `_wind`), donc
    elles gardent la série postulée. Un changement ici doit être délibéré.
    """
    import inspect
    attendu = {'clarinette': 'tutt', 'saxophone': 'ideal',
               'bombarde': 'ideal', 'cornemuse': 'ideal'}
    for nom, moteur in attendu.items():
        d = inspect.signature(hybrid.INSTRUMENTS[nom]).parameters['engine'].default
        assert d == moteur, (nom, d)


def test_la_perce_decide_du_registre_et_pas_l_anche():
    """Même excitateur des deux côtés : seule la géométrie change, et c'est
    elle qui donne la douzième ou l'octave."""
    cyl = hybrid.clarinette(147.0, engine='tutt').resonator.modes
    cone = hybrid.saxophone(233.0, engine='tutt').resonator.modes
    assert 2.9 < cyl[1].freq_hz / cyl[0].freq_hz < 3.15      # douzième
    assert 1.9 < cone[1].freq_hz / cone[0].freq_hz < 2.2     # octave


def test_la_clarinette_tutt_reste_utilisable_en_ideal():
    """`engine='ideal'` doit rester un secours qui marche, pas juste un mot
    dans une docstring."""
    v = hybrid.clarinette(147.0, engine='ideal')
    assert v.resonator.n_modes > 0
    ratios = [m.freq_hz / v.resonator.modes[0].freq_hz for m in v.resonator.modes[:3]]
    assert ratios == pytest.approx([1.0, 3.0, 5.0], abs=1e-6)
