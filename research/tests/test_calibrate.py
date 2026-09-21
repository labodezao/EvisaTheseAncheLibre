"""Calage d'une anche du modèle sur un son mesuré."""
import os

import numpy as np
import pytest

from banc_recherche import calibrate as cal
from banc_recherche import modal


def test_homothetie_ne_touche_que_les_longueurs():
    from banc_recherche.reed_model import SECTIONS_DEFAULT
    s = cal.scale_sections(SECTIONS_DEFAULT, 0.5)
    assert np.allclose(s[:, 0], SECTIONS_DEFAULT[:, 0] * 0.5)
    assert np.allclose(s[:, 1:], SECTIONS_DEFAULT[:, 1:])   # profil conservé


def test_sections_for_mode_atteint_la_cible():
    for f in (98.0, 220.0, 880.0):
        s = cal.sections_for_mode(f, n_modes=2)
        got = float(np.sort(modal.natural_frequencies_np(s, n_modes=2))[0])
        assert abs(got - f) / f < 1e-9


def test_build_model_accorde_la_languette():
    """Régression : le calage doit utiliser le MÊME nombre de modes que le
    modèle. Caler sur une base à 1 mode puis évaluer sur 2 décalait la note de
    2 % (220,1 Hz visés, 215,7 obtenus) — Rayleigh-Ritz abaisse la première
    fréquence quand on ajoute des modes."""
    for f in (110.0, 220.0, 440.0):
        m = cal.build_model(f, n_modes=2)
        assert abs(m.f_modes[0] - f) / f < 1e-6


def test_build_model_coherent_a_trois_modes():
    m = cal.build_model(196.0, n_modes=3)
    assert abs(m.f_modes[0] - 196.0) / 196.0 < 1e-6


def test_frequence_cible_invalide_rejetee():
    for mauvais in (0.0, -100.0, float("nan")):
        with pytest.raises(ValueError):
            cal.sections_for_mode(mauvais)


def test_anche_plus_aigue_est_plus_courte():
    """f ∝ 1/L² : monter d'une octave raccourcit d'un facteur √2."""
    grave = cal.sections_for_mode(110.0)
    aigu = cal.sections_for_mode(220.0)
    assert abs(grave[:, 0].sum() / aigu[:, 0].sum() - np.sqrt(2)) < 1e-9


@pytest.mark.skipif(not os.environ.get("BANC_TESTS_LENTS"),
                    reason="cherche des seuils : lancer avec BANC_TESTS_LENTS=1")
def test_le_ressort_d_air_remonte_la_note():
    """La fréquence de jeu dépasse la fréquence propre de la languette, et
    `tune_to_playing_frequency` inverse ce décalage."""
    m = cal.build_model(220.0)
    f_play = cal.playing_frequency(m, n_scan=14)
    assert f_play > m.f_modes[0]

    modele, joue, mode = cal.tune_to_playing_frequency(220.0, n_iter=5, n_scan=14)
    assert abs(joue - 220.0) < 2.0
    assert mode < joue                      # la languette est accordée plus bas


@pytest.mark.skipif(not os.environ.get("BANC_TESTS_LENTS"),
                    reason="simulation complète : lancer avec BANC_TESTS_LENTS=1")
def test_synthese_produit_un_son_physique():
    m = cal.build_model(220.0)
    audio, nfo = cal.synthesize(m, dur=0.4, fs=22050.0, drive=2.0, oversample=8,
                                settle=0.4)
    assert audio.size == int(0.4 * 22050)
    assert abs(np.max(np.abs(audio)) - 1.0) < 1e-9      # normalisé
    assert 0.0 < nfo["excursion_mm"] < 1.5              # course d'accordéon
    assert nfo["p_on"] > 0
