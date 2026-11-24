"""Réglages de timbre de l'accordéon en CC MIDI (ordre 7 de la feuille de route).

Quatre grandeurs que personne n'a mesurées sur une lame réelle (volume de
chambre, largeur de lame, Q, jeu de fente) sont des facteurs de timbre, CC 70 à
73 : CC 64 = le défaut d'avant, à l'échantillon près. Leurs valeurs par défaut
restent provisoires, non mesurées.

L'instrument (notes 45 à 84, accordées) se construit une fois pour tout le
fichier : un peu plus de deux minutes.
"""
import numpy as np
import pytest

from banc_recherche import live

pytestmark = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")

SR = 48000.0
NOMS = tuple(live.TIMBRE_CC)


@pytest.fixture(scope='module')
def acc():
    return live.build_instrument('accordeon', lo=45, hi=84)


def _synth(inst, expr, timbre=None, poly=1):
    s = live.Synth(inst, polyphony=poly, timbre=timbre)
    s.pression_mesuree = True
    s.expression = expr
    return s


def _jouer(s, n_total, bloc=256, evts=None):
    out = np.zeros(n_total, np.float32)
    for k, i in enumerate(range(0, n_total, bloc)):
        if evts and k in evts:
            evts[k](s)
        n = min(bloc, n_total - i)
        out[i:i + n] = s.render(n)
    return out


def _note(inst, note, expr, timbre=None, duree=1.0):
    s = _synth(inst, expr, timbre)
    s.note_on(note, 100)
    return _jouer(s, int(duree * SR)), s


def _centroide(x):
    x = np.asarray(x, float)
    x = x - x.mean()
    a = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 16))
    fr = np.fft.rfftfreq(1 << 16, 1 / SR)
    return float((fr * a).sum() / a.sum())


def _niveau_dbfs(x, inst, gain=0.5):
    x = np.asarray(x, float)[-int(0.3 * SR):]
    r = np.sqrt(np.mean((x - x.mean()) ** 2)) * gain * inst.output_scale
    return 20 * np.log10(max(r, 1e-30))


# -- la table ------------------------------------------------------------------

def test_la_table_des_cc_est_unique_et_libre():
    numeros = [v[0] for v in live.TIMBRE_CC.values()]
    assert numeros == [70, 71, 72, 73]
    assert len(set(numeros)) == 4
    pris = set(live.CC_EXPRESSION) | {123, 1, 7, 10, 64}
    assert not pris & set(numeros)
    assert live.CC_TIMBRE == {70: 'chambre', 71: 'largeur', 72: 'q', 73: 'jeu'}


@pytest.mark.parametrize('nom', NOMS)
def test_facteur_logarithmique_borne_et_64_vaut_un(nom):
    _, fmin, fmax, _ = live.TIMBRE_CC[nom]
    assert live.facteur_timbre(nom, 64) == 1.0
    assert live.facteur_timbre(nom, 0) == pytest.approx(fmin)
    assert live.facteur_timbre(nom, 127) == pytest.approx(fmax)
    f = [live.facteur_timbre(nom, v) for v in range(128)]
    assert all(b > a for a, b in zip(f, f[1:]))                 # monotone
    # logarithmique : le milieu de chaque demi-échelle est la moyenne géométrique
    assert live.facteur_timbre(nom, 32) == pytest.approx(np.sqrt(fmin))
    # hors plage : bornée
    assert live.facteur_timbre(nom, 300) == pytest.approx(fmax)
    assert live.facteur_timbre(nom, -5) == pytest.approx(fmin)


def test_les_bornes_de_la_consigne():
    t = live.TIMBRE_CC
    assert (t['chambre'][1], t['chambre'][2]) == (0.5, 2.0)
    assert (t['largeur'][1], t['largeur'][2]) == (0.5, 2.0)
    assert (t['q'][1], t['q'][2]) == (0.5, 2.0)
    assert (t['jeu'][1], t['jeu'][2]) == (0.5, 3.0)


def test_l_option_en_ligne_de_commande_existe():
    assert live.main(['accordeon', '--cc-chambre', '96', '--cc-largeur', '30',
                      '--cc-q', '64', '--cc-jeu', '100', '--liste']) == 0


# -- CC 64 = le défaut, à l'échantillon près ----------------------------------------

@pytest.mark.parametrize('note', (50, 69, 76))
def test_cc_64_redonne_le_son_par_defaut(acc, note):
    ref, _ = _note(acc, note, 0.5)
    tout, _ = _note(acc, note, 0.5, timbre={n: 64 for n in NOMS})
    assert np.array_equal(ref, tout)
    for nom in NOMS:
        un, _ = _note(acc, note, 0.5, timbre={nom: 64})
        assert np.array_equal(ref, un), nom


def test_cc_64_par_message_redonne_le_son_par_defaut(acc):
    """Le CC arrivé par `timbre_cc` (comme dans un fichier) avant la note."""
    ref, _ = _note(acc, 57, 0.5)
    s = _synth(acc, 0.5)
    for cc in (70, 71, 72, 73):
        assert s.timbre_cc(cc, 64)
    assert not s.timbre_cc(11, 64)               # l'expression n'est pas du timbre
    s.note_on(57, 100)
    assert np.array_equal(ref, _jouer(s, int(SR)))


def test_les_autres_familles_ignorent_les_cc_de_timbre():
    cl = live.build_instrument('clarinette', lo=60, hi=60)
    s = live.Synth(cl, polyphony=1, timbre={'chambre': 127, 'largeur': 0})
    s.note_on(60, 100)
    a = s.render(4000)
    s2 = live.Synth(cl, polyphony=1)
    s2.note_on(60, 100)
    assert np.array_equal(a, s2.render(4000))


# -- le sens des effets -----------------------------------------------------------

@pytest.mark.parametrize('note', (57, 69))
def test_chambre_et_largeur_baissent_le_centroide_dans_le_sens_attendu(acc, note):
    d, _ = _note(acc, note, 0.5)
    c0 = _centroide(d[-int(0.3 * SR):])
    plus, _ = _note(acc, note, 0.5, timbre={'chambre': 127})      # chambre x2
    moins, _ = _note(acc, note, 0.5, timbre={'chambre': 0})       # chambre x0,5
    assert _centroide(plus[-int(0.3 * SR):]) < c0
    if note == 57:
        # À hauteur gardée (l'accord suit le timbre), la chambre réduite
        # n'éclaircit plus à coup sûr : à la note 69 le centroïde baisse de 4 %
        # (mesuré, accordeon/cc_accord). Avant l'accord, cette hausse venait
        # de la hauteur qui montait de 13 cents.
        assert c0 < _centroide(moins[-int(0.3 * SR):])
    large, _ = _note(acc, note, 0.5, timbre={'largeur': 127})     # lame x2
    fine, _ = _note(acc, note, 0.5, timbre={'largeur': 0})        # lame x0,5
    assert _centroide(fine[-int(0.3 * SR):]) < c0
    if note == 57:
        # Hauteur tenue à 0,3 cent près, la lame large ne déplace plus le
        # centroïde de la note 57 que de -0,2 % (mesuré) : sous la précision de
        # ce test, on n'en exige pas le sens. À la note 69 : +2,8 %.
        assert _centroide(large[-int(0.3 * SR):]) > 0.99 * c0
    else:
        assert c0 < _centroide(large[-int(0.3 * SR):])


@pytest.mark.parametrize('nom', ('q', 'jeu'))
def test_q_et_jeu_changent_le_son_aux_bornes(acc, nom):
    """Q règle la réponse des graves et le jeu a peu d'effet (mesuré hors
    moteur) : on exige seulement que les deux bornes ne rendent pas le signal
    du défaut, sans fixer un sens que la mesure n'a pas donné (cf. effets.txt)."""
    d, _ = _note(acc, 50, 0.5)
    for v in (0, 127):
        x, _ = _note(acc, 50, 0.5, timbre={nom: v})
        assert not np.array_equal(d, x)
        assert np.isfinite(x).all()


# -- aucune note ne se tait aux bornes -----------------------------------------------

def _bornes(tous0=True):
    """Chaque CC seul à une borne, puis les quatre ensemble."""
    cas = [{nom: v} for nom in NOMS for v in (0, 127)]
    cas.append({nom: 127 for nom in NOMS})
    if tous0:
        cas.append({nom: 0 for nom in NOMS})
    return cas


def _muettes(acc, expr, cas):
    muettes = []
    for timbre in cas:
        for note in range(45, 85):
            x, _ = _note(acc, note, expr, timbre=timbre, duree=0.8)
            n = _niveau_dbfs(x, acc)
            if n < -80.0:
                muettes.append((note, timbre, round(float(n), 1)))
    return muettes


@pytest.mark.parametrize('expr', (0.3, 1.0))
def test_aucune_note_de_45_a_84_ne_se_tait_aux_bornes(acc, expr):
    """Silence = sous -80 dBFS (même règle que les rendus de l'accordéon), sur la
    dernière 0,3 s de 0,8 s de note, gain 0,5 et échelle de sortie. Chaque CC
    seul à 0 puis à 127, les quatre à 127, et (expression 1,0) les quatre à 0."""
    muettes = _muettes(acc, expr, _bornes(tous0=(expr == 1.0)))
    assert not muettes, muettes


# Avant la loi de source en r² (24/11/2026), ce test était un xfail strict : les
# quatre CC à 0 ensemble, expression 0,3, les notes 81 à 84 se taisaient (-87 à
# -94 dBFS ; voir accordeon/cc_timbre/effets.txt). Avec R = 1,5e7 r² elles
# jouent : le xfail strict est devenu un échec (XPASS), le test est maintenant
# un test ordinaire, même assertion.
def test_les_quatre_cc_a_zero_a_expression_faible_eteignent_le_haut(acc):
    assert not _muettes(acc, 0.3, [{nom: 0 for nom in NOMS}])


# -- pas de clic quand un CC bouge pendant une note --------------------------------------

def _raideur(x, w=480):
    """Plus grand saut d'échantillon rapporté au RMS de la même fenêtre de 10 ms,
    pour chaque fenêtre : un clic le fait monter, un simple changement de niveau
    (le timbre bouge, la note devient plus forte ou plus faible) non."""
    x = np.asarray(x, float)
    d = np.abs(np.diff(x))
    n = (len(d) // w) * w
    mx = d[:n].reshape(-1, w).max(axis=1)
    rms = np.sqrt(np.mean(x[:n].reshape(-1, w) ** 2, axis=1))
    return mx / np.maximum(rms, 1e-12)


@pytest.mark.parametrize('nom,val', [(n, v) for n in NOMS for v in (0, 127)])
def test_pas_de_clic_quand_un_cc_bouge_pendant_une_note(acc, nom, val):
    """Le CC saute de 64 à 0 ou 127 sur une note tenue. Le saut d'échantillon
    rapporté au niveau (par fenêtre de 10 ms) ne dépasse nulle part, pendant
    0,4 s après le changement, 1,5 fois son maximum du régime établi avant ; rien
    n'est non fini ; le facteur lissé arrive à sa cible."""
    s = _synth(acc, 0.5)
    s.note_on(57, 100)
    k_saut = int(1.0 * SR) // 256
    i0 = k_saut * 256
    x = _jouer(s, int(1.6 * SR), evts={k_saut: lambda sy: sy.regler_timbre(nom, val)})
    assert np.isfinite(x).all()
    avant = _raideur(x[i0 - int(0.3 * SR):i0]).max()
    apres = _raideur(x[i0:i0 + int(0.4 * SR)]).max()
    assert apres <= 1.5 * avant, (apres, avant)
    assert s.facteurs_timbre()[nom] == pytest.approx(live.facteur_timbre(nom, val))


def test_le_changement_vaut_pour_les_notes_qui_sonnent(acc):
    """Un CC bougé pendant la note change le son de CETTE note, sans retoucher
    à son attaque."""
    ref, _ = _note(acc, 57, 0.5, duree=1.6)
    s = _synth(acc, 0.5)
    s.note_on(57, 100)
    k = int(1.0 * SR) // 256
    x = _jouer(s, int(1.6 * SR), evts={k: lambda sy: sy.regler_timbre('chambre', 127)})
    assert np.array_equal(x[:k * 256], ref[:k * 256])             # avant : rien
    c0 = _centroide(ref[-int(0.3 * SR):])
    assert _centroide(x[-int(0.3 * SR):]) < c0                    # après : plus sombre


def test_un_fichier_midi_porte_les_cc_de_timbre(acc, tmp_path):
    mido = pytest.importorskip('mido')
    def fichier(cc_val):
        mid = mido.MidiFile(ticks_per_beat=480)
        tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.Message('control_change', control=11, value=64, time=0))
        for cc in (70, 71, 72, 73):
            if cc_val is not None:
                tr.append(mido.Message('control_change', control=cc, value=cc_val[cc], time=0))
        tr.append(mido.Message('note_on', note=57, velocity=100, time=0))
        tr.append(mido.Message('note_off', note=57, velocity=0, time=960))
        p = tmp_path / ('a%d.mid' % (0 if cc_val is None else 1 + cc_val[70]))
        mid.save(str(p))
        return str(p)
    def rendre(p, **kw):
        return live.rendre_midi(p, acc, polyphonie=2, cc='pression', par_canal=False,
                                queue_s=0.1, **kw)
    sans = rendre(fichier(None))
    egal = rendre(fichier({70: 64, 71: 64, 72: 64, 73: 64}))
    assert np.array_equal(sans, egal)
    autre = rendre(fichier({70: 127, 71: 64, 72: 64, 73: 64}))
    assert not np.array_equal(sans, autre)
    # l'option de départ : même rendu que le CC du fichier mis à 127 avant la note
    opt = rendre(fichier(None), timbre={'chambre': 127})
    assert np.array_equal(opt, autre)
