"""L'accord suit le timbre : un CC de timbre ne change pas la hauteur de la note.

Chambre (CC 70), largeur de lame (71) et Q (72) déplaçaient la hauteur jusqu'à
une trentaine de cents, parce que l'accord se fait une fois, à la construction.
Un accordeur ramène la lame à sa note après tout changement ; le moteur le fait
en retouchant la fréquence propre de la lame (`live.table_accord_timbre`).

Mesuré à la **pression d'accord** (celle de `level_default`) : à d'autres
pressions la dérive du timbre n'est pas la même, et le tableau, mesuré à une
seule pression, ne la suit qu'en partie (non testé ici).

Dans le grave, ce test tenait 2,4 cents (note 45) et 1,5 cent (note 57) : la
hauteur jouée n'avançait que par marches de 4 et 1 cent quand la lame bougeait,
avec des retours en arrière. La cause était le biquad de l'anche du moteur C, dont
les coefficients en simple précision ne placent pas ses pôles plus finement que
cela près de z = 1 (`hv_reed` stocke maintenant a1 + 2 et 1 - a2) ; la mesure de
hauteur n'y était pour rien. Les quatre notes sont tenues à ±1 cent, la hauteur étant lue sur la seconde
moitié d'une note de 3 s : à Q élevé dans le grave, elle met plus d'une seconde
à se poser.
"""
import dataclasses

import numpy as np
import pytest

from banc_recherche import live

pytestmark = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")

SR = 48000.0
NOTES = (45, 57, 69, 84)
VALS = (0, 16, 32, 48, 64, 80, 96, 112, 127)
#: écart toléré à la hauteur de CC 64, en cents
TOLERANCE = {45: 1.0, 57: 1.0, 69: 1.0, 84: 1.0}


@pytest.fixture(scope='module')
def acc():
    return live.build_instrument('accordeon', lo=45, hi=84)


def _expression_accord(inst):
    """Expression qui donne la pression d'accord (p = p_max x expression²)."""
    s = live.Synth(inst, polyphony=1)
    pression = inst.level_default / inst.params_for(57).src_admit
    return float(np.sqrt(pression / s.p_max))


def _synth(inst, timbre=None):
    s = live.Synth(inst, polyphony=1, timbre=timbre)
    s.pression_mesuree = True
    s.expression = _expression_accord(inst)
    return s


def _hauteur(inst, note, timbre=None, duree=3.0):
    s = _synth(inst, timbre)
    s.note_on(note, 100)
    x = np.concatenate([s.render(256) for _ in range(int(duree * SR) // 256)])
    return live._hauteur_longue(x[len(x) // 2:].astype(float), SR,
                                live.midi_to_hz(note))


def _cents(f, f0):
    return 1200.0 * np.log2(f / f0)


def test_le_tableau_couvre_les_notes(acc):
    assert sorted(acc.accord_timbre) == list(range(45, 85))
    forme = tuple(len(live.ACCORD_GRILLE[n]) for n in live.ACCORD_NOMS)
    for n, tab in acc.accord_timbre.items():
        assert tab.shape == forme and np.all(np.isfinite(tab))
        assert tab[4, 1, 4] == 0.0                     # tous à 64 : rien


def test_tous_a_64_le_son_est_celui_d_avant(acc):
    """Aucun accord appliqué : mêmes paramètres, même son à l'échantillon près."""
    sans = dataclasses.replace(acc, accord_timbre={})
    sons = []
    for inst in (acc, sans):
        s = _synth(inst)
        for nom in live.TIMBRE_CC:
            s.regler_timbre(nom, 64)
        s.note_on(69, 100)
        assert s.voices[0].params is inst.params_for(69)
        sons.append(np.concatenate([s.render(256) for _ in range(40)]))
    assert np.array_equal(sons[0], sons[1])


@pytest.mark.parametrize('note', (45, 57))
def test_la_hauteur_suit_la_lame_au_demi_cent(acc, note):
    """Fréquence propre de la lame demandée de 0,5 cent en 0,5 cent : la hauteur
    jouée avance d'autant, sans marche ni retour en arrière (le biquad de l'anche
    en simple précision la faisait avancer de 4 cents d'un coup à la note 45,
    avec des retours)."""
    base, f_nom = acc.params_for(note), live.midi_to_hz(note)
    h = [_cents(live._hauteur_note(
        live.params_timbre(base, accord=2.0 ** (c / 1200.0)), acc.level_default,
        f_nom, SR), f_nom) for c in np.arange(0.0, 3.01, 0.5)]
    pas = np.diff(h)
    assert np.all(pas > 0.2) and np.all(pas < 0.8), np.round(h, 2)


@pytest.mark.parametrize('note', NOTES)
def test_un_cc_seul_garde_la_hauteur(acc, note):
    f0 = _hauteur(acc, note)
    pires = {}
    for nom in live.TIMBRE_CC:
        ecarts = [_cents(_hauteur(acc, note, {nom: v}), f0) for v in VALS]
        pires[nom] = max(abs(e) for e in ecarts)
    assert max(pires.values()) <= TOLERANCE[note], pires


@pytest.mark.parametrize('note', (69, 84))
def test_pas_de_saut_de_hauteur_quand_le_cc_bouge(acc, note):
    """Note tenue, chambre à 127 à 1 s puis retour à 64 à 2,2 s : la hauteur,
    mesurée par fenêtres de 100 ms, reste à 1,5 cent de ce qu'elle était, avant,
    pendant le lissage et après ; le signal n'a pas de saut brusque."""
    s = _synth(acc)
    s.note_on(note, 100)
    blocs = [s.render(256) for _ in range(int(3.4 * SR) // 256)]
    k_haut, k_bas = int(1.0 * SR) // 256, int(2.2 * SR) // 256
    s = _synth(acc)
    s.note_on(note, 100)
    blocs = []
    for k in range(int(3.4 * SR) // 256):
        if k == k_haut:
            s.regler_timbre('chambre', 127)
        if k == k_bas:
            s.regler_timbre('chambre', 64)
        blocs.append(s.render(256))
    x = np.concatenate(blocs).astype(float)
    f_nom = live.midi_to_hz(note)
    pas, fen = int(0.05 * SR), int(0.1 * SR)
    hauteurs = [(i / SR, live._hauteur_longue(x[i:i + fen], SR, f_nom))
                for i in range(int(0.6 * SR), len(x) - fen, pas)]
    avant = np.median([f for t, f in hauteurs if t < 0.95])
    ecarts = [abs(_cents(f, avant)) for t, f in hauteurs]
    assert max(ecarts) <= 1.5, max(ecarts)
    # pas de clic : la plus forte variation d'un échantillon à l'autre ne
    # dépasse pas 2,5 fois celle du régime d'avant (le niveau, lui, bouge)
    d = np.abs(np.diff(x))
    avant_clic = d[int(0.6 * SR):int(0.95 * SR)].max()
    assert d[int(0.95 * SR):].max() <= 2.5 * avant_clic
