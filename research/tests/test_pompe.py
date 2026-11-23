"""Le débit déplacé par la lame elle-même (« pompe ») dans le débit rayonné.

Le son rayonné du moteur était la dérivée du débit de fente seul ; il manquait
le débit que la lame déplace en bougeant, `q_pompe = S_eff × vitesse de la lame`,
avec `S_eff = F × largeur × longueur de la lame` (`force_area_m2`). Le réglage
`pompe` (F, sans unité) l'ajoute au débit rayonné avant la dérivation et le
filtre anti-repliement ; le bilan de la chambre et la lame ne changent pas.

Défaut F = 0 : le son d'avant, à l'échantillon près. Les références du moteur
d'avant (`ref_pompe_f0.npz`) ont été rendues par le moteur de `origin/main`
avant l'ajout. Le défaut de F, 0,8 au CC 74 = 64, est **provisoire, non mesuré**.
"""
import pathlib

import numpy as np
import pytest

from banc_recherche import embedded as emb
from banc_recherche import hybrid, live

sans_compilateur = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")

SR = 48000.0
NIVEAU = 2.9e-6                      # m³/s, niveau nominal de l'anche libre
REF = pathlib.Path(__file__).with_name('ref_pompe_f0.npz')
NOTES = (57, 65, 69)
F_TEST = 0.8


def _params(f0=220.0, pompe=0.0):
    return emb.params_from_voice(hybrid.accordeon(f0_hz=f0), samplerate=SR,
                                 name='accordeon', pompe=pompe)


def _c(p, n_blocs):
    cp, _garde = live._to_c_params(p)
    v = live.Voice()
    v.note_on(cp, 57, NIVEAU)
    bloc = np.zeros(256, np.float32)
    morceaux = []
    for _ in range(n_blocs):
        v.render(bloc, glide=1.0)
        morceaux.append(bloc.copy())
    return np.concatenate(morceaux)


@pytest.fixture(scope='module')
def acc():
    return live.build_instrument('accordeon', lo=57, hi=69)


def _tenue(inst, note, F=0.0, expr=80 / 127.0, duree=3.0):
    """Une note tenue à CC 11 = 80 (pression mesurée), 3 s, `Synth(pompe=F)`."""
    s = live.Synth(inst, polyphony=1, pompe=F)
    s.pression_mesuree = True
    s.expression = expr
    s.note_on(note, 100)
    return np.concatenate([s.render(256).copy()
                           for _ in range(int(duree * SR) // 256)])


def _f0_et_partiels(x, f_nom, n=6):
    """Fréquence de la fondamentale (pic de la TF fenêtrée, interpolé) et les
    `n` premiers partiels en dB par rapport au premier."""
    x = np.asarray(x, float)[-int(2.0 * SR):]
    x = x - x.mean()
    N = 1 << 19
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)), N))
    fr = np.fft.rfftfreq(N, 1 / SR)

    def pic(f, largeur):
        i = np.where(np.abs(fr - f) < largeur)[0]
        k = i[np.argmax(X[i])]
        a, b, c = np.log(X[k - 1:k + 2] + 1e-30)
        d = 0.5 * (a - c) / (a - 2 * b + c)
        return fr[k] + d * (fr[1] - fr[0]), X[k]

    f0, a1 = pic(f_nom, f_nom * 0.03)
    dB = [20 * np.log10(pic(k * f0, f0 * 0.02)[1] / a1) for k in range(1, n + 1)]
    return f0, dB


# -- la table du CC 74 ---------------------------------------------------------

def test_le_cc_74_est_libre_et_lineaire():
    assert live.CC_POMPE == 74 and live.POMPE_CC[0] == 74
    pris = set(live.CC_EXPRESSION) | {123, 1, 7, 10, 64} | set(live.CC_TIMBRE)
    assert 74 not in pris
    assert live.facteur_pompe(0) == 0.0
    assert live.facteur_pompe(64) == pytest.approx(0.8)
    assert live.facteur_pompe(127) == pytest.approx(1.6)
    assert live.facteur_pompe(32) == pytest.approx(0.4)
    assert live.facteur_pompe(200) == pytest.approx(1.6)      # borné
    # croissant, sans trou
    v = [live.facteur_pompe(c) for c in range(128)]
    assert all(b > a for a, b in zip(v, v[1:]))
    # les quatre réglages de timbre n'ont pas bougé
    assert live.CC_TIMBRE == {70: 'chambre', 71: 'largeur', 72: 'q', 73: 'jeu'}


def test_la_table_dit_que_le_defaut_est_provisoire():
    src = pathlib.Path(live.__file__).read_text(encoding='utf-8')
    i = src.index('POMPE_CC = (')
    avant = src[max(0, i - 2500):i]
    assert 'provisoire, non mesuré' in avant


# -- F = 0 : le moteur d'avant, à l'échantillon près ---------------------------

def test_f0_python_identique_au_moteur_d_avant():
    ref = np.load(REF)['python']
    py, _ = emb.RealtimeVoice(_params()).render(len(ref), NIVEAU)
    assert np.array_equal(py, ref)


@sans_compilateur
def test_f0_c_identique_au_moteur_d_avant():
    ref = np.load(REF)['c']
    assert np.array_equal(_c(_params(), len(ref) // 256), ref)


@sans_compilateur
def test_f0_synth_identique_au_moteur_d_avant():
    inst = live.build_instrument('accordeon', lo=57, hi=57)
    ref = np.load(REF)['synth']
    for kw in ({}, {'pompe': 0.0}):
        s = live.Synth(inst, polyphony=1, **kw)
        s.pression_mesuree = True
        s.expression = 80 / 127.0
        s.note_on(57, 100)
        x = np.concatenate([s.render(256).copy() for _ in range(40)])
        assert np.array_equal(x, ref)
    # le CC 74 à 0 est F = 0 : même son
    s = live.Synth(inst, polyphony=1)
    s.pression_mesuree = True
    s.expression = 80 / 127.0
    assert s.timbre_cc(74, 0)
    s.note_on(57, 100)
    x = np.concatenate([s.render(256).copy() for _ in range(40)])
    assert np.array_equal(x, ref)


# -- F = 0,8 : C et Python égaux, la lame ne change pas ------------------------

@sans_compilateur
def test_c_et_python_egaux_a_f_0_8():
    # Même fenêtre (512 échantillons) et même tolérance que
    # `test_le_noyau_c_suit_la_reference_python` : au-delà, l'écart float32 /
    # float64 grandit de lui-même, à F = 0 comme à F = 0,8 (mesuré sur 4096
    # échantillons : 3,1e-3 sans pompe, 3,0e-3 avec). On le vérifie aussi :
    # la pompe n'ajoute pas d'écart.
    p = _params(pompe=F_TEST)
    assert p.pump_area_m2 == pytest.approx(F_TEST * p.force_area_m2)
    n = 4096
    c = _c(p, n // 256).astype(float)
    c0 = _c(_params(), n // 256).astype(float)
    py, _ = emb.RealtimeVoice(p).render(n, NIVEAU)
    py0, _ = emb.RealtimeVoice(_params()).render(n, NIVEAU)
    assert np.max(np.abs(py - py0)) > 0.5 * np.std(py0)       # la pompe s'entend
    assert np.max(np.abs(c[:512] - py[:512])) < 1e-2 * np.std(py)
    assert (np.max(np.abs(c - py)) < 2.0 * np.max(np.abs(c0 - py0)))


class _EnregistreY(emb.RealtimeVoice):
    """Garde la position de la lame à chaque pas interne."""

    def reset(self):
        super().reset()
        self.ys = []

    def _exciter(self, response, level):
        r = super()._exciter(response, level)
        self.ys.append(self._y_anche)
        return r


def test_la_lame_ne_change_pas_et_la_sortie_est_lineaire_en_f():
    n = 6000
    x0, h0 = emb.RealtimeVoice(_params()).render(n, NIVEAU, out_opening=True)
    x1, h1 = emb.RealtimeVoice(_params(pompe=F_TEST)).render(
        n, NIVEAU, out_opening=True)
    x2, h2 = emb.RealtimeVoice(_params(pompe=2 * F_TEST)).render(
        n, NIVEAU, out_opening=True)
    # le bilan de la chambre et la lame ne dépendent pas de F : exactement
    assert np.array_equal(h0, h1) and np.array_equal(h0, h2)
    # la sortie ne fait qu'ajouter le terme de pompe : linéaire en F
    assert np.allclose(x2 - x0, 2 * (x1 - x0), rtol=1e-9, atol=1e-9 * np.std(x0))


def test_le_signe_la_pompe_est_moins_s_eff_fois_l_acceleration_de_la_lame():
    """Débit net = débit de fente - S_eff x vitesse de la lame (y > 0 ouvre la
    fente : la lame qui monte retire du débit net). La part de pompe de la
    sortie est donc la dérivée de -S_eff x vitesse, filtrée comme le reste : on
    la recalcule à part, depuis la position de la lame enregistrée à chaque pas
    interne, et on la compare à l'écart des deux rendus."""
    n = 3000
    v0 = _EnregistreY(_params())
    x0, _ = v0.render(n, NIVEAU)
    v1 = _EnregistreY(_params(pompe=F_TEST))
    x1, _ = v1.render(n, NIVEAU)
    assert np.array_equal(v0.ys, v1.ys)                       # la lame ne change pas
    y = np.asarray(v1.ys)
    p = v1.p if hasattr(v1, 'p') else _params(pompe=F_TEST)
    fs = p.fs_internal
    S = p.pump_area_m2
    vy = np.concatenate([[0.0], np.diff(y)]) * fs
    q = -S * vy                                              # terme ajouté au débit
    # dérivée arrière (la première vaut 0 : _net_prec est amorcé sur la valeur)
    dq = np.concatenate([[0.0], np.diff(q)]) * fs
    aa = emb.RealtimeVoice(_params()).aa
    sortie = np.array([aa.step(d) for d in dq])[p.oversample - 1::p.oversample]
    ecart = x1 - x0
    assert np.max(np.abs(ecart - sortie)) < 1e-9 * np.max(np.abs(ecart))
    assert np.max(np.abs(ecart)) > 0.5 * np.std(x0)


@sans_compilateur
def test_le_signe_dans_le_spectre_suit_l_essai_hors_moteur(acc):
    """Essai hors moteur (note 57, CC 11 = 80) : avec S_eff = +0,8 x surface,
    A2/A1 = -14,5 dB et A3/A1 = -8,9 dB ; le signe contraire donne -14,8 et
    -8,2 : A3/A1 plus haut."""
    plus = _f0_et_partiels(_tenue(acc, 57, +F_TEST), 220.0)[1]
    moins = _f0_et_partiels(_tenue(acc, 57, -F_TEST), 220.0)[1]
    assert abs(plus[1] - (-14.5)) < 1.0 and abs(plus[2] - (-8.9)) < 1.0, plus
    assert moins[2] > plus[2] + 0.3, (plus, moins)


# -- F = 0,8 : le partiel 1 est le plus fort, la hauteur ne bouge pas ----------

@sans_compilateur
@pytest.mark.parametrize('note', NOTES)
def test_a_f_0_8_le_partiel_1_est_le_plus_fort(acc, note):
    # Seuil tiré de la mesure (essai hors moteur et moteur, note 57 : A2/A1 de
    # +5,7 à -14,4 dB ; note 65 : -9,0 ; note 69 : -6,8 ; A3/A1 au plus
    # -5,1 dB) : chaque partiel 2 à 6 est au moins 3 dB sous le premier. Sans
    # pompe, le deuxième partiel dépasse le premier (+5,7, +10,0, +11,5 dB).
    f = 440.0 * 2 ** ((note - 69) / 12)
    _, sans = _f0_et_partiels(_tenue(acc, note, 0.0), f)
    _, avec = _f0_et_partiels(_tenue(acc, note, F_TEST), f)
    assert sans[1] > 0.0, sans
    assert max(avec[1:]) < -3.0, avec


@sans_compilateur
@pytest.mark.parametrize('note', NOTES)
def test_la_hauteur_tenue_ne_bouge_pas_de_0_1_cent(acc, note):
    f = 440.0 * 2 ** ((note - 69) / 12)
    f_sans, _ = _f0_et_partiels(_tenue(acc, note, 0.0), f)
    f_avec, _ = _f0_et_partiels(_tenue(acc, note, F_TEST), f)
    assert abs(1200 * np.log2(f_avec / f_sans)) < 0.1


# -- le CC 74 -------------------------------------------------------------------

@sans_compilateur
def test_le_cc_74_regle_f_avec_le_lissage_des_cc_de_timbre(acc):
    s = live.Synth(acc, polyphony=1)
    s.pression_mesuree = True
    s.expression = 80 / 127.0
    s.note_on(57, 100)
    s.render(256)
    assert s._pompe_lisse == 0.0
    assert s.timbre_cc(74, 64) is True
    assert s._pompe_cible == pytest.approx(0.8)
    assert s._pompe_lisse == 0.0                    # voix active : lissé
    s.render(256)
    assert 0.0 < s._pompe_lisse < 0.8
    t = live.params_timbre(s.voices[0].base, **s._timbre_voix(57))
    assert t.pump_area == pytest.approx(s._pompe_lisse * t.surface_force)
    for _ in range(200):
        s.render(256)
    assert s._pompe_lisse == pytest.approx(0.8)
    assert s.voices[0].params.pump_area == pytest.approx(
        0.8 * s.voices[0].base.surface_force)
    # sans voix active, pris tout de suite
    s2 = live.Synth(acc, polyphony=1)
    s2.timbre_cc(74, 127)
    assert s2._pompe_lisse == pytest.approx(1.6)


@sans_compilateur
def test_rendre_midi_prend_pompe_et_le_cc_74(acc, tmp_path):
    import mido
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.Message('control_change', control=11, value=80, time=0))
    tr.append(mido.Message('note_on', note=57, velocity=100, time=0))
    tr.append(mido.Message('note_off', note=57, velocity=0, time=960))
    f = tmp_path / 'a.mid'
    mid.save(str(f))
    a = live.rendre_midi(str(f), acc, cc='pression', par_canal=False,
                         limiteur=False)
    b = live.rendre_midi(str(f), acc, cc='pression', par_canal=False,
                         limiteur=False, pompe=0.0)
    c = live.rendre_midi(str(f), acc, cc='pression', par_canal=False,
                         limiteur=False, pompe=F_TEST)
    a, b, c = (np.asarray(next(iter(v.values())) if isinstance(v, dict) else v)
               for v in (a, b, c))
    assert np.array_equal(a, b)
    assert np.max(np.abs(c - a)) > 0.1 * np.std(a)
