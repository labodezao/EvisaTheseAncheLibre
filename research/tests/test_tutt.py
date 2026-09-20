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
    """`V0`/`V1` et `MREED`/`KREED` portent la physique de l'anche.

    C'est par eux que passe le volume équivalent d'anche, qui corrige les
    octaves d'une perce conique (Ninob, *Modes propres d'un tronc de cône*).
    """
    d = tutt.read_dat(_dat_cylindre(tmp_path))
    assert d.embouchure['V0'] == pytest.approx(26.0)
    assert d.embouchure['V1'] == pytest.approx(17.0)
    assert d.embouchure['KREED'] == pytest.approx(800.0)
    assert d.is_flute is False


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
