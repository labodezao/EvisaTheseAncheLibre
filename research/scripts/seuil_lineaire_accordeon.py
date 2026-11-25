#!/usr/bin/env python
"""Seuil linéaire de l'accordéon (partie A, hors moteur) : plus petite pression de
soufflet P_s pour laquelle l'équilibre (anche, chambre) devient instable.

Équations du moteur (`embedded.RealtimeVoice._exciter`, loi traversante) :
  y'' + (w/Q) y' + w^2 y = w^2 (h0/p_ferm) p
  C p' = (P_s - p)/R - q_out(y, p)
  q_out = vena * largeur * h(y) * sqrt(2/rho) * p / sqrt(p + visc)   (p > 0)
  h(y) = sqrt(g^2 + jeu^2), g = z si z = h0 + y > 0, sinon max(-z - lame - plaque, 0)
Sorties : seuil_lineaire.json, A1.txt, A2.txt, A3.txt, figure_A1.png dans --sortie.
"""
import argparse
import json
import pathlib
import sys
from multiprocessing import Pool

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
SORTIE = 'J:/claude/tmp/modele_instruments/accordeon/clavier_pression/source'
CARTE = 'J:/claude/tmp/modele_instruments/accordeon/clavier_pression'
PS_GRILLE = np.logspace(np.log10(5.0), np.log10(5000.0), 400)


def f_de(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


def constantes(note, R=None, R_ref=None, visc=1.0):
    """Paramètres du moteur pour la note. R fixe (défaut 2e8) ou R = R_ref r^2."""
    from banc_recherche import hybrid, embedded
    f0 = f_de(note)
    r = f0 / 110.0
    kw = {}
    if R_ref is not None:
        kw['source_impedance'] = R_ref * r * r
    elif R is not None:
        kw['source_impedance'] = R
    p = embedded.params_from_voice(hybrid.accordeon(f0, **kw))
    return dict(h0=p.rest_opening_m, pf=p.closing_pressure_pa, w=2 * np.pi * p.reed_freq_hz,
                Q=p.reed_q, C=p.compliance, R=p.source_impedance, vena=p.vena_contracta,
                width=p.width_m, tongue=p.tongue_m, plate=p.plate_m, clear=p.clearance_m,
                visc=visc, rho=embedded.RHO, r=r, f0=f0)


def q_out(c, y, p):
    z = c['h0'] + y
    g = z if z > 0 else max(-z - c['tongue'] - c['plate'], 0.0)
    h = np.sqrt(g * g + c['clear'] ** 2)
    if p <= 0:
        return 0.0
    return c['vena'] * c['width'] * h * np.sqrt(2.0 / c['rho']) * p / np.sqrt(p + c['visc'])


def champ(c, x, Ps):
    y, v, p = x
    return np.array([v,
                     -c['w'] ** 2 * y - c['w'] / c['Q'] * v + c['w'] ** 2 * c['h0'] / c['pf'] * p,
                     ((Ps - p) / c['R'] - q_out(c, y, p)) / c['C']])


def equilibre(c, Ps):
    F = lambda p: (Ps - p) / c['R'] - q_out(c, c['h0'] * p / c['pf'], p)
    lo, hi = 0.0, Ps
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if F(m) > 0:
            lo = m
        else:
            hi = m
    p0 = 0.5 * (lo + hi)
    return np.array([c['h0'] * p0 / c['pf'], 0.0, p0])


def valeur_propre(c, Ps):
    x0 = equilibre(c, Ps)
    steps = np.array([1e-3 * c['h0'], 1e-3 * c['h0'] * c['w'], 1e-5 * max(x0[2], 1.0)])
    J = np.zeros((3, 3))
    for j in range(3):
        e = np.zeros(3)
        e[j] = steps[j]
        J[:, j] = (champ(c, x0 + e, Ps) - champ(c, x0 - e, Ps)) / (2 * steps[j])
    ev = np.linalg.eigvals(J)
    k = int(np.argmax(ev.real))
    return float(ev[k].real), float(abs(ev[k].imag) / (2 * np.pi)), float(x0[2])


def seuil(c):
    """P_on (plus petite P_s à partie réelle > 0), P_off (retour négatif au-dessus, ou None)."""
    re = np.array([valeur_propre(c, P)[0] for P in PS_GRILLE])
    pos = re > 0
    if not pos.any():
        return dict(P_on=None, P_off=None, re_max=float(re.max()))
    i = int(np.argmax(pos))
    if i == 0:
        p_on = float(PS_GRILLE[0])
    else:
        lo, hi = PS_GRILLE[i - 1], PS_GRILLE[i]
        for _ in range(60):
            m = np.sqrt(lo * hi)
            if valeur_propre(c, m)[0] > 0:
                hi = m
            else:
                lo = m
        p_on = float(hi)
    p_off = None
    nb = np.nonzero(~pos & (np.arange(len(pos)) > i))[0]
    if len(nb):
        j = int(nb[0])
        lo, hi = PS_GRILLE[j - 1], PS_GRILLE[j]
        for _ in range(60):
            m = np.sqrt(lo * hi)
            if valeur_propre(c, m)[0] > 0:
                lo = m
            else:
                hi = m
        p_off = float(lo)
    return dict(P_on=p_on, P_off=p_off, re_max=float(re.max()))


def tache(a):
    note, kw, etiquette = a
    c = constantes(note, **kw)
    s = seuil(c)
    s.update(note=note, etiquette=etiquette, R=c['R'], f_lame=c['w'] / 2 / np.pi)
    for P in (100, 300, 1000):
        re, f, p0 = valeur_propre(c, P)
        s['re_%d' % P], s['f_%d' % P], s['p0s_%d' % P] = re, f, p0 / P
    return s


def fmt(v, f='%7.1f'):
    return '    -  ' if v is None else f % v


def lire_mesures():
    rampe = {}
    for ligne in open(CARTE + '/rampe.txt', encoding='utf-8').read().splitlines()[1:]:
        t = ligne.split()
        if len(t) >= 6:
            n = int(t[0])
            dep = None if t[2] == '-' else float(t[2])
            arr = None if t[-1] == '-' else float(t[-1])
            rampe[n] = (dep, arr)
    carte = json.load(open(CARTE + '/carte.json', encoding='utf-8'))
    pmin = {}
    for n, v in carte['carte'].items():
        ok = [p for p in carte['pressions'] if v['cases'][str(p)]['etat'] == 'J']
        pmin[int(n)] = min(ok) if ok else None
    return rampe, pmin


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sortie', default=SORTIE)
    a = ap.parse_args()
    out = pathlib.Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    notes = list(range(36, 97))
    n2 = [36, 48, 60, 72, 84, 96]
    cases = [('R fixe 2e8', dict(R=2e8), 1.0), ('R fixe 2e8', dict(R=2e8), 1e-6),
             ('R=2e8 r2', dict(R_ref=2e8), 1.0), ('R=2e8 r2', dict(R_ref=2e8), 1e-6)]
    t2 = [(n, dict(kw, visc=v), '%s|visc=%g' % (nom, v)) for nom, kw, v in cases for n in n2]
    refs = [2e6, 5e6, 1e7, 1.5e7, 2e7, 4e7, 1e8, 2e8, 5e8, 1e9]
    n3 = [36, 60, 84, 96]
    t3 = [(n, dict(R_ref=R), 'Rref=%g' % R) for R in refs for n in n3]
    with Pool(10) as pool:
        A1 = pool.map(tache, [(n, {}, 'fixe') for n in notes])
        A2 = pool.map(tache, t2)
        A3 = pool.map(tache, t3)
    json.dump(dict(A1=A1, A2=A2, A3=A3), open(out / 'seuil_lineaire.json', 'w'), indent=1)
    rampe, pmin = lire_mesures()
    L = ['A1 : R fixe 2e8. P_on = seuil lineaire ; mesures : rampe (p_dep montee, p_arr descente) et grille (pmin J)',
         'note  f_lame   P_on   P_off  p_dep  p_arr  pmin_J  P_on/p_dep  Re300  f300']
    for s in A1:
        n = s['note']
        dep, arr = rampe.get(n, (None, None))
        rat = '%7.2f' % (s['P_on'] / dep) if (s['P_on'] and dep) else '   -   '
        L.append('%4d %7.1f %s %s %s %s %s  %s %7.1f %7.1f' % (
            n, s['f_lame'], fmt(s['P_on']), fmt(s['P_off']), fmt(dep, '%6.0f'), fmt(arr, '%6.0f'),
            fmt(pmin.get(n), '%6.0f'), rat, s['re_300'], s['f_300']))
    (out / 'A1.txt').write_text('\n'.join(L) + '\n', encoding='utf-8')
    L = ['A2 : P_on (Pa)', 'cas | note: ' + ' '.join('%8d' % n for n in n2)]
    for et in sorted({s['etiquette'] for s in A2}):
        L.append('%-28s ' % et + ' '.join('%8s' % ('-' if s['P_on'] is None else '%.1f' % s['P_on'])
                                         for s in A2 if s['etiquette'] == et))
    (out / 'A2.txt').write_text('\n'.join(L) + '\n', encoding='utf-8')
    L = ['A3 : R = R_ref r^2. P_on ; Re (1/s) a 100/300/1000 Pa ; p0/P_s a 100/300/1000']
    for R in refs:
        for s in [s for s in A3 if s['etiquette'] == 'Rref=%g' % R]:
            L.append('Rref=%-6g note %2d P_on=%s Re=%8.1f %8.1f %8.1f  p0/Ps=%.3f %.3f %.3f' % (
                R, s['note'], fmt(s['P_on']), s['re_100'], s['re_300'], s['re_1000'],
                s['p0s_100'], s['p0s_300'], s['p0s_1000']))
    (out / 'A3.txt').write_text('\n'.join(L) + '\n', encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 6))
    ns = [s['note'] for s in A1]
    nan = float('nan')
    ax.plot(ns, [s['P_on'] or nan for s in A1], 'k-', lw=2, label='seuil linéaire P_on (calcul)')
    ax.plot(ns, [s['P_off'] or nan for s in A1], 'k:', lw=1, label='retour stable P_off (calcul)')
    ax.plot(ns, [rampe[n][0] or nan for n in ns], 'o-', ms=3, lw=1, label='p_départ (rampe, moteur C)')
    ax.plot(ns, [rampe[n][1] or nan for n in ns], '^-', ms=3, lw=1, label="p_arrêt (rampe, moteur C)")
    ax.plot(ns, [pmin[n] or nan for n in ns], 's', ms=3, label='pression minimale qui joue (grille)')
    ax.set_yscale('log')
    ax.grid(alpha=0.3, which='both')
    ax.set_xlabel('note MIDI')
    ax.set_ylabel('pression de soufflet (Pa)')
    ax.set_title('Seuil linéaire et mesures du moteur, R fixe = 2e8 Pa·s/m³')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / 'figure_A1.png', dpi=200)
    print('fini')


if __name__ == '__main__':
    principal()
