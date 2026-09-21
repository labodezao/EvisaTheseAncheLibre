"""Pont vers TUTT : lecture des perces, impédance d'entrée, résonances.

Les fichiers d'exemple sont fabriqués dans le test lui-même : la banque de
perces d'Ewen n'est pas versionnée (elle ne m'appartient pas), et un test qui
dépend d'un fichier absent est un test qui ne sert à rien.
"""
import pathlib

import numpy as np
import pytest

from banc_recherche import tutt

C = tutt.CELERITE


def _dat_cylindre(tmp_path, longueur=0.5, diametre=0.015, nom="tube d'essai"):
    """Fichier TUTT minimal : un seul tronçon cylindrique, bout ouvert."""
    tmp_path = pathlib.Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "cyl.dat"
    p.write_text(
        "VERSION FORMAT DE FICHIER D'ENTREE AVEC MENTION DE LA VERSION DE TUTT\n"
        "TUTT43_2024.11\n"
        f"{nom}\n"
        "PARAMETRES PHYSIQUES DE L' AIR :RHOA,P0,GAMMA,CV,ETA,TONEW,DLAMBA\n"
        "1.204 1.014E5  1.400  719. 1.8E-5 11.7 2.4E-2\n"
        "NOMBRE DE TRONCONS DE LA LIGNE (-1) N\n"
        "0\n"
        "BAS DE LIGNE OUVERT OU FERME C1 (0=OUVERT, 1=FERME)\n"
        "0\n"
        "TABLEAU PERCE D0 (DIMENSION N+1)\n"
        f"{diametre}\n"
        "TABLEAU PERCE DL (DIMENSION N+1)\n"
        f"{diametre}\n"
        "TABLEAU DES TRONCONS DE LA LIGNE PRINCIPALE L (DIMENSION N+1)\n"
        f"{longueur}\n"
        "TEMPERATURE DE L' AIR EN HAUT ET EN BAS DE LA LIGNE (CELSIUS)\n"
        "20. 20.\n"
        "FREQUENCE DU LA DE REFERENCE FLA\n"
        "415.\n"
        "DONNEES CONCERNANT L' EMBOUCHURE\n"
        "IFLUTE FCM FCP G0 LA0 alpha E0 V0 V1\n"
        "0 1.4 0. 9.5e-3 3.1e-3 1. 7.3e-4 26. 17.\n"
        "MREED KREED LBUCC TANDELTA\n"
        "0. 800. 0.1 1.\n", encoding='latin-1')
    return p


# =============================================================================
# Lecture
# =============================================================================

def test_read_dat_lit_la_geometrie(tmp_path):
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.52, 0.015))
    assert d.lengths == pytest.approx([0.52])
    assert d.d0 == pytest.approx([0.015])
    assert d.dl == pytest.approx([0.015])
    assert d.closed_bottom is False
    assert d.a4_hz == pytest.approx(415.0)
    assert d.total_length_m == pytest.approx(0.52)
    assert "essai" in d.title


def test_read_dat_lit_l_embouchure(tmp_path):
    """`IFLUTE` dit l'inverse de son nom, et `V0` n'est pas un volume.

    Le source de TUTT tranche les deux : `IFLUTE ∈ {1,2}` désigne une anche
    **solide**, toute autre valeur une anche aérienne (un jet de flûte) ; et
    `V EST LA VITESSE DU JET`, donc `V0`/`V1` sont des **m/s**.

    Je m'étais trompé sur les deux, et le second m'aurait fait poser une
    cavité de 26 cm³ là où le fichier dit 26 m/s.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path))
    assert d.solid_reed is False        # IFLUTE = 0 -> anche aérienne
    assert d.air_reed is True
    assert d.jet_velocity_ms == pytest.approx((26.0, 17.0))
    assert d.reed_oscillator == pytest.approx((0.0, 800.0))   # MREED, KREED


def test_iflute_1_est_une_anche_solide(tmp_path):
    p = _dat_cylindre(tmp_path)
    p.write_text(p.read_text(encoding='latin-1').replace(
        "0 1.4 0. 9.5e-3", "1 1.4 0. 9.5e-3"), encoding='latin-1')
    assert tutt.read_dat(p).solid_reed is True


def test_les_nombres_fortran_libres_sont_lus(tmp_path):
    """Régression : `10.e-3` et `1.e10` ont un point sans décimale derrière.

    Une regex qui l'ignore ne lève pas d'erreur — elle découpe `10.e-3` en
    `10` puis `-3`, décale toutes les colonnes du tableau, et on lit un
    paramètre pour un autre. C'est ainsi que j'avais lu `V0 = 1,0` là où le
    fichier dit `1.e10`.
    """
    assert tutt._floats('10.e-3') == pytest.approx([1e-2])
    assert tutt._floats('1.e10') == pytest.approx([1e10])
    assert tutt._floats('.5') == pytest.approx([0.5])
    assert tutt._floats('-2.4E-02 3.69E-02') == pytest.approx([-0.024, 0.0369])


def test_read_out_convertit_les_pulsations_en_frequences(tmp_path):
    """`OREF` et `OTUBE` sont des **pulsations** : 3100,9 rad/s = 493,5 Hz.

    Les lire comme des fréquences donnerait un facteur 2π, soit près de cinq
    octaves d'erreur — le genre de bug qui ne se voit qu'à l'oreille.
    """
    p = tmp_path / "r.out"
    p.write_text(
        "   NOTE     JUSTESSE  EMBOUCHURE\n"
        " ..............................\n"
        "     do       0.38E-02   0.17E-02   0.15E+06   0.19E+00\n"
        "     3100.9     3089.0   0.00E+00   0.27E+02   0.81E+00\n"
        "                  -6.6   0.23E-05   0.59E+03\n"
        " ..............................\n", encoding='latin-1')
    notes = tutt.read_out(p)
    assert len(notes) == 1
    n = notes[0]
    assert n.name == "do"
    assert n.f_target_hz == pytest.approx(3100.9 / (2 * np.pi), rel=1e-6)
    assert n.f_tube_hz == pytest.approx(3089.0 / (2 * np.pi), rel=1e-6)
    assert n.f_target_hz == pytest.approx(493.5, abs=0.2)     # do5 au diapason 415
    assert n.q == pytest.approx(27.0)
    # l'écart annoncé par TUTT doit recouper celui qu'on recalcule
    assert n.cents == pytest.approx(n.cents_recalcules, abs=0.2)


# =============================================================================
# Impédance d'entrée
# =============================================================================

def test_cylindre_ferme_a_l_anche_donne_les_quarts_d_onde(tmp_path):
    """Contrôle analytique : `f_n = (2n−1)·c/(4L)`, aux corrections près.

    Deux corrections légitimes tirent vers le grave : la charge de
    rayonnement (allongement ~0,6·r) et le ralentissement visco-thermique de
    l'onde. D'où une tolérance large, mais la **structure impaire** doit être
    exacte.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.5, 0.015))
    freqs, qs, pics = tutt.resonances(d, 50, 2000, n_peaks=4)
    assert len(freqs) >= 3

    nu = C / (4 * 0.5)
    assert freqs[0] == pytest.approx(nu, rel=0.06)
    for i, f in enumerate(freqs[:4]):
        assert f / freqs[0] == pytest.approx(2 * i + 1, rel=0.03)


def test_une_perce_reelle_n_est_pas_exactement_harmonique(tmp_path):
    """Le résultat qui justifie tout le module.

    Les résonances d'un vrai tuyau ne sont pas des multiples exacts : la
    charge de rayonnement et les pertes ne décalent pas tous les rangs de la
    même façon. Sur un cylindre de 52 cm, la douzième sort **une douzaine de
    cents trop haute** — et la hauteur du registre suit la deuxième résonance
    au cent près, donc cet écart s'entend.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.52, 0.015))
    freqs, _, _ = tutt.resonances(d, 50, 2000, n_peaks=3)
    ecart = 1200 * np.log2((freqs[1] / freqs[0]) / 3.0)
    assert ecart > 5.0          # sensiblement décalé, et vers le haut
    assert ecart < 40.0         # mais pas absurde


def test_un_tuyau_plus_long_sonne_plus_grave(tmp_path):
    court = tutt.resonances(tutt.read_dat(_dat_cylindre(tmp_path / "a", 0.30)),
                            50, 1200, n_peaks=1)[0][0]
    long_ = tutt.resonances(tutt.read_dat(_dat_cylindre(tmp_path / "b", 0.60)),
                            50, 1200, n_peaks=1)[0][0]
    assert long_ < court
    assert court / long_ == pytest.approx(2.0, rel=0.08)


def test_une_perce_etroite_est_plus_amortie(tmp_path):
    """Les pertes de couche limite croissent quand le rayon diminue.

    C'est la raison physique pour laquelle un piccolo demande plus de souffle
    qu'une flûte basse, et pourquoi une bombarde est si exigeante.
    """
    large = tutt.resonances(tutt.read_dat(_dat_cylindre(tmp_path / "l", 0.5, 0.020)),
                            50, 1200, n_peaks=1)[1][0]
    etroit = tutt.resonances(tutt.read_dat(_dat_cylindre(tmp_path / "e", 0.5, 0.006)),
                             50, 1200, n_peaks=1)[1][0]
    assert etroit < large


def test_le_bout_ferme_change_la_serie(tmp_path):
    """Fermer les deux bouts donne des demi-ondes, pas des quarts d'onde."""
    p = _dat_cylindre(tmp_path, 0.5, 0.015)
    txt = p.read_text(encoding='latin-1').replace(
        "BAS DE LIGNE OUVERT OU FERME C1 (0=OUVERT, 1=FERME)\n0\n",
        "BAS DE LIGNE OUVERT OU FERME C1 (0=OUVERT, 1=FERME)\n1\n")
    p.write_text(txt, encoding='latin-1')
    d = tutt.read_dat(p)
    assert d.closed_bottom is True
    freqs, _, _ = tutt.resonances(d, 50, 2000, n_peaks=3)
    assert freqs[1] / freqs[0] == pytest.approx(2.0, rel=0.05)   # série complète


def test_geometrie_vide_est_refusee():
    with pytest.raises(ValueError):
        tutt.input_impedance(tutt.BoreDat(), np.array([100.0, 200.0]))


# =============================================================================
# Le pont
# =============================================================================

def test_resonator_from_dat_rend_un_resonateur_utilisable(tmp_path):
    from banc_recherche import hybrid
    res, infos = tutt.resonator_from_dat(_dat_cylindre(tmp_path, 0.52, 0.015),
                                         50, 2000, n_peaks=5)
    assert isinstance(res, hybrid.Resonator)
    assert res.n_modes >= 3
    assert infos['longueur_mm'] == pytest.approx(520.0)
    assert 'NON POSÉS' in infos['trous_latéraux']      # l'aveu, pas l'oubli
    assert len(infos['inharmonicité_cents']) == res.n_modes
    assert infos['inharmonicité_cents'][0] == pytest.approx(0.0, abs=0.01)


def test_le_pont_conserve_les_Q_calcules(tmp_path):
    """Les Q viennent de la largeur des sommets, pas de la loi en √f.

    Quand on a l'impédance, plus rien n'est supposé : c'est tout l'intérêt.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.52, 0.015))
    freqs, qs, _ = tutt.resonances(d, 50, 2000, n_peaks=4)
    res, _ = tutt.resonator_from_dat(d, 50, 2000, n_peaks=4)
    for mode, q in zip(res.modes, qs):
        assert mode.q == pytest.approx(q, rel=1e-6)


def test_les_resonances_sortent_dans_l_ordre_des_frequences(tmp_path):
    """Régression : retenir les sommets les plus **forts** casse la série.

    Une série de résonances est ordonnée en fréquence. Prendre les plus forts
    ramasse des rangs non consécutifs, et l'octave calculée dessus est fausse
    sans prévenir — c'est ce qui m'a fait annoncer une série harmonique sur
    une bombarde dont les résonances valent en réalité 1 : 1,65 : 2,68.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.5, 0.015))
    freqs, _, pics = tutt.resonances(d, 50, 2000, n_peaks=5)
    assert freqs == sorted(freqs)
    # et ce sont bien les **premières**, donc des rangs consécutifs : sur un
    # cylindre fermé à l'anche, les rapports doivent être 1, 3, 5, 7…
    for i, f in enumerate(freqs):
        assert f / freqs[0] == pytest.approx(2 * i + 1, rel=0.04)


def test_la_rugosite_agit_sur_le_Q_et_pas_sur_la_note(tmp_path):
    """`OFILIB` est un rapport de **périmètres**, pas de sections.

    Le source le dit (« PERIMETRE MICROSCOPIQUE / PERIMETRE OFFICIEL ») et le
    calcul fait `PERI = π·OFILIB·DM`. Donc un OFILIB de 1,5 sur une bombarde
    n'en décale pas les résonances de 50 % : il en abaisse le Q. C'est la
    rugosité de la paroi, à laquelle Ninob a consacré un article entier.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.5, 0.015))
    f_lisse, q_lisse, _ = tutt.resonances(d, 50, 1200, n_peaks=1)

    d.ofilib = np.full(len(d.lengths), 2.0)
    f_rug, q_rug, _ = tutt.resonances(d, 50, 1200, n_peaks=1)

    assert q_rug[0] < 0.7 * q_lisse[0]                       # bien plus amorti
    assert f_rug[0] == pytest.approx(f_lisse[0], rel=0.03)   # mais presque la même note


def test_celerite_suppose_de_l_air_expire(tmp_path):
    """`329,95 + 0,69·T` : air saturé d'humidité, 2,5 % de CO₂.

    C'est l'air du musicien, pas celui de la pièce — d'où une célérité un peu
    plus haute que la valeur sèche usuelle.
    """
    assert tutt.celerite(20.0) == pytest.approx(343.75, abs=0.01)
    assert tutt.celerite(25.0) > tutt.celerite(15.0)


def test_une_cavite_au_bec_abaisse_les_frequences(tmp_path):
    """Sens vérifié contre Ninob : une cavité au petit bout « abaisse les
    fréquences en jeu ». Posée en parallèle au nœud du bec, et toujours sur
    demande explicite — elle ne se déduit d'aucun champ du fichier."""
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.5, 0.015))
    ref = tutt.resonances(d, 50, 2000, n_peaks=1)[0][0]
    for v in (1e-8, 1e-7, 1e-6):
        f = tutt.resonances(d, 50, 2000, n_peaks=1, reed_volume_m3=v)[0][0]
        assert f <= ref
        ref = f


def test_to_tutt43_ajoute_les_blocs_manquants(tmp_path):
    """Les fichiers d'avant (tutt25/tutt40) n'ont pas tous les blocs de 4.3.

    Et chacun doit se poser **après la ligne de valeurs**, pas après
    l'étiquette : glisser un bloc entre une étiquette et ses valeurs coupe la
    lecture Fortran sur « Bad real number », ce qui m'est arrivé.
    """
    vieux = tmp_path / "vieux.dat"
    vieux.write_text(
        "un titre\n"
        "PARAMETRES PHYSIQUES DE L' AIR :RHOA,P0,GAMMA,CV,ETA,TONEW,DLAMBA\n"
        "1.204 1.014E5 1.400 719. 1.8E-5 11.7 2.4E-2\n"
        "NOMBRE DE TRONCONS DE LA LIGNE (-1) N\n0\n"
        "BAS DE LIGNE OUVERT OU FERME C1 (0=OUVERT, 1=FERME)\n0\n"
        "TABLEAU PERCE D0 (DIMENSION N+1)\n0.015\n"
        "TABLEAU PERCE DL (DIMENSION N+1)\n0.015\n"
        "TABLEAU DES TRONCONS DE LA LIGNE PRINCIPALE L (DIMENSION N+1)\n0.5\n"
        "TEMPERATURE DE L' AIR EN HAUT ET EN BAS DE LA LIGNE (CELSIUS)\n25. 20.\n"
        "FREQUENCE DU LA DE REFERENCE FLA\n440\n"
        "TABLE DES DOIGTES\n"
        " 1  1 'fa    '100\t1\t1\n"
        "DONNEES CONCERNANT L' EMBOUCHURE\n"
        "IFLUTE FCM FCP G0 LA0 alpha E0 V0 V1\n"
        "1 0. 0. 10.e-3 1.4e-2 1. 1.e-4 1.e10 0.\n"
        "DONNEES CONCERNANT L' AUTO ENTRETIEN GA GB\n700. 1.\n"
        "COEFFICIENTS SUR LES CRITERES CJUS CTIM CVOL CEMI CLIB\n1. 0. 0. 0. 0.\n",
        encoding='latin-1')

    neuf = tutt.to_tutt43(vieux, tmp_path / "neuf.dat")
    lignes = [l for l in open(neuf, encoding='latin-1').read().split('\n')]

    assert 'VERSION FORMAT' in lignes[0].upper()
    i_mreed = next(i for i, l in enumerate(lignes) if 'MREED' in l.upper())
    i_iflute = next(i for i, l in enumerate(lignes) if 'IFLUTE' in l.upper())
    assert i_mreed == i_iflute + 2          # après l'étiquette ET ses valeurs

    i_imp = next(i for i, l in enumerate(lignes) if 'IMPADM' in l.upper())
    i_auto = next(i for i, l in enumerate(lignes) if 'AUTO ENTRETIEN' in l.upper())
    assert i_imp == i_auto + 2
    assert lignes[i_auto + 1].strip().startswith('700')   # valeurs préservées

    assert "' 100" in '\n'.join(lignes)      # séparateur après le nom du doigté


def test_to_tutt43_ne_double_pas_un_bloc_deja_present(tmp_path):
    d = _dat_cylindre(tmp_path)              # format 4.3, MREED déjà là
    neuf = tutt.to_tutt43(d, tmp_path / "n.dat")
    txt = open(neuf, encoding='latin-1').read()
    assert txt.upper().count('MREED') == 1


def test_le_souffle_chaud_est_du_cote_de_l_embouchure(tmp_path):
    """Le fichier donne les températures « en haut et en bas de la ligne ».

    En haut, c'est l'embouchure — là où souffle le musicien. Les inverser
    refroidit le bec et réchauffe le pavillon, soit l'exact contraire de ce
    qui se passe, et décale la note puisque la célérité suit la température.
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path, 0.5, 0.015))
    d.temperature_c = (30.0, 10.0)           # embouchure chaude, pavillon froid
    chaud_au_bec = tutt.resonances(d, 50, 1200, n_peaks=1)[0][0]

    d.temperature_c = (10.0, 30.0)           # l'inverse
    froid_au_bec = tutt.resonances(d, 50, 1200, n_peaks=1)[0][0]

    # les deux diffèrent : la température n'est pas moyennée le long du tube,
    # elle est pondérée exponentiellement vers l'embouchure
    assert abs(1200 * np.log2(chaud_au_bec / froid_au_bec)) > 5.0


# =============================================================================
# Perce idéale — TUTT comme moteur par défaut du cylindre, pas encore du cône
# =============================================================================

def test_le_cylindre_ideal_vise_a_peu_pres_la_bonne_note():
    """Solide : aucune troncature de cône à trancher.

    La longueur vient d'un quart d'onde exact ; le calcul y ajoute pertes et
    rayonnement, qui font sonner le tuyau un peu plus grave — l'écart est
    donc attendu, petit, et du côté prévisible (jamais plus aigu que visé).
    """
    dat = tutt.bore_dat_ideal('cylindrique', 220.0, 14.6)
    freqs, qs, pics = tutt.resonances(dat, 50, 3000, n_peaks=4)
    assert freqs, "aucune résonance trouvée"
    ecart_cents = 1200 * np.log2(freqs[0] / 220.0)
    assert -150.0 < ecart_cents < 0.0


def test_le_cylindre_ideal_garde_la_serie_impaire():
    """Signature d'un tuyau fermé à l'anche : que des rangs impairs."""
    dat = tutt.bore_dat_ideal('cylindrique', 220.0, 14.6)
    freqs, qs, pics = tutt.resonances(dat, 50, 3000, n_peaks=4)
    ratios = np.array(freqs) / freqs[0]
    attendu = np.array([1.0, 3.0, 5.0, 7.0])[:len(ratios)]
    assert np.max(np.abs(ratios - attendu)) < 0.15


def test_le_cone_idealise_tronque_n_est_pas_encore_juste():
    """Document le résultat négatif plutôt que le taire.

    Un cône à un seul tronçon, tronqué à `bore_mm` au lieu de rejoindre une
    vraie pointe, ne redonne pas le registre à l'octave attendu — ses
    résonances suivent `tan(kL)=kL`, pas la série harmonique d'un cône
    entraîné près de sa pointe. `hybrid.saxophone` etc. n'utilisent donc pas
    ce chemin par défaut (`engine='ideal'`). Si ce test se met à échouer,
    c'est que quelqu'un a réussi à corriger le modèle — bonne nouvelle, et
    l'avertissement de `bore_dat_ideal`/`hybrid._wind` doit alors être retiré
    en même temps que ce test.
    """
    dat = tutt.bore_dat_ideal('conique', 220.0, 5.0)
    freqs, qs, pics = tutt.resonances(dat, 50, 3000, n_peaks=3)
    ratio2 = freqs[1] / freqs[0]
    assert abs(ratio2 - 2.0) > 0.15, (
        "le cône idéalisé donne enfin l'octave — mettre à jour "
        "hybrid._wind / bore_dat_ideal en conséquence")


def test_ideal_resonator_renvoie_un_resonateur_hybrid_utilisable():
    res, infos = tutt.ideal_resonator('cylindrique', 220.0, 14.6, n_modes=6)
    assert res.n_modes >= 3
    assert infos['tronçons'] == 1
