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


def test_le_cone_donne_bien_le_registre_a_l_octave():
    """Un cône doit donner la série harmonique complète — l'octave, pas la
    douzième. C'est ce qui distingue un saxophone d'une clarinette.

    Ce test a d'abord été écrit **à l'envers** : il figeait le constat qu'un
    cône idéalisé ne donnait *pas* l'octave (rapports 1 : 1,72 : 2,42, la
    signature de `tan(kL)=kL`), en prévoyant d'échouer si quelqu'un corrigeait
    un jour le modèle. C'est exactement ce qui est arrivé : la faute était à
    l'empilement de cylindres, pas au cône. Avec la vraie ligne de transfert
    conique de TUTT (`_z_troncon`), l'octave revient toute seule.
    """
    dat = tutt.bore_dat_ideal('conique', 220.0, 5.0, taper=10.0)
    freqs, qs, pics = tutt.resonances(dat, 40, 2000, n_peaks=4)
    ratios = np.array(freqs) / freqs[0]
    attendu = np.array([1.0, 2.0, 3.0, 4.0])[:len(ratios)]
    # un cône tronqué reste un peu étiré : on demande le bon rang, pas la
    # perfection — la troncature se corrige par la cavité d'anche (ci-dessous)
    assert np.max(np.abs(ratios - attendu) / attendu) < 0.06


def test_le_cylindre_garde_la_douzieme_et_le_cone_prend_l_octave():
    """Les deux familles se séparent sur la seule géométrie, comme il faut."""
    cyl = tutt.bore_dat_ideal('cylindrique', 220.0, 14.6)
    cone = tutt.bore_dat_ideal('conique', 220.0, 5.0, taper=10.0)
    r_cyl = np.array(tutt.resonances(cyl, 40, 2000, n_peaks=2)[0])
    r_cone = np.array(tutt.resonances(cone, 40, 2000, n_peaks=2)[0])
    assert 2.9 < r_cyl[1] / r_cyl[0] < 3.15      # la douzième
    assert 1.9 < r_cone[1] / r_cone[0] < 2.12    # l'octave


def test_la_cavite_d_anche_corrige_l_octave_du_cone_tronque():
    """Le résultat de Ninob (*Modes propres d'un tronc de cône*), vérifié.

    Un cône tronqué a son octave trop haute — il manque le bout pointu. Une
    anche solide au petit bout se comporte comme une cavité ajoutée, qui
    abaisse les modes graves plus que les aigus et **corrige l'octave**.
    C'est ce qui permet à un saxophone ou à un hautbois d'octavier juste.

    Mesuré ici : sans cavité +95 cents, avec 1,5 cm³ +2 cents.
    """
    dat = tutt.bore_dat_ideal('conique', 294.0, 5.0, taper=4.5)

    def octave_cents(volume):
        f = np.array(tutt.resonances(dat, 40, 2600, n_peaks=2,
                                     reed_volume_m3=volume)[0])
        return 1200 * np.log2((f[1] / f[0]) / 2.0)

    sans = octave_cents(None)
    avec = octave_cents(1.5e-6)
    assert sans > 60.0                 # nettement trop haute sans cavité
    assert abs(avec) < 15.0            # corrigée
    assert avec < sans


def test_ideal_resonator_renvoie_un_resonateur_hybrid_utilisable():
    res, infos = tutt.ideal_resonator('cylindrique', 220.0, 14.6, n_modes=6)
    assert res.n_modes >= 3
    assert infos['tronçons'] == 1


# =============================================================================
# Mise à l'échelle — la vraie réponse à « peut-on simplifier une perce »
# =============================================================================

def _perce_a_trois_troncons():
    return tutt.BoreDat(
        n_sections=3, closed_bottom=False,
        d0=np.array([0.005, 0.010, 0.015]),
        dl=np.array([0.010, 0.015, 0.022]),
        lengths=np.array([0.15, 0.20, 0.25]),
        ofilib=np.ones(3), temperature_c=(32.0, 20.0),
    )


def test_scale_bore_garde_les_rapports_de_resonance():
    """C'est ce qui décide le registre : une forme réduite à un tronçon les
    perd (test_le_cone_idealise_tronque_n_est_pas_encore_juste), une forme
    mise à l'échelle les garde.
    """
    dat = _perce_a_trois_troncons()
    freqs0, _, _ = tutt.resonances(dat, 30, 2000, n_peaks=4)
    ratios0 = np.array(freqs0) / freqs0[0]

    for k in (0.5, 0.8, 1.3, 2.0):
        dat_k = tutt.scale_bore(dat, k)
        freqs_k, _, _ = tutt.resonances(dat_k, 30 / k, 2000 / k, n_peaks=4)
        ratios_k = np.array(freqs_k) / freqs_k[0]
        # On ne compare que les trois premiers rangs. Le quatrième de cette
        # perce d'essai est à −30 dB pile, la hauteur du seuil d'élagage :
        # comme les pertes ne suivent pas la mise à l'échelle (couche limite
        # en 1/√f), il passe au-dessus ou en dessous selon le facteur, et
        # l'entrée n° 4 de la liste change alors de mode. Ce n'est pas une
        # dérive du registre, c'est un mode marginal qui entre et sort.
        n = 3
        derive = np.abs(ratios_k[:n] - ratios0[:n]) / ratios0[:n]
        assert np.max(derive) < 0.02, (k, ratios_k, ratios0)


def test_scale_bore_deplace_la_fondamentale_en_1_sur_k():
    dat = _perce_a_trois_troncons()
    f0, _, _ = tutt.resonances(dat, 30, 2000, n_peaks=1)
    for k in (0.5, 2.0):
        dat_k = tutt.scale_bore(dat, k)
        fk, _, _ = tutt.resonances(dat_k, 30 / k, 2000 / k, n_peaks=1)
        assert fk[0] == pytest.approx(f0[0] / k, rel=0.02)


def test_scale_bore_ne_touche_pas_l_ofilib_ni_l_embouchure():
    """La rugosité est sans dimension ; l'anche suivrait sa propre loi —
    pas encore écrite ici, donc pas mise à l'échelle en douce."""
    dat = _perce_a_trois_troncons()
    dat.ofilib = np.array([1.3, 1.3, 1.3])
    dat.embouchure = {'MREED': 2.0e-4, 'KREED': 800.0}
    dat2 = tutt.scale_bore(dat, 1.5)
    assert np.array_equal(dat2.ofilib, dat.ofilib)
    assert dat2.embouchure == dat.embouchure


def test_scale_bore_refuse_un_facteur_negatif_ou_nul():
    dat = _perce_a_trois_troncons()
    with pytest.raises(ValueError):
        tutt.scale_bore(dat, 0.0)
    with pytest.raises(ValueError):
        tutt.scale_bore(dat, -1.0)


def test_scale_bore_to_converge_en_deux_ou_trois_passes():
    dat = _perce_a_trois_troncons()
    cible = 220.0
    d = dat
    for _ in range(3):
        d = tutt.scale_bore_to(d, cible, fmin=30, fmax=2000)
    f, _, _ = tutt.resonances(d, 30, 2000, n_peaks=1)
    assert f[0] == pytest.approx(cible, abs=1.0)


# =============================================================================
# Trous latéraux — le chantier nommé « prochain » depuis le début
# =============================================================================

def _flute_a_six_trous(d_trou=0.008, h_trou=0.004):
    """Tube de 500 mm, six cheminées régulières, plus un raccord sans trou."""
    n = 7
    return tutt.BoreDat(
        n_sections=n, closed_bottom=False,
        d0=np.full(n, 0.015), dl=np.full(n, 0.015),
        lengths=np.full(n, 0.5 / n),
        hole_d0=np.array([d_trou] * 6 + [0.0]),
        hole_dl=np.array([d_trou] * 6 + [0.0]),
        hole_len=np.array([h_trou] * 6 + [0.0]),
        ofilib=np.ones(n), temperature_c=(20.0, 20.0),
    )


def test_sans_doigte_tout_est_ferme_et_rien_ne_change():
    """Le défaut doit redonner exactement l'ancien module, trous éteints."""
    cyl = tutt.BoreDat(n_sections=1, closed_bottom=False,
                       d0=np.array([0.015]), dl=np.array([0.015]),
                       lengths=np.array([0.5]), ofilib=np.ones(1),
                       temperature_c=(20.0, 20.0))
    f = tutt.resonances(cyl, 50, 1400, n_peaks=3)[0]
    assert f[0] == pytest.approx(167.4, abs=1.0)
    assert f[1] / f[0] == pytest.approx(3.0, abs=0.1)


def test_ouvrir_un_trou_fait_monter_la_note():
    """La vérification qui compte : c'est à ça que sert un trou."""
    dat = _flute_a_six_trous()
    ferme = tutt.resonances(dat, 50, 1600, n_peaks=1)[0][0]
    precedent = ferme
    for k in range(1, 7):
        doigte = [0] * k + [1] * (7 - k)      # on ouvre depuis le pavillon
        f = tutt.resonances(dat, 50, 2200, n_peaks=1, fingering=doigte)[0][0]
        assert f > precedent, f"ouvrir le trou {k} devrait monter la note"
        precedent = f
    assert precedent / ferme > 2.0            # plus d'une octave au total


def test_un_trou_ferme_n_est_pas_neutre():
    """Il reste le volume de la cheminée, qui alourdit un peu la colonne.

    C'est pour ça que TUTT garde les trous fermés dans le calcul au lieu de
    les effacer — et c'est mesurable : la note descend légèrement.
    """
    avec = _flute_a_six_trous()
    sans = _flute_a_six_trous(d_trou=0.0, h_trou=0.0)
    f_avec = tutt.resonances(avec, 50, 1200, n_peaks=1)[0][0]
    f_sans = tutt.resonances(sans, 50, 1200, n_peaks=1)[0][0]
    assert f_avec < f_sans
    assert 0 < 1200 * np.log2(f_sans / f_avec) < 60.0     # quelques cents


def test_un_trou_plus_gros_fait_monter_plus_haut():
    """Une grande cheminée court-circuite mieux qu'une petite."""
    doigte = [0] + [1] * 6
    petit = tutt.resonances(_flute_a_six_trous(d_trou=0.004), 50, 1600,
                            n_peaks=1, fingering=doigte)[0][0]
    grand = tutt.resonances(_flute_a_six_trous(d_trou=0.010), 50, 1600,
                            n_peaks=1, fingering=doigte)[0][0]
    assert grand > petit


def test_le_doigte_se_donne_par_nom_ou_par_tableau():
    dat = _flute_a_six_trous()
    dat.fingerings = [('sol', [0, 1, 1, 1, 1, 1, 1])]
    par_nom = tutt.resonances(dat, 50, 1600, n_peaks=1, fingering='sol')[0][0]
    par_tab = tutt.resonances(dat, 50, 1600, n_peaks=1,
                              fingering=[0, 1, 1, 1, 1, 1, 1])[0][0]
    assert par_nom == pytest.approx(par_tab)
    with pytest.raises(ValueError):
        tutt.resonances(dat, 50, 1600, n_peaks=1, fingering='zorglub')


def test_un_dans_le_doigte_veut_bien_dire_ferme():
    """Le piège d'inversion : on dit « boucher un trou » et on écrit 1.

    Si la convention était lue à l'envers, tout doigté jouerait l'inverse de
    ce qu'il dit — et tous les fichiers de Ninob seraient faux d'un coup.
    """
    dat = _flute_a_six_trous()
    tout_ferme = tutt.resonances(dat, 50, 2200, n_peaks=1,
                                 fingering=[1] * 7)[0][0]
    tout_ouvert = tutt.resonances(dat, 50, 2200, n_peaks=1,
                                  fingering=[0] * 6 + [1])[0][0]
    assert tout_ouvert > tout_ferme


# =============================================================================
# Le critère de TUTT : les zéros de Im(Z), et Proxi pour choisir
# =============================================================================

def _cylindre_nu():
    return tutt.BoreDat(n_sections=1, closed_bottom=False,
                        d0=np.array([0.015]), dl=np.array([0.015]),
                        lengths=np.array([0.5]), ofilib=np.ones(1),
                        temperature_c=(20.0, 20.0))


def test_les_zeros_de_im_z_tombent_sur_les_sommets_de_module():
    """Validation croisée des deux critères, l'un par l'autre.

    TUTT cherche les zéros de la partie imaginaire ; ce module cherchait les
    sommets du module. Sur un tube peu amorti les deux doivent coïncider —
    et s'ils coïncident, c'est que les deux sont bons.
    """
    cyl = _cylindre_nu()
    zeros = np.array(tutt.playing_frequencies(cyl, 50, 1400))
    sommets = np.array(tutt.resonances(cyl, 50, 1400, n_peaks=4)[0])
    for f in sommets:
        assert np.min(np.abs(zeros - f)) < 0.5, f       # à moins d'un demi-hertz


def test_les_zeros_alternent_sommets_et_creux():
    """Im(Z)=0 aux résonances **et** aux antirésonances — d'où Proxi.

    C'est précisément pourquoi TUTT ne peut pas se contenter de la liste :
    il faut ensuite choisir, et c'est le rôle de `mode_le_plus_proche`.
    """
    cyl = _cylindre_nu()
    zeros = np.array(tutt.playing_frequencies(cyl, 50, 1400))
    assert zeros.size >= 6
    sommets = np.array(tutt.resonances(cyl, 50, 1400, n_peaks=3)[0])
    # un zéro sur deux est un sommet ; ceux du milieu n'en sont pas
    for f in sommets:
        assert np.min(np.abs(zeros - f)) < 0.5
    entre = zeros[1]
    assert np.min(np.abs(sommets - entre)) > 50.0


def test_mode_le_plus_proche_fait_ce_que_fait_proxi():
    modes = [167.5, 506.0, 845.1, 1184.6]
    rang, f, cents = tutt.mode_le_plus_proche(modes, 500.0)
    assert rang == 1 and f == pytest.approx(506.0)
    assert cents == pytest.approx(1200 * np.log2(506.0 / 500.0), abs=1e-6)

    # débordements : TUTT prend le mode extrême plutôt que de refuser
    assert tutt.mode_le_plus_proche(modes, 20.0)[0] == 0
    assert tutt.mode_le_plus_proche(modes, 5000.0)[0] == len(modes) - 1
    with pytest.raises(ValueError):
        tutt.mode_le_plus_proche([], 440.0)


def test_l_impedance_d_anche_change_de_signe_a_sa_resonance():
    """`j(mω − k/ω)/A²` : raideur en dessous, masse au-dessus, nulle dessus.

    C'est ce qui fait que l'anche tire la note vers sa propre fréquence
    d'autant plus fort qu'elle en est proche.
    """
    m, k, a = 2.0e-6, 800.0, 1.0e-4
    f_anche = np.sqrt(k / m) / (2 * np.pi)
    z = tutt.reed_impedance([f_anche * 0.5, f_anche, f_anche * 2.0], m, k, a)
    assert np.imag(z[0]) < 0                       # dominée par la raideur
    assert abs(np.imag(z[1])) < 1e-6 * abs(np.imag(z[0]))
    assert np.imag(z[2]) > 0                       # dominée par la masse
    with pytest.raises(ValueError):
        tutt.reed_impedance([440.0], m, k, 0.0)


def test_la_cavite_qui_accorde_l_octave_la_trouve():
    """Le geste du facteur : on ajuste jusqu'à ce que l'octave tombe juste."""
    dat = tutt.bore_dat_ideal('conique', 294.0, 5.0, taper=4.5)
    avant = tutt.resonances(dat, 40, 2600, n_peaks=2)[0]
    ecart_avant = 1200 * np.log2((avant[1] / avant[0]) / 2.0)
    assert ecart_avant > 60.0                       # nettement trop haute

    v, ecart = tutt.cavite_qui_accorde_l_octave(dat)
    assert 0 < v < 5e-6                             # quelques cm³
    assert abs(ecart) < 1.0                         # juste au cent près


def test_la_cavite_trouvee_depend_de_la_troncature():
    """Moins le cône est tronqué, moins il manque de volume à rendre."""
    court = tutt.bore_dat_ideal('conique', 294.0, 5.0, taper=4.5)
    long_ = tutt.bore_dat_ideal('conique', 294.0, 5.0, taper=8.0)
    v_court, _ = tutt.cavite_qui_accorde_l_octave(court)
    v_long, _ = tutt.cavite_qui_accorde_l_octave(long_)
    assert v_court > v_long


def test_sur_un_cylindre_il_n_y_a_pas_d_octave_a_accorder():
    """Un cylindre ne fait pas l'octave mais la douzième : la fonction doit
    le dire en rendant le meilleur essai, pas lever une erreur."""
    cyl = tutt.bore_dat_ideal('cylindrique', 294.0, 14.6)
    v, ecart = tutt.cavite_qui_accorde_l_octave(cyl)
    assert v == 0.0
    assert ecart > 600.0                            # c'est une douzième


def test_gamme_des_doigtes_rend_la_gamme_de_la_perce():
    """Une vraie perce ne se transpose pas : elle a des trous, et chaque
    combinaison de doigts donne une note. C'est cette liste-là."""
    dat = _flute_a_six_trous()
    dat.fingerings = [(f'd{k}', [0] * k + [1] * (7 - k)) for k in range(7)]
    gamme = tutt.gamme_des_doigtes(dat, fmax=2400)
    assert len(gamme) == 7
    freqs = [f for _, _, f in gamme]
    assert freqs == sorted(freqs)                 # rendue du grave à l'aigu
    assert freqs[-1] / freqs[0] > 2.0
    with pytest.raises(ValueError):
        tutt.gamme_des_doigtes(tutt.BoreDat())


def test_un_nom_de_doigte_peut_contenir_des_chiffres(tmp_path):
    """« do5 », « fa#4 » : les noms de notes en ont, et la première version
    de la lecture les tronquait silencieusement à la première décimale."""
    p = pathlib.Path(tmp_path) / 'doigtes.dat'
    p.write_text(
        "essai de doigtés\n"
        "NOMBRE DE TRONCONS DE LA LIGNE (-1) N\n3\n"
        "BAS DE LIGNE OUVERT OU FERME C1 (0=OUVERT, 1=FERME)\n0\n"
        "TABLEAU PERCE D0 (DIMENSION N+1)\n0.015 0.015 0.015 0.015\n"
        "TABLEAU PERCE DL (DIMENSION N+1)\n0.015 0.015 0.015 0.015\n"
        "TABLEAU DES TRONCONS DE LA LIGNE PRINCIPALE L (DIMENSION N+1)\n"
        "0.12 0.12 0.12 0.12\n"
        "1 1 1 'do5 ' 100\n"
        "0 1 1 'fa#4 ' 100\n", encoding='latin-1')
    noms = [nom.strip() for nom, _ in tutt.read_dat(p).fingerings]
    assert 'do5' in noms and 'fa#4' in noms
