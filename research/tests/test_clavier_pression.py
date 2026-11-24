"""Le clavier de l'accordéon selon la pression : la résistance de source suit la note.

Cause (mesurée le 24/11/2026) : dans `hybrid.accordeon(f0)`, toutes les cotes
suivaient la similitude `r = f0/110` sauf la résistance de source, fixe à
2·10⁸ Pa·s/m³. Les notes graves (36 à 48) et aiguës (88 à 96) ne partaient
pas à basse pression : 348 cases sur 427 jouaient (61 notes × 7 pressions de
100 à 1000 Pa), les notes 95 et 96 étaient muettes partout. Avec
`R = 1,5·10⁷ r²`, 427 cases sur 427.

La valeur de référence 1,5·10⁷ est **provisoire** (aucune mesure de la
résistance de passage) : ces tests gardent la loi en `r²`, pas le coefficient.
"""
import importlib.util
import pathlib

import numpy as np
import pytest

from banc_recherche import embedded, hybrid, live

SCRIPT_SEUIL = (pathlib.Path(__file__).resolve().parents[1] / 'scripts'
                / 'seuil_lineaire_accordeon.py')
NOTES = (36, 60, 84, 96)
SR = 48000


def _f(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


def test_la_resistance_de_source_suit_la_similitude():
    """(a) `source_impedance / r²` constant : la source suit la note comme les cotes."""
    rapports = []
    for n in NOTES:
        r = _f(n) / hybrid.ACCORDEON_REF_HZ
        p = embedded.params_from_voice(hybrid.accordeon(_f(n)))
        rapports.append(p.source_impedance / r ** 2)
    assert np.allclose(rapports, hybrid.ACCORDEON_SOURCE_REF, rtol=1e-9)


def test_une_valeur_explicite_l_emporte_sur_la_loi():
    v = hybrid.accordeon(_f(96), source_impedance=2.0e8)
    assert v.exciter.source_impedance == 2.0e8
    # le défaut de la classe, lui, ne change pas
    assert hybrid.FreeReedExciter().source_impedance == 2.0e8


def _charger_seuil():
    spec = importlib.util.spec_from_file_location('seuil_lineaire_accordeon',
                                                  SCRIPT_SEUIL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_le_seuil_lineaire_est_plat_sur_le_clavier():
    """(b) Hors moteur : P_on identique (5 %) aux quatre notes, et sous 100 Pa."""
    mod = _charger_seuil()
    p_on = []
    for n in NOTES:
        s = mod.seuil(mod.constantes(n))
        assert s['P_on'] is not None, f"note {n} : pas de seuil"
        p_on.append(s['P_on'])
    p_on = np.array(p_on)
    assert np.all(p_on < 100.0), p_on
    assert np.max(np.abs(p_on / np.median(p_on) - 1.0)) < 0.05, p_on


# --------------------------------------------------------------------------
# moteur C
# --------------------------------------------------------------------------
sans_compilo = pytest.mark.skipif(live._compilateur()[0] is None,
                                  reason="pas de compilateur C")


def _poser_d_un_coup(inst, note, pression_pa, duree=3.0):
    cp = inst.params_for(note)
    niveau = pression_pa * float(cp.src_admit)
    nb = int(duree * SR) // 256 + 1
    v = live.Voice()
    v.note_on(cp, note, niveau)
    sortie = np.empty(nb * 256, np.float32)
    bloc = np.zeros(256, np.float32)
    for i in range(nb):
        v.target = niveau
        bloc[:] = 0.0
        v.render(bloc, glide=1.0, silence=0.0)
        sortie[i * 256:(i + 1) * 256] = bloc
    return sortie[:int(duree * SR)].astype(float)


def _rms_db(x):
    x = x - x.mean()
    return 20.0 * np.log10(max(float(np.sqrt(np.mean(x ** 2))), 1e-30))


def _joue(x, note):
    """(joue, variation de niveau en dB sur la dernière seconde, écart en cents)."""
    fin = x[-SR:]
    pas = SR // 10
    niveaux = [_rms_db(fin[i * pas:(i + 1) * pas]) for i in range(10)]
    if max(niveaux) < -85.0:
        return False, float('inf'), float('nan')
    f = live._hauteur_longue(fin, SR, _f(note))
    cents = 1200.0 * np.log2(f / _f(note)) if f > 0 else float('nan')
    return True, max(niveaux) - min(niveaux), cents


@sans_compilo
@pytest.mark.parametrize('pression', [100.0, 1000.0])
def test_toutes_les_notes_jouent_a_basse_et_haute_pression(pression):
    """(c) Posée d'un coup, chaque note accordée tient son niveau et sa hauteur."""
    for n in (36, 48, 60, 72, 84, 96):
        inst = live.build_instrument('accordeon', lo=n, hi=n, accord_timbre=False)
        joue, variation, cents = _joue(_poser_d_un_coup(inst, n, pression), n)
        assert joue, f"note {n} muette à {pression:.0f} Pa"
        assert variation < 3.0, f"note {n} à {pression:.0f} Pa : niveau instable ({variation:.1f} dB)"
        assert abs(cents) < 30.0, f"note {n} à {pression:.0f} Pa : {cents:+.1f} cents"


@sans_compilo
def test_temoin_l_ancienne_resistance_fixe_laisse_la_96_muette():
    """(d) La trouvaille gardée : à 2·10⁸ fixe, la note 96 ne joue pas à 1000 Pa."""
    n = 96
    inst = live.build_instrument('accordeon', lo=n, hi=n, accord_timbre=False,
                                 source_impedance=2.0e8)
    assert inst.params_for(n).src_admit == pytest.approx(1.0 / 2.0e8)
    joue, _, _ = _joue(_poser_d_un_coup(inst, n, 1000.0), n)
    assert not joue


@sans_compilo
def test_le_nominal_est_une_pression_convertie_par_note():
    """Le niveau nominal d'une note = 580 Pa × son admittance de source."""
    inst = live.build_instrument('accordeon', lo=36, hi=96, tune=False)
    assert inst.pression_nominale == hybrid.ACCORDEON_PRESSION_NOMINALE_PA
    for n in (36, 69, 96):
        assert inst.niveau_pour(n) == pytest.approx(
            hybrid.ACCORDEON_PRESSION_NOMINALE_PA * inst.params_for(n).src_admit)
    # R = 2·10⁸ redonne exactement l'ancien nominal
    assert live.niveau_nominal(hybrid.FreeReedExciter()) == 2.9e-6
