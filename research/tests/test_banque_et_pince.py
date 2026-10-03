"""Banque d'anches (CSV -> yaml) et son pincé (fréquence, amortissement)."""
import os
import wave

import numpy as np
import pytest

from banc_recherche import pince
from banc_recherche.banque_anches import ecrire_banque, importer, nom_note, note_hz

EN_TETE = ("type;id;longueur_mm;largeur_debut_mm;largeur_fin_mm;epaisseur_debut_mm;epaisseur_fin_mm;materiau;"
           "instrument;rang;note;sens;position;chambre;levee_mm;fente_longueur_mm;fente_largeur_mm;plaque_mm;"
           "masse_bout;rivet_mm;son_pince;seuils_csv;date;source\n")


def test_notes():
    assert note_hz("la3") == pytest.approx(440.0)
    assert note_hz("A4") == pytest.approx(440.0)
    assert note_hz("sib2") == pytest.approx(440 * 2 ** (-11 / 12))
    assert note_hz("440,5") == pytest.approx(440.5)
    assert nom_note(261.63)[0] == "do3"
    with pytest.raises(ValueError):
        note_hz("lala")


def test_import_et_valeurs_a_mesurer():
    csv = EN_TETE + ("anche;A1;;;;;;;accordéon;R12;la3?;pousse;exterieure;6;0,6;;;;non;;;;;essai\n"
                     "troncon;A1;10;4;4;0,35;0,30;acier\n"
                     "troncon;A1;20;4;3,5;0,30;\n")
    anches, pb = importer(csv)
    assert not [p for p in pb if p.niveau == "erreur"]
    a = anches[0]
    assert a.valeur("levee_mm") == 0.6 and not a.a_mesurer("levee_mm")
    assert a.a_mesurer("note") and a.valeur("note_Hz") == pytest.approx(440.0)     # « la3? »
    assert a.a_mesurer("fente_largeur_mm")                                         # vide -> nominal
    assert a.troncons[1]["epaisseur_mm"] == [0.30, 0.30]                           # fin vide = début
    assert a.languette().L == pytest.approx(30e-3)


def test_valeurs_absurdes_et_unites():
    csv = EN_TETE + ("anche;B;;;;;;;;;;;;;;;;;;;;;;\n"
                     "troncon;B;0,03;4;4;0,3;0,3;acier\n"       # 0,03 mm : des mètres ?
                     "troncon;B;20;4;4;35;35;acier\n"            # 35 mm : des centièmes ?
                     "troncon;B;20;4;4;0,3;0,3;inconnium\n")
    _, pb = importer(csv)
    txt = " ".join(str(p) for p in pb)
    assert "mètres" in txt and "centièmes" in txt and "inconnu" in txt


def test_aller_retour_banque(tmp_path):
    csv = EN_TETE + ("anche;C;;;;;;;;;mi4?;tire;interieure;;;;;;;;;;;\n"
                     "troncon;C;15;3;3;0,25;0,25;acier\n")
    anches, _ = importer(csv)
    ch = tmp_path / "b.csv"
    ecrire_banque(anches, ch)
    anches2, pb = importer(str(ch))
    assert anches2[0].valeur("note") == "mi4" and anches2[0].a_mesurer("note")
    assert anches2[0].troncons == anches[0].troncons


def test_yaml(tmp_path):
    pytest.importorskip("yaml")
    from banc_recherche.banque_anches import charger_yaml, ecrire_yaml
    anches, _ = importer(EN_TETE + "anche;D;;;;;;;;;la3;;;;;;;;;;;;;\n")
    ch = tmp_path / "a.yaml"
    ecrire_yaml(anches, str(ch))
    a = charger_yaml(str(ch))[0]
    assert a.troncons_a_mesurer and a.languette().L > 0


def _pincements(f, zeta, fs=48000, n=3, ecart=1.0, bruit=1e-3, seed=0):
    rng = np.random.default_rng(seed)
    x = np.zeros(int((0.5 + n * ecart + 1) * fs))
    for k in range(n):
        t = np.arange(int((ecart + 1) * fs)) / fs
        w = 2 * np.pi * f
        s = (0.3 + 0.2 * k) * np.exp(-zeta * w * t) * np.sin(w * t + k)
        s += 0.1 * np.exp(-3 * zeta * w * t) * np.sin(6.27 * w * t)          # mode 2
        i = int((0.5 + k * ecart) * fs)
        m = min(len(s), len(x) - i)
        x[i:i + m] += s[:m]
    return x + rng.normal(0, bruit, len(x)), fs


@pytest.mark.parametrize("f,zeta", [(67.47, 0.0015), (440.0, 0.002), (880.0, 0.0008)])
def test_son_pince(f, zeta):
    x, fs = _pincements(f, zeta, ecart=3.0 if f < 100 else 1.0)
    r = pince.analyser(x, fs)
    assert len(r.pincements) == 3
    assert r.f_hz == pytest.approx(f, rel=1e-4)
    assert r.zeta == pytest.approx(zeta, rel=0.03)


def test_son_pince_wav(tmp_path):
    x, fs = _pincements(440.0, 0.002)
    ch = str(tmp_path / "p.wav")
    with wave.open(ch, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs)
        w.writeframes((x / np.max(np.abs(x)) * 30000).astype("<i2").tobytes())
    r = pince.analyser_fichier(ch)
    assert r.f_hz == pytest.approx(440.0, rel=1e-4) and r.zeta == pytest.approx(0.002, rel=0.03)
