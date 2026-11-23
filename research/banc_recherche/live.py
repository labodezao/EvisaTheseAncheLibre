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
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

import numpy as np

from . import hybrid
from .embedded import (RealtimeParams, params_from_voice, to_c_engine, loi_c,
                       biquad_bandpass, biquad_reed, FAMILY_BOW,
                       FAMILY_SINGLE_REED, FAMILY_FREE_REED, SORTIE_RAYONNEE,
                       SORTIE_PRESSION)
from .hybrid import RHO

HV_MAX_MODES = 24
HV_MAX_AA = 5


# =============================================================================
# Le moteur C, compilé et appelé par ctypes
# =============================================================================

class _Biquad(ctypes.Structure):
    _fields_ = [(n, ctypes.c_float) for n in ('b0', 'b1', 'b2', 'a1', 'a2')]


class _Reed(ctypes.Structure):
    """Biquad de l'anche (`hv_reed`) : `da1` = a1 + 2, `ea2` = 1 - a2."""
    _fields_ = [(n, ctypes.c_float) for n in ('b0', 'b1', 'b2', 'da1', 'ea2')]


class _BqState(ctypes.Structure):
    _fields_ = [('z1', ctypes.c_float), ('z2', ctypes.c_float)]


class _Params(ctypes.Structure):
    _fields_ = [
        ('family', ctypes.c_int), ('n_modes', ctypes.c_int),
        ('oversample', ctypes.c_int),
        ('modes', ctypes.POINTER(_Biquad)),
        ('reed', _Reed),
        ('rest_opening', ctypes.c_float), ('width', ctypes.c_float),
        ('vena', ctypes.c_float), ('max_open', ctypes.c_float),
        ('leak', ctypes.c_float), ('src_admit', ctypes.c_float),
        ('flow_gain', ctypes.c_float), ('visc_pa', ctypes.c_float),
        ('mu_s', ctypes.c_float), ('mu_d', ctypes.c_float),
        ('v_char', ctypes.c_float), ('bow_speed', ctypes.c_float),
        ('cavity_gain', ctypes.c_float), ('cavity_leak', ctypes.c_float),
        ('out_mode', ctypes.c_int), ('fs_out', ctypes.c_float),
        ('free_law', ctypes.c_int), ('plate', ctypes.c_float),
        ('tongue', ctypes.c_float), ('clear', ctypes.c_float),
        ('pump_area', ctypes.c_float),
        ('n_aa', ctypes.c_int), ('aa', ctypes.POINTER(_Biquad)),
    ]


class _State(ctypes.Structure):
    _fields_ = [('z', _BqState * HV_MAX_MODES), ('reed_z', _BqState),
                ('aa_z', _BqState * HV_MAX_AA),
                ('response', ctypes.c_float), ('cavity', ctypes.c_float),
                ('kicked', ctypes.c_int),
                ('net_prec', ctypes.c_float), ('net_ok', ctypes.c_int),
                ('y_prev', ctypes.c_float), ('y_ok', ctypes.c_int)]


_LIB = None


#: Les deux seules fonctions que le moteur expose. MSVC n'exporte rien tout
#: seul : il lui faut cette liste, écrite dans un `.def`. On préfère ça à un
#: `__declspec(dllexport)` dans le source — celui-là part sur la carte, il n'a
#: pas à savoir que Windows existe.
HV_EXPORTS = ('hv_reset', 'hv_render')


def _nom_bibliotheque():
    """Comment s'appelle une bibliothèque partagée, ici."""
    if sys.platform == 'win32':
        return 'hybridvoice.dll'
    if sys.platform == 'darwin':
        return 'libhybridvoice.dylib'
    return 'libhybridvoice.so'


def _compilateur():
    """Le premier compilateur utilisable, et sa famille.

    `CC` l'emporte toujours. Sinon on prend ce qu'il y a : `cc` sur Unix,
    et sous Windows on cherche d'abord un gcc/clang (MSYS2, w64devkit,
    MinGW) avant MSVC — non par préférence de goût, mais parce que `gcc
    -shared` exporte tout seul, là où `cl /LD` n'exporte rien sans qu'on le
    lui dise.
    """
    force = os.environ.get('CC')
    if force:
        famille = 'msvc' if pathlib.Path(force).stem.lower() == 'cl' else 'unix'
        return force, famille
    if sys.platform == 'win32':
        for nom in ('gcc', 'clang', 'cc'):
            if shutil.which(nom):
                return nom, 'unix'
        if shutil.which('cl'):
            return 'cl', 'msvc'
        return None, None
    for nom in ('cc', 'gcc', 'clang'):
        if shutil.which(nom):
            return nom, 'unix'
    return None, None


_AIDE_COMPILATEUR = {
    'win32': ("Installe un compilateur C, au choix :\n"
              "  • MSYS2   →  pacman -S mingw-w64-ucrt-x86_64-gcc  "
              "(puis ajoute son bin/ au PATH)\n"
              "  • w64devkit — une archive à dézipper, rien à installer\n"
              "  • Visual Studio Build Tools — ouvre « x64 Native Tools "
              "Command Prompt » et relance depuis là.\n"
              "Ou pointe-le à la main :  set CC=C:\\chemin\\vers\\gcc.exe"),
    'darwin': ("Installe les outils de ligne de commande :\n"
               "  xcode-select --install"),
}
_AIDE_COMPILATEUR_DEFAUT = ("Installe un compilateur C :\n"
                            "  sudo apt install build-essential   (Debian/Ubuntu)\n"
                            "  sudo dnf install gcc               (Fedora)")


def _aide_compilateur():
    return _AIDE_COMPILATEUR.get(sys.platform, _AIDE_COMPILATEUR_DEFAUT)


def _commande_compilation(cc, famille, dossier, source, cible):
    """La ligne de commande qui fabrique la bibliothèque, selon le compilateur."""
    if famille == 'msvc':
        deff = dossier / 'hybridvoice.def'
        deff.write_text("EXPORTS\n" + "\n".join(HV_EXPORTS) + "\n",
                        encoding='utf-8')
        return [cc, '/nologo', '/O2', '/LD', f'/DHV_MAX_MODES={HV_MAX_MODES}', f'/DHV_MAX_AA={HV_MAX_AA}',
                str(source), f'/Fe:{cible}', '/link', f'/DEF:{deff}']
    cmd = [cc, '-std=c99', '-O2', '-shared',
           f'-DHV_MAX_MODES={HV_MAX_MODES}', f'-DHV_MAX_AA={HV_MAX_AA}', str(source), '-o', str(cible)]
    if sys.platform != 'win32':
        cmd.insert(3, '-fPIC')          # inutile et bruyant sous Windows
        cmd.append('-lm')               # la libm y est déjà dans la libc
    elif pathlib.Path(cc).stem.lower() in ('gcc', 'cc'):
        # sinon la DLL réclame libgcc_s au chargement, et MinGW n'est pas dans
        # le PATH d'un Python installé normalement : erreur incompréhensible
        # au moment d'ouvrir la bibliothèque, pas au moment de la compiler.
        cmd.insert(3, '-static-libgcc')
    return cmd


def engine_library(force=False):
    """Compile le moteur C en bibliothèque partagée, et la charge.

    Le binaire est mis en cache dans le dossier temporaire, clé de hachage du
    source : régénérer le moteur le recompile, sinon on le réutilise. On ne
    veut pas payer une compilation à chaque note.

    Marche sur Linux, macOS et Windows — le source, lui, ne change pas d'un
    octet : c'est celui qui part sur la carte. Seuls l'extension du fichier,
    le compilateur et ses options diffèrent.
    """
    global _LIB
    if _LIB is not None and not force:
        return _LIB

    src = to_c_engine()
    cle = hashlib.sha256(
        (src['hybrid_voice.h'] + src['hybrid_voice.c']).encode()).hexdigest()[:16]
    d = pathlib.Path(tempfile.gettempdir()) / f"banc_hv_{cle}"
    so = d / _nom_bibliotheque()

    if force or not so.exists():
        cc, famille = _compilateur()
        if cc is None:
            raise RuntimeError("aucun compilateur C trouvé.\n"
                               + _aide_compilateur())
        d.mkdir(parents=True, exist_ok=True)
        for nom, texte in src.items():
            (d / nom).write_text(texte, encoding='utf-8')
        cmd = _commande_compilation(cc, famille, d, d / 'hybrid_voice.c', so)
        # cwd dans le dossier de travail : MSVC sème ses .obj là où il est
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(d),
                           encoding='utf-8', errors='replace')
        if r.returncode != 0 or not so.exists():
            raise RuntimeError(
                f"impossible de compiler le moteur C avec « {cc} » :\n"
                + (r.stderr or r.stdout)[:800] + "\n" + _aide_compilateur())

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

    # un seul tableau : les modes, puis les sections du filtre anti-repliement
    aa = p.sections_antirepliement
    nm = max(len(coeffs), 1)
    modes = (_Biquad * (nm + len(aa)))()
    for i, c in enumerate(coeffs):
        modes[i] = _Biquad(*[float(x) for x in c])
    for i, c in enumerate(aa):
        modes[nm + i] = _Biquad(*[float(x) for x in c])

    if p.family == FAMILY_BOW:
        reed = _Reed(0., 0., 0., 0., 0.)
    else:
        signe = -1.0 if p.family == FAMILY_SINGLE_REED else 1.0
        reed = _Reed(*biquad_reed(
            p.reed_freq_hz, p.reed_q,
            signe * p.rest_opening_m / p.closing_pressure_pa, fs))

    cp = _Params()
    cp.family = int(p.family)
    cp.n_modes = len(coeffs)
    cp.oversample = int(p.oversample)
    cp.modes = ctypes.cast(modes, ctypes.POINTER(_Biquad))
    cp.n_aa = len(aa)
    cp.aa = ctypes.cast(ctypes.addressof(modes) + nm * ctypes.sizeof(_Biquad),
                        ctypes.POINTER(_Biquad))
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
    cp.out_mode = 0 if p.sortie_effective == SORTIE_RAYONNEE else 1
    cp.fs_out = float(p.samplerate)
    cp.free_law = loi_c(p)
    cp.plate, cp.tongue, cp.clear = p.plate_m, p.tongue_m, p.clearance_m
    cp.pump_area = p.pump_area_m2
    if p.family == FAMILY_FREE_REED:
        # surface de force (largeur x longueur de lame) : de quoi refaire
        # S_eff = F x surface quand F change (CC 74)
        cp.surface_force = float(p.force_area_m2)
        # de quoi refaire le biquad de l'anche quand son Q change (CC de timbre)
        cp.base_anche = (p.reed_freq_hz, p.reed_q,
                         p.rest_opening_m / p.closing_pressure_pa, fs)
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
    #: pour un instrument bâti sur une vraie perce : la gamme de ses doigtés,
    #: `[(nom, trous, fréquence, note MIDI), …]`. Vide sinon.
    fingerings: list = field(default_factory=list, repr=False)
    _params: dict = field(default_factory=dict, repr=False)
    _keep: list = field(default_factory=list, repr=False)
    #: accord des réglages de timbre (anche libre) : `{note: tableau}`, voir
    #: `table_accord_timbre`. Vide : le timbre ne retouche pas la lame.
    accord_timbre: dict = field(default_factory=dict, repr=False)

    def params_for(self, note):
        """Structure C de la note, ou de la plus proche disponible.

        Une perce réelle ne remplit pas le clavier : elle a les notes de ses
        doigtés, et rien entre. On rend alors la plus proche — jouer une
        touche vide doit donner *quelque chose*, comme un doigté approché.
        """
        n = int(np.clip(int(note), self.lo, self.hi))
        if n in self._params:
            return self._params[n]
        dispo = min(self._params, key=lambda k: abs(k - n))
        return self._params[dispo]

    def __len__(self):
        return len(self._params)


def _frequence_jouee(cp, niveau, samplerate, dur=None, debut=None, f_nom=None):
    """Ce que la note joue **vraiment**, mesuré sur le moteur lui-même.

    On mesure la hauteur **établie**, pas celle de l'attaque. Deux choses
    faussaient l'accord de construction, mesurées sur l'accordéon (pression de
    chambre) :

    - la fenêtre : la première moitié de 0,6 s ne suffit pas, la hauteur
      s'établit en 0,5 s et plus (note 45 : -1,21 cent tenue, +3,8 à 0,25 s) ;
      `ACCORD_DUREE_S` et `ACCORD_DEBUT_S` donnent la durée rendue et le début
      de la fenêtre, ceux de la table d'accord du timbre ;
    - l'estimateur : `hybrid.playing_frequency` (autocorrélation sur 0,3 s)
      lit +0,04 cent là où la note 48 tient -2,30 (jusqu'à 1,4 cent de biais
      sur 0,3 s, 0,2 encore sur 0,6 s). `_hauteur_longue` donne, à 0,01 cent,
      ce que donne la pente de phase du fondamental sur 1 s.

    `f_nom` : la hauteur attendue, autour de laquelle `_hauteur_longue`
    cherche ; sans elle, `playing_frequency` en donne une première valeur.
    `dur` plus court que `ACCORD_DUREE_S` : la fenêtre commence à sa moitié
    au plus. On retire la moyenne : une anche libre sort une pression de
    chambre fortement décalée, et l'autocorrélation d'un signal à composante
    continue pointe sur le décalage plutôt que sur la période.
    """
    # La hauteur est celle de l'oscillateur, pas du signal qu'on écoute. On la
    # mesure donc sur la pression de la chambre, lisse : l'autocorrélation d'un
    # rayonnement (dérivée d'un quasi-carré, des impulsions de signes
    # alternés) se trompe d'octave. Mesuré : la même note à -1904 cents sur le
    # rayonnement, à -2 cents sur la pression.
    dur = ACCORD_DUREE_S if dur is None else float(dur)
    if debut is None:
        debut = min(ACCORD_DEBUT_S, dur / 2.0)
    mesure = _Params()
    ctypes.memmove(ctypes.byref(mesure), ctypes.byref(cp), ctypes.sizeof(cp))
    mesure.out_mode = 1
    v = Voice()
    v.note_on(mesure, 60, niveau)
    n = int(dur * samplerate)
    buf = np.zeros(512, dtype=np.float32)
    x = np.empty(n, dtype=np.float32)
    for i in range(0, n, 512):
        buf[:] = 0.0
        v.render(buf)
        x[i:i + 512] = buf[:min(512, n - i)]
    y = x[int(debut * samplerate):].astype('float64')
    y -= y.mean()
    if np.max(np.abs(y)) < 1e-9:
        return None                       # rien ne sort : rien à accorder
    if not f_nom:
        f_nom = hybrid.playing_frequency(y, samplerate)
        if not f_nom > 0.0:
            return float('nan')
    return _hauteur_longue(y, samplerate, f_nom)


def _accorder(name, cible_hz, niveau, samplerate, passes=8, sortie=None, **kw):
    """Retouche la note jusqu'à ce qu'elle joue juste. Un accordage, vraiment.

    Un modèle physique ne joue pas la fréquence qu'on lui dessine : la perce
    a une correction de pavillon, l'anche tire la hauteur vers elle, la
    chambre raidit la languette. L'écart va de 1 à 40 cents selon la note et
    la famille — audible, et faux au clavier.

    Le facteur d'instrument fait exactement ce qu'on fait ici : il mesure ce
    que ça donne, corrige la cote, remesure. L'écart est presque proportionnel à la
    correction : l'accordéon tient à 0,05 cent en deux corrections ; les autres
    familles (perce, pavillon, anche double) oscillent parfois d'une passe à
    l'autre autour de la cible. On garde donc **la meilleure des mesures**
    (au plus `passes` corrections, arrêt dès 0,05 cent), pas la dernière.

    Ce n'est **pas** une correction de hauteur plaquée à la sortie : c'est la
    géométrie qu'on change. Le timbre, le transitoire et le seuil sont ceux
    de l'instrument accordé, pas ceux d'un instrument faux qu'on transpose.
    """
    design = float(cible_hz)
    voix = hybrid.INSTRUMENTS[name](f0_hz=design, **kw)
    p = params_from_voice(voix, samplerate=samplerate, name=name, sortie=sortie)
    cp, garde = _to_c_params(p)
    meilleur = (float('inf'), cp, garde)
    for k in range(int(passes) + 1):
        joue = _frequence_jouee(cp, niveau, samplerate, f_nom=cible_hz)
        if not joue or not (0.5 < joue / cible_hz < 2.0):
            if k == 0:
                meilleur = (0.0, cp, garde)
            break                         # muette, ou dans un autre registre
        ecart = abs(1200.0 * float(np.log2(joue / cible_hz)))
        if ecart < meilleur[0]:
            meilleur = (ecart, cp, garde)
        if ecart <= ACCORD_ARRET_CENTS or k == int(passes):
            break
        design *= cible_hz / joue
        voix = hybrid.INSTRUMENTS[name](f0_hz=design, **kw)
        p = params_from_voice(voix, samplerate=samplerate, name=name,
                              sortie=sortie)
        cp, garde = _to_c_params(p)
    return meilleur[1], meilleur[2]


def niveau_nominal(ex) -> float:
    """Niveau de jeu nominal d'un excitateur, **dans son unité à lui**.

    Chaque famille se commande avec une grandeur différente, et les échelles
    n'ont rien de commun : un archet se pousse en newtons, une anche battante
    en pascals, une anche libre en **mètres cubes par seconde**. Mélanger les
    deux dernières, c'est passer 2480 là où il faut 2,9·10⁻⁶ — neuf ordres de
    grandeur, et un instrument muet ou explosé.

    Ce choix était dupliqué entre `build_instrument` et `build_from_dat`, et
    les deux copies avaient divergé : la seconde avait perdu la branche de
    l'anche libre et rabattait tout sur la pression de fermeture. Monter une
    anche libre sur une perce — ce que `hybrid` permet justement — donnait
    alors un débit de 2480 m³/s.
    """
    if isinstance(ex, hybrid.BowExciter):
        return 0.25
    if isinstance(ex, hybrid.FreeReedExciter):
        return 2.9e-6
    return 0.62 * getattr(ex, 'closing_pressure_pa', 4000.0)


def build_instrument(name="clarinette", lo=36, hi=96, samplerate=48000.0,
                     a4_hz=440.0, on_progress=None, tune=True, sortie=None,
                     accord_timbre=True, **kw):
    """Prépare un instrument jouable : une perce par demi-ton.

    Chaque note a **sa propre géométrie** — c'est un modèle physique, pas un
    échantillon transposé. Une clarinette grave et une clarinette aiguë n'ont
    pas les mêmes pertes ni la même coupure de réseau, et ça s'entend.

    `tune=True` accorde ensuite chaque note sur le moteur (cf. `_accorder`).
    `tune=False` laisse l'instrument tel que la géométrie le donne — c'est ce
    qu'il faut pour étudier l'écart lui-même, pas pour jouer.

    `sortie` : ce que les voix sortent. Par défaut celui de la famille : pour
    l'anche libre (accordéon), le rayonnement, dérivée du débit net
    (`embedded.SORTIE_RAYONNEE`). `embedded.SORTIE_PRESSION` redonne l'ancienne
    sortie, la pression de la chambre, pour comparer.

    `accord_timbre` (anche libre accordée seulement) : calcule, ou relit de son
    cache, le tableau qui ramène la lame à sa note quand un CC de timbre
    bouge (`table_accord_timbre`). `False` pour s'en passer.
    """
    voix_ref = hybrid.build(name)
    ex = voix_ref.exciter
    niveau = niveau_nominal(ex)

    inst = Instrument(name=name, lo=int(lo), hi=int(hi),
                      samplerate=float(samplerate), a4_hz=float(a4_hz),
                      level_default=float(niveau),
                      control_unit=getattr(ex, 'control_unit', '') or '')

    for n in range(inst.lo, inst.hi + 1):
        f0 = midi_to_hz(n, a4_hz)
        if tune:
            cp, garde = _accorder(name, f0, niveau, samplerate, sortie=sortie,
                                  **kw)
        else:
            voix = hybrid.INSTRUMENTS[name](f0_hz=f0, **kw)
            p = params_from_voice(voix, samplerate=samplerate, name=name,
                                  sortie=sortie)
            cp, garde = _to_c_params(p)
        inst._params[n] = cp
        inst._keep.append(garde)          # sans ça, le tableau est libéré
        if on_progress:
            on_progress(n - inst.lo + 1, inst.hi - inst.lo + 1)

    inst.output_scale = _mesurer_echelle(inst)
    if tune and accord_timbre:
        inst.accord_timbre = table_accord_timbre(inst)
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


def _facteur_limiteur(x, seuil=0.7):
    """Le facteur (≤ 1) que `_limiteur` applique à chaque échantillon de `x`."""
    a = np.abs(x)
    f = np.ones(a.shape, dtype=np.float32)
    haut = a > seuil
    if np.any(haut):
        marge = 1.0 - seuil
        f[haut] = (seuil + marge * np.tanh((a[haut] - seuil) / marge)) / a[haut]
    return f


def build_instrument_from_bore(dat, famille='cornemuse', doigtes=None,
                              samplerate=48000.0, a4_hz=440.0, n_modes=10,
                              cutoff_hz=None, reed_volume_m3=None,
                              on_progress=None, **kw):
    """Un instrument jouable bâti sur une **vraie perce**, doigté par doigté.

    C'est l'aboutissement du pont vers TUTT, et il change la nature de
    l'objet. `build_instrument` fabrique une perce *par demi-ton* : pratique
    au clavier, mais aucun instrument réel ne marche comme ça. Ici, la perce
    est **une seule et même pièce** — celle du fichier — et ce sont les
    **doigts** qui changent la note, comme sur l'instrument. Chaque doigté
    est calculé (impédance d'entrée, cheminées ouvertes ou fermées, résonances
    réelles), puis rangé sur la touche MIDI dont il est le plus proche.

    Ce que ça implique, et qu'il vaut mieux savoir avant de jouer :

    - la tessiture est celle de l'instrument, pas celle du clavier. Une perce
      à six trous donne sept notes, pas soixante-et-une ;
    - si deux doigtés tombent sur la même touche, le plus proche gagne et
      l'autre est perdu — c'est le fichier qui le dit, pas nous ;
    - **la justesse n'est pas corrigée**. `build_instrument` accorde chaque
      note sur le moteur ; ici, surtout pas : l'écart entre ce que la perce
      donne et ce qu'elle devrait donner *est* le résultat qu'on vient
      chercher. Le corriger reviendrait à effacer la mesure.

    `famille` choisit l'excitateur (n'importe quel nom de `hybrid.INSTRUMENTS`
    à perce) ; la géométrie, elle, vient entièrement du fichier.
    """
    from . import tutt as _tutt

    gamme = _tutt.gamme_des_doigtes(dat, doigtes=doigtes,
                                    reed_volume_m3=reed_volume_m3)
    if not gamme:
        raise ValueError("aucun doigté exploitable dans cette perce")

    modele = hybrid.build(famille)
    ex = modele.exciter
    niveau = niveau_nominal(ex)

    notes = [int(round(69 + 12 * np.log2(f / a4_hz))) for _, _, f in gamme]
    inst = Instrument(name=f"{dat.title or 'perce'} ({famille})",
                      lo=min(notes), hi=max(notes),
                      samplerate=float(samplerate), a4_hz=float(a4_hz),
                      level_default=float(niveau),
                      control_unit=getattr(ex, 'control_unit', '') or '')

    _ecarts: dict[int, float] = {}
    for k, ((nom, trous, f_hz), note) in enumerate(zip(gamme, notes)):
        res, _infos = _tutt.resonator_from_dat(
            dat, fmin=max(20.0, 0.5 * f_hz), fmax=min(9000.0, f_hz * 12.0),
            n_peaks=int(n_modes), cutoff_hz=cutoff_hz, fingering=trous,
            reed_volume_m3=reed_volume_m3)
        voix = hybrid.HybridVoice(type(ex)(**kw) if kw else ex, res,
                                  name=f"{famille} {nom}")
        p = params_from_voice(voix, samplerate=samplerate, name=famille)
        cp, garde = _to_c_params(p)
        # Deux doigtés peuvent tomber sur la même touche (les notes sont
        # arrondies au MIDI). C'est le plus **proche** du tempéré qui gagne,
        # comme l'annonce la docstring — pas le dernier lu.
        ecart = abs(1200.0 * np.log2(f_hz / midi_to_hz(note, a4_hz)))
        if note in inst._params and ecart >= _ecarts.get(note, np.inf):
            continue
        _ecarts[note] = ecart
        inst._params[note] = cp
        inst._keep.append(garde)
        inst.fingerings = [e for e in inst.fingerings if e[3] != note]
        inst.fingerings.append((nom, trous, f_hz, note))
        if on_progress:
            on_progress(k + 1, len(gamme))

    inst.output_scale = _mesurer_echelle(inst, notes=sorted(set(notes)))
    return inst


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

# =============================================================================
# Réglages de timbre de l'accordéon, pilotés en CC MIDI
# =============================================================================

#: LA table des CC de timbre (24/11/2026, ordre 7 de la feuille de route).
#: `nom: (numéro de CC, facteur à CC 0, facteur à CC 127, grandeur réglée)`.
#:
#: Chaque réglage est un **facteur multiplicatif** de la valeur par défaut du
#: modèle, en échelle logarithmique : CC 64 = facteur 1 (le défaut, à
#: l'échantillon près), CC 0 = facteur mini, CC 127 = facteur maxi.
#:
#: **Les valeurs par défaut de ces quatre grandeurs sont provisoires, non
#: mesurées sur une lame réelle** (volume de chambre : 40 cm³ à 110 Hz ; largeur
#: de lame : 4,8 mm ; Q : 60 ; jeu : 15 µm). Ce sont des réglages de timbre, pas
#: des cotes d'instrument : leur facteur 1 n'est pas une mesure.
#:
#: Les numéros 70 à 73 sont ceux des « sound controllers » du MIDI ; aucun
#: n'était lu par le moteur (il lit 2, 11 et 123). Seule l'anche libre a ces
#: réglages ; les autres familles les ignorent.
#:
#: Effets mesurés hors moteur : volume x2 et largeur x0,5 baissent chacun le
#: spectre d'environ 5 dB et ralentissent la montée ; Q règle le temps de
#: réponse des graves ; le jeu a peu d'effet.
TIMBRE_CC = {
    'chambre': (70, 0.5, 2.0, "volume de la chambre de l'anche"),
    'largeur': (71, 0.5, 2.0, "largeur de la lame"),
    'q':       (72, 0.5, 2.0, "facteur de qualité Q de la lame"),
    'jeu':     (73, 0.5, 3.0, "jeu latéral lame / fente"),
}
#: numéro de CC → nom du réglage
CC_TIMBRE = {v[0]: k for k, v in TIMBRE_CC.items()}
#: constante de temps du lissage d'un CC de timbre, en s
TAU_TIMBRE_S = 0.02

#: Le débit déplacé par la lame elle-même (le « pompage » : q_pompe = S_eff ×
#: vitesse de la lame), ajouté au débit rayonné. `(numéro de CC, F à CC 0, F à
#: CC 64, F à CC 127, grandeur)`. **F est un facteur sans unité** :
#: `S_eff = F × largeur × longueur de la lame` de la note (`force_area_m2`, la
#: surface de force qui sert déjà à la raideur de la lame). Échelle
#: **linéaire** en F (pas logarithmique : F vaut 0 à CC 0), en deux segments :
#: CC 0 = 0 (sans pompe), CC 64 = 0,8, CC 127 = 1,6.
#:
#: **0,8 est provisoire, non mesuré** : c'est la valeur qui, dans l'essai hors
#: moteur (note 57, CC 11 = 80), ramène A2/A1 à -14,5 dB (réel : -20) ; la
#: surface efficace de la lame n'a pas été mesurée sur une lame réelle.
#: Différent de `TIMBRE_CC` : 64 n'est pas « le défaut ». Le défaut, sans aucun
#: message CC 74 et sans l'argument `pompe`, est F = 0 : le son d'avant, à
#: l'échantillon près. Même lissage (`TAU_TIMBRE_S`) que les CC 70 à 73 ; seule
#: l'anche libre en sortie rayonnée l'entend. Le bilan de la chambre et la lame
#: ne changent pas : ni l'accord ni la dynamique.
POMPE_CC = (74, 0.0, 0.8, 1.6,
            "débit déplacé par la lame (S_eff = F x largeur x longueur)")
CC_POMPE = POMPE_CC[0]


def facteur_pompe(valeur_cc):
    """Valeur de CC 74 (0 à 127) → F, linéaire : 0 → 0, 64 → 0,8, 127 → 1,6."""
    _, f0, f64, f127, _ = POMPE_CC
    v = float(np.clip(valeur_cc, 0, 127))
    if v <= 64.0:
        return float(f0 + (f64 - f0) * v / 64.0)
    return float(f64 + (f127 - f64) * (v - 64.0) / 63.0)


def facteur_timbre(nom, valeur_cc):
    """Valeur de CC (0 à 127) → facteur multiplicatif du défaut, en échelle
    logarithmique : 64 donne exactement 1.0, 0 le facteur mini, 127 le maxi."""
    _, fmin, fmax, _ = TIMBRE_CC[nom]
    v = float(np.clip(valeur_cc, 0, 127))
    if v == 64.0:
        return 1.0
    if v < 64.0:
        return float(fmin ** ((64.0 - v) / 64.0))
    return float(fmax ** ((v - 64.0) / 63.0))


def params_timbre(base, chambre=1.0, largeur=1.0, q=1.0, jeu=1.0, accord=1.0,
                  pompe=None):
    """Copie de `base` (structure C d'une note d'anche libre) avec les quatre
    facteurs de timbre. Tous à 1.0 (ou famille sans anche libre) : `base`
    elle-même, donc le son par défaut est celui d'avant, à l'échantillon près.

    - chambre : compliance ∝ volume, donc `cavity_gain` ÷ facteur ;
    - largeur : `flow_gain` et `width` × facteur ;
    - q : biquad de l'anche refait avec Q × facteur (même fréquence, même gain
      statique) ;
    - jeu : `clear` × facteur.
    - accord : facteur de la fréquence propre de la lame (`accord_pour`),
      1.0 par défaut.
    - pompe : F, facteur du débit déplacé par la lame (`POMPE_CC`) :
      `pump_area` = F × surface de force de la lame. `None` : celui de `base`.
    """
    info = getattr(base, 'base_anche', None)
    if info is None:
        return base
    surface = getattr(base, 'surface_force', 0.0)
    aire = base.pump_area if pompe is None else float(pompe) * surface
    if (chambre == 1.0 and largeur == 1.0 and q == 1.0
            and jeu == 1.0 and accord == 1.0 and aire == base.pump_area):
        return base
    cp = _Params.from_buffer_copy(base)
    cp.base_anche = info
    cp.surface_force = surface
    cp.pump_area = aire
    cp._base = base                     # le tableau de modes reste vivant
    if base.cavity_gain > 0.0:
        cp.cavity_gain = base.cavity_gain / chambre
    cp.width = base.width * largeur
    cp.flow_gain = base.flow_gain * largeur
    cp.clear = base.clear * jeu
    if q != 1.0 or accord != 1.0:
        f, q0, gain, fs = info
        cp.reed = _Reed(*biquad_reed(f * accord, q0 * q, gain, fs))
    return cp


# -----------------------------------------------------------------------------
# L'accord suit le timbre : la lame est retouchée pour que la note reste juste
# -----------------------------------------------------------------------------
#
# Chambre, largeur de lame et Q déplacent la hauteur de la note de quelques
# cents (jusqu'à 50 aux bornes, dans l'aigu) : l'accord se fait une fois, à la
# construction, avec les réglages par défaut. Un accordeur, après avoir changé
# la chambre ou la lame, retouche la lame pour ramener la note. C'est ce
# geste : la **fréquence propre de la lame** est corrigée selon les réglages.
#
# Mesuré (accordeon/cc_accord) : la somme des dérives de chaque CC seul ne
# prédit pas celle d'une combinaison (jusqu'à 26 cents d'écart à la note 84,
# chambre et Q à 0). Le tableau est donc tabulé en trois dimensions, chambre x
# largeur x Q, par note, sur la hauteur mesurée du modèle. Le jeu de fente (CC 73) déplace la hauteur de 0,4 cent au
# plus : pas de correction.

#: réglages tabulés et valeurs de CC de leur grille
ACCORD_GRILLE = {
    'chambre': (0, 16, 32, 48, 64, 80, 96, 112, 127),
    'largeur': (0, 64, 127),
    'q':       (0, 16, 32, 48, 64, 80, 96, 112, 127),
}
ACCORD_NOMS = tuple(ACCORD_GRILLE)
#: durée rendue pour mesurer une hauteur, s, et début de la fenêtre analysée :
#: dans le grave à Q élevé, la hauteur met plus d'une seconde à se poser (note
#: 45, Q 127 : -4,0 cents à 0,5-1 s, -5,5 à 1-1,5 s, -5,8 à 1,5-2 s)
ACCORD_DUREE_S = 2.5
ACCORD_DEBUT_S = 1.5
#: l'accord de construction s'arrête quand la note tient sa cible à ce point
#: près, en cents (la mesure elle-même est juste à 0,03 cent)
ACCORD_ARRET_CENTS = 0.05
#: à changer quand une modification de ce bloc change les chiffres du tableau
ACCORD_VERSION = 4


def _hauteur_longue(y, fs, f_nom):
    """Fréquence (Hz) d'un signal périodique, par autocorrélation sur un long
    retard : le pic de `m` périodes est localisé à un échantillon près, donc la
    période à 1/m d'échantillon (m allant jusqu'à une vingtaine). Cherché
    autour de la hauteur nominale `f_nom` (écart toléré : un quart de période).
    `nan` si le signal est vide ou non périodique."""
    y = np.asarray(y, dtype='float64')
    y = y - y.mean()
    n = y.size
    if n < 64 or float(np.std(y)) < 1e-12:
        return float('nan')
    m_fft = 1 << int(np.ceil(np.log2(2 * n)))
    F = np.fft.rfft(y, m_fft)
    ac = np.fft.irfft(F * np.conj(F), m_fft)[:n]
    ac = ac / ac[0]

    def pic(k0, w):
        k0 = int(round(k0))
        lo, hi = max(k0 - w, 2), min(k0 + w, n - 2)
        if hi <= lo:
            return None
        k = lo + int(np.argmax(ac[lo:hi + 1]))
        a, b, c = ac[k - 1], ac[k], ac[k + 1]
        den = a - 2.0 * b + c
        return k + (0.5 * (a - c) / den if den < 0.0 else 0.0), b

    T = fs / float(f_nom)
    r = pic(T, max(int(T / 4.0), 2))
    if r is None or r[1] < 0.3:
        return float('nan')
    T1, m = r[0], 1
    m_max = int(0.45 * n / T1)
    while m < m_max:
        m2 = min(4 * m, m_max)
        r = pic(m2 * T1, max(int(T1 / 4.0), 2))
        if r is None:
            break
        T1, m = r[0] / m2, m2
    return float(fs / T1)


def _hauteur_note(base, niveau, f_nom, samplerate, dur=ACCORD_DUREE_S):
    """Hauteur (Hz) que joue `base` à `niveau`, sur la pression de chambre,
    comme `_frequence_jouee` (mêmes raisons), mais mesurée par
    `_hauteur_longue`, sur la fenêtre qui commence à `ACCORD_DEBUT_S`. `nan` si
    rien ne sort."""
    mesure = _Params()
    ctypes.memmove(ctypes.byref(mesure), ctypes.byref(base),
                   ctypes.sizeof(base))
    mesure.out_mode = 1
    v = Voice()
    v.note_on(mesure, 60, niveau)
    n = int(dur * samplerate)
    buf = np.zeros(1024, dtype=np.float32)
    x = np.empty(n, dtype=np.float32)
    for i in range(0, n, 1024):
        buf[:] = 0.0
        v.render(buf)
        x[i:i + 1024] = buf[:min(1024, n - i)]
    return _hauteur_longue(x[int(ACCORD_DEBUT_S * samplerate):], samplerate,
                           f_nom)


def _facteurs_grille(i, j, k):
    return dict(chambre=facteur_timbre('chambre', ACCORD_GRILLE['chambre'][i]),
                largeur=facteur_timbre('largeur', ACCORD_GRILLE['largeur'][j]),
                q=facteur_timbre('q', ACCORD_GRILLE['q'][k]))


def _ecart_cents(base, fac, lg, niveau, f_nom, samplerate, f_ref):
    """Écart de hauteur (cents) à `f_ref`, la lame retouchée de `lg` (ln du
    facteur de fréquence) ; `nan` si la note ne sonne pas."""
    f = _hauteur_note(params_timbre(base, accord=float(np.exp(lg)), **fac),
                      niveau, f_nom, samplerate)
    return 1200.0 * float(np.log2(f / f_ref)) if f > 0.0 else float('nan')


#: pas de tâtonnement de la lame (ln de la fréquence) quand la sécante ne
#: suffit pas : 0,0004 vaut un peu moins d'un cent de lame
ACCORD_PAS = 0.0004


def _tableau_note(base, niveau, f_nom, samplerate, tolerance_cents=0.3):
    """Le tableau d'une note : `ln(facteur de fréquence de lame)` qui ramène la
    hauteur jouée à celle des réglages par défaut, pour chaque point de la
    grille. Mesuré sur le moteur, point par point.

    La hauteur jouée suit la lame d'un pour un, continûment (le biquad de
    l'anche du moteur C n'avait pas la finesse : marches de 4 cents à la note
    45, cf. `embedded.hv_reed`). On part de la correction du voisin, on se
    rapproche à la sécante, puis, si l'écart reste au-dessus de
    `tolerance_cents`, on tâte la lame de part et d'autre par pas de
    `ACCORD_PAS` pour trouver le palier le plus proche, dont on prend le
    milieu (filet de sécurité). Un point où la note ne sonne pas ou reste à
    plus de 3 cents reste à 0. Rend `(tableau, pire écart en cents sur les points gardés, nombre de
    points sans mesure)`.
    """
    f_ref = _hauteur_note(base, niveau, f_nom, samplerate)
    ng = [len(ACCORD_GRILLE[nom]) for nom in ACCORD_NOMS]
    tab = np.zeros(ng)
    if not np.isfinite(f_ref):
        return tab, 0.0, int(np.prod(ng))
    K0 = 1200.0 / np.log(2.0) * 0.93                 # cents par unité de ln
    pire, perdus, lg = 0.0, 0, 0.0

    for i in range(ng[0]):
        for jj in range(ng[1]):
            j = jj if i % 2 == 0 else ng[1] - 1 - jj     # va-et-vient : le
            for kk in range(ng[2]):                      # voisin reste proche
                k = kk if (i * ng[1] + jj) % 2 == 0 else ng[2] - 1 - kk
                cc = (ACCORD_GRILLE['chambre'][i], ACCORD_GRILLE['largeur'][j],
                      ACCORD_GRILLE['q'][k])
                if cc == (64, 64, 64):
                    lg = 0.0
                    continue
                fac = _facteurs_grille(i, j, k)
                vus = {}

                def ecart(x):
                    x = round(float(x), 6)
                    if x not in vus:
                        vus[x] = _ecart_cents(base, fac, x, niveau, f_nom,
                                              samplerate, f_ref)
                    return vus[x]

                K, prec, x = K0, None, lg
                for _ in range(4):
                    d = ecart(x)
                    if not np.isfinite(d) or abs(d) <= tolerance_cents:
                        break
                    if prec is not None and abs(x - prec[0]) > 1e-9:
                        K = float(np.clip((d - prec[1]) / (x - prec[0]),
                                          0.4 * K0, 2.0 * K0))
                    pas = d / K
                    if prec is not None and abs(d - prec[1]) < 0.25:
                        pas = np.sign(d) * max(abs(pas), ACCORD_PAS)
                    prec = (x, d)
                    x -= pas
                bons = {u: v for u, v in vus.items() if np.isfinite(v)}
                if not bons:
                    perdus += 1
                    lg = 0.0
                    continue
                u0 = min(bons, key=lambda u: abs(bons[u]))
                if abs(bons[u0]) > tolerance_cents:
                    for sens in (-1.0, 1.0):          # on tâte la lame
                        for m in (1, 2, 3):
                            e = ecart(u0 + sens * m * ACCORD_PAS)
                            if not np.isfinite(e) or abs(e) > abs(bons[u0]) + 1.0:
                                break
                    bons = {u: v for u, v in vus.items() if np.isfinite(v)}
                    u0 = min(bons, key=lambda u: abs(bons[u]))
                # le milieu des essais qui valent le meilleur
                egaux = [u for u, v in bons.items()
                         if abs(abs(v) - abs(bons[u0])) < 0.15
                         and abs(u - u0) <= 3 * ACCORD_PAS]
                lg = float(np.mean(egaux))
                d = ecart(lg) if round(lg, 6) in vus else _ecart_cents(
                    base, fac, lg, niveau, f_nom, samplerate, f_ref)
                if np.isfinite(d) and abs(d) <= 3.0:
                    tab[i, j, k] = lg
                    pire = max(pire, abs(d))
                else:
                    perdus += 1
                    lg = 0.0
    return tab, pire, perdus


def _cle_accord(inst, notes):
    h = hashlib.sha1()
    h.update(repr((ACCORD_VERSION, ACCORD_GRILLE, ACCORD_DUREE_S, ACCORD_DEBUT_S,
                   inst.name,
                   inst.samplerate, inst.a4_hz, inst.level_default,
                   TIMBRE_CC)).encode())
    for n in notes:
        p = inst._params[n]
        h.update(repr((n, getattr(p, 'base_anche', None), p.cavity_gain,
                       p.width, p.flow_gain, p.clear, p.rest_opening, p.vena,
                       p.max_open, p.leak, p.src_admit, p.visc_pa, p.plate,
                       p.tongue, p.oversample)).encode())
    return h.hexdigest()[:16]


def dossier_cache():
    """Où `table_accord_timbre` garde ses tableaux : la variable
    d'environnement `BANC_RECHERCHE_CACHE`, sinon `research/.cache_banc/`
    (ignoré par git)."""
    d = os.environ.get('BANC_RECHERCHE_CACHE')
    return pathlib.Path(d) if d else (pathlib.Path(__file__).resolve()
                                      .parent.parent / '.cache_banc')


def table_accord_timbre(inst, cache=True, fils=None, rapport=None):
    """Tableau d'accord du timbre pour toutes les notes d'un instrument à anche
    libre : `{note: ndarray (chambre, largeur, Q)}` de `ln(facteur de
    fréquence de lame)`, à passer à `params_timbre(accord=exp(...))`.

    Mesuré sur le moteur (cf. `_tableau_note`), une note par fil : l'appel C
    rend le verrou de Python. Calculé une fois puis gardé dans
    `dossier_cache()`, sous une clé qui dépend des paramètres des notes et de
    la grille. Instrument sans anche libre : `{}`. `rapport`, s'il est donné
    (un dict), reçoit `ecart_max_cents`, `points_sans_mesure`, `secondes`,
    `depuis_cache`.
    """
    import time
    notes = sorted(n for n, p in inst._params.items()
                   if getattr(p, 'base_anche', None) is not None)
    if not notes:
        return {}
    cle = _cle_accord(inst, notes)
    fichier = dossier_cache() / ('accord_%s_%s.npz' % (inst.name, cle))
    if cache and fichier.exists():
        with np.load(fichier) as z:
            if list(z['notes']) == notes:
                if rapport is not None:
                    rapport.update(depuis_cache=True, ecart_max_cents=float(
                        z['ecart_max']), points_sans_mesure=int(z['perdus']))
                return {n: z['tab'][i] for i, n in enumerate(notes)}
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.perf_counter()

    def une(n):
        return _tableau_note(inst._params[n], inst.level_default,
                             midi_to_hz(n, inst.a4_hz), inst.samplerate)

    nfils = fils or min(16, os.cpu_count() or 1)
    with ThreadPoolExecutor(max_workers=nfils) as ex:
        res = list(ex.map(une, notes))
    tabs = np.array([r[0] for r in res])
    pire = max(r[1] for r in res)
    perdus = sum(r[2] for r in res)
    if cache:
        try:
            fichier.parent.mkdir(parents=True, exist_ok=True)
            np.savez(fichier, notes=np.array(notes), tab=tabs,
                     ecart_max=pire, perdus=perdus)
        except OSError:
            pass                      # pas de cache : on le recalculera
    if rapport is not None:
        rapport.update(depuis_cache=False, ecart_max_cents=float(pire),
                       points_sans_mesure=int(perdus),
                       secondes=time.perf_counter() - t0)
    return {n: tabs[i] for i, n in enumerate(notes)}


def _cc_de_facteur(nom, ln_facteur):
    """Inverse de `facteur_timbre`, sur le logarithme du facteur."""
    _, fmin, fmax, _ = TIMBRE_CC[nom]
    x = float(ln_facteur)
    if x <= 0.0:
        return 64.0 - 64.0 * x / float(np.log(fmin))
    return 64.0 + 63.0 * x / float(np.log(fmax))


def accord_pour(inst, note, ln_facteurs):
    """Facteur de fréquence de lame qui garde `note` à sa hauteur quand les
    réglages valent `ln_facteurs` (`{nom: ln du facteur}`, ceux de
    `Synth._tim_lisse`) : interpolation trilinéaire du tableau, dans l'espace
    des valeurs de CC. Tous les réglages à leur défaut : exactement 1.0."""
    if not inst.accord_timbre or all(ln_facteurs[nom] == 0.0
                                     for nom in ACCORD_NOMS):
        return 1.0
    n = int(np.clip(int(note), min(inst.accord_timbre),
                    max(inst.accord_timbre)))
    tab = inst.accord_timbre.get(n)
    if tab is None:
        n = min(inst.accord_timbre, key=lambda k: abs(k - n))
        tab = inst.accord_timbre[n]
    pos = []
    for nom in ACCORD_NOMS:
        g = ACCORD_GRILLE[nom]
        v = float(np.clip(_cc_de_facteur(nom, ln_facteurs[nom]), g[0], g[-1]))
        i = max(int(min(np.searchsorted(g, v, side='right') - 1,
                        len(g) - 2)), 0)
        pos.append((i, (v - g[i]) / (g[i + 1] - g[i])))
    total = 0.0
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                w = ((pos[0][1] if a else 1 - pos[0][1])
                     * (pos[1][1] if b else 1 - pos[1][1])
                     * (pos[2][1] if c else 1 - pos[2][1]))
                if w:
                    total += w * tab[pos[0][0] + a, pos[1][0] + b,
                                     pos[2][0] + c]
    return float(np.exp(total))


class Voice:
    """Une voix : un état C, une note, une nuance."""

    def __init__(self):
        self.state = _State()
        self.params = None
        self.base = None           # paramètres de la note, sans timbre
        self.note = -1
        self.level = 0.0
        self.target = 0.0
        self.active = False
        self.tenue = False         # touche enfoncée (le soufflet la nourrit)
        self.canal = 0             # canal MIDI, pour séparer les sommes
        self.appuis = 0            # appuis non relâchés sur (canal, note)
        self.age = 0

    def note_on(self, params, note, level, canal=0, timbre=None):
        engine_library().hv_reset(ctypes.byref(self.state))
        self.base = params
        self.params = params_timbre(params, **timbre) if timbre else params
        self.note = int(note)
        self.canal = int(canal)
        self.level = self.target = float(level)
        self.active = True
        self.tenue = True
        self.appuis = 1
        self.age = 0

    def note_off(self, tout=False):
        """Un relâchement. La soupape ne se ferme qu'au dernier appui
        (`tout=True` : sans compter, pour « toutes notes coupées »)."""
        self.appuis = 0 if tout else max(0, self.appuis - 1)
        if self.appuis > 0:
            return
        self.target = 0.0          # on coupe l'alimentation, pas le son
        self.tenue = False

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
        # une touche tenue reste vivante même soufflet à zéro : il peut repartir
        if self.target == 0.0 and abs(self.level) < 1e-9 and not self.tenue:
            crete = float(np.max(np.abs(out))) if out.size else 0.0
            if crete < silence:
                self.active = False
        return self.active


def _soufflet_par_defaut(instrument):
    """Un `Soufflet` pour l'anche libre, `None` pour le reste."""
    if instrument.control_unit != "m³/s":
        return None
    from .soufflet import Soufflet
    return Soufflet()


class Synth:
    """Moteur polyphonique. C'est l'objet que pilote la GUI.

    Sans dépendance audio ni MIDI : il rend des blocs quand on lui en demande.
    C'est ce qui le rend testable sans carte son — et ce qui permet de
    mesurer honnêtement s'il tient le temps réel.
    """

    def __init__(self, instrument: Instrument, polyphony=6, gain=0.5,
                 soufflet='auto', p_max=3000.0, timbre=None, pompe=0.0):
        self.inst = instrument
        self.voices = [Voice() for _ in range(int(polyphony))]
        self.gain = float(gain)
        self.expression = 1.0           # 0..1, molette ou contrôleur à vent
        # Avec un soufflet (`soufflet.Soufflet`), l'expression et le sens sont
        # le geste du bras : une pression commune à toutes les notes, bornée
        # par la main. Sans lui, le niveau fixe d'avant (vélocité × expression).
        # `'auto'` (défaut) : un soufflet pour une voix qui se commande en
        # débit derrière une résistance (anche libre, accordéon) ; aucun pour
        # les autres familles, qui se commandent en pression de bouche ou en
        # force d'archet. `None` : jamais de soufflet.
        if isinstance(soufflet, str) and soufflet == 'auto':
            soufflet = _soufflet_par_defaut(instrument)
        self.soufflet = soufflet
        self.sens = 1.0                 # +1 poussé, -1 tiré
        self.p_max = float(p_max)       # Pa, haut de la plage de jeu
        self.pression = 0.0             # Pa, dernière pression du soufflet
        # `True` : l'expression est déjà une pression mesurée (CC 11 d'un
        # fichier tiré d'un enregistrement) ; elle ne repasse pas par le bras
        # ni par le réservoir. Le jeu en direct reste à `False` : le CC est
        # alors un geste.
        self.pression_mesuree = False
        self._dt_soufflet = 1.0 / 2000.0
        self._reste_soufflet = 0.0
        self._scratch = None
        # −100 dBFS une fois l'échelle de sortie appliquée : inaudible, et
        # atteint en quelques dizaines de millisecondes au lieu d'une seconde.
        self._silence = 1e-5 / max(instrument.output_scale, 1e-12)
        # Réglages de timbre : cible et valeur lissée, en logarithme népérien
        # du facteur (0 = défaut).
        self._tim_cible = {k: 0.0 for k in TIMBRE_CC}
        self._tim_lisse = {k: 0.0 for k in TIMBRE_CC}
        for nom, valeur in (timbre or {}).items():
            self.regler_timbre(nom, valeur)
        # Débit déplacé par la lame : F, cible et valeur lissée (linéaire).
        self._pompe_cible = self._pompe_lisse = float(pompe)

    # -- timbre --------------------------------------------------------------
    def regler_timbre(self, nom, valeur_cc):
        """Fixe un réglage de timbre par sa valeur de CC (0 à 127, 64 = défaut).

        Le changement est **lissé** (constante de temps `TAU_TIMBRE_S`, appliquée
        bloc par bloc) et vaut pour les notes qui sonnent comme pour les
        suivantes. Sans voix active, il est pris tout de suite.

        Les valeurs par défaut des quatre grandeurs sont provisoires, non
        mesurées.

        **L'accord suit.** La fréquence propre de la lame est retouchée selon
        les réglages (`table_accord_timbre`, `accord_pour`) : la note garde sa
        hauteur, à ±1 cent de celle des réglages par défaut pour un CC seul ;
        une combinaison laisse un résidu mesuré (accordeon/cc_accord). Sans
        tableau (`accord_timbre=False`, instrument non accordé), la hauteur
        dérive comme avant.
        """
        if nom not in TIMBRE_CC:
            raise KeyError("réglage de timbre inconnu : %r (connus : %s)"
                           % (nom, ', '.join(TIMBRE_CC)))
        self._tim_cible[nom] = float(np.log(facteur_timbre(nom, valeur_cc)))
        if not any(v.active for v in self.voices):
            self._tim_lisse[nom] = self._tim_cible[nom]

    def regler_pompe(self, F):
        """Fixe F, le facteur du débit déplacé par la lame (`POMPE_CC`), lissé
        comme les réglages de timbre ; pris tout de suite sans voix active."""
        self._pompe_cible = float(F)
        if not any(v.active for v in self.voices):
            self._pompe_lisse = self._pompe_cible

    def timbre_cc(self, cc, valeur):
        """Un message CC : `True` s'il était un CC de timbre (`TIMBRE_CC`) ou
        le CC 74 de la pompe (`POMPE_CC`)."""
        if int(cc) == CC_POMPE:
            self.regler_pompe(facteur_pompe(valeur))
            return True
        nom = CC_TIMBRE.get(int(cc))
        if nom is None:
            return False
        self.regler_timbre(nom, valeur)
        return True

    def facteurs_timbre(self):
        """Facteurs multiplicatifs en cours (lissés), `{nom: facteur}`."""
        return {k: float(np.exp(x)) if x != 0.0 else 1.0
                for k, x in self._tim_lisse.items()}

    def _timbre_voix(self, note):
        """Les arguments de `params_timbre` d'une note : les quatre facteurs
        lissés, et l'accord de la lame qui garde la note à sa hauteur
        (`accord_pour`)."""
        t = self.facteurs_timbre()
        t['accord'] = accord_pour(self.inst, note, self._tim_lisse)
        t['pompe'] = self._pompe_lisse
        return t

    def _avancer_timbre(self, n):
        """Rapproche les réglages de leur cible de `n` échantillons ; si l'un
        a bougé, refait les paramètres des voix qui sonnent."""
        if (all(self._tim_lisse[k] == self._tim_cible[k] for k in TIMBRE_CC)
                and self._pompe_lisse == self._pompe_cible):
            return
        a = 1.0 - float(np.exp(-n / (self.inst.samplerate * TAU_TIMBRE_S)))
        c, x = self._pompe_cible, self._pompe_lisse
        x += (c - x) * a
        self._pompe_lisse = c if abs(c - x) < 1e-4 else x
        for k in TIMBRE_CC:
            c, x = self._tim_cible[k], self._tim_lisse[k]
            x += (c - x) * a
            self._tim_lisse[k] = c if abs(c - x) < 1e-4 else x
        for v in self.voices:
            if v.active and v.base is not None:
                v.params = params_timbre(v.base, **self._timbre_voix(v.note))

    # -- clavier -------------------------------------------------------------
    def note_on(self, note, velocity=100, canal=0):
        # Une anche par note et par voix : une note rejouée pendant qu'elle
        # tient garde sa soupape ouverte, on compte l'appui de plus. Son
        # relâchement (le off de l'ancienne note, qui peut tomber après ce
        # on) ne ferme alors pas la nouvelle ; la soupape ne se ferme qu'au
        # dernier relâchement.
        v = next((v for v in self.voices
                  if v.active and v.tenue and v.note == int(note)
                  and v.canal == int(canal)), None)
        if v is not None:
            v.appuis += 1
            return v
        v = next((v for v in self.voices if not v.active), None)
        if v is None:                    # toutes prises : on vole la plus vieille
            v = max(self.voices, key=lambda x: x.age)
        params = self.inst.params_for(note)
        if self.soufflet is not None:
            # la touche ne change pas la pression : ce levier appartient au
            # bras (these_parties_2_a_5_fr.md l. 1058)
            niveau = self._niveau_soufflet(params, self.pression)
        else:
            niveau = self.inst.level_default * self._nuance(velocity)
        v.note_on(params, note, niveau, canal=canal,
                  timbre=self._timbre_voix(note))
        return v

    def note_off(self, note, canal=None):
        """Relâche `note` ; `canal=None` : sur tous les canaux."""
        for v in self.voices:
            if (v.active and v.note == int(note)
                    and (canal is None or v.canal == int(canal))):
                v.note_off()

    def all_notes_off(self):
        for v in self.voices:
            v.note_off(tout=True)

    def _nuance(self, velocity):
        """Vélocité et expression → multiple du niveau nominal.

        Borné en bas à 0,45 : sous le seuil de démarrage, un modèle physique
        ne joue pas *doucement*, il **ne joue pas du tout**. Une vélocité
        faible qui ne produit aucun son passerait pour un bug alors que c'est
        la physique — autant garder l'instrument dans sa plage utile.
        """
        v = float(np.clip(velocity, 1, 127)) / 100.0
        return float(np.clip(0.45 + 0.75 * v * self.expression, 0.45, 1.8))

    # -- soufflet --------------------------------------------------------------
    def _niveau_soufflet(self, params, p):
        """Pression du soufflet → commande de la voix (cf. `soufflet.niveau_pour`).

        Une anche libre se commande en m³/s derrière la résistance `R` du
        passage : level = |p|/R = |p|·src_admit. Une source parfaite
        (src_admit nul) ne reçoit pas de pression : on le refuse.
        """
        unite = self.inst.control_unit
        if unite == "Pa":
            return abs(float(p))
        if unite == "m³/s":
            admit = float(params.src_admit)
            if admit <= 0.0:
                raise ValueError("source parfaite : pas de pression à recevoir")
            return abs(float(p)) * admit
        raise ValueError(f"commande en « {unite} » : pas une voix à soufflet")

    def _avancer_soufflet(self, n):
        """Le soufflet avance de `n` échantillons, au pas de 0,5 ms."""
        from .soufflet import pression_demandee
        self._reste_soufflet += n / self.inst.samplerate
        tenues = sum(1 for v in self.voices if v.active and v.tenue)
        p_dem = float(pression_demandee(self.expression, self.sens,
                                        self.p_max, self.soufflet.gamma))
        if self.pression_mesuree:
            self._reste_soufflet = 0.0
            self.pression = p_dem
            return
        while self._reste_soufflet >= self._dt_soufflet:
            self.pression, _, _ = self.soufflet.pas(
                p_dem, self._dt_soufflet, n_anches=tenues)
            self._reste_soufflet -= self._dt_soufflet

    # -- audio ---------------------------------------------------------------
    def _rendre_voix(self, n):
        """Avance le soufflet et les voix de `n` échantillons.

        Rend `[(voix, bloc brut float32), …]` : la sortie du moteur, avant
        gain, avant somme. Le bloc est à la voix, pas partagé.
        """
        self._avancer_timbre(n)
        if self.soufflet is not None:
            self._avancer_soufflet(n)
        blocs = []
        for v in self.voices:
            if not v.active:
                continue
            bloc = np.zeros(n, dtype=np.float32)
            if self.soufflet is not None and v.tenue:
                # le soufflet a déjà borné la pente : pas de glissé en plus
                v.target = self._niveau_soufflet(v.params, self.pression)
                v.render(bloc, glide=1.0, silence=self._silence)
            else:
                v.render(bloc, silence=self._silence)
            blocs.append((v, bloc))
        return blocs

    def render(self, n_frames):
        """Rend `n_frames` échantillons mono, en float32, normalisés au gain.

        Chaque voix sort le **rayonnement** (dérivée du débit net, cf.
        `embedded.SORTIE_RAYONNEE`) : sans composante continue, donc la somme
        d'un accord n'a pas de pression continue qui sature le limiteur.
        """
        n = int(n_frames)
        somme = np.zeros(n, dtype=np.float32)
        for _, bloc in self._rendre_voix(n):
            somme += bloc
        np.multiply(somme, self.gain * self.inst.output_scale, out=somme)
        return _limiteur(somme)

    def render_canaux(self, n_frames, limiteur=True):
        """Comme `render`, mais la somme des voix reste séparée par canal MIDI.

        Rend `{canal: tableau float32}`. Le soufflet, la pression et le gain
        sont communs ; le limiteur aussi, appliqué à la **somme de tous les
        canaux** : on lui prend le facteur de réduction par échantillon et on
        l'applique à chaque canal, donc la somme des canaux rendus vaut
        exactement ce que `render` aurait sorti. `limiteur=False` rend les
        canaux linéaires (pour mesurer la crête de la somme et choisir un gain).
        """
        n = int(n_frames)
        echelle = self.gain * self.inst.output_scale
        canaux = {}
        for v, bloc in self._rendre_voix(n):
            if v.canal not in canaux:
                canaux[v.canal] = np.zeros(n, dtype=np.float32)
            canaux[v.canal] += bloc
        total = np.zeros(n, dtype=np.float32)
        for x in canaux.values():
            x *= echelle
            total += x
        if limiteur:
            facteur = _facteur_limiteur(total)
            for x in canaux.values():
                x *= facteur
        return canaux

    @property
    def active_voices(self):
        return sum(1 for v in self.voices if v.active)


# =============================================================================
# Un fichier MIDI, hors temps réel
# =============================================================================

#: Contrôleurs MIDI qui tiennent le geste du bras : expression (11) et
#: contrôleur de souffle (2), comme `_jouer_midi`. La vélocité, elle, n'est
#: lue que sans soufflet (`Synth._nuance`) : avec soufflet, la touche ne change
#: pas la pression, elle ouvre seulement la soupape.
CC_EXPRESSION = (2, 11)


def lire_midi(chemin):
    """Les messages d'un fichier MIDI, triés : `[(seconde, message), …]`.

    `mido` est importé ici : le moteur et ses tests n'en ont pas besoin. Le
    temps est celui du fichier, tempo compris (`mido` itère en secondes).
    """
    import mido
    t = 0.0
    out = []
    for msg in mido.MidiFile(str(chemin)):
        t += msg.time
        if not msg.is_meta:
            out.append((t, msg))
    return out


def rendre_midi(chemin_mid, instrument, debut_s=None, fin_s=None,
                polyphonie=16, par_canal=True, gain=0.5, soufflet='auto',
                bloc=256, queue_s=1.5, sens=1.0, lo=None, hi=None,
                samplerate=48000.0, limiteur=True, cc='geste', timbre=None,
                pompe=0.0):
    """Joue un fichier MIDI sur le modèle, hors temps réel, et rend le son.

    - `instrument` : un `Instrument`, ou un nom (`'accordeon'`) : l'instrument
      est alors bâti sur l'étendue des notes du fichier (`lo`, `hi`).
    - notes et CC 2/11 arrivent au synthé **à l'échantillon près** : le rendu
      est coupé aux dates des messages, par blocs d'au plus `bloc` échantillons.
    - un seul `Synth` : un seul soufflet, une seule pression commune (le CC 11
      est celui du bras, quel que soit son canal), un seul gain, un seul
      limiteur. Seule la **somme des voix** est séparée par canal MIDI.
    - `par_canal=True` : `{canal: float32}` (un tableau par canal qui joue ;
      0 mélodie, 1 basses, 2 accords dans nos fichiers). `False` : un seul
      tableau, la somme.
    - `debut_s`, `fin_s` : fenêtre rendue. Le fichier est joué depuis le début
      (le soufflet, les notes tenues et les voix doivent être dans leur
      état), seul le son de la fenêtre est gardé. `queue_s` laisse les
      dernières notes s'éteindre quand `fin_s` dépasse le fichier.

    - `cc` : ce que le CC 11 (et 2) du fichier représente.
      `'geste'` (défaut, le jeu en direct) : le geste du bras, qui passe par
      le soufflet (passe-bas, pentes bornées, réservoir).
      `'pression'` : une pression déjà mesurée, par exemple le CC 11 de la
      chaîne audio vers MIDI. Ce niveau vient d'un enregistrement, donc d'un
      vrai soufflet ; la chaîne lui a déjà appliqué les bornes de la thèse
      (bande 8 Hz, pentes 120 / 190 dB/s). Le faire repasser par le bras les
      appliquerait deux fois et retarderait l'enveloppe de 45 ms. La pression
      commune vaut alors `soufflet.pression_demandee(expression)` sans bras
      ni réservoir. Les CC arrivent par pas de 10 ms : l'expression est
      interpolée linéairement entre deux messages consécutifs (au centre de
      chaque bloc, 5,3 ms au plus) pour éviter les marches ; au-delà de
      `GAP_CC_MAX_S` sans message, la valeur est tenue, pas rampée.
      Le soufflet reste celui du direct : rien n'est retiré, il n'est pas
      appliqué deux fois.

    La vélocité est transmise telle quelle à `Synth.note_on`.

    - `timbre` : valeurs de départ des réglages de timbre, `{nom: CC 0 à 127}`
      (noms et numéros de CC : `TIMBRE_CC`, 70 à 73 ; 64 = défaut). Le fichier
      peut les faire bouger ensuite par ses propres CC 70 à 73. **Les défauts
      de ces quatre grandeurs sont provisoires, non mesurés.**

    - `pompe` : F, facteur du débit déplacé par la lame (`POMPE_CC`), 0 par
      défaut (le son d'avant, à l'échantillon près). Le fichier peut le faire
      bouger par son CC 74 (64 = 0,8, **provisoire, non mesuré**).

    `limiteur=False` rend les canaux linéaires : pour mesurer la crête de la
    somme et en tirer un gain commun, jamais pour écouter.
    """
    evts = lire_midi(chemin_mid)
    notes = [m.note for _, m in evts if m.type == 'note_on']
    if isinstance(instrument, str):
        instrument = build_instrument(
            instrument,
            lo=int(lo if lo is not None else (min(notes) if notes else 45)),
            hi=int(hi if hi is not None else (max(notes) if notes else 84)),
            samplerate=samplerate)
    sr = float(instrument.samplerate)
    synth = Synth(instrument, polyphony=polyphonie, gain=gain,
                  soufflet=soufflet, timbre=timbre, pompe=pompe)
    synth.sens = float(sens)
    if cc not in ('geste', 'pression'):
        raise ValueError("cc : 'geste' ou 'pression', pas %r" % (cc,))
    interp = None
    if cc == 'pression' and synth.soufflet is not None:
        synth.pression_mesuree = True
        cc_evts = [(t, m.value / 127.0) for t, m in evts
                   if m.type == 'control_change' and m.control in CC_EXPRESSION]
        if cc_evts:
            interp = _expression_interpolee(cc_evts)

    duree = (evts[-1][0] if evts else 0.0) + float(queue_s)
    fin = duree if fin_s is None else float(fin_s)
    n_total = int(round(fin * sr))
    n_debut = int(round(max(0.0, float(debut_s or 0.0)) * sr))
    canaux = sorted({m.channel for _, m in evts if m.type == 'note_on'}) or [0]
    sortie = {c: np.zeros(n_total, dtype=np.float32) for c in canaux}

    dates = [int(round(t * sr)) for t, _ in evts]
    i_evt = 0
    pos = 0
    while pos < n_total:
        while i_evt < len(evts) and dates[i_evt] <= pos:
            _appliquer_midi(synth, evts[i_evt][1])
            i_evt += 1
        suivant = dates[i_evt] if i_evt < len(evts) else n_total
        n = max(1, min(int(bloc), suivant - pos, n_total - pos))
        if interp is not None:
            synth.expression = interp((pos + 0.5 * n) / sr)
        for c, x in synth.render_canaux(n, limiteur=limiteur).items():
            if c not in sortie:
                sortie[c] = np.zeros(n_total, dtype=np.float32)
            sortie[c][pos:pos + n] = x
        pos += n

    sortie = {c: x[n_debut:] for c, x in sortie.items()}
    if par_canal:
        return sortie
    return np.sum(list(sortie.values()), axis=0, dtype=np.float32)


#: Au-delà de cet écart entre deux CC, `rendre_midi(cc='pression')` tient la
#: valeur au lieu de la rampe (la chaîne émet un CC toutes les 10 ms).
GAP_CC_MAX_S = 0.05


def _expression_interpolee(cc_evts):
    """`[(t, expression)]` → fonction `t → expression`, linéaire entre deux
    messages écartés de `GAP_CC_MAX_S` au plus, constante sinon."""
    ts = np.array([t for t, _ in cc_evts], dtype=float)
    vs = np.array([v for _, v in cc_evts], dtype=float)

    def f(t):
        k = int(np.searchsorted(ts, t, side='right')) - 1
        if k < 0:
            return float(vs[0])
        if k + 1 >= len(ts) or ts[k + 1] - ts[k] > GAP_CC_MAX_S:
            return float(vs[k])
        a = (t - ts[k]) / (ts[k + 1] - ts[k])
        return float(vs[k] + a * (vs[k + 1] - vs[k]))
    return f


def _appliquer_midi(synth, msg):
    """Un message MIDI → le synthé. Même table que `_jouer_midi`."""
    if msg.type == 'note_on' and msg.velocity > 0:
        synth.note_on(msg.note, msg.velocity, canal=msg.channel)
    elif msg.type in ('note_off', 'note_on'):
        synth.note_off(msg.note, canal=msg.channel)
    elif msg.type == 'control_change':
        if msg.control in CC_EXPRESSION:
            synth.expression = msg.value / 127.0
        elif msg.control == 123:
            synth.all_notes_off()
        else:
            synth.timbre_cc(msg.control, msg.value)


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


class _Touches:
    """Lire les touches une par une, sans attendre la touche Entrée.

    Deux mondes, deux mécanismes : sous Unix on met le terminal en mode
    « cbreak » et on interroge l'entrée standard ; sous Windows c'est
    `msvcrt`, qui donne déjà les touches à l'unité. D'où cette petite façade
    plutôt qu'un `if sys.platform` semé dans la boucle de jeu.
    """

    def __enter__(self):
        self._windows = sys.platform == 'win32'
        if self._windows:
            import msvcrt
            self._msvcrt = msvcrt
        else:
            import termios
            import tty
            self._termios = termios
            self._fd = sys.stdin.fileno()
            self._avant = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, *e):
        if not self._windows:
            self._termios.tcsetattr(self._fd, self._termios.TCSADRAIN,
                                    self._avant)
        return False

    def lire(self, delai=0.05):
        """Une touche, ou None si rien n'est venu pendant `delai`."""
        if self._windows:
            import time
            fin = time.monotonic() + delai
            while time.monotonic() < fin:
                if self._msvcrt.kbhit():
                    ch = self._msvcrt.getwch()
                    if ch in ('\x00', '\xe0'):   # touche spéciale : 2 octets
                        self._msvcrt.getwch()
                        return None
                    return ch
                time.sleep(0.005)
            return None
        import select
        if select.select([sys.stdin], [], [], delai)[0]:
            return sys.stdin.read(1)
        return None


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

    Linux, macOS et Windows — la lecture des touches passe par `_Touches`,
    qui sait dans quel monde elle est. La disposition du clavier, elle, est
    l'affaire du système : on reçoit le caractère, pas la position.
    """
    import time

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

    try:
        with _Touches() as clavier:
            while True:
                ch = clavier.lire(0.05)
                if ch is not None:
                    if ch in ('q', '\x1b', '\x03'):
                        break
                    if ch == '0':
                        synth.all_notes_off(); vues.clear(); continue
                    if ch in '12':
                        octave = int(np.clip(octave + (1 if ch == '2' else -1),
                                             0, 9))
                        ecrire(f"  octave {octave}")
                        continue
                    if ch in '34':
                        pas = 0.1 if ch == '4' else -0.1
                        synth.expression = float(
                            np.clip(synth.expression + pas, 0.05, 1.0))
                        ecrire(f"  nuance {100 * synth.expression:.0f} %")
                        continue
                    if ch in touches:
                        note = 12 * octave + touches[ch]
                        if note not in vues:
                            synth.note_on(note, 100)
                        vues[note] = time.monotonic()

                maintenant = time.monotonic()
                for note, vu in list(vues.items()):
                    if maintenant - vu > tenue:   # plus de répétition : on lâche
                        synth.note_off(note)
                        del vues[note]
    except KeyboardInterrupt:
        pass
    finally:
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
    p.add_argument('--midi-fichier', metavar='FICHIER.mid',
                   help="jouer ce fichier MIDI hors temps réel, vers --wav "
                        "(notes et CC 11, à l'échantillon près)")
    p.add_argument('--debut', type=float, default=None,
                   help="--midi-fichier : début de la fenêtre rendue, en s")
    p.add_argument('--fin', type=float, default=None,
                   help="--midi-fichier : fin de la fenêtre rendue, en s")
    p.add_argument('--par-canal', action='store_true',
                   help="--midi-fichier : un WAV par canal MIDI "
                        "(FICHIER_canalN.wav), un seul gain commun")
    p.add_argument('--cc-pression', action='store_true',
                   help="--midi-fichier : le CC 11 est une pression déjà "
                        "mesurée (chaîne audio vers MIDI), pas un geste : "
                        "sans bras ni réservoir")
    p.add_argument('--sans-soufflet', action='store_true',
                   help="pas de soufflet : niveau fixe, vélocité × expression")
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
    p.add_argument('--perce', metavar='FICHIER.dat',
                   help="jouer une VRAIE perce TUTT, par ses doigtés : la "
                        "géométrie ne bouge pas, ce sont les doigts qui "
                        "changent la note. La justesse n'est pas corrigée.")
    p.add_argument('--cavite-cm3', type=float, default=None,
                   help="volume de cavité d'anche (corrige l'octave d'un cône "
                        "tronqué ; cf. tutt.cavite_qui_accorde_l_octave)")
    for nom, (cc_n, fmin, fmax, grandeur) in TIMBRE_CC.items():
        p.add_argument('--cc-' + nom, type=int, default=64, metavar='0-127',
                       help=f"CC {cc_n} : {grandeur}, de x{fmin:g} (0) à "
                            f"x{fmax:g} (127), 64 = défaut (provisoire, non "
                            f"mesuré)")
    p.add_argument('--pompe', type=float, default=0.0, metavar='F',
                   help=f"CC {CC_POMPE} : facteur F du débit déplacé par la "
                        f"lame (S_eff = F x largeur x longueur), 0 = sans "
                        f"(défaut) ; CC 64 = 0,8 (provisoire, non mesuré)")
    args = p.parse_args(argv)
    timbre = {nom: getattr(args, 'cc_' + nom) for nom in TIMBRE_CC}

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

    if args.perce:
        from . import tutt as _tutt
        print(f"lecture de « {args.perce} »…", file=sys.stderr)
        dat = _tutt.read_dat(args.perce)
        print(f"  {dat}", file=sys.stderr)
        inst = build_instrument_from_bore(
            dat, famille=args.instrument, samplerate=args.sr, a4_hz=args.la,
            reed_volume_m3=(args.cavite_cm3 * 1e-6 if args.cavite_cm3 else None))
        print(f"  {len(inst.fingerings)} doigté(s) — la justesse est celle de "
              f"la perce, elle n'est pas corrigée :", file=sys.stderr)
        for nom, _trous, f_hz, note in inst.fingerings:
            ecart = 1200 * np.log2(f_hz / midi_to_hz(note, args.la))
            print(f"    {nom:<8} {f_hz:8.2f} Hz   touche {note:3d}   "
                  f"{ecart:+7.1f} cents", file=sys.stderr)
    else:
        print(f"préparation de « {args.instrument} » : une perce par demi-ton"
              + ("" if args.brut else ", puis accordage note à note") + "…",
              file=sys.stderr)
        inst = build_instrument(args.instrument, lo=args.grave, hi=args.aigu,
                                samplerate=args.sr, a4_hz=args.la,
                                tune=not args.brut)
    synth = Synth(inst, polyphony=args.polyphonie, gain=args.gain,
                  soufflet=None if args.sans_soufflet else 'auto', timbre=timbre,
                  pompe=args.pompe)

    if args.midi_fichier:
        if not args.wav:
            print("--midi-fichier demande --wav FICHIER.wav", file=sys.stderr)
            return 2
        canaux = rendre_midi(args.midi_fichier, inst, debut_s=args.debut,
                             fin_s=args.fin, polyphonie=args.polyphonie,
                             gain=args.gain, par_canal=True,
                             soufflet=None if args.sans_soufflet else 'auto',
                             cc='pression' if args.cc_pression else 'geste',
                             timbre=timbre, pompe=args.pompe)
        mix = np.sum(list(canaux.values()), axis=0)
        _ecrire_wav(args.wav, mix, inst.samplerate)
        print(f"→ {args.wav}  ({len(mix) / inst.samplerate:.1f} s, canaux "
              f"{sorted(canaux)} sommés)")
        if args.par_canal:
            base = pathlib.Path(args.wav)
            for c, x in sorted(canaux.items()):
                f = base.with_name(f"{base.stem}_canal{c}{base.suffix}")
                _ecrire_wav(f, x, inst.samplerate)
                print(f"→ {f}")
        return 0

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
            else:
                synth.timbre_cc(msg.control, msg.value)

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
