#!/usr/bin/env python
"""Carte du clavier de l'accordéon selon la pression (mesure, rien n'est corrigé).

Pour chaque note 36..96 de l'instrument `accordeon` (loi traversante, défaut
d'origin/main), on pilote une `Voice` directement : `note_on`, puis `render`
par blocs de 256, `glide=1.0`, `level = p x src_admit` (m3/s), sortie 48 kHz.

  a. grille à pression fixe, posée d'un coup, 3 s (9 pressions) ;
  b. rampe lente 0 -> 3000 Pa en 10 s, puis retour en 10 s.

Sorties : carte.json, carte.txt, rampe.txt, 3 images, muets/*.wav.
Usage : python carte_clavier_pression.py [--sortie DOSSIER] [--lo 36] [--hi 96]
        [--notes 60,72] [--sans-figures]
numpy seul + le moteur ; matplotlib importé à la demande.
"""
import argparse
import json
import pathlib
import sys
import time
import wave

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

SR = 48000
BLOC = 256
PRESSIONS = [100, 150, 200, 300, 500, 700, 1000, 1500, 2500]
DUREE = 3.0
BANDE = (100, 1000)
SORTIE_DEFAUT = 'J:/claude/tmp/modele_instruments/accordeon/clavier_pression'

#: Seuil absolu « le son existe » (dB re l'échelle brute). Mesuré à l'essai : une note
#: qui joue est à -56 dB ou plus ; le choc de la pose d'un coup (échelon) vaut -43 à -90 dB
#: dans les 100 premières ms puis retombe sous -100 dB. Le seuil s'applique donc aux
#: fenêtres de 0,2 s à 3 s ; le premier dixième de seconde (choc) est écarté.
SEUIL_DB = -85.0


def f_de(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


def _db(x):
    return 20.0 * np.log10(max(float(x), 1e-30))


def _rms(x):
    x = np.asarray(x, float)
    return float(np.sqrt(np.mean((x - x.mean()) ** 2))) if x.size else 0.0


# --------------------------------------------------------------------------
# rendu
# --------------------------------------------------------------------------
def rendre(live, params, note, niveaux):
    """`niveaux` : un niveau (m3/s) par bloc de BLOC échantillons."""
    v = live.Voice()
    v.note_on(params, note, float(niveaux[0]))
    out = np.empty(len(niveaux) * BLOC, np.float32)
    bloc = np.zeros(BLOC, np.float32)
    for i, niv in enumerate(niveaux):
        v.target = float(niv)
        bloc[:] = 0.0
        v.render(bloc, glide=1.0, silence=0.0)
        out[i * BLOC:(i + 1) * BLOC] = bloc
    return out.astype(float)


# --------------------------------------------------------------------------
# mesures
# --------------------------------------------------------------------------
def f0_fft(x, f_nom, fenetre_cents=600.0):
    """Pic FFT (Hann, bourrage, interpolation parabolique sur log-module),
    affiné par les partiels 2 à 4 (pic voisin de k f / k)."""
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    nfft = 1 << 19
    w = np.hanning(n)
    a = np.abs(np.fft.rfft(x * w, nfft))
    df = SR / nfft

    def pic(f_c, cents):
        lo = f_c * 2 ** (-cents / 1200.0)
        hi = f_c * 2 ** (cents / 1200.0)
        i0, i1 = int(lo / df), int(hi / df) + 1
        i1 = min(i1, len(a) - 2)
        if i1 <= i0 + 2:
            return None, 0.0
        k = i0 + int(np.argmax(a[i0:i1]))
        if k < 1 or k >= len(a) - 1:
            return None, 0.0
        l0, l1, l2 = np.log(a[k - 1] + 1e-30), np.log(a[k] + 1e-30), np.log(a[k + 1] + 1e-30)
        den = l0 - 2 * l1 + l2
        d = 0.5 * (l0 - l2) / den if den != 0 else 0.0
        return (k + d) * df, a[k]

    f1, a1 = pic(f_nom, fenetre_cents)
    if f1 is None:
        return None
    est, poids = [f1], [a1]
    for k in (2, 3, 4):
        fk, ak = pic(k * f1, 40.0)
        if fk is not None and ak > 0.05 * a1:
            est.append(fk / k)
            poids.append(ak)
    return float(np.average(est, weights=poids))


def f0_croisements(x, f_est):
    """Autre méthode : passe-bas FFT (1,5 f0), puis passages montants par zéro
    interpolés, f = (N-1)/(t_dernier - t_premier)."""
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1.0 / SR)
    X[fr > 1.5 * f_est] = 0.0
    X[fr < 0.5 * f_est] = 0.0
    y = np.fft.irfft(X, n)
    s = np.nonzero((y[:-1] < 0) & (y[1:] >= 0))[0]
    if len(s) < 3:
        return None
    t = s + (-y[s]) / (y[s + 1] - y[s])
    return float((len(t) - 1) * SR / (t[-1] - t[0]))


def f0_autocorr(x, f_est):
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    nf = 1 << int(np.ceil(np.log2(2 * n)))
    F = np.fft.rfft(x, nf)
    r = np.fft.irfft(np.abs(F) ** 2, nf)[:n]
    lag0 = SR / f_est
    a, b = int(lag0 * 0.9), int(lag0 * 1.1) + 1
    k = a + int(np.argmax(r[a:b]))
    if k < 1 or k >= n - 1:
        return None
    y0, y1, y2 = r[k - 1], r[k], r[k + 1]
    d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return float(SR / (k + d))


def partiels(x, f0, n=8):
    """Niveaux des partiels 1..n en dB re partiel 1 (pic du spectre autour de k f0)."""
    x = np.asarray(x, float) - np.mean(x)
    nfft = 1 << 18
    a = np.abs(np.fft.rfft(x * np.hanning(len(x)), nfft))
    df = SR / nfft
    out = []
    for k in range(1, n + 1):
        fk = k * f0
        if fk >= SR / 2 - 100:
            out.append(None)
            continue
        i0 = int(fk * 2 ** (-25 / 1200.0) / df)
        i1 = int(fk * 2 ** (25 / 1200.0) / df) + 1
        out.append(float(a[i0:i1].max()))
    if not out or out[0] is None or out[0] <= 0:
        return [None] * n
    return [None if v is None else _db(v / out[0]) for v in out]


def analyser_case(x, f_nom):
    """Mesures d'une case (signal de 3 s)."""
    pas = SR // 10
    n10 = len(x) // pas
    niv10 = [_db(_rms(x[i * pas:(i + 1) * pas])) for i in range(n10)]
    fin = x[-SR:]
    l_fin = _db(_rms(fin))
    l_max = max(niv10)
    # stabilité sur la dernière seconde
    niv_fin = niv10[-10:]
    var_db = max(niv_fin) - min(niv_fin)
    res = {'niveau_10': niv10, 'niveau_fin_db': l_fin, 'niveau_max_db': l_max,
           'variation_fin_db': var_db}
    # temps d'établissement : 90 % du niveau final (amplitude), fenêtres de 10 ms
    p10 = SR // 100
    env = np.array([_rms(x[i * p10:(i + 1) * p10]) for i in range(len(x) // p10)])
    fin_lin = 10 ** (l_fin / 20.0)
    idx = np.nonzero(env >= 0.9 * fin_lin)[0]
    res['t_etab_s'] = float(idx[0] * 0.01) if (len(idx) and l_fin > SEUIL_DB) else None
    if l_fin > SEUIL_DB:
        f0 = f0_fft(fin, f_nom)
        res['f0_hz'] = f0
        if f0:
            res['ecart_cents'] = 1200 * np.log2(f0 / f_nom)
            res['partiels_db'] = partiels(fin, f0)
            # f0 par quart de seconde (stabilité de la hauteur)
            q = []
            for i in range(4):
                fq = f0_fft(fin[i * SR // 4:(i + 1) * SR // 4], f_nom)
                q.append(None if fq is None else 1200 * np.log2(fq / f_nom))
            res['cents_quarts'] = q
    return res


def classer(res):
    lf = res['niveau_fin_db']
    lm = max(res['niveau_10'][2:])         # fenetres de 0,2 s a 3 s
    if lm <= SEUIL_DB:
        return 'N'                      # ne part pas
    if lf <= lm - 20.0:
        return 'E'                      # s'éteint (a sonné puis retombe)
    if res['variation_fin_db'] > 3.0:
        return 'I'
    e = res.get('ecart_cents')
    if e is None or abs(e) > 50.0:
        return 'I'
    qs = [c for c in res.get('cents_quarts', []) if c is not None]
    if len(qs) < 4 or max(qs) - min(qs) > 50.0:
        return 'I'
    return 'J'


# --------------------------------------------------------------------------
# rampe
# --------------------------------------------------------------------------
def analyser_rampe(x, p_t, sr=SR):
    """Enveloppe efficace sur 20 ms contre pression ; 4 pressions caractéristiques."""
    pas = int(0.02 * sr)
    n = len(x) // pas
    env = np.array([_rms(x[i * pas:(i + 1) * pas]) for i in range(n)])
    p = np.array([p_t[min(len(p_t) - 1, int((i + 0.5) * pas / BLOC))] for i in range(n)])
    imax_p = int(np.argmax(p))
    mont = slice(0, imax_p + 1)
    desc = slice(imax_p, n)
    emax = env.max() if n else 0.0
    out = {'env_max_db': _db(emax)}
    if emax <= 10 ** (SEUIL_DB / 20.0):   # jamais de son
        out.update(p_depart=None, p_extinction_haute=None, p_reprise=None, p_arret=None)
        return out, env, p
    seuil = max(emax * 10 ** (-40 / 20.0), 10 ** (SEUIL_DB / 20.0))
    em, pm = env[mont], p[mont]
    on = np.nonzero(em > seuil)[0]
    p_dep = float(pm[on[0]]) if len(on) else None
    p_ext = None
    if len(on):
        cum = np.maximum.accumulate(em)
        chute = np.nonzero((em < cum * 0.1) & (np.arange(len(em)) > on[0]))[0]
        if len(chute):
            p_ext = float(pm[chute[0]])
    ed, pd = env[desc], p[desc]
    ond = np.nonzero(ed > seuil)[0]
    p_rep = p_arr = None
    if len(ond):
        # à la descente : première reprise après une extinction haute, puis arrêt
        cum = np.maximum.accumulate(ed)
        if p_ext is not None:
            # dernier état "éteint" au sommet : cherche le premier retour au-dessus du seuil
            bas = np.nonzero(ed < seuil)[0]
            if len(bas) and ed[0] < seuil:
                apres = np.nonzero((ed > seuil) & (np.arange(len(ed)) > bas[0]))[0]
                if len(apres):
                    p_rep = float(pd[apres[0]])
        p_arr = float(pd[ond[-1]])
    out.update(p_depart=p_dep, p_extinction_haute=p_ext, p_reprise=p_rep, p_arret=p_arr)
    return out, env, p


# --------------------------------------------------------------------------
# WAV 24 bits
# --------------------------------------------------------------------------
def ecrire_wav24(chemin, x):
    x = np.asarray(x, float)
    crete = np.max(np.abs(x))
    if crete > 0:
        x = x / crete
    v = np.round(np.clip(x, -1, 1) * 8388607).astype(np.int32)
    b = np.empty((len(v), 3), np.uint8)
    b[:, 0] = v & 0xFF
    b[:, 1] = (v >> 8) & 0xFF
    b[:, 2] = (v >> 16) & 0xFF
    with wave.open(str(chemin), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b.tobytes())


# --------------------------------------------------------------------------
# paramètres C
# --------------------------------------------------------------------------
def params_c(params, note):
    """Champs utiles de la structure `_Params`, plus la lame lue dans son biquad."""
    d = {}
    for nom in ('family', 'n_modes', 'oversample', 'rest_opening', 'width', 'vena',
                'max_open', 'leak', 'src_admit', 'flow_gain', 'cavity_gain',
                'cavity_leak', 'out_mode', 'fs_out', 'free_law', 'plate',
                'tongue', 'clear', 'pump_area'):
        d[nom] = float(getattr(params, nom))
    r = params.reed
    a1 = r.da1 - 2.0
    a2 = 1.0 - r.ea2
    d['reed_b'] = [float(r.b0), float(r.b1), float(r.b2)]
    if a2 > 0:
        rho = np.sqrt(a2)
        c = -a1 / (2 * rho)
        if abs(c) <= 1:
            w0 = np.arccos(c)
            d['lame_hz'] = float(w0 * SR * max(1, params.oversample) / (2 * np.pi))  # biquad à fs x suréchantillonnage
            d['lame_q'] = float(-w0 / (2 * np.log(rho))) if rho < 1 else None
    return d


def params_python(note):
    """Réglage nominal avant accord (hybrid.accordeon) : compliance, pression de fermeture..."""
    from banc_recherche import hybrid
    v = hybrid.accordeon(f_de(note))
    ex, res = v.exciter, v.resonator if hasattr(v, 'resonator') else None
    d = {k: getattr(ex, k) for k in (
        'freq_hz', 'q', 'width_m', 'rest_offset_m', 'max_open_m', 'leak_m', 'loi',
        'plate_m', 'tongue_m', 'clearance_m', 'force_area_m2', 'mass_kg',
        'vena_contracta', 'source_impedance', 'closing_pressure_pa')
        if hasattr(ex, k)}
    if res is not None and hasattr(res, 'compliance'):
        d['compliance_m3_pa'] = float(res.compliance)
    return d


# --------------------------------------------------------------------------
# programme
# --------------------------------------------------------------------------
def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sortie', default=SORTIE_DEFAUT)
    ap.add_argument('--lo', type=int, default=36)
    ap.add_argument('--hi', type=int, default=96)
    ap.add_argument('--notes', default='')
    ap.add_argument('--sans-figures', action='store_true')
    a = ap.parse_args()
    sortie = pathlib.Path(a.sortie)
    (sortie / 'muets').mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    from banc_recherche import live
    inst = live.build_instrument('accordeon', lo=a.lo, hi=a.hi, samplerate=float(SR))
    print('instrument construit en %.0f s' % (time.time() - t0), flush=True)
    notes = [int(s) for s in a.notes.split(',') if s] or list(range(a.lo, a.hi + 1))

    carte, rampes, ptxt = {}, {}, {}
    for n in notes:
        cp = inst.params_for(n)
        admit = float(cp.src_admit)
        fn = f_de(n)
        ptxt[n] = {'c': params_c(cp, n), 'python_nominal': params_python(n)}
        cases = {}
        for p in PRESSIONS:
            nb = int(DUREE * SR) // BLOC + 1
            x = rendre(live, cp, n, [p * admit] * nb)[:int(DUREE * SR)]
            res = analyser_case(x, fn)
            res['etat'] = classer(res)
            cases[str(p)] = res
            if res['etat'] != 'J' and BANDE[0] <= p <= BANDE[1]:
                ecrire_wav24(sortie / 'muets' / ('n%02d_p%04d_%s.wav' % (n, p, res['etat'])), x)
        # rampe
        nb_m = int(10 * SR) // BLOC
        pm = np.linspace(0, 3000, nb_m)
        p_t = np.concatenate([pm, pm[::-1]])
        x = rendre(live, cp, n, p_t * admit)
        rr, env, pe = analyser_rampe(x, p_t)
        rampes[str(n)] = rr
        carte[str(n)] = {'f_nom_hz': fn, 'cases': cases}
        e = ' '.join('%s%s' % (cases[str(p)]['etat'],
                               '' if 'ecart_cents' not in cases[str(p)] else '%+.0f' % cases[str(p)]['ecart_cents'])
                     for p in PRESSIONS)
        print('note %d (%.1f Hz) : %s | rampe %s  [%.0f s]' % (
            n, fn, e, {k: (None if v is None else round(v, 1)) for k, v in rr.items() if k != 'env_max_db'},
            time.time() - t0), flush=True)

    with open(sortie / 'carte.json', 'w', encoding='utf-8') as f:
        json.dump({'pressions': PRESSIONS, 'carte': carte, 'rampes': rampes,
                   'params': {str(k): v for k, v in ptxt.items()},
                   'duree_s': time.time() - t0, 'seuil_db': SEUIL_DB}, f, ensure_ascii=False,
                  indent=1, default=float)
    ecrire_textes(sortie, notes, carte, rampes, ptxt)
    if not a.sans_figures:
        figures(sortie, notes, carte, rampes)
    print('fini en %.0f s' % (time.time() - t0))


def ecrire_textes(sortie, notes, carte, rampes, ptxt):
    L = ['Etat : J joue, E s\'eteint, N ne part pas, I instable ; suivi de l\'ecart en cents a la note tempérée.',
         'note  Hz     ' + ''.join('%8d' % p for p in PRESSIONS)]
    for n in notes:
        c = carte[str(n)]['cases']
        cell = ''
        for p in PRESSIONS:
            r = c[str(p)]
            cell += '%8s' % (r['etat'] + ('' if 'ecart_cents' not in r else '%+.0f' % r['ecart_cents']))
        L.append('%4d %7.1f %s' % (n, f_de(n), cell))
    L += ['', 'Niveau de la derniere seconde (dB re echelle brute) et temps d\'etablissement (s)']
    for n in notes:
        c = carte[str(n)]['cases']
        cell = ''
        for p in PRESSIONS:
            r = c[str(p)]
            cell += '%7.0f/%s' % (r['niveau_fin_db'], '-' if r['t_etab_s'] is None else '%.2f' % r['t_etab_s'])
        L.append('%4d %s' % (n, cell))
    L += ['', 'Cases non « joue » dans la bande %d a %d Pa : parametres de la note' % BANDE]
    vus = set()
    for n in notes:
        for p in PRESSIONS:
            if BANDE[0] <= p <= BANDE[1] and carte[str(n)]['cases'][str(p)]['etat'] != 'J':
                if n not in vus:
                    vus.add(n)
                    L.append('note %d : C = %s' % (n, json.dumps(ptxt[n]['c'], default=float)))
                    L.append('        python nominal = %s' % json.dumps(ptxt[n]['python_nominal'], default=float))
                L.append('   p=%d : %s' % (p, carte[str(n)]['cases'][str(p)]['etat']))
    (sortie / 'carte.txt').write_text('\n'.join(L) + '\n', encoding='utf-8')
    R = ['note   Hz   p_depart  p_extinction_haute  p_reprise  p_arret   (Pa)']
    f = lambda v: '   -   ' if v is None else '%7.0f' % v
    for n in notes:
        r = rampes[str(n)]
        R.append('%4d %7.1f %s %s %s %s' % (n, f_de(n), f(r['p_depart']), f(r['p_extinction_haute']),
                                           f(r['p_reprise']), f(r['p_arret'])))
    (sortie / 'rampe.txt').write_text('\n'.join(R) + '\n', encoding='utf-8')


def figures(sortie, notes, carte, rampes):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cm = plt.get_cmap('viridis')
    cols = [cm(i / (len(PRESSIONS) - 1)) for i in range(len(PRESSIONS))]
    for nom, cle, ylab, titre in (
            ('niveau', 'niveau_fin_db', 'niveau établi (dB re échelle brute)', 'Niveau établi selon la note'),
            ('cents', 'ecart_cents', 'écart à la note tempérée (cents)', 'Écart de hauteur selon la note')):
        fig, ax = plt.subplots(figsize=(11, 6))
        vals = []
        for i, p in enumerate(PRESSIONS):
            xs = [n for n in notes if cle in carte[str(n)]['cases'][str(p)]]
            ys = [carte[str(n)]['cases'][str(p)][cle] for n in xs]
            if cle == 'niveau_fin_db':
                ok = [carte[str(n)]['cases'][str(p)]['etat'] == 'J' for n in xs]
                xs2 = [x for x, o in zip(xs, ok) if o]
                ys2 = [y for y, o in zip(ys, ok) if o]
                ax.plot(xs2, ys2, '-', color=cols[i], lw=1.2, label='%d Pa' % p)
                vals += ys2
            else:
                ax.plot(xs, ys, '-', color=cols[i], lw=1.2, label='%d Pa' % p)
                vals += ys
        if cle == 'niveau_fin_db':
            bas = (min(vals) - 6) if vals else -150
            for i, p in enumerate(PRESSIONS):
                m = [n for n in notes if carte[str(n)]['cases'][str(p)]['etat'] != 'J']
                ax.plot(m, [bas] * len(m), 'x', color=cols[i], ms=5)
            ax.set_ylim(bas - 4, None)
        else:
            ax.axhline(0, color='k', lw=0.5)
        ax.set_xlabel('note MIDI (36 = do1, 69 = la3 440 Hz)')
        ax.set_ylabel(ylab)
        ax.set_title(titre + ('  (croix : case qui ne joue pas)' if cle == 'niveau_fin_db' else ''))
        ax.grid(alpha=0.3)
        ax.legend(ncol=3, fontsize=8)
        fig.tight_layout()
        fig.savefig(sortie / ('figure_%s.png' % nom), dpi=200)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 6))
    for cle, lab, st in (('p_depart', 'pression de départ (montée)', 'o-'),
                         ('p_extinction_haute', 'extinction haute (montée)', 's-'),
                         ('p_arret', 'pression d\'arrêt (descente)', '^-')):
        xs = [n for n in notes if rampes[str(n)][cle] is not None]
        ax.plot(xs, [rampes[str(n)][cle] for n in xs], st, ms=3, lw=1, label=lab)
    ax.axhspan(*BANDE, color='0.85', zorder=0, label='bande de jeu 100 à 1000 Pa')
    ax.set_yscale('log')
    ax.set_xlabel('note MIDI')
    ax.set_ylabel('pression (Pa)')
    ax.set_title('Pressions caractéristiques de la rampe lente selon la note')
    ax.grid(alpha=0.3, which='both')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(sortie / 'figure_pressions.png', dpi=200)
    plt.close(fig)


if __name__ == '__main__':
    principal()
