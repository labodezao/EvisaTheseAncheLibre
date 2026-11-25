#!/usr/bin/env python
"""Stabilité de l'équilibre de l'accordéon en loi écrêtée, hors moteur C, en double précision.

Cause prouvée du test `test_la_somme_des_voix_n_a_pas_de_composante_continue` (25/11/2026) : à
l'ouverture de soupape par défaut (5 ms) la voix écrêtée reste au silence, parce que son équilibre
(chambre à 635 Pa, languette au-delà de `max_open`) est stable ; seule la pose en échelon la
décroche. Le modèle est celui de `seuil_lineaire_accordeon.py` (anche du second ordre, chambre
sans mode), avec la loi d'ouverture du moteur : écrêtée `clip(h0 + y, fuite, max_open)` ou
traversante.

Sortie : pour chaque loi, la valeur propre oscillante à l'équilibre, sa partie réelle selon la
pression de soufflet P_s, la pression de changement de signe ; avec `--cycle`, les amplitudes
d'une perturbation de l'anche qui amorcent ou non le cycle (Runge-Kutta 4, plus lent).
Le point par défaut est celui du test : note 57, expression 0,7, P_s = 1454,2 Pa (`level / src_admit`
d'une voix du `Synth` : 2,4237e-5 m³/s et 1/6e7).
"""
import argparse
import pathlib
import sys

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from banc_recherche import embedded as emb, hybrid  # noqa: E402

PS_TEST = 1454.2333


def constantes(loi, f0=220.0, sr=48000.0):
    p = emb.params_from_voice(hybrid.accordeon(f0_hz=f0, loi=loi), samplerate=sr, name='accordeon')
    return dict(h0=p.rest_opening_m, pf=p.closing_pressure_pa, w=2 * np.pi * p.reed_freq_hz,
                Q=p.reed_q, C=p.compliance, R=p.source_impedance, vena=p.vena_contracta,
                width=p.width_m, tongue=p.tongue_m, plate=p.plate_m, clear=p.clearance_m,
                leak=p.leak_m, maxo=p.max_open_m, visc=p.visc_pa, loi=p.loi)


def hauteur(c, y):
    z = c['h0'] + y
    if c['loi'] == emb.LOI_TRAVERSANTE:
        g = z if z > 0 else max(-z - c['tongue'] - c['plate'], 0.0)
        return np.sqrt(g * g + c['clear'] ** 2)
    return min(max(z, c['leak']), c['maxo'])


def q_out(c, y, p):
    if p <= 0:
        return 0.0
    return c['vena'] * c['width'] * hauteur(c, y) * np.sqrt(2.0 / emb.RHO) * p / np.sqrt(p + c['visc'])


def champ(c, x, Ps):
    y, v, p = x
    return np.array([v, -c['w'] ** 2 * y - c['w'] / c['Q'] * v + c['w'] ** 2 * c['h0'] / c['pf'] * p,
                     ((Ps - p) / c['R'] - q_out(c, y, p)) / c['C']])


def equilibre(c, Ps):
    F = lambda p: champ(c, [c['h0'] * p / c['pf'], 0.0, p], Ps)[2]
    lo, hi = 0.0, Ps
    for _ in range(300):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if F(m) > 0 else (lo, m)
    p0 = 0.5 * (lo + hi)
    return np.array([c['h0'] * p0 / c['pf'], 0.0, p0])


def valeur_propre(c, Ps):
    """Valeur propre de plus grande partie réelle du jacobien 3x3 (différences centrées)."""
    x0 = equilibre(c, Ps)
    pas = np.array([1e-4 * c['h0'], 1e-4 * c['h0'] * c['w'], 1e-6 * max(x0[2], 1.0)])
    J = np.zeros((3, 3))
    for j in range(3):
        e = np.zeros(3)
        e[j] = pas[j]
        J[:, j] = (champ(c, x0 + e, Ps) - champ(c, x0 - e, Ps)) / (2 * pas[j])
    ev = np.linalg.eigvals(J)
    return ev[int(np.argmax(ev.real))], x0


def changements_de_signe(c):
    g = np.logspace(np.log10(5), np.log10(5000), 1500)
    re = np.array([valeur_propre(c, P)[0].real for P in g])
    sorties = []
    for i in np.nonzero(np.diff(np.sign(re)))[0]:
        lo, hi = g[i], g[i + 1]
        for _ in range(60):
            m = np.sqrt(lo * hi)
            lo, hi = (m, hi) if np.sign(valeur_propre(c, m)[0].real) == np.sign(re[i]) else (lo, m)
        sorties.append((float(lo), float(re[i]), float(re[i + 1])))
    return sorties


def rk4_p(c, x, Ps, duree=0.4, dt=1 / 96000.0):
    n = int(duree / dt)
    out = np.empty(n)
    f = lambda u: champ(c, u, Ps)
    for i in range(n):
        k1 = f(x); k2 = f(x + dt / 2 * k1); k3 = f(x + dt / 2 * k2); k4 = f(x + dt * k3)
        x = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        out[i] = x[2]
    return out


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ps', type=float, default=PS_TEST)
    ap.add_argument('--cycle', action='store_true')
    a = ap.parse_args()
    for loi in (emb.LOI_ECRETEE, emb.LOI_TRAVERSANTE):
        c = constantes(loi)
        l, x0 = valeur_propre(c, a.ps)
        print('%s : P_s %.1f Pa, p0 %.1f Pa, z0 %.3e m (max_open %.3e) ; lambda = %+.2f %+.1fj /s ; '
              '-w/2Q = %.2f' % (loi, a.ps, x0[2], c['h0'] + x0[0], c['maxo'], l.real, l.imag,
                                 -c['w'] / 2 / c['Q']))
        for ps, avant, apres in changements_de_signe(c):
            print('   Re change de signe à P_s = %.1f Pa (%+.1f -> %+.1f)' % (ps, avant, apres))
        if a.cycle:
            for i, nom, vals in ((0, 'y', (-0.2, -0.35, -0.4, -0.5)), (2, 'p', (1e-2, 0.2))):
                for rel in vals:
                    x = x0.copy()
                    x[i] *= 1 + rel
                    p = rk4_p(c, x, a.ps)
                    n = len(p) // 4
                    print('   %s x(1%+g) : crête-à-crête de p, 1er quart %.2e, dernier %.2e Pa'
                          % (nom, rel, np.ptp(p[:n]), np.ptp(p[-n:])))


if __name__ == '__main__':
    principal()
