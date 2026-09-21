"""Interface en ligne de commande du banc de recherche.

Permet de rejouer une campagne et de produire `plan_exp.csv` + figures **sans**
ouvrir la GUI (utile en lot, sur serveur, ou pour la reproductibilité) :

    banc-recherche-cli batch data/Measure_dataset_....hdf5 --plots out/
    banc-recherche-cli devices
    banc-recherche-cli gui
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys


def _cmd_batch(args) -> int:
    from . import batch
    def prog(k, tot, msg):
        print(f"\r[{k:>5}/{tot}] {msg}", end="", file=sys.stderr, flush=True)
    df = batch.analyse_campaign(args.hdf5, samplerate=args.sr,
                                csv_path=args.csv, progress=prog)
    print(f"\n{len(df)} points → {args.csv}", file=sys.stderr)
    if args.plots:
        from . import plots
        os.makedirs(args.plots, exist_ok=True)
        figs = {
            "impedance_vs_pressure.png": plots.impedance_vs_pressure,
            "tresp_map.png": plots.tresp_map,
            "formants_vs_pressure.png": plots.formants_vs_pressure,
        }
        for name, fn in figs.items():
            try:
                fig = fn(df)
                fig.savefig(os.path.join(args.plots, name), dpi=150)
            except Exception as e:                       # une figure ratée n'arrête pas le lot
                print(f"  ! {name}: {e}", file=sys.stderr)
        print(f"figures → {args.plots}/", file=sys.stderr)
    return 0


def _cmd_devices(_args) -> int:
    from . import audio
    print(audio.list_devices())
    return 0


def _cmd_gui(_args) -> int:
    from .gui.app import main
    return main()


def _cmd_justesse(args) -> int:
    """Ce qu'une perce donne, doigté par doigté, contre ce qu'elle vise.

    L'écart **médian** se rattrape : on pousse l'anche, on allonge le bocal,
    on change de diapason. C'est la **dispersion** autour de cette médiane
    qui juge une perce, parce que rien ne la rattrape — sauf les doigts et
    les lèvres du musicien, qui ont mieux à faire.
    """
    import numpy as np
    from . import tutt

    dat = tutt.read_dat(args.dat)
    if not dat.fingerings:
        print(f"{args.dat} : aucun doigté dans ce fichier.")
        return 1
    table = tutt.justesse(dat, jet=not args.sans_jet, n_points=args.points)
    titre = dat.title or pathlib.Path(args.dat).stem
    print(f"{titre} — {len(dat.lengths)} tronçons, "
          f"{dat.total_length_m * 1e3:.0f} mm, "
          f"{'anche solide' if dat.solid_reed else 'anche aérienne (flûte)'}, "
          f"la = {dat.a4_hz:g} Hz")
    print(f"{'doigté':<12}{'visé':>10}{'obtenu':>10}{'cents':>9}")
    for nom, cible, f, cents in table:
        obtenu = f"{f:10.1f}" if f == f else f"{'—':>10}"
        ecart = f"{cents:+9.1f}" if cents == cents else f"{'—':>9}"
        print(f"{nom.strip():<12}{cible:10.1f}{obtenu}{ecart}")
    c = np.array([x[3] for x in table], dtype=float)
    c = c[~np.isnan(c)]
    if len(c):
        med = float(np.median(c))
        print(f"\nécart médian {med:+.1f} cents (rattrapable), "
              f"dispersion autour {float((c - med).std()):.1f} cents, "
              f"étendue {float(c.max() - c.min()):.0f} cents")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="banc-recherche-cli",
                                description="Banc de recherche — anches libres")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("batch", help="analyser une campagne HDF5 → plan_exp.csv")
    b.add_argument("hdf5", help="fichier HDF5 de campagne (Mesures.py)")
    b.add_argument("--sr", type=int, default=48000, help="fréquence d'échantillonnage audio")
    b.add_argument("--csv", default="plan_exp.csv", help="CSV de sortie")
    b.add_argument("--plots", metavar="DIR", help="dossier où enregistrer les figures")
    b.set_defaults(func=_cmd_batch)

    d = sub.add_parser("devices", help="lister les périphériques audio (Behringer)")
    d.set_defaults(func=_cmd_devices)

    g = sub.add_parser("gui", help="lancer l'interface graphique")
    g.set_defaults(func=_cmd_gui)

    j = sub.add_parser("justesse",
                       help="table de justesse d'une perce TUTT (.dat)")
    j.add_argument("dat", help="fichier d'entrée TUTT")
    j.add_argument("--sans-jet", action="store_true",
                   help="une seule passe, sans effet de jet dans les trous")
    j.add_argument("--points", type=int, default=3000,
                   help="finesse du balayage autour de chaque note")
    j.set_defaults(func=_cmd_justesse)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
