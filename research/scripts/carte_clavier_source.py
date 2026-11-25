#!/usr/bin/env python
"""Carte du clavier avec une résistance de source en similitude (R = R_ref r^2).

Reprend les mesures de `carte_clavier_pression.py` (importées, rien de refait) :
même grille (100..2500 Pa posés d'un coup, 3 s), même rampe (0 -> 3000 -> 0 Pa,
10 s + 10 s), mêmes classements. Pour chaque cas, R = R_ref r^2, r = f0/110, voix
accordée par `live._accorder('accordeon', f0, niveau, 48000, source_impedance=R)`,
niveau = 580 Pa / R. Le témoin garde R = 2e8 fixe.

Sorties dans --sortie : carte_<cas>.json/.txt, rampe_<cas>.txt, trois figures,
resume.json, resume.txt.
Usage : python carte_clavier_source.py [--sortie D] [--notes 60,72]
"""
import argparse
import json
import pathlib
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import carte_clavier_pression as cc  # noqa: E402

SORTIE = 'J:/claude/tmp/modele_instruments/accordeon/clavier_pression/source'
CAS = [('Rref_5e6', 5e6), ('Rref_1.5e7', 1.5e7), ('Rref_4e7', 4e7), ('Rfixe_2e8', None)]
PRESSION_NOMINALE = 580.0
BANDE_P = [100, 150, 200, 300, 500, 700, 1000]
NOTES_PENTE = [48, 60, 72, 84]
NOTES_TIMBRE = [45, 57, 69, 81, 93]


def R_de(R_ref, note):
    r = cc.f_de(note) / 110.0
    return 2e8 if R_ref is None else R_ref * r * r


def tache(a):
    """Une note d'un cas : accord, grille, rampe."""
    cas, R_ref, n = a
    from banc_recherche import live
    R = R_de(R_ref, n)
    niveau = PRESSION_NOMINALE / R
    cp, garde = live._accorder('accordeon', cc.f_de(n), niveau, 48000.0, source_impedance=R)
    admit = float(cp.src_admit)
    fn = cc.f_de(n)
    cases = {}
    for p in cc.PRESSIONS:
        nb = int(cc.DUREE * cc.SR) // cc.BLOC + 1
        x = cc.rendre(live, cp, n, [p * admit] * nb)[:int(cc.DUREE * cc.SR)]
        res = cc.analyser_case(x, fn)
        res['etat'] = cc.classer(res)
        cases[str(p)] = res
    nb_m = int(10 * cc.SR) // cc.BLOC
    pm = np.linspace(0, 3000, nb_m)
    p_t = np.concatenate([pm, pm[::-1]])
    x = cc.rendre(live, cp, n, p_t * admit)
    rr, _, _ = cc.analyser_rampe(x, p_t)
    pc = cc.params_c(cp, n)
    pc['R_nominal'] = R
    pc['niveau_m3s'] = niveau
    return cas, n, dict(f_nom_hz=fn, cases=cases), rr, {'c': pc, 'python_nominal': {'source_impedance': R}}, admit


def verifier_transmission():
    from banc_recherche import live
    n, R_ref = 60, 5e6
    R = R_de(R_ref, n)
    cp, _ = live._accorder('accordeon', cc.f_de(n), PRESSION_NOMINALE / R, 48000.0, source_impedance=R)
    print('transmission : note %d, R = %.6g, 1/R = %.6g, src_admit de la structure C = %.6g (float32)'
          % (n, R, 1.0 / R, float(cp.src_admit)), flush=True)
    cp2, _ = live._accorder('accordeon', cc.f_de(n), 2.9e-6, 48000.0)
    print('   defaut : src_admit = %.6g (1/2e8 = %.6g)' % (float(cp2.src_admit), 1 / 2e8), flush=True)


def resumer(nom, notes, carte, rampes):
    """Comptes et listes d'un cas."""
    jouent, non, tet = 0, [], []
    for n in notes:
        for p in BANDE_P:
            r = carte[str(n)]['cases'][str(p)]
            if r['etat'] == 'J':
                jouent += 1
                if r['t_etab_s'] is not None:
                    tet.append(r['t_etab_s'])
            else:
                non.append('%d@%d:%s' % (n, p, r['etat']))
    pentes = {}
    for n in NOTES_PENTE:
        if n not in notes:
            continue
        xs, ys = [], []
        for p in (300, 500, 700, 1000):
            r = carte[str(n)]['cases'][str(p)]
            if 'ecart_cents' in r and r['etat'] in ('J', 'I'):
                xs.append(p)
                ys.append(r['ecart_cents'])
        pentes[n] = float(np.polyfit(xs, ys, 1)[0] * 100) if len(xs) >= 3 else None
    timbre = {}
    for n in NOTES_TIMBRE:
        if n not in notes:
            continue
        for p in (300, 1000):
            timbre['%d@%d' % (n, p)] = carte[str(n)]['cases'][str(p)].get('partiels_db')
    return dict(cas=nom, jouent=jouent, total=len(notes) * len(BANDE_P), non_jouent=non,
                t_etab_med=float(np.median(tet)) if tet else None,
                t_etab_max=float(np.max(tet)) if tet else None, pente_cents_100Pa=pentes,
                timbre=timbre)


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sortie', default=SORTIE)
    ap.add_argument('--notes', default='')
    a = ap.parse_args()
    out = pathlib.Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    notes = [int(s) for s in a.notes.split(',') if s] or list(range(36, 97))
    t0 = time.time()
    verifier_transmission()
    taches = [(c, R, n) for c, R in CAS for n in notes]
    res = {c: dict(carte={}, rampes={}, ptxt={}) for c, _ in CAS}
    with Pool(10) as pool:
        for cas, n, ca, rr, pt, admit in pool.imap_unordered(tache, taches):
            res[cas]['carte'][str(n)] = ca
            res[cas]['rampes'][str(n)] = rr
            res[cas]['ptxt'][n] = pt
    print('mesures finies en %.0f s' % (time.time() - t0), flush=True)
    resumes = {}
    import tempfile
    for cas, R_ref in CAS:
        r = res[cas]
        carte = {str(n): r['carte'][str(n)] for n in notes}
        rampes = {str(n): r['rampes'][str(n)] for n in notes}
        json.dump({'cas': cas, 'R_ref': R_ref, 'pressions': cc.PRESSIONS, 'carte': carte, 'rampes': rampes,
                   'params': {str(k): v for k, v in r['ptxt'].items()}, 'seuil_db': cc.SEUIL_DB},
                  open(out / ('carte_%s.json' % cas), 'w', encoding='utf-8'), ensure_ascii=False, indent=1,
                  default=float)
        tmp = pathlib.Path(tempfile.mkdtemp(dir='J:/claude/tmp'))
        cc.ecrire_textes(tmp, notes, carte, rampes, r['ptxt'])
        (out / ('carte_%s.txt' % cas)).write_text((tmp / 'carte.txt').read_text(encoding='utf-8'), encoding='utf-8')
        (out / ('rampe_%s.txt' % cas)).write_text((tmp / 'rampe.txt').read_text(encoding='utf-8'), encoding='utf-8')
        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()
        resumes[cas] = resumer(cas, notes, carte, rampes)
    json.dump(resumes, open(out / 'resume.json', 'w', encoding='utf-8'), indent=1, default=float)
    figures(out, notes, res, resumes)
    print('fini en %.0f s' % (time.time() - t0))


def figures(out, notes, res, resumes):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    etiq = {'Rref_5e6': 'R = 5e6 r²', 'Rref_1.5e7': 'R = 1,5e7 r²', 'Rref_4e7': 'R = 4e7 r²',
            'Rfixe_2e8': 'R = 2e8 fixe (témoin)'}
    nan = float('nan')
    fig, ax = plt.subplots(figsize=(11, 6))
    for cas, _ in CAS:
        rp = res[cas]['rampes']
        ax.plot(notes, [rp[str(n)]['p_depart'] or nan for n in notes], 'o-', ms=3, lw=1.2, label=etiq[cas])
    ax.axhspan(*cc.BANDE, color='0.85', zorder=0, label='bande de jeu 100 à 1000 Pa')
    ax.set_yscale('log')
    ax.set_xlabel('note MIDI')
    ax.set_ylabel('pression de départ en rampe (Pa)')
    ax.set_title('Pression de départ selon la note (trou : la note ne part pas)')
    ax.grid(alpha=0.3, which='both')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / 'figure_p_depart.png', dpi=200)
    plt.close(fig)

    fig, axs = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    for ax, p in zip(axs, (100, 300, 1000)):
        for cas, _ in CAS:
            ca = res[cas]['carte']
            ys = [ca[str(n)]['cases'][str(p)]['niveau_fin_db'] if ca[str(n)]['cases'][str(p)]['etat'] == 'J'
                  else nan for n in notes]
            ax.plot(notes, ys, '-', lw=1.2, label=etiq[cas])
        ax.set_ylabel('niveau établi (dB)')
        ax.set_title('%d Pa (seules les cases qui jouent)' % p, fontsize=9)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8)
    axs[-1].set_xlabel('note MIDI')
    fig.tight_layout()
    fig.savefig(out / 'figure_niveau.png', dpi=200)
    plt.close(fig)

    cand = [c for c, R in CAS if R is not None]
    meilleur = max(cand, key=lambda c: (resumes[c]['jouent'], -(resumes[c]['t_etab_max'] or 1e9)))
    fig, axs = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    for ax, p in zip(axs, (100, 300, 1000)):
        for cas in (meilleur, 'Rfixe_2e8'):
            ca = res[cas]['carte']
            ys = [ca[str(n)]['cases'][str(p)].get('ecart_cents', nan) for n in notes]
            ax.plot(notes, ys, '-', lw=1.2, label=etiq[cas])
        ax.axhline(0, color='k', lw=0.5)
        ax.set_ylabel('écart (cents)')
        ax.set_title('%d Pa' % p, fontsize=9)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8)
    axs[-1].set_xlabel('note MIDI')
    fig.tight_layout()
    fig.savefig(out / 'figure_cents.png', dpi=200)
    plt.close(fig)
    print('meilleur cas :', meilleur)


if __name__ == '__main__':
    principal()
