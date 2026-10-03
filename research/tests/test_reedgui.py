"""reedgui sans fenêtre : ouvrir matrix.txt, calculer, éditer, enregistrer dans la banque."""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "reedgui"))
import reedgui  # noqa: E402

MATRIX = os.path.join(ICI, "..", "reedgui", "matrix.txt")


def test_ouvrir_matrix_et_calculer():
    e = reedgui.Etat()
    e.ouvrir(MATRIX)
    assert len(e.troncons) == 4 and e.troncons[1]["epaisseur_debut_mm"] == "0,2"
    assert e.troncons[0]["materiau"] == "acier"
    lang, lignes = e.calculer(5)
    assert len(lignes) == 5
    assert lignes[0]["f_hz"] == pytest.approx(67.36, abs=0.02)
    assert lignes[0]["f_rr_hz"] > lignes[0]["f_hz"]                  # Rayleigh-Ritz : borne haute


def test_saisies_fausses_donnent_un_message():
    e = reedgui.Etat()
    e.troncons[0]["longueur_mm"] = ""
    with pytest.raises(ValueError, match="case vide"):
        e.calculer()
    e.troncons[0]["longueur_mm"] = "abc"
    with pytest.raises(ValueError, match="pas un nombre"):
        e.calculer()
    e.troncons[0]["longueur_mm"] = "30"
    e.troncons[0]["materiau"] = "carton"
    with pytest.raises(ValueError, match="inconnu"):
        e.calculer()
    e.troncons[0]["materiau"] = "200 GPa / 7850"
    e.calculer()
    with pytest.raises(ValueError):
        e.supprimer(0)                                                  # il en faut un


def test_editer_et_enregistrer_dans_la_banque(tmp_path):
    e = reedgui.Etat()
    e.ouvrir(MATRIX)
    e.id, e.note = "essai", "do#1"
    i = e.dupliquer(1)
    e.troncons[i]["largeur_fin_mm"] = "3,8"                             # largeur variable
    e.masse_bout_g = "0,05"
    f_avant = e.calculer(3)[1][0]["f_hz"]
    ch = str(tmp_path / "banque.csv")
    e.enregistrer(ch)
    e2 = reedgui.Etat()
    assert e2.ouvrir(ch) == ["essai"]
    assert e2.note == "do#1" and e2.masse_bout_g == "0,05" and len(e2.troncons) == 5
    assert e2.calculer(3)[1][0]["f_hz"] == pytest.approx(f_avant, rel=1e-6)
