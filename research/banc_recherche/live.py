"""Jouer le modèle physique en direct, au clavier MIDI.

Tout ce qui précède calcule juste mais **ne joue pas** : `hybrid` intègre en
RK4 et `embedded.RealtimeVoice` boucle en Python. Les deux mettent plusieurs
secondes à produire une seconde de son. Injouable.

La solution était déjà écrite : `embedded` génère un moteur C temps réel pour
le STM32. On le compile ici en bibliothèque partagée et on l'appelle par
`ctypes`. **Le même code que sur la carte**, à vitesse native — et donc, en
prime, une vérification permanente que ce qui est destiné au STM32 fonctionne
vraiment.

Ce que ça donne
---------------
- une voix = une structure C, rendue par blocs de 64 à 256 échantillons ;
- la polyphonie est une somme de voix, faite en numpy ;
- la **nuance** (pression de souffle, force d'archet) est réévaluée à chaque
  bloc, donc toutes les 1 à 5 ms : assez fin pour un contrôleur à vent ou une
  molette de modulation ;
- l'attaque n'est pas une enveloppe plaquée : c'est le temps que met
  l'oscillation à s'installer. C'est le point de tout l'exercice.

Ce qu'il faut sur la machine
----------------------------
- un compilateur C (`cc`), présent partout ;
- `sounddevice` pour la sortie audio — déjà dans `requirements.txt` ;
- `mido` + `python-rtmidi` pour l'entrée MIDI — `pip install -e ".[live]"`.

Les deux derniers sont importés **paresseusement** : le moteur et les tests
tournent sans eux.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import pathlib
import subprocess
import tempfile
from dataclasses import dataclass, field

import numpy as np

from . import hybrid
from .embedded import (RealtimeParams, params_from_voice, to_c_engine,
                       biquad_bandpass, biquad_lowpass, FAMILY_BOW,
                       FAMILY_SINGLE_REED, FAMILY_FREE_REED)
from .hybrid import RHO

HV_MAX_MODES = 24


# =============================================================================
# Le moteur C, compilé et appelé par ctypes
# =============================================================================

class _Biquad(ctypes.Structure):
    _fields_ = [(n, ctypes.c_float) for n in ('b0', 'b1', 'b2', 'a1', 'a2')]


class _BqState(ctypes.Structure):
    _fields_ = [('z1', ctypes.c_float), ('z2', ctypes.c_float)]


class _Params(ctypes.Structure):
    _fields_ = [
        ('family', ctypes.c_int), ('n_modes', ctypes.c_int),
        ('oversample', ctypes.c_int),
        ('modes', ctypes.POINTER(_Biquad)),
        ('reed', _Biquad),
        ('rest_opening', ctypes.c_float), ('width', ctypes.c_float),
        ('vena', ctypes.c_float), ('max_open', ctypes.c_float),
        ('leak', ctypes.c_float), ('src_admit', ctypes.c_float),
        ('flow_gain', ctypes.c_float), ('visc_pa', ctypes.c_float),
        ('mu_s', ctypes.c_float), ('mu_d', ctypes.c_float),
        ('v_char', ctypes.c_float), ('bow_speed', ctypes.c_float),
        ('cavity_gain', ctypes.c_float), ('cavity_leak', ctypes.c_float),
    ]


class _State(ctypes.Structure):
    _fields_ = [('z', _BqState * HV_MAX_MODES), ('reed_z', _BqState),
                ('response', ctypes.c_float), ('cavity', ctypes.c_float),
                ('kicked', ctypes.c_int)]


_LIB = None


def engine_library(force=False):
    """Compile le moteur C en bibliothèque partagée, et la charge.

    Le binaire est mis en cache dans le dossier temporaire, clé de hachage du
    source : régénérer le moteur le recompile, sinon on le réutilise. On ne
    veut pas payer une compilation à chaque note.
    """
    global _LIB
    if _LIB is not None and not force:
        return _LIB

    src = to_c_engine()
    cle = hashlib.sha256(
        (src['hybrid_voice.h'] + src['hybrid_voice.c']).encode()).hexdigest()[:16]
    d = pathlib.Path(tempfile.gettempdir()) / f"banc_hv_{cle}"
    so = d / "libhybridvoice.so"

    if force or not so.exists():
        d.mkdir(parents=True, exist_ok=True)
        for nom, texte in src.items():
            (d / nom).write_text(texte, encoding='utf-8')
        cmd = [os.environ.get('CC', 'cc'), '-std=c99', '-O2', '-fPIC', '-shared',
               f'-DHV_MAX_MODES={HV_MAX_MODES}',
               str(d / 'hybrid_voice.c'), '-o', str(so), '-lm']
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not so.exists():
            raise RuntimeError(
                "impossible de compiler le moteur C (cc présent ?) :\n"
                + (r.stderr or r.stdout)[:800])

    lib = ctypes.CDLL(str(so))
    lib.hv_reset.argtypes = [ctypes.POINTER(_State)]
    lib.hv_render.argtypes = [ctypes.POINTER(_Params), ctypes.POINTER(_State),
                              ctypes.c_float,
                              np.ctypeslib.ndpointer(dtype=np.float32, flags='C'),
                              ctypes.c_int]
    _LIB = lib
    return lib


def _to_c_params(p: RealtimeParams):
    """Traduit un `RealtimeParams` en structure C prête à rendre.

    Renvoie `(params, tableau_de_modes)` — il faut **garder une référence** au
    tableau, sinon Python le libère et la structure pointe dans le vide. Un
    segfault silencieux au milieu d'un concert serait une mauvaise surprise.
    """
    fs = p.fs_internal
    coeffs = [biquad_bandpass(f, q, pk, fs) for f, q, pk in p.modes]
    coeffs = [c for c in coeffs if c is not None][:HV_MAX_MODES]

    modes = (_Biquad * max(len(coeffs), 1))()
    for i, c in enumerate(coeffs):
        modes[i] = _Biquad(*[float(x) for x in c])

    if p.family == FAMILY_BOW:
        reed = _Biquad(0., 0., 0., 0., 0.)
    else:
        signe = -1.0 if p.family == FAMILY_SINGLE_REED else 1.0
        c = biquad_lowpass(p.reed_freq_hz, p.reed_q,
                           signe * p.rest_opening_m / p.closing_pressure_pa, fs)
        reed = _Biquad(*[float(x) for x in (c or (0.,) * 5)])

    cp = _Params()
    cp.family = int(p.family)
    cp.n_modes = len(coeffs)
    cp.oversample = int(p.oversample)
    cp.modes = ctypes.cast(modes, ctypes.POINTER(_Biquad))
    cp.reed = reed
    cp.rest_opening = p.rest_opening_m
    cp.width = p.width_m
    cp.vena = p.vena_contracta
    cp.max_open = p.max_open_m
    cp.leak = p.leak_m
    cp.src_admit = (1.0 / p.source_impedance) if p.source_impedance > 0 else 0.0
    cp.flow_gain = p.vena_contracta * p.width_m * float(np.sqrt(2.0 / RHO))
    cp.visc_pa = float(p.visc_pa)
    cp.mu_s, cp.mu_d = p.mu_static, p.mu_dynamic
    cp.v_char, cp.bow_speed = p.v_char, p.bow_speed
    cp.cavity_gain = (1.0 / (p.compliance * fs)) if p.compliance > 0 else 0.0
    cp.cavity_leak = 0.99999 if cp.cavity_gain else 0.0
    return cp, modes


# =============================================================================
# Une note = un jeu de paramètres ; on les prépare toutes d'avance
# =============================================================================

def midi_to_hz(note, a4_hz=440.0):
    """Hauteur d'une note MIDI. 69 = la3 = 440 Hz par convention."""
    return float(a4_hz) * 2.0 ** ((float(note) - 69.0) / 12.0)


@dataclass
class Instrument:
    """Un instrument prêt à jouer : un jeu de paramètres par note MIDI.

    Les biquads sont calculés **à la construction**, pas à l'attaque : une
    allocation ou un calcul de coefficients dans le fil audio, c'est un clic
    dans le haut-parleur. Soixante notes coûtent quelques dizaines de
    kilo-octets, autant les payer une fois.
    """
    name: str = "clarinette"
    lo: int = 36
    hi: int = 96
    samplerate: float = 48000.0
    a4_hz: float = 440.0
    level_default: float = 1.0
    control_unit: str = ""
    output_scale: float = 1.0
    _params: dict = field(default_factory=dict, repr=False)
    _keep: list = field(default_factory=list, repr=False)

    def params_for(self, note):
        """Structure C de la note, ou de la plus proche disponible."""
        n = int(np.clip(int(note), self.lo, self.hi))
        return self._params[n]

    def __len__(self):
        return len(self._params)


def _frequence_jouee(cp, niveau, samplerate, dur=0.6):
    """Ce que la note joue **vraiment**, mesuré sur le moteur lui-même.

    On coupe la première moitié : le transitoire d'attaque n'est pas encore
    périodique, et le mesurer reviendrait à accorder un instrument pendant
    qu'on souffle dedans pour la première fois. On retire aussi la moyenne —
    une anche libre sort une pression de chambre fortement décalée, et
    l'autocorrélation d'un signal à composante continue pointe sur le
    décalage plutôt que sur la période.
    """
    v = Voice()
    v.note_on(cp, 60, niveau)
    n = int(dur * samplerate)
    buf = np.zeros(512, dtype=np.float32)
    x = np.empty(n, dtype=np.float32)
    for i in range(0, n, 512):
        buf[:] = 0.0
        v.render(buf)
        x[i:i + 512] = buf[:min(512, n - i)]
    y = x[n // 2:].astype('float64')
    y -= y.mean()
    if np.max(np.abs(y)) < 1e-9:
        return None                       # rien ne sort : rien à accorder
    return hybrid.playing_frequency(y, samplerate)


def _accorder(name, cible_hz, niveau, samplerate, passes=2, **kw):
    """Retouche la note jusqu'à ce qu'elle joue juste. Un accordage, vraiment.

    Un modèle physique ne joue pas la fréquence qu'on lui dessine : la perce
    a une correction de pavillon, l'anche tire la hauteur vers elle, la
    chambre raidit la languette. L'écart va de 1 à 40 cents selon la note et
    la famille — audible, et faux au clavier.

    Le facteur d'instrument fait exactement ce qu'on fait ici : il mesure ce
    que ça donne, corrige la cote, remesure. Deux passes suffisent, l'écart
    étant presque proportionnel à la correction.

    Ce n'est **pas** une correction de hauteur plaquée à la sortie : c'est la
    géométrie qu'on change. Le timbre, le transitoire et le seuil sont ceux
    de l'instrument accordé, pas ceux d'un instrument faux qu'on transpose.
    """
    design = float(cible_hz)
    voix = hybrid.INSTRUMENTS[name](f0_hz=design, **kw)
    p = params_from_voice(voix, samplerate=samplerate, name=name)
    cp, garde = _to_c_params(p)
    for _ in range(int(passes)):
        joue = _frequence_jouee(cp, niveau, samplerate)
        if not joue or not (0.5 < joue / cible_hz < 2.0):
            break                         # muette, ou dans un autre registre
        design *= cible_hz / joue
        voix = hybrid.INSTRUMENTS[name](f0_hz=design, **kw)
        p = params_from_voice(voix, samplerate=samplerate, name=name)
        cp, garde = _to_c_params(p)
    return cp, garde


def build_instrument(name="clarinette", lo=36, hi=96, samplerate=48000.0,
                     a4_hz=440.0, on_progress=None, tune=True, **kw):
    """Prépare un instrument jouable : une perce par demi-ton.

    Chaque note a **sa propre géométrie** — c'est un modèle physique, pas un
    échantillon transposé. Une clarinette grave et une clarinette aiguë n'ont
    pas les mêmes pertes ni la même coupure de réseau, et ça s'entend.

    `tune=True` accorde ensuite chaque note sur le moteur (cf. `_accorder`).
    `tune=False` laisse l'instrument tel que la géométrie le donne — c'est ce
    qu'il faut pour étudier l'écart lui-même, pas pour jouer.
    """
    voix_ref = hybrid.build(name)
    ex = voix_ref.exciter
    if isinstance(ex, hybrid.BowExciter):
        niveau = 0.25
    elif isinstance(ex, hybrid.FreeReedExciter):
        niveau = 2.9e-6
    else:
        niveau = 0.62 * ex.closing_pressure_pa

    inst = Instrument(name=name, lo=int(lo), hi=int(hi),
                      samplerate=float(samplerate), a4_hz=float(a4_hz),
                      level_default=float(niveau),
                      control_unit=getattr(ex, 'control_unit', '') or '')

    for n in range(inst.lo, inst.hi + 1):
        f0 = midi_to_hz(n, a4_hz)
        if tune:
            cp, garde = _accorder(name, f0, niveau, samplerate, **kw)
        else:
            voix = hybrid.INSTRUMENTS[name](f0_hz=f0, **kw)
            p = params_from_voice(voix, samplerate=samplerate, name=name)
            cp, garde = _to_c_params(p)
        inst._params[n] = cp
        inst._keep.append(garde)          # sans ça, le tableau est libéré
        if on_progress:
            on_progress(n - inst.lo + 1, inst.hi - inst.lo + 1)

    inst.output_scale = _mesurer_echelle(inst)
    return inst


def _limiteur(x, seuil=0.7):
    """Écrêtage doux, en place. Linéaire jusqu'à `seuil`, puis compressé.

    L'échelle de sortie est mesurée sur cinq notes ; les cinquante-six autres
    peuvent dépasser. Un `clip` dur transformerait ce dépassement en
    distorsion carrée — et on entendrait le défaut du normalisateur plutôt
    que l'instrument. La courbe ci-dessous est continue **et** de dérivée
    continue au coude (la tangente vaut 1 des deux côtés), donc rien ne
    s'entend tant qu'on reste sous le seuil.
    """
    a = np.abs(x)
    haut = a > seuil
    if np.any(haut):
        marge = 1.0 - seuil
        comprime = seuil + marge * np.tanh((a[haut] - seuil) / marge)
        x[haut] = np.sign(x[haut]) * comprime
    return x


def _crete_etablie(inst: Instrument, note, dur=2.5, fenetre=0.1):
    """Crête d'une note, une fois le régime **vraiment** installé.

    On rend la durée entière et on garde le maximum. Tentant de s'arrêter dès
    que la crête cesse de monter : ça ne marche pas. Une corde frottée monte
    par paliers — 0,87 puis 0,98, puis un faux plateau à 0,99, puis 1,5. Le
    critère d'arrêt s'y laissait prendre et sous-estimait la vielle de 25 %,
    qui saturait ensuite en jeu. Deux secondes et demie de rendu coûtent
    quelques centièmes de seconde au moteur C : autant les prendre.
    """
    v = Voice()
    v.note_on(inst.params_for(note), int(note), inst.level_default)
    bloc = max(64, int(fenetre * inst.samplerate))
    buf = np.zeros(bloc, dtype=np.float32)
    crete = 0.0
    for _ in range(max(2, int(dur / fenetre))):
        buf[:] = 0.0
        v.render(buf)
        crete = max(crete, float(np.max(np.abs(buf))))
    return crete


def _mesurer_echelle(inst: Instrument, notes=None):
    """Facteur de normalisation, **mesuré** sur l'instrument lui-même.

    La sortie du moteur est une grandeur physique — des pascals dans une
    perce, des mètres par seconde sur une corde — et ces nombres n'ont aucune
    raison de tenir entre −1 et 1. Une clarinette sort quelques milliers de
    pascals, une corde frottée un peu plus d'un mètre par seconde : à gain
    fixe, l'une saturerait et l'autre serait inaudible.

    On relève la crête sur **cinq notes** réparties dans la tessiture et on
    garde la plus forte. Une seule note ne suffit pas : l'amplitude varie
    d'une perce à l'autre — du simple au double entre le grave et l'aigu de
    la vielle — et normaliser sur la plus faible fait écrêter tout le reste.
    Mieux vaut mesurer que deviner un facteur par famille.

    Cinq notes ne couvrent pas les 61 : le reste est rattrapé par le
    limiteur de `Synth.render`, pas par une marge inventée ici.
    """
    if notes is None:
        etendue = inst.hi - inst.lo
        notes = sorted({inst.lo + int(etendue * f)
                        for f in (0.0, 0.25, 0.5, 0.75, 1.0)})
    crete = max(_crete_etablie(inst, n) for n in notes)
    return 1.0 / crete if crete > 1e-12 else 1.0


# =============================================================================
# Polyphonie
# =============================================================================

class Voice:
    """Une voix : un état C, une note, une nuance."""

    def __init__(self):
        self.state = _State()
        self.params = None
        self.note = -1
        self.level = 0.0
        self.target = 0.0
        self.active = False
        self.age = 0

    def note_on(self, params, note, level):
        engine_library().hv_reset(ctypes.byref(self.state))
        self.params, self.note = params, int(note)
        self.level = self.target = float(level)
        self.active = True
        self.age = 0

    def note_off(self):
        self.target = 0.0          # on coupe l'alimentation, pas le son

    def render(self, out, glide=0.35, silence=1e-6):
        """Rend un bloc dans `out` (float32). Renvoie `True` si la voix vit.

        `silence` est le seuil de libération, exprimé dans la **grandeur
        brute** du modèle — des pascals pour un vent, des m/s pour une corde.
        Le fixer en absolu serait une erreur : une clarinette part de quelques
        milliers de pascals, et redescendre à 10⁻⁶ Pa demande 192 dB, soit
        plus d'une seconde après l'extinction. La voix resterait occupée bien
        après qu'on ne l'entend plus. `Synth` le calcule donc à partir de
        l'échelle de sortie mesurée, pour qu'il corresponde à −100 dBFS.

        La nuance glisse vers sa cible au lieu de sauter : un échelon de
        pression dans un modèle physique s'entend comme un choc, alors qu'un
        musicien ne pousse jamais d'un coup.

        Un `note_off` ne coupe pas le son : il ramène la pression à zéro et
        **l'oscillation s'éteint d'elle-même**, en passant sous son seuil.
        C'est l'extinction physique, avec son hystérésis — la note tient un
        peu plus bas qu'elle n'a démarré.
        """
        if not self.active:
            return False
        self.level += (self.target - self.level) * float(glide)
        engine_library().hv_render(ctypes.byref(self.params),
                                   ctypes.byref(self.state),
                                   ctypes.c_float(self.level),
                                   out, len(out))
        self.age += len(out)
        if self.target == 0.0 and abs(self.level) < 1e-9:
            crete = float(np.max(np.abs(out))) if out.size else 0.0
            if crete < silence:
                self.active = False
        return self.active


class Synth:
    """Moteur polyphonique. C'est l'objet que pilote la GUI.

    Sans dépendance audio ni MIDI : il rend des blocs quand on lui en demande.
    C'est ce qui le rend testable sans carte son — et ce qui permet de
    mesurer honnêtement s'il tient le temps réel.
    """

    def __init__(self, instrument: Instrument, polyphony=6, gain=0.5):
        self.inst = instrument
        self.voices = [Voice() for _ in range(int(polyphony))]
        self.gain = float(gain)
        self.expression = 1.0           # 0..1, molette ou contrôleur à vent
        self._scratch = None
        # −100 dBFS une fois l'échelle de sortie appliquée : inaudible, et
        # atteint en quelques dizaines de millisecondes au lieu d'une seconde.
        self._silence = 1e-5 / max(instrument.output_scale, 1e-12)

    # -- clavier -------------------------------------------------------------
    def note_on(self, note, velocity=100):
        v = next((v for v in self.voices if not v.active), None)
        if v is None:                    # toutes prises : on vole la plus vieille
            v = max(self.voices, key=lambda x: x.age)
        niveau = self.inst.level_default * self._nuance(velocity)
        v.note_on(self.inst.params_for(note), note, niveau)
        return v

    def note_off(self, note):
        for v in self.voices:
            if v.active and v.note == int(note):
                v.note_off()

    def all_notes_off(self):
        for v in self.voices:
            v.note_off()

    def _nuance(self, velocity):
        """Vélocité et expression → multiple du niveau nominal.

        Borné en bas à 0,45 : sous le seuil de démarrage, un modèle physique
        ne joue pas *doucement*, il **ne joue pas du tout**. Une vélocité
        faible qui ne produit aucun son passerait pour un bug alors que c'est
        la physique — autant garder l'instrument dans sa plage utile.
        """
        v = float(np.clip(velocity, 1, 127)) / 100.0
        return float(np.clip(0.45 + 0.75 * v * self.expression, 0.45, 1.8))

    # -- audio ---------------------------------------------------------------
    def render(self, n_frames):
        """Rend `n_frames` échantillons mono, en float32, normalisés au gain."""
        n = int(n_frames)
        if self._scratch is None or self._scratch.size != n:
            self._scratch = np.zeros(n, dtype=np.float32)
        somme = np.zeros(n, dtype=np.float32)
        for v in self.voices:
            if not v.active:
                continue
            self._scratch[:] = 0.0
            v.render(self._scratch, silence=self._silence)
            somme += self._scratch
        np.multiply(somme, self.gain * self.inst.output_scale, out=somme)
        return _limiteur(somme)

    @property
    def active_voices(self):
        return sum(1 for v in self.voices if v.active)


def realtime_factor(instrument: Instrument, n_voices=4, block=256,
                    seconds=0.5):
    """Combien de fois plus vite que le temps réel — le seul chiffre qui dit
    si c'est jouable.

    En dessous de 1, l'audio craque. Au-dessus de 5, on est tranquille même
    avec une interface graphique qui s'agite à côté.
    """
    import time
    s = Synth(instrument, polyphony=n_voices)
    for i in range(n_voices):
        s.note_on(instrument.lo + 12 + 5 * i, 100)
    blocs = max(1, int(seconds * instrument.samplerate / block))
    s.render(block)                      # amorçage hors chronomètre
    t0 = time.perf_counter()
    for _ in range(blocs):
        s.render(block)
    dt = time.perf_counter() - t0
    audio_s = blocs * block / instrument.samplerate
    return audio_s / dt if dt > 0 else float('inf')


# =============================================================================
# Jouer depuis un terminal — sans GUI, sans clavier MIDI, sans carte
# =============================================================================

#: Disposition de tracker sur AZERTY : la rangée du bas donne les touches
#: blanches, celle du dessus les noires, comme sur un vrai clavier.
#:
#:      s d   g h j        ← noires  (do# ré#   fa# sol# la#)
#:     w x c v b n , ;     ← blanches (do ré mi fa sol la si do)
CLAVIER_AZERTY = {
    'w': 0, 's': 1, 'x': 2, 'd': 3, 'c': 4, 'v': 5, 'g': 6,
    'b': 7, 'h': 8, 'n': 9, 'j': 10, ',': 11, ';': 12, 'k': 13, ':': 14,
}

#: Même disposition sur un clavier QWERTY, pour qui n'est pas en AZERTY.
CLAVIER_QWERTY = {
    'z': 0, 's': 1, 'x': 2, 'd': 3, 'c': 4, 'v': 5, 'g': 6,
    'b': 7, 'h': 8, 'n': 9, 'j': 10, 'm': 11, ',': 12, 'l': 13, '.': 14,
}

DISPOSITIONS = {'azerty': CLAVIER_AZERTY, 'qwerty': CLAVIER_QWERTY}


def _sortie_audio(synth, blocksize=256, device=None):
    """Ouvre la sortie audio et y branche le synthé. Rend le flux, à fermer."""
    try:
        import sounddevice as sd
    except Exception as e:                      # pas de carte : on le dit net
        raise RuntimeError(
            "sounddevice est absent ou inutilisable (%s).\n"
            "  pip install sounddevice     — et sur Linux, le paquet système "
            "libportaudio2\n"
            "Sans carte son, --wav rend quand même une phrase dans un "
            "fichier." % e) from e

    def cb(outdata, frames, time_info, status):
        outdata[:, 0] = synth.render(frames)

    flux = sd.OutputStream(samplerate=synth.inst.samplerate, channels=1,
                           dtype='float32', blocksize=int(blocksize),
                           device=device, callback=cb)
    flux.start()
    return flux


def jouer_au_terminal(synth, disposition='azerty', octave=5, tenue=0.6,
                      blocksize=256, device=None, ecrire=print):
    """Clavier d'ordinateur → modèle physique, sans rien d'autre qu'un terminal.

    Un terminal ne signale **pas** le relâchement d'une touche : il n'envoie
    que des caractères. La répétition automatique du clavier sert donc de
    « touche tenue » — tant qu'elle arrive, la note reste soufflée ; dès
    qu'elle cesse pendant `tenue` secondes, on relâche, et l'oscillation
    s'éteint d'elle-même comme elle le ferait sous un vrai doigt.

    C'est une contrainte du terminal, pas du moteur : en MIDI, le relâchement
    est exact.
    """
    import select
    import sys
    import termios
    import time
    import tty

    touches = DISPOSITIONS.get(str(disposition).lower(), CLAVIER_AZERTY)
    inst = synth.inst
    flux = _sortie_audio(synth, blocksize=blocksize, device=device)
    vues = {}                                   # note → dernier appui

    ecrire("")
    ecrire(f"  {inst.name} — {len(inst)} notes, ×"
           f"{realtime_factor(inst, n_voices=len(synth.voices), seconds=0.2):.0f} "
           f"le temps réel")
    ecrire(f"  touches   {' '.join(sorted(touches, key=touches.get))}"
           f"   (disposition {disposition})")
    ecrire("  1 / 2     octave −/+          0   couper tout")
    ecrire("  3 / 4     nuance −/+          q   quitter")
    ecrire("  garde la touche enfoncée : la note tient tant que ça répète.")
    ecrire("")

    fd = sys.stdin.fileno()
    avant = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch = sys.stdin.read(1)
                if ch in ('q', '\x1b', '\x03'):
                    break
                if ch == '0':
                    synth.all_notes_off(); vues.clear(); continue
                if ch in '12':
                    octave = int(np.clip(octave + (1 if ch == '2' else -1), 0, 9))
                    ecrire(f"  octave {octave}")
                    continue
                if ch in '34':
                    pas = 0.1 if ch == '4' else -0.1
                    synth.expression = float(np.clip(synth.expression + pas, 0.05, 1.0))
                    ecrire(f"  nuance {100 * synth.expression:.0f} %")
                    continue
                if ch in touches:
                    note = 12 * octave + touches[ch]
                    if note not in vues:
                        synth.note_on(note, 100)
                    vues[note] = time.monotonic()

            maintenant = time.monotonic()
            for note, vu in list(vues.items()):
                if maintenant - vu > tenue:     # plus de répétition : on lâche
                    synth.note_off(note)
                    del vues[note]
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, avant)
        synth.all_notes_off()
        time.sleep(0.4)                          # laisser les notes s'éteindre
        flux.stop(); flux.close()
    ecrire("")
    return 0


def rendre_phrase(synth, notes=(60, 62, 64, 67, 64, 60), duree=0.5,
                  queue=1.2):
    """Rend une petite phrase, relâchement compris. Aucune carte son requise.

    `queue` laisse le temps à la dernière note de s'éteindre **physiquement**
    plutôt que d'être coupée : c'est la partie qu'un échantillonneur ne sait
    pas faire.
    """
    sr = synth.inst.samplerate
    morceaux = []
    for note in notes:
        synth.note_on(int(note), 100)
        for _ in range(max(1, int(duree * sr / 512))):
            morceaux.append(synth.render(512))
        synth.note_off(int(note))
    for _ in range(max(1, int(queue * sr / 512))):
        morceaux.append(synth.render(512))
    return np.concatenate(morceaux)


def _ecrire_wav(chemin, signal, samplerate):
    """Écrit un WAV 16 bits sans dépendre de scipy."""
    import wave
    x = np.clip(np.asarray(signal, dtype='float64'), -1.0, 1.0)
    with wave.open(str(chemin), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(int(samplerate))
        f.writeframes((x * 32767.0).astype('<i2').tobytes())
    return chemin


def main(argv=None):
    """`banc-recherche-jouer` — le modèle physique, sur le PC, tout de suite.

    Rien de tout ça ne demande de carte : le moteur est le C du STM32 compilé
    à la volée pour la machine où l'on est.

        banc-recherche-jouer --liste
        banc-recherche-jouer cornemuse                 # clavier d'ordinateur
        banc-recherche-jouer violon --midi "LPK25"     # clavier MIDI
        banc-recherche-jouer accordeon --wav essai.wav # sans carte son
    """
    import argparse
    import sys

    p = argparse.ArgumentParser(
        prog='banc-recherche-jouer',
        description="Jouer le modèle physique sur le PC (sans STM32).")
    p.add_argument('instrument', nargs='?', default='clarinette',
                   help="clarinette, saxophone, bombarde, cornemuse, "
                        "accordeon, violon, vielle")
    p.add_argument('--liste', action='store_true',
                   help="instruments, sorties audio et ports MIDI disponibles")
    p.add_argument('--wav', metavar='FICHIER',
                   help="rendre une phrase dans un WAV au lieu de jouer")
    p.add_argument('--midi', metavar='PORT',
                   help="jouer depuis ce port MIDI (sous-chaîne du nom)")
    p.add_argument('--grave', type=int, default=40, help="note MIDI la plus basse")
    p.add_argument('--aigu', type=int, default=88, help="note MIDI la plus haute")
    p.add_argument('--polyphonie', type=int, default=6)
    p.add_argument('--gain', type=float, default=0.45)
    p.add_argument('--la', type=float, default=440.0, help="hauteur du la3, en Hz")
    p.add_argument('--octave', type=int, default=5, help="octave de départ au clavier")
    p.add_argument('--tenue', type=float, default=0.6,
                   help="silence de touche avant relâchement, en secondes")
    p.add_argument('--disposition', default='azerty', choices=sorted(DISPOSITIONS))
    p.add_argument('--sr', type=float, default=48000.0)
    p.add_argument('--bloc', type=int, default=256)
    p.add_argument('--sortie', help="périphérique de sortie audio (nom ou index)")
    p.add_argument('--brut', action='store_true',
                   help="ne pas accorder les notes (montre l'écart de géométrie)")
    args = p.parse_args(argv)

    if args.liste:
        print("instruments :", ', '.join(sorted(hybrid.INSTRUMENTS)))
        try:
            import sounddevice as sd
            print("\nsorties audio :")
            for i, d in enumerate(sd.query_devices()):
                if d['max_output_channels'] > 0:
                    print(f"  [{i}] {d['name']}")
        except Exception as e:
            print(f"\nsounddevice indisponible ({e})")
        try:
            import mido
            noms = mido.get_input_names()
            print("\nports MIDI :", '\n  '.join([''] + noms) if noms else " aucun")
        except Exception:
            print("\nports MIDI : mido absent — pip install -e \".[live]\"")
        return 0

    if args.instrument not in hybrid.INSTRUMENTS:
        print(f"instrument inconnu : {args.instrument}\n"
              f"connus : {', '.join(sorted(hybrid.INSTRUMENTS))}", file=sys.stderr)
        return 2

    print(f"préparation de « {args.instrument} » : une perce par demi-ton"
          + ("" if args.brut else ", puis accordage note à note") + "…",
          file=sys.stderr)
    inst = build_instrument(args.instrument, lo=args.grave, hi=args.aigu,
                            samplerate=args.sr, a4_hz=args.la,
                            tune=not args.brut)
    synth = Synth(inst, polyphony=args.polyphonie, gain=args.gain)

    if args.wav:
        x = rendre_phrase(synth)
        _ecrire_wav(args.wav, x, inst.samplerate)
        print(f"→ {args.wav}  ({len(x) / inst.samplerate:.1f} s, "
              f"attaque, tenue et extinction physique)")
        return 0

    device = args.sortie
    if device is not None and device.isdigit():
        device = int(device)

    try:
        if args.midi:
            return _jouer_midi(synth, args.midi, blocksize=args.bloc,
                               device=device)
        return jouer_au_terminal(synth, disposition=args.disposition,
                                 octave=args.octave, tenue=args.tenue,
                                 blocksize=args.bloc, device=device)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2


def _jouer_midi(synth, motif, blocksize=256, device=None):
    """Brancher un vrai clavier : là, le relâchement est exact."""
    import sys
    import time
    try:
        import mido
    except Exception:
        print("mido absent : pip install -e \".[live]\"", file=sys.stderr)
        return 2
    noms = mido.get_input_names()
    trouve = next((n for n in noms if motif.lower() in n.lower()), None)
    if trouve is None:
        print(f"aucun port MIDI ne correspond à « {motif} ».\n"
              f"ports : {', '.join(noms) or 'aucun'}", file=sys.stderr)
        return 2

    def on_msg(msg):
        if msg.type == 'note_on' and msg.velocity > 0:
            synth.note_on(msg.note, msg.velocity)
        elif msg.type in ('note_off', 'note_on'):
            synth.note_off(msg.note)
        elif msg.type == 'control_change':
            if msg.control in (1, 2, 11):
                synth.expression = msg.value / 127.0
            elif msg.control == 123:
                synth.all_notes_off()

    flux = _sortie_audio(synth, blocksize=blocksize, device=device)
    port = mido.open_input(trouve, callback=on_msg)
    print(f"MIDI ouvert sur « {trouve} » — joue. Ctrl-C pour quitter.")
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        port.close()
        synth.all_notes_off()
        time.sleep(0.4)
        flux.stop(); flux.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
