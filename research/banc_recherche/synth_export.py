"""Export d'un `SampleModel` vers une cible embarquée (STM32 / Dream SAM5716).

Trois formats, parce que trois architectures possibles — voir
`docs/sample_vers_modele_physique.md` :

1. **JSON** (`to_json`) — la référence lisible et versionnable. C'est le
   format pivot : tout le reste en dérive.
2. **En-tête C** (`to_c_header`) — tables `const` pour un modèle qui tourne
   **sur le STM32** : coefficients de biquads du résonateur, niveaux et
   enveloppes des partiels, loi de dynamique. Flottant ou **Q15** (les DSP
   audio embarqués travaillent souvent en virgule fixe).
3. **Wavetable** (`to_wavetable`) — un cycle représentatif + enveloppes, pour
   l'approche sampleur/wavetable, la seule qui parle nativement à un moteur
   type Dream sans firmware DSP custom.

**Ce que ce module ne fait pas** : il n'écrit aucun message SysEx ni registre
propriétaire Dream. L'API du firmware SAM5716 relève de la documentation
constructeur (probablement sous NDA) ; inventer des adresses de registres
donnerait du code qui a l'air juste et qui ne marche pas. Le point d'extension
est `DreamAdapter` : une classe volontairement vide, à remplir avec la doc en
main.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


# ==============================================================================
# Biquads (résonateur)
# ==============================================================================

def biquad_peaking(freq_hz, q, gain_db, samplerate):
    """Coefficients d'un biquad **peaking EQ** (formules RBJ), normalisés a0=1.

    C'est la brique du résonateur : chaque pic de résonance mesuré sur le
    sample (`sample_extract.resonator_peaks`) devient un biquad.

    Renvoie `{b0, b1, b2, a1, a2}` (forme directe I/II, `y = b0·x + b1·x₁ +
    b2·x₂ − a1·y₁ − a2·y₂`).
    """
    a_gain = 10 ** (float(gain_db) / 40.0)
    w0 = 2 * np.pi * float(freq_hz) / float(samplerate)
    alpha = np.sin(w0) / (2 * max(float(q), 1e-6))
    cos_w0 = np.cos(w0)

    b0 = 1 + alpha * a_gain
    b1 = -2 * cos_w0
    b2 = 1 - alpha * a_gain
    a0 = 1 + alpha / a_gain
    a1 = -2 * cos_w0
    a2 = 1 - alpha / a_gain

    return dict(b0=float(b0 / a0), b1=float(b1 / a0), b2=float(b2 / a0),
                a1=float(a1 / a0), a2=float(a2 / a0))


def resonator_biquads(model, samplerate=None):
    """Tous les biquads du résonateur d'un `SampleModel`."""
    sr = samplerate or model.samplerate
    return [biquad_peaking(r['freq_hz'], r['q'], r['gain_db'], sr)
            for r in model.resonators]


def to_q15(x):
    """Conversion en Q15 (entier 16 bits signé, 1.0 -> 32767), avec saturation.

    Les coefficients de biquads dépassent souvent ±1 : diviser par 2 (Q14) ou
    utiliser Q2.13 selon le DSP cible. On sature ici au lieu de boucler
    silencieusement — une saturation s'entend, un débordement explose.
    """
    return int(np.clip(round(float(x) * 32767), -32768, 32767))


# ==============================================================================
# Export JSON (format pivot)
# ==============================================================================

def to_json(model, path=None, indent=2):
    """Sérialise le modèle. Écrit dans `path` si fourni ; renvoie la chaîne."""
    data = model.to_dict()
    data['_format'] = 'banc_recherche.sample_model/1'
    text = json.dumps(data, indent=indent, ensure_ascii=False, allow_nan=True)
    if path:
        Path(path).write_text(text, encoding='utf-8')
    return text


# ==============================================================================
# Export en-tête C (modèle tournant sur STM32)
# ==============================================================================

def _c_ident(name):
    """Identifiant C valide, dérivé d'un nom quelconque."""
    out = ''.join(c if c.isalnum() else '_' for c in (name or 'voice'))
    if not out or out[0].isdigit():
        out = 'v_' + out
    return out.lower()


def to_c_header(model, path=None, fixed_point=False, guard=None):
    """Génère un en-tête C avec les tables `const` du modèle.

    `fixed_point=True` émet les coefficients en **Q15** (`int16_t`) en plus du
    flottant — pour un DSP en virgule fixe. Les deux sont émis : le code cible
    choisit, rien n'est perdu.

    Renvoie le texte de l'en-tête ; l'écrit dans `path` si fourni.
    """
    ident = _c_ident(model.name)
    guard = guard or f"{ident.upper()}_MODEL_H"
    biquads = resonator_biquads(model)

    L = []
    L.append("/* Généré par banc_recherche.synth_export — NE PAS ÉDITER À LA MAIN.")
    L.append(" *")
    L.append(f" * Source : sample « {model.name} »")
    L.append(f" * f0 = {_f(model.f0_hz)} Hz · {model.samplerate} Hz · {model.duration_s:.2f} s")
    L.append(" *")
    L.append(" * Modèle source -> résonateur :")
    L.append(" *   - excitation : pente spectrale + part de bruit")
    L.append(" *   - résonateur : banc de biquads peaking (corps de l'instrument)")
    L.append(" *   - partiels   : niveaux + enveloppes en points de rupture")
    L.append(" */")
    L.append(f"#ifndef {guard}")
    L.append(f"#define {guard}")
    L.append("")
    L.append("#include <stdint.h>")
    L.append("")

    # -- constantes de base
    L.append(f"#define {ident.upper()}_SAMPLERATE   {model.samplerate}")
    L.append(f"#define {ident.upper()}_F0_HZ        {_f(model.f0_hz)}f")
    L.append(f"#define {ident.upper()}_N_PARTIALS   {len(model.partial_levels_db)}")
    L.append(f"#define {ident.upper()}_N_BIQUADS    {len(biquads)}")
    L.append(f"#define {ident.upper()}_VIB_RATE_HZ  {_f(model.vibrato_rate_hz)}f")
    L.append(f"#define {ident.upper()}_VIB_DEPTH_CT {_f(model.vibrato_depth_cents)}f")
    L.append(f"#define {ident.upper()}_SRC_SLOPE    {_f(model.source_slope_db_per_oct)}f  /* dB/octave de rang */")
    L.append(f"#define {ident.upper()}_BRIGHT_SLOPE {_f(model.brightness_slope_hz_per_db)}f  /* Hz de centroide par dB */")
    L.append(f"#define {ident.upper()}_NOISE_PCT    {_f(model.percussive_pct)}f")
    L.append("")

    # -- biquads du résonateur
    L.append("/* Résonateur : biquads peaking, a0 normalisé.")
    L.append(" * y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2] */")
    L.append("typedef struct { float b0, b1, b2, a1, a2; } biquad_f32_t;")
    L.append(f"static const biquad_f32_t {ident}_resonator[{max(len(biquads), 1)}] = {{")
    if biquads:
        for bq, r in zip(biquads, model.resonators):
            L.append(f"    {{ {bq['b0']:+.8f}f, {bq['b1']:+.8f}f, {bq['b2']:+.8f}f, "
                     f"{bq['a1']:+.8f}f, {bq['a2']:+.8f}f }},"
                     f"  /* {r['freq_hz']:.0f} Hz, Q={r['q']:.1f}, {r['gain_db']:+.1f} dB */")
    else:
        L.append("    { 1.0f, 0.0f, 0.0f, 0.0f, 0.0f },  /* aucun pic détecté : passe-tout */")
    L.append("};")
    L.append("")

    if fixed_point:
        L.append("/* Mêmes coefficients en Q15 (int16). Attention : |coef| > 1 sature —")
        L.append(" * prévoir un décalage (Q14/Q2.13) côté DSP selon la plage réelle. */")
        L.append("typedef struct { int16_t b0, b1, b2, a1, a2; } biquad_q15_t;")
        L.append(f"static const biquad_q15_t {ident}_resonator_q15[{max(len(biquads), 1)}] = {{")
        if biquads:
            for bq in biquads:
                L.append("    { " + ", ".join(f"{to_q15(bq[k]):6d}" for k in
                                              ('b0', 'b1', 'b2', 'a1', 'a2')) + " },")
        else:
            L.append("    { 32767, 0, 0, 0, 0 },")
        L.append("};")
        L.append("")

    # -- partiels
    L.append("/* Niveau moyen de chaque partiel, en dB relatifs au fondamental. */")
    L.append(f"static const float {ident}_partial_db[{max(len(model.partial_levels_db), 1)}] = {{")
    L.append("    " + ", ".join(f"{_f(v)}f" for v in model.partial_levels_db) or "    0.0f")
    L.append("};")
    L.append("")

    L.append("/* Instant (s) où chaque partiel atteint 90 % de son maximum :")
    L.append(" * l'étalement de l'attaque, ce qu'un sampleur fige et qu'un modèle rejoue. */")
    L.append(f"static const float {ident}_partial_attack_s[{max(len(model.partial_attack_s), 1)}] = {{")
    L.append("    " + ", ".join(f"{_f(v)}f" for v in model.partial_attack_s) or "    0.0f")
    L.append("};")
    L.append("")

    # -- enveloppe globale en points de rupture
    env = model.amplitude_envelope
    L.append("/* Enveloppe d'amplitude en points de rupture (t en s, amplitude 0..1). */")
    L.append("typedef struct { float t; float v; } breakpoint_t;")
    L.append(f"#define {ident.upper()}_N_ENV {max(len(env), 1)}")
    L.append(f"static const breakpoint_t {ident}_envelope[{max(len(env), 1)}] = {{")
    if env:
        for t, v in env:
            L.append(f"    {{ {t:.6f}f, {v:.6f}f }},")
    else:
        L.append("    { 0.0f, 0.0f },")
    L.append("};")
    L.append("")

    L.append(f"#endif /* {guard} */")

    text = "\n".join(L) + "\n"
    if path:
        Path(path).write_text(text, encoding='utf-8')
    return text


def _f(x):
    """Formate un flottant pour du C, en neutralisant nan/inf."""
    v = float(x)
    if not np.isfinite(v):
        return "0.0"
    return f"{v:.6f}"


# ==============================================================================
# Export wavetable (approche sampleur / moteur Dream natif)
# ==============================================================================

def to_wavetable(model, table_size=256):
    """Synthétise **un cycle** à partir des niveaux de partiels mesurés.

    Pour un moteur wavetable (ce que sait faire nativement une puce type
    Dream), c'est la voie directe : un cycle par « couleur » de timbre, que le
    moteur boucle et enveloppe. On reconstruit le cycle par somme des partiels
    à leurs niveaux relatifs mesurés (phases nulles : le timbre perçu d'un son
    tenu dépend peu des phases).

    Renvoie un tableau float32 de `table_size` échantillons, normalisé ±1.
    """
    n = int(table_size)
    phase = np.arange(n) / n * 2 * np.pi
    wave = np.zeros(n)
    for k, level_db in enumerate(model.partial_levels_db, start=1):
        if not np.isfinite(level_db) or level_db < -80:
            continue
        wave += (10 ** (level_db / 20.0)) * np.sin(k * phase)
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave /= peak
    return wave.astype('float32')


# ==============================================================================
# Resynthèse — le contrôle de cohérence du modèle
# ==============================================================================

def _envelope_at(breakpoints, t):
    """Évalue une enveloppe en points de rupture sur une grille temporelle."""
    if not breakpoints:
        return np.zeros_like(t)
    bt = np.array([p[0] for p in breakpoints], dtype='float64')
    bv = np.array([p[1] for p in breakpoints], dtype='float64')
    return np.interp(t, bt, bv)


def resynthesize(model, duration_s=None, samplerate=None, mode='additive',
                 noise=True, seed=0):
    """Reconstruit un signal **depuis le modèle** — pour vérifier l'extraction.

    C'est le contrôle honnête : si les paramètres extraits décrivent vraiment
    le son, une resynthèse doit y ressembler. Deux modes, qui ne testent pas
    la même chose :

    - `'additive'` : rejoue chaque partiel avec son enveloppe mesurée. Les
      niveaux des partiels **contiennent déjà** l'effet du résonateur (ils ont
      été mesurés en sortie), donc on ne réapplique **pas** les biquads —
      sinon on filtrerait deux fois. Valide l'extraction des partiels.

    - `'source_filter'` : fabrique une source à la pente spectrale mesurée,
      puis la passe dans le banc de biquads du résonateur. Valide la
      **séparation source / résonateur** — c'est le vrai test du modèle
      physique, et le plus sévère.

    Renvoie un tableau float64 normalisé à ±1.
    """
    sr = int(samplerate or model.samplerate)
    dur = float(duration_s or model.duration_s or 1.0)
    n = max(1, int(dur * sr))
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)

    f0 = model.f0_hz
    if not np.isfinite(f0) or f0 <= 0:
        return np.zeros(n)

    # hauteur instantanée : vibrato mesuré (cents -> facteur multiplicatif)
    if np.isfinite(model.vibrato_rate_hz) and model.vibrato_depth_cents > 0:
        dev = (model.vibrato_depth_cents / 1200.0) * np.sin(
            2 * np.pi * model.vibrato_rate_hz * t)
        f_inst = f0 * (2.0 ** dev)
    else:
        f_inst = np.full(n, f0)
    phase = 2 * np.pi * np.cumsum(f_inst) / sr

    if mode == 'additive':
        y = np.zeros(n)
        for k, bps in enumerate(model.partial_envelopes, start=1):
            if k * f0 >= sr / 2:
                break
            env = _envelope_at(bps, t)
            y += env * np.sin(k * phase + rng.uniform(0, 2 * np.pi))

    elif mode == 'source_filter':
        from scipy import signal as _sig
        # source : partiels à la pente spectrale mesurée (amplitude ∝ n^(slope/6))
        slope = model.source_slope_db_per_oct
        slope = slope if np.isfinite(slope) else -6.0
        src = np.zeros(n)
        k = 1
        while k * f0 < sr / 2:
            amp = 10 ** ((slope * np.log2(k)) / 20.0)
            src += amp * np.sin(k * phase + rng.uniform(0, 2 * np.pi))
            k += 1
        # résonateur : le corps de l'instrument
        y = src
        for bq in resonator_biquads(model, sr):
            y = _sig.lfilter([bq['b0'], bq['b1'], bq['b2']],
                             [1.0, bq['a1'], bq['a2']], y)
        # enveloppe globale mesurée
        y = y * _envelope_at(model.amplitude_envelope, t)

    else:
        raise ValueError("mode doit être 'additive' ou 'source_filter'")

    # part de bruit mesurée (souffle, frottement) — en proportion d'énergie
    if noise and np.isfinite(model.percussive_pct) and model.percussive_pct > 0:
        rms = np.sqrt(np.mean(y ** 2)) or 1.0
        frac = np.sqrt(min(model.percussive_pct, 50.0) / 100.0)
        nz = rng.standard_normal(n) * rms * frac
        nz *= _envelope_at(model.amplitude_envelope, t) / (
            np.max(_envelope_at(model.amplitude_envelope, t)) or 1.0)
        y = y + nz

    peak = np.max(np.abs(y))
    return y / peak if peak > 0 else y


def spectral_distance_db(a, b, samplerate, n_fft=4096):
    """Distance log-spectrale moyenne (dB) entre deux signaux.

    Mesure de cohérence : 0 dB = spectres moyens identiques. Compare les
    **spectres moyens**, pas les formes d'onde — deux sons peuvent être
    perceptivement identiques avec des phases différentes.
    """
    from . import timbre
    Sa, fa, _ = timbre.stft_mag(np.asarray(a, dtype='float64'), samplerate, n_fft=n_fft)
    Sb, fb, _ = timbre.stft_mag(np.asarray(b, dtype='float64'), samplerate, n_fft=n_fft)
    ma, mb = Sa.mean(axis=1), Sb.mean(axis=1)
    ref_a, ref_b = ma.max() or 1.0, mb.max() or 1.0
    la = 20 * np.log10(np.maximum(ma / ref_a, 1e-6))
    lb = 20 * np.log10(np.maximum(mb / ref_b, 1e-6))
    band = fa < samplerate / 2 * 0.9
    return float(np.mean(np.abs(la[band] - lb[band])))


def wavetable_to_c(wave, name="voice", path=None, fixed_point=True):
    """Émet une wavetable en tableau C (`int16_t` Q15 par défaut)."""
    ident = _c_ident(name)
    L = ["/* Wavetable générée par banc_recherche.synth_export. */",
         "#include <stdint.h>", ""]
    if fixed_point:
        vals = [to_q15(v) for v in wave]
        L.append(f"static const int16_t {ident}_wavetable[{len(vals)}] = {{")
    else:
        vals = [f"{float(v):+.8f}f" for v in wave]
        L.append(f"static const float {ident}_wavetable[{len(vals)}] = {{")
    for i in range(0, len(vals), 8):
        L.append("    " + ", ".join(str(v) for v in vals[i:i + 8]) + ",")
    L.append("};")
    text = "\n".join(L) + "\n"
    if path:
        Path(path).write_text(text, encoding='utf-8')
    return text


# ==============================================================================
# Point d'extension constructeur
# ==============================================================================

class DreamAdapter:
    """Adaptateur vers le firmware Dream SAM5716 — **délibérément non
    implémenté**.

    Le protocole de configuration d'un SAM5716 (messages SysEx propriétaires,
    format de banque en Flash SPI, API du firmware) n'est pas public : il
    vient de la documentation Dream, généralement sous accord de
    confidentialité. Écrire ici des adresses de registres « plausibles »
    produirait du code qui compile, qui a l'air correct, et qui ne pilote
    rien — le pire des deux mondes.

    À remplir avec la doc en main. Ce dont tu auras besoin est déjà calculé :

    - `resonator_biquads(model)` → coefficients du banc de filtres ;
    - `to_wavetable(model)` → un cycle, si le moteur est wavetable ;
    - `model.partial_levels_db` / `partial_attack_s` → mise en forme des
      partiels et étalement de l'attaque ;
    - `model.brightness_slope_hz_per_db` → loi de commande du contrôleur
      continu (souffle, expression, pression de soufflet).

    Question à trancher en premier avec la doc : le 5716 expose-t-il un moteur
    de filtrage programmable par voie, ou seulement un sampleur + effets ? La
    réponse décide entre le modèle-sur-STM32 et l'approche wavetable.
    """

    def __init__(self, model):
        self.model = model

    def to_sysex(self):
        raise NotImplementedError(
            "Protocole SysEx Dream non public : voir la documentation "
            "constructeur du SAM5716, puis implémenter ici. "
            "En attendant : to_c_header() (modèle sur STM32) ou "
            "to_wavetable() (moteur sampleur).")
