"""L'accord de construction mesure la hauteur établie, avec l'estimateur juste.

`_accorder` croyait les notes 45 à 59 de l'accordéon à 0 cent alors que la
hauteur tenue (pression de chambre, 3 à 4 s) était entre -0,6 et -2,3 cents.
Deux causes, mesurées : la fenêtre (0,3 à 0,6 s : la hauteur n'est pas encore
établie, jusqu'à 1 cent d'écart à la note 48) et l'estimateur
(`hybrid.playing_frequency` sur 0,3 s : jusqu'à 1,4 cent de biais). Les conditions
de mesure (pression de chambre contre son rayonné, table d'accord du timbre au
réglage par défaut) ne déplaçaient rien.

La hauteur tenue est lue ici tard (3 à 4 s) par `_hauteur_longue`, dont la
valeur coïncide à 0,01 cent avec la pente de phase du fondamental.
"""
import ctypes

import numpy as np
import pytest

from banc_recherche import live

pytestmark = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")

SR = 48000.0
NOTES = (45, 48, 52, 57, 59, 69, 84)


def _tenue_cents(inst, n, debut_s=3.0, fin_s=4.0):
    """Hauteur tenue de la note `n` (cents contre sa cible), sur la pression de
    chambre, au niveau de construction, lue entre `debut_s` et `fin_s`."""
    cible = live.midi_to_hz(n, inst.a4_hz)
    m = live._Params()
    cp = inst.params_for(n)
    ctypes.memmove(ctypes.byref(m), ctypes.byref(cp), ctypes.sizeof(cp))
    m.out_mode = 1
    v = live.Voice()
    v.note_on(m, 60, inst.niveau_pour(n))
    buf = np.zeros(512, dtype=np.float32)
    sortie = []
    for _ in range(int(fin_s * SR) // 512):
        buf[:] = 0.0
        v.render(buf)
        sortie.append(buf.copy())
    x = np.concatenate(sortie).astype('float64')
    f = live._hauteur_longue(x[int(debut_s * SR):], SR, cible)
    return 1200.0 * float(np.log2(f / cible))


@pytest.fixture(scope='module')
def acc():
    return live.build_instrument('accordeon', lo=45, hi=84, accord_timbre=False)


@pytest.mark.parametrize('n', NOTES)
def test_l_accordeon_construit_tient_sa_cible_a_un_cent(acc, n):
    assert abs(_tenue_cents(acc, n)) <= 1.0


@pytest.mark.parametrize('n', (45, 48))
def test_la_mesure_d_accord_voit_la_hauteur_tenue(acc, n):
    """Ce que `_frequence_jouee` lit est ce que la note tient, à 0,1 cent."""
    cible = live.midi_to_hz(n, acc.a4_hz)
    lue = live._frequence_jouee(acc.params_for(n), acc.niveau_pour(n), SR,
                                f_nom=cible)
    lue = 1200.0 * float(np.log2(lue / cible))
    assert abs(lue - _tenue_cents(acc, n)) <= 0.1


@pytest.mark.parametrize('nom,n', (('clarinette', 50), ('clarinette', 57),
                                   ('saxophone', 57), ('cornemuse', 57),
                                   ('bombarde', 67), ('violon', 55)))
def test_les_autres_familles_tiennent_leur_cible_a_un_cent(nom, n):
    inst = live.build_instrument(nom, lo=n, hi=n)
    assert abs(_tenue_cents(inst, n)) <= 1.0
