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
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
