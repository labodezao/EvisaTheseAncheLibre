"""Sortie rayonnée de l'anche libre : la dérivée du débit net, pas la pression.

Audit du 23/11/2026 : le moteur sortait la pression de la chambre. Elle
intègre le débit (partiel 8 à -43,5 dB au lieu de -7,5 dB), et elle porte la
pression continue du soufflet, qui s'additionne d'une voix à l'autre et
écrase le limiteur : un accord de quatre notes était muet.

La partie Python n'a besoin que de numpy. Celle du noyau C saute sans
compilateur (`live._compilateur`, qui trouve aussi MSVC), celle du lecteur
MIDI sans `mido`.
"""
import numpy as np
import pytest

from banc_recherche import embedded as emb
from banc_recherche import hybrid, live
from banc_recherche.soufflet import Soufflet, pression_demandee

SR = 48000.0
NIVEAU = 2.9e-6                      # m³/s, niveau nominal de l'anche libre

sans_compilateur = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")


def partiels(x, f_nom, sr, n=8):
    """Niveaux des partiels 1..n (dB, relatifs au fondamental)."""
    x = np.asarray(x, float) - np.mean(x)
    A = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 18))
    fr = np.fft.rfftfreq(1 << 18, 1.0 / sr)

    def pic(fc, tol):
        m = (fr > fc * (1 - tol)) & (fr < fc * (1 + tol))
        return fr[m][np.argmax(A[m])], A[m].max()

    f1, a1 = pic(f_nom, 0.03)
    return [20 * np.log10(pic(k * f1, 0.02)[1] / a1) for k in range(1, n + 1)]


def _params_accordeon(f0=220.0, sortie=None, loi=None):
    """`loi=None` : le défaut de `hybrid.accordeon` (traversante) ; 'ecretee'
    pour fixer l'ancienne loi, quand un test en dépend."""
    # R = 2e8 fixe : NIVEAU est un débit (m³/s) calculé pour l'ancienne source
    kw = {'source_impedance': 2.0e8}
    if loi is not None:
        kw['loi'] = loi
    return emb.params_from_voice(hybrid.accordeon(f0_hz=f0, **kw), samplerate=SR,
                                 name='accordeon', sortie=sortie)


@pytest.fixture(scope='module')
def la220():
    """Le la 220 en moteur Python de référence : rayonnée et pression."""
    out = {}
    for nom in (emb.SORTIE_RAYONNEE, emb.SORTIE_PRESSION):
        x, _ = emb.RealtimeVoice(_params_accordeon(sortie=nom)).render(
            int(0.8 * SR), NIVEAU)
        out[nom] = x[int(0.3 * SR):]
    return out


# -- la sortie par défaut -----------------------------------------------------

def test_l_anche_libre_sort_le_rayonnement_par_defaut():
    assert _params_accordeon().sortie_effective == emb.SORTIE_RAYONNEE
    assert (_params_accordeon(sortie=emb.SORTIE_PRESSION).sortie_effective
            == emb.SORTIE_PRESSION)


def test_les_autres_familles_gardent_leur_sortie():
    """La pression de la perce reste celle d'un tuyau, la vitesse celle d'une corde."""
    for nom in ('clarinette', 'violon'):
        p = emb.params_from_voice(hybrid.build(nom))
        assert p.sortie_effective == emb.SORTIE_PRESSION
    p = emb.params_from_voice(hybrid.build('clarinette'),
                              sortie=emb.SORTIE_RAYONNEE)
    assert p.sortie_effective == emb.SORTIE_RAYONNEE      # demandée : possible


def test_la_table_c_exportee_dit_la_sortie():
    ray = emb.to_c_params(_params_accordeon())
    pre = emb.to_c_params(_params_accordeon(sortie=emb.SORTIE_PRESSION))
    assert '.out_mode = 0,' in ray and '.out_mode = 1,' in pre
    assert '.fs_out = 48000.0f,' in ray


# -- le spectre -----------------------------------------------------------------

def test_le_partiel_8_du_la_220_est_celui_de_hybrid_radiated(la220):
    """La référence : `VoiceResult.radiated` du modèle continu (RK4)."""
    res = hybrid.accordeon(f0_hz=220.0, source_impedance=2.0e8).simulate(
        dur=0.5, fs=24000.0, level=NIVEAU, oversample=4, settle=0.3)
    ref = partiels(res.radiated, 220.0, 24000.0)
    moteur = partiels(la220[emb.SORTIE_RAYONNEE], 220.0, SR)
    assert abs(moteur[7] - ref[7]) < 3.0             # mesuré : 0,3 dB
    assert moteur[7] > -12.0                          # avant : -43,5 dB
    for k in range(1, 8):
        assert abs(moteur[k] - ref[k]) < 3.0


def test_l_ancienne_sortie_reste_accessible_sous_son_nom(la220):
    pre = la220[emb.SORTIE_PRESSION]
    assert partiels(pre, 220.0, SR)[7] < -35.0        # la chambre coupe les aigus
    assert np.mean(pre) > np.std(pre)                 # et porte une pression continue


# -- le continu -----------------------------------------------------------------

def test_la_sortie_rayonnee_n_a_pas_de_composante_continue(la220):
    ray = la220[emb.SORTIE_RAYONNEE]
    assert abs(np.mean(ray)) < 0.01 * np.std(ray)


def test_la_decimation_passe_le_debit_au_pas_interne_dans_le_filtre_elliptique():
    """La sortie à 48 kHz est exactement la dérivée du débit net au pas interne
    (192 kHz), passée dans le filtre anti-repliement, dont on garde un pas sur
    quatre. Le pas interne est obtenu sans décimation (suréchantillonnage 1 à
    192 kHz : mêmes biquads, mêmes pas) et filtré par `scipy.signal.sosfilt`."""
    from dataclasses import replace
    from scipy import signal
    p = _params_accordeon()
    assert p.oversample == 4
    sos = emb.antirepliement_sos(4, SR)
    assert len(sos) >= 4
    a, _ = emb.RealtimeVoice(p).render(2000, NIVEAU)
    p1 = replace(p, samplerate=4 * SR, oversample=1)
    interne, _ = emb.RealtimeVoice(p1).render(4 * 2000, NIVEAU)
    ref = signal.sosfilt(np.array([[*c[:3], 1.0, *c[3:]] for c in sos]),
                         interne)[3::4]
    assert np.max(np.abs(a - ref)) < 1e-9 * np.max(np.abs(ref))


def test_le_premier_pas_apres_reset_est_nul():
    """Pas de débit net précédent : la dérivée du premier pas interne vaut 0,
    pas `drive × fs` (suréchantillonnage 1 : aucun filtre, la sortie est ce pas)."""
    from dataclasses import replace
    rv = emb.RealtimeVoice(replace(_params_accordeon(), oversample=1))
    a, _ = rv.render(4, NIVEAU)
    assert a[0] == 0.0 and np.any(a[1:] != 0.0)


# -- le noyau C : identique à la référence Python ------------------------------

@sans_compilateur
@pytest.mark.parametrize("sortie", [emb.SORTIE_RAYONNEE, emb.SORTIE_PRESSION])
def test_le_noyau_c_suit_la_reference_python(sortie):
    # L'ancienne loi, explicitement : la tolérance de 5e-3 a été fixée sur elle.
    # En loi traversante, l'écart float32 / float64 de la montée d'amplitude
    # est un peu plus grand (1e-2 mesuré) : voir test_loi_traversante.py, qui
    # compare les deux chemins pour la nouvelle loi.
    p = _params_accordeon(sortie=sortie, loi='ecretee')
    cp, garde = live._to_c_params(p)
    v = live.Voice()
    v.note_on(cp, 57, NIVEAU)
    bloc = np.zeros(256, np.float32)
    morceaux = []
    for _ in range(2):
        v.render(bloc, glide=1.0)
        morceaux.append(bloc.copy())
    c = np.concatenate(morceaux).astype(float)
    py, _ = emb.RealtimeVoice(p).render(512, NIVEAU)
    # L'écart est l'arrondi float32 du biquad de l'anche (près de z = 1, il
    # amplifie l'arrondi) : avec ce seul biquad calculé en float32, la référence
    # retombe à 6e-5. Il valait 4,0e-3 avec les coefficients de l'anche en
    # float32, 5,6e-3 avec ses écarts a1 + 2 et 1 - a2 (`hv_reed`) : un autre
    # tirage de l'arrondi, pas une dérive de la physique. D'où 1e-2.
    assert np.max(np.abs(c - py)) < 1e-2 * np.std(py)    # float32 contre float64


# -- le synthé : somme des voix, limiteur, soufflet ----------------------------

@pytest.fixture(scope='module')
def accordeon():
    return live.build_instrument('accordeon', lo=57, hi=69, tune=False)


def _niveau_db(x):
    x = np.asarray(x, float)
    return 20 * np.log10(max(np.sqrt(np.mean((x - x.mean()) ** 2)), 1e-12))


def _jouer(inst, notes, expression, duree=1.5, bloc=256, gain=0.5):
    s = live.Synth(inst, polyphony=6, soufflet=Soufflet(), gain=gain)
    s.expression = expression
    for _ in range(int(2.0 * SR / bloc)):
        s.render(bloc)                 # soufflet établi avant la touche
    for n in notes:
        s.note_on(n, 100)
    x = np.concatenate([s.render(bloc) for _ in range(int(duree * SR / bloc))])
    return s, x[int(0.5 * SR):]


@sans_compilateur
def test_un_accord_de_quatre_notes_n_ecrase_pas_une_note(accordeon):
    _, une = _jouer(accordeon, (57,), 0.7)
    _, accord = _jouer(accordeon, (57, 61, 64, 69), 0.7)
    assert _niveau_db(accord) >= _niveau_db(une)          # avant : 67 dB plus bas
    assert np.max(np.abs(accord)) < 1.0


@pytest.fixture(scope='module')
def accordeon_ecretee():
    return live.build_instrument('accordeon', lo=57, hi=69, tune=False,
                                 loi='ecretee')


@sans_compilateur
def test_la_somme_des_voix_n_a_pas_de_composante_continue(accordeon_ecretee):
    # Ancienne loi, explicitement : à 0,7 la loi traversante, plus forte, fait
    # travailler le limiteur (crête 1,0), dont l'écrêtage asymétrique crée un
    # continu (3,7 % de l'écart type) qui n'est pas celui de la voix. Même
    # propriété pour la loi traversante, sous le limiteur : test suivant.
    _, accord = _jouer(accordeon_ecretee, (57, 61, 64, 69), 0.7)
    assert abs(np.mean(accord)) < 0.01 * np.std(accord)   # avant : +2,2 pour 0,7


@sans_compilateur
def test_la_somme_des_voix_n_a_pas_de_composante_continue_en_loi_traversante(accordeon):
    # gain réduit : à 0,5 la somme de quatre voix traversantes dépasse le seuil du limiteur
    _, accord = _jouer(accordeon, (57, 61, 64, 69), 0.7, gain=0.1)
    assert np.max(np.abs(accord)) < 0.7                   # le limiteur n'agit pas
    assert abs(np.mean(accord)) < 0.01 * np.std(accord)


@sans_compilateur
def test_une_note_tenue_suit_l_expression(accordeon):
    """Soufflet branché : le CC 11 change une note déjà sonnante."""
    s = live.Synth(accordeon, polyphony=2, soufflet=Soufflet())
    s.expression = 0.3
    for _ in range(int(2.0 * SR / 256)):
        s.render(256)
    s.note_on(57, 100)
    bas = np.concatenate([s.render(256) for _ in range(int(1.5 * SR / 256))])
    s.expression = 0.9
    haut = np.concatenate([s.render(256) for _ in range(int(1.5 * SR / 256))])
    assert _niveau_db(haut[int(0.5 * SR):]) > _niveau_db(bas[int(0.5 * SR):]) + 3.0


def test_le_soufflet_est_branche_par_defaut_pour_l_anche_libre():
    libre = live.Instrument(name='accordeon', control_unit='m³/s')
    vent = live.Instrument(name='clarinette', control_unit='Pa')
    assert live.Synth(libre).soufflet is not None
    assert live.Synth(vent).soufflet is None              # pression de bouche
    assert live.Synth(libre, soufflet=None).soufflet is None


@sans_compilateur
def test_la_sortie_par_canal_somme_a_la_sortie_commune(accordeon):
    def synth():
        s = live.Synth(accordeon, polyphony=4, soufflet=Soufflet())
        s.expression = 0.7
        for n, c in ((57, 1), (64, 2), (69, 0)):
            s.note_on(n, 100, canal=c)
        return s
    a, b = synth(), synth()
    for _ in range(40):
        somme = a.render(256)
        canaux = b.render_canaux(256)
        assert np.allclose(sum(canaux.values()), somme, atol=1e-6)
    assert set(canaux) == {0, 1, 2}


# -- le lecteur de fichier MIDI -------------------------------------------------

@sans_compilateur
def test_rendre_midi_notes_et_cc_a_l_echantillon_pres(accordeon, tmp_path):
    mido = pytest.importorskip('mido')
    mid = mido.MidiFile(ticks_per_beat=1000)         # 60 bpm : 1000 ticks = 1 s
    for canal, note in ((0, 69), (1, 57), (2, 64)):
        t = mido.MidiTrack()
        if canal == 0:
            t.append(mido.MetaMessage('set_tempo', tempo=1000000, time=0))
            t.append(mido.Message('control_change', channel=0, control=11,
                                  value=100, time=0))
        t.append(mido.Message('note_on', channel=canal, note=note, velocity=90,
                              time=1000 + 100 * canal))
        t.append(mido.Message('note_off', channel=canal, note=note, velocity=0,
                              time=1000))
        mid.tracks.append(t)
    chemin = tmp_path / 'essai.mid'
    mid.save(str(chemin))

    sortie = live.rendre_midi(chemin, accordeon, polyphonie=4, fin_s=3.0)
    assert sorted(sortie) == [0, 1, 2]
    assert all(len(x) == int(3.0 * SR) for x in sortie.values())
    assert all(np.all(np.isfinite(x)) for x in sortie.values())
    for canal, x in sortie.items():
        debut = int((1.0 + 0.1 * canal) * SR)
        assert np.max(np.abs(x[:debut])) == 0.0, canal         # rien avant la note
        assert np.max(np.abs(x[debut:debut + 4800])) > 0.0, canal

    # fenêtre : seules les secondes demandées, un seul tableau si pas par canal
    fen = live.rendre_midi(chemin, accordeon, debut_s=1.0, fin_s=2.0,
                           polyphonie=4, par_canal=False)
    assert fen.shape == (int(1.0 * SR),)
    assert np.allclose(fen, sum(x[int(1.0 * SR):int(2.0 * SR)]
                                for x in sortie.values()), atol=1e-6)


@sans_compilateur
def test_l_accordage_se_mesure_sur_la_pression_pas_sur_le_rayonnement():
    """L'autocorrélation d'un rayonnement (impulsions de signes alternés) se
    trompait d'octave : sur le rayonnement, la, do# et fa# sortaient à +1200
    ou +1900 cents. L'oscillateur, lui, joue la même note quelle que soit la
    sortie : l'accordage la mesure sur la pression de la chambre."""
    inst = live.build_instrument('accordeon', lo=62, hi=66)         # accordé
    assert inst.params_for(64).out_mode == 0                        # sortie : rayonnée
    for note in (62, 63, 64, 65, 66):
        v = live.Voice()
        v.note_on(inst.params_for(note), note, NIVEAU)
        bloc = np.zeros(256, np.float32)
        xs = []
        for _ in range(int(2.0 * SR / 256)):
            v.render(bloc, glide=1.0)
            xs.append(bloc.copy())
        net = np.cumsum(np.concatenate(xs).astype(float)[int(1.0 * SR):])
        f = hybrid.playing_frequency(net, SR)            # intégrale = débit net, lisse
        ecart = 1200 * np.log2(f / live.midi_to_hz(note))
        assert abs(ecart) < 40.0, (note, ecart)


# -- le CC du fichier : un geste, ou une pression déjà mesurée ----------------

def _retard_s(ref, x, pas_s, max_s=0.2):
    """Retard de `x` sur `ref` (s), au maximum de la corrélation croisée."""
    ref = np.asarray(ref, float) - np.mean(ref)
    x = np.asarray(x, float) - np.mean(x)
    n = int(max_s / pas_s)
    cc = [np.dot(ref[:len(ref) - k], x[k:]) for k in range(n)]
    return int(np.argmax(cc)) * pas_s


def _pression_suivie(tmp_path, monkeypatch, cc):
    """Pression commune du synthé pendant un CC en créneaux lissés, relevée
    à chaque bloc ; sans voix, donc sans compilateur."""
    mido = pytest.importorskip('mido')
    pas = 0.01
    t = np.arange(0.0, 6.0, pas)
    # créneaux (période 1,2 s) lissés sur 0,3 s : proche d'un niveau mesuré
    carre = (np.sin(2 * np.pi * t / 1.2) > 0).astype(float)
    lisse = np.convolve(carre, np.ones(30) / 30, mode='same')
    valeurs = np.round(127 * (0.3 + 0.6 * lisse)).astype(int)
    mid = mido.MidiFile(ticks_per_beat=1000)
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage('set_tempo', tempo=1000000, time=0))
    tr.append(mido.Message('note_on', channel=0, note=57, velocity=90, time=0))
    for v in valeurs:
        tr.append(mido.Message('control_change', channel=0, control=11,
                               value=int(v), time=10))
    mid.tracks.append(tr)
    chemin = tmp_path / 'creneaux.mid'
    mid.save(str(chemin))

    releves = []                      # (fin du bloc en s, pression)
    fait = [0]

    class SynthSansVoix(live.Synth):
        def note_on(self, *a, **k):
            pass

        def _rendre_voix(self, n):
            self._avancer_soufflet(n)
            fait[0] += n
            releves.append((fait[0] / SR, self.pression))
            return []

    monkeypatch.setattr(live, 'Synth', SynthSansVoix)
    inst = live.Instrument(name='accordeon', lo=57, hi=57, samplerate=SR,
                           control_unit='m³/s')
    live.rendre_midi(chemin, inst, fin_s=6.0, bloc=64, cc=cc)
    attendu = pression_demandee(valeurs / 127.0)     # à chaque message (10 ms)
    # pression relevée sur la même grille de 10 ms (dernier bloc avant la date)
    ts = np.array([r[0] for r in releves])
    ps = np.array([r[1] for r in releves])
    idx = np.searchsorted(ts, t + pas, side='right') - 1
    return _retard_s(attendu, ps[np.clip(idx, 0, None)], pas)


def test_cc_pression_suit_la_demande_sans_retard(tmp_path, monkeypatch):
    assert _pression_suivie(tmp_path, monkeypatch, 'pression') < 0.005


def test_cc_geste_garde_le_retard_du_soufflet(tmp_path, monkeypatch):
    assert _pression_suivie(tmp_path, monkeypatch, 'geste') > 0.020


def test_cc_inconnu_refuse(tmp_path):
    mido = pytest.importorskip('mido')
    mid = mido.MidiFile(ticks_per_beat=1000)
    mid.tracks.append(mido.MidiTrack())
    chemin = tmp_path / 'vide.mid'
    mid.save(str(chemin))
    inst = live.Instrument(name='accordeon', lo=57, hi=57, samplerate=SR,
                           control_unit='m³/s')
    with pytest.raises(ValueError):
        live.rendre_midi(chemin, inst, fin_s=0.1, cc='autre')
