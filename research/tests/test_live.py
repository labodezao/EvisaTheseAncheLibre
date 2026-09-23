"""Moteur jouable : le C du STM32, compilé ici et piloté par ctypes.

Ces tests ne demandent ni carte son ni clavier MIDI — seulement un
compilateur C. C'est voulu : le moteur doit être vérifiable sans matériel,
sinon on ne le vérifie jamais.
"""
import numpy as np
import pytest

from banc_recherche import live, hybrid

pytestmark = pytest.mark.skipif(
    __import__('shutil').which('cc') is None and
    __import__('shutil').which('gcc') is None,
    reason="pas de compilateur C")


@pytest.fixture(scope='module')
def clarinette():
    return live.build_instrument('clarinette', lo=55, hi=72)


def test_le_moteur_c_se_compile_et_se_charge():
    lib = live.engine_library()
    assert hasattr(lib, 'hv_render') and hasattr(lib, 'hv_reset')


def test_midi_vers_hertz():
    assert live.midi_to_hz(69) == pytest.approx(440.0)
    assert live.midi_to_hz(57) == pytest.approx(220.0)       # une octave sous
    assert live.midi_to_hz(60) == pytest.approx(261.626, abs=0.01)
    assert live.midi_to_hz(69, a4_hz=415.0) == pytest.approx(415.0)


def test_une_perce_par_demi_ton(clarinette):
    """C'est un modèle physique, pas un échantillon transposé.

    Chaque note a sa propre géométrie, donc ses propres pertes et sa propre
    coupure de réseau — et ça s'entend d'un bout à l'autre de la tessiture.
    """
    assert len(clarinette) == 72 - 55 + 1
    a = clarinette.params_for(60)
    b = clarinette.params_for(67)
    assert a.modes[0].a1 != b.modes[0].a1      # coefficients réellement différents


def test_hors_tessiture_on_prend_la_note_la_plus_proche(clarinette):
    assert clarinette.params_for(20) is clarinette.params_for(clarinette.lo)
    assert clarinette.params_for(127) is clarinette.params_for(clarinette.hi)


def test_l_instrument_joue_juste(clarinette):
    """Le contrôle qui compte pour un clavier : la note demandée sort."""
    s = live.Synth(clarinette, polyphony=1)
    s.note_on(60, 100)
    a = s.render(24000).astype('float64')
    f = hybrid.playing_frequency(a[9000:], clarinette.samplerate)
    ecart = 1200 * np.log2(f / live.midi_to_hz(60))
    assert abs(ecart) < 25.0                   # moins d'un quart de ton


def test_l_echelle_de_sortie_est_mesuree_pas_devinee(clarinette):
    """Une perce sort des milliers de pascals, une corde ~1 m/s.

    À gain fixe, l'une saturerait et l'autre serait inaudible. Le facteur est
    donc mesuré sur une vraie note — et il faut le mesurer **avant**
    l'écrêtage, sinon on lit 1,0 pour tout le monde.
    """
    assert 0 < clarinette.output_scale < 0.1   # un vent : gros nombres bruts
    s = live.Synth(clarinette, polyphony=1, gain=0.4)
    s.note_on(64, 100)
    a = s.render(24000)
    crete = float(np.max(np.abs(a[9000:])))
    assert 0.05 < crete < 1.0                  # audible, et sans saturer


def test_une_corde_a_une_echelle_toute_autre():
    violon = live.build_instrument('violon', lo=60, hi=64)
    assert violon.output_scale > 0.05          # m/s : nombres de l'ordre de 1


def test_note_off_laisse_le_son_s_eteindre(clarinette):
    """Un relâché ne coupe pas : il retire la pression.

    L'oscillation s'éteint d'elle-même en repassant sous son seuil. C'est
    l'extinction physique, et c'est précisément ce qu'un sampler ne fait pas.
    """
    s = live.Synth(clarinette, polyphony=1)
    s.note_on(60, 100)
    s.render(12000)
    s.note_off(60)
    juste_apres = float(np.max(np.abs(s.render(256))))
    assert juste_apres > 1e-4                  # ça sonne encore
    for _ in range(200):
        s.render(256)
    assert s.active_voices == 0                 # mais ça finit par s'éteindre


def test_la_polyphonie_additionne_les_voix(clarinette):
    s = live.Synth(clarinette, polyphony=3)
    for n in (60, 64, 67):
        s.note_on(n, 100)
    assert s.active_voices == 3
    a = s.render(8000)
    assert np.all(np.isfinite(a))
    assert np.max(np.abs(a)) > 0


def test_le_vol_de_voix_ne_laisse_pas_tomber_la_derniere(clarinette):
    s = live.Synth(clarinette, polyphony=2)
    s.note_on(60, 100); s.render(512)
    s.note_on(64, 100); s.render(512)
    s.note_on(67, 100)                          # une de trop
    assert s.active_voices == 2
    assert 67 in [v.note for v in s.voices if v.active]


def test_la_nuance_ne_descend_jamais_sous_le_seuil(clarinette):
    """Sous son seuil, un modèle physique ne joue pas *doucement* : il se tait.

    Une vélocité faible qui ne produirait aucun son passerait pour un bug.
    On borne donc la nuance dans la plage où l'instrument parle.
    """
    s = live.Synth(clarinette, polyphony=1)
    assert s._nuance(1) >= 0.45
    assert s._nuance(127) > s._nuance(64) > s._nuance(1)
    s.expression = 0.0
    assert s._nuance(127) >= 0.45


def test_la_sortie_reste_bornee(clarinette):
    s = live.Synth(clarinette, polyphony=4, gain=1.0)
    for n in (55, 60, 64, 67):
        s.note_on(n, 127)
    for _ in range(20):
        a = s.render(1024)
        assert np.all(np.isfinite(a))
        assert np.max(np.abs(a)) <= 1.0         # jamais hors de la plage audio


def test_le_moteur_tient_le_temps_reel(clarinette):
    """Le seul chiffre qui dit si c'est jouable. En dessous de 1, ça craque."""
    r = live.realtime_factor(clarinette, n_voices=4, block=256, seconds=0.2)
    assert r > 3.0


def test_l_anche_libre_parle_sur_toute_la_tessiture():
    """Une languette de la grave ne sonne pas dans l'aigu — elle se tait.

    Avant que les cotes ne suivent la note, l'accordéon devenait muet
    au-dessus de 185 Hz : la languette se couchait dans le courant d'air sans
    jamais osciller, et la « crête » qu'on lisait n'était qu'une pression
    continue. D'où le test sur la partie **alternative** du signal.
    """
    inst = live.build_instrument('accordeon', lo=48, hi=84)
    for note in (48, 60, 72, 84):
        x = np.zeros(int(0.8 * inst.samplerate), dtype='float32')
        v = live.Voice()
        v.note_on(inst.params_for(note), note, inst.level_default)
        for i in range(0, x.size - 512, 512):
            v.render(x[i:i + 512])
        alternatif = x[x.size // 2:].astype('float64')
        alternatif -= alternatif.mean()
        assert np.max(np.abs(alternatif)) > 1e-3, f"muette sur {note}"


def test_l_accordage_rattrape_ce_que_la_geometrie_donne_de_travers():
    """Un modèle physique ne joue pas la fréquence qu'on lui dessine.

    Correction de pavillon, tirage de l'anche, raideur de la chambre : selon
    la note, l'écart va de quelques cents à plus d'un demi-ton. On mesure et
    on retouche la géométrie, comme un facteur — pas la sortie.
    """
    brut = live.build_instrument('accordeon', lo=79, hi=79, tune=False)
    accorde = live.build_instrument('accordeon', lo=79, hi=79, tune=True)

    def ecart(inst):
        f = live._frequence_jouee(inst.params_for(79), inst.level_default,
                                  inst.samplerate, dur=1.0)
        return abs(1200 * np.log2(f / live.midi_to_hz(79)))

    assert ecart(accorde) < 5.0
    assert ecart(accorde) < ecart(brut)


def test_le_limiteur_ne_touche_pas_ce_qui_passe(clarinette):
    """Un écrêtage dur ferait entendre le normalisateur, pas l'instrument.

    Sous le seuil, la courbe doit être l'identité au bit près ; au-dessus,
    elle comprime sans jamais sortir de la plage — et sans coude audible, la
    tangente valant 1 des deux côtés.
    """
    x = np.linspace(-3.0, 3.0, 20001, dtype='float32')
    y = live._limiteur(x.copy())
    sous = np.abs(x) <= 0.7
    assert np.allclose(y[sous], x[sous])
    assert np.max(np.abs(y)) < 1.0
    assert np.all(np.diff(y) >= 0)                  # monotone : pas de repli


def test_rendre_une_phrase_sans_carte_son(clarinette):
    """Tout doit être essayable sur un PC nu — pas de carte, pas de MIDI."""
    s = live.Synth(clarinette, polyphony=4)
    x = live.rendre_phrase(s, notes=(60, 64, 67), duree=0.3, queue=0.6)
    assert x.dtype == np.float32
    assert x.size == pytest.approx(1.5 * clarinette.samplerate, rel=0.05)
    assert 0.05 < np.max(np.abs(x)) <= 1.0
    # la queue est une extinction, pas une coupure : ça décroît sans s'annuler
    fin = x[-int(0.1 * clarinette.samplerate):]
    assert np.max(np.abs(fin)) < np.max(np.abs(x))


def test_le_wav_ecrit_est_relisible(tmp_path, clarinette):
    import wave
    s = live.Synth(clarinette, polyphony=2)
    x = live.rendre_phrase(s, notes=(62,), duree=0.3, queue=0.4)
    f = tmp_path / 'essai.wav'
    live._ecrire_wav(f, x, clarinette.samplerate)
    with wave.open(str(f)) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        assert w.getframerate() == int(clarinette.samplerate)
        assert w.getnframes() == x.size


def test_les_dispositions_de_clavier_couvrent_une_octave():
    """Une disposition qui saute un demi-ton se remarque en jouant, pas en
    lisant le code."""
    for nom, table in live.DISPOSITIONS.items():
        demi_tons = sorted(table.values())
        assert demi_tons[:13] == list(range(13)), nom
        assert len(set(table)) == len(table), nom        # pas de touche double


def test_la_ligne_de_commande_rend_un_wav(tmp_path):
    f = tmp_path / 'cli.wav'
    code = live.main(['clarinette', '--wav', str(f), '--grave', '60',
                      '--aigu', '64', '--polyphonie', '2'])
    assert code == 0 and f.stat().st_size > 1000


def test_la_ligne_de_commande_refuse_un_instrument_inconnu():
    assert live.main(['zorglub']) == 2


# --- portabilité : ce qui change d'un système à l'autre ----------------------
# Ces tests tournent sur n'importe quelle machine en faisant croire à `live`
# qu'il est ailleurs. C'est le seul moyen honnête de vérifier le chemin
# Windows depuis un Linux — et ça vaut mieux que de le découvrir chez
# quelqu'un qui n'a que Windows.

@pytest.mark.parametrize('plateforme,attendu', [
    ('win32', 'hybridvoice.dll'),
    ('darwin', 'libhybridvoice.dylib'),
    ('linux', 'libhybridvoice.so'),
])
def test_le_nom_de_la_bibliotheque_suit_le_systeme(monkeypatch, plateforme,
                                                   attendu):
    monkeypatch.setattr(live.sys, 'platform', plateforme)
    assert live._nom_bibliotheque() == attendu


def test_sous_windows_on_cherche_gcc_avant_msvc(monkeypatch):
    """`gcc -shared` exporte tout seul ; `cl /LD` n'exporte rien sans liste."""
    monkeypatch.setattr(live.sys, 'platform', 'win32')
    monkeypatch.delenv('CC', raising=False)
    monkeypatch.setattr(live.shutil, 'which',
                        lambda n: f"C:\\\\bin\\\\{n}.exe" if n in ('gcc', 'cl') else None)
    assert live._compilateur()[1] == 'unix'

    monkeypatch.setattr(live.shutil, 'which',
                        lambda n: "C:\\\\bin\\\\cl.exe" if n == 'cl' else None)
    cc, famille = live._compilateur()
    assert famille == 'msvc'

    monkeypatch.setattr(live.shutil, 'which', lambda n: None)
    assert live._compilateur() == (None, None)


def test_msvc_recoit_la_liste_des_symboles_a_exporter(tmp_path, monkeypatch):
    """Sans `.def`, MSVC produit une DLL vide : `hv_render` serait introuvable."""
    monkeypatch.setattr(live.sys, 'platform', 'win32')
    cmd = live._commande_compilation('cl', 'msvc', tmp_path,
                                     tmp_path / 'hybrid_voice.c',
                                     tmp_path / 'hybridvoice.dll')
    assert '/LD' in cmd
    deff = tmp_path / 'hybridvoice.def'
    assert deff.exists()
    lignes = deff.read_text().split()
    for symbole in live.HV_EXPORTS:
        assert symbole in lignes


def test_sous_windows_gcc_ne_recoit_ni_fPIC_ni_lm(tmp_path, monkeypatch):
    """Deux options qui n'ont pas de sens là-bas, et que gcc signale."""
    monkeypatch.setattr(live.sys, 'platform', 'win32')
    cmd = live._commande_compilation('gcc', 'unix', tmp_path,
                                     tmp_path / 'hybrid_voice.c',
                                     tmp_path / 'hybridvoice.dll')
    assert '-fPIC' not in cmd and '-lm' not in cmd and '-shared' in cmd

    monkeypatch.setattr(live.sys, 'platform', 'linux')
    cmd = live._commande_compilation('cc', 'unix', tmp_path,
                                     tmp_path / 'hybrid_voice.c',
                                     tmp_path / 'libhybridvoice.so')
    assert '-fPIC' in cmd and '-lm' in cmd


def test_sans_compilateur_le_message_dit_quoi_installer(monkeypatch):
    for plateforme, mot in (('win32', 'MSYS2'), ('darwin', 'xcode-select'),
                            ('linux', 'build-essential')):
        monkeypatch.setattr(live.sys, 'platform', plateforme)
        assert mot in live._aide_compilateur()


def test_mingw_lie_libgcc_statiquement(tmp_path, monkeypatch):
    """Sinon la DLL se compile très bien et refuse de se charger : MinGW n'est
    pas dans le PATH d'un Python installé normalement."""
    monkeypatch.setattr(live.sys, 'platform', 'win32')
    cmd = live._commande_compilation('gcc', 'unix', tmp_path,
                                     tmp_path / 'hybrid_voice.c',
                                     tmp_path / 'hybridvoice.dll')
    assert '-static-libgcc' in cmd
    # clang ne l'accepte pas partout : on ne le lui impose pas
    cmd = live._commande_compilation('clang', 'unix', tmp_path,
                                     tmp_path / 'hybrid_voice.c',
                                     tmp_path / 'hybridvoice.dll')
    assert '-static-libgcc' not in cmd


# --- une vraie perce, jouée par ses doigtés ---------------------------------

def _perce_a_six_trous():
    """Perce fabriquée sur place : la banque d'Ewen n'est pas versionnée."""
    from banc_recherche import tutt
    n = 7
    dat = tutt.BoreDat(
        n_sections=n, closed_bottom=False,
        d0=np.full(n, 0.015), dl=np.full(n, 0.015),
        lengths=np.full(n, 0.5 / n),
        hole_d0=np.array([0.008] * 6 + [0.0]),
        hole_dl=np.array([0.008] * 6 + [0.0]),
        hole_len=np.array([0.004] * 6 + [0.0]),
        ofilib=np.ones(n), temperature_c=(20.0, 20.0), title='essai')
    dat.fingerings = [(f'd{k}', [0] * k + [1] * (7 - k)) for k in range(7)]
    return dat


def test_une_perce_reelle_donne_un_instrument_jouable():
    inst = live.build_instrument_from_bore(_perce_a_six_trous(),
                                           famille='clarinette')
    assert len(inst.fingerings) == 7
    notes = [n for _, _, _, n in inst.fingerings]
    assert notes == sorted(notes) and len(set(notes)) == 7
    s = live.Synth(inst, polyphony=1)
    s.note_on(notes[0], 100)
    a = s.render(24000).astype('float64')
    f = hybrid.playing_frequency(a[9000:], inst.samplerate)
    attendu = inst.fingerings[0][2]
    assert abs(1200 * np.log2(f / attendu)) < 40.0


def test_la_justesse_d_une_vraie_perce_n_est_pas_corrigee():
    """`build_instrument` accorde chaque note ; ici surtout pas.

    L'écart entre ce que la perce donne et ce qu'elle devrait donner **est**
    le résultat qu'on vient chercher — le corriger effacerait la mesure.
    """
    inst = live.build_instrument_from_bore(_perce_a_six_trous(),
                                           famille='clarinette')
    ecarts = [1200 * np.log2(f / live.midi_to_hz(n))
              for _, _, f, n in inst.fingerings]
    assert max(abs(e) for e in ecarts) > 10.0     # la perce d'essai est fausse
    assert all(abs(e) < 100.0 for e in ecarts)    # mais rangée sur la bonne touche


def test_une_touche_sans_doigte_rend_la_plus_proche():
    """Une perce réelle ne remplit pas le clavier : jouer entre deux doigtés
    doit donner quelque chose, pas planter."""
    inst = live.build_instrument_from_bore(_perce_a_six_trous(),
                                           famille='clarinette')
    notes = sorted(n for _, _, _, n in inst.fingerings)
    trou = next(n for n in range(notes[0], notes[-1]) if n not in notes)
    assert inst.params_for(trou) is not None
