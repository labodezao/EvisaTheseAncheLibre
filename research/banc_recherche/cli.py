"""Interface en ligne de commande du banc de recherche.

Permet de rejouer une campagne et de produire `plan_exp.csv` + figures **sans**
ouvrir la GUI (utile en lot, sur serveur, ou pour la reproductibilité) :

    banc-recherche-cli batch data/Measure_dataset_....hdf5 --plots out/
    banc-recherche-cli devices
    banc-recherche-cli gui
    banc-recherche-cli seuils seuils_2026-10-03.csv --png seuils.png
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


def _fmt(x, d=0):
    return "—" if x != x else f"{x:.{d}f}"


def _cmd_seuils(args) -> int:
    """Seuils d'auto-entretien d'un export « Seuils » de l'onglet Banc :
    démarrage, extinction, plaquage, reprise, par cycle puis en moyenne."""
    import numpy as np
    from . import seuil

    d = seuil.read_bench_csv(args.csv)
    if not d["t_s"].size:
        print(f"{args.csv} : aucune ligne de mesure.")
        return 1
    q = d["q_slm"] if np.isfinite(d["q_slm"]).any() else None
    res = seuil.analyse_run(d["t_s"], d["p_Pa"], d["level_db"], d["clarity"], q=q,
                            lag_s=args.lag, clarity_min=args.clarte,
                            margin_db=args.marge, hold_s=args.maintien,
                            min_rise=args.min_rise)
    s = res.summary
    print(f"{args.csv} — {d['t_s'].size} instants, fond {res.floor_db:.1f} dB, "
          f"{len(s.cycles)} cycle(s) montée-descente")
    print(f"{'cycle':>5} {'p_on':>7} {'p_off':>7} {'p_plaq':>7} {'p_rep':>7} "
          f"{'hyst':>6} {'plage':>7} {'rapport':>7}")
    for k, c in enumerate(s.cycles, 1):
        print(f"{k:>5} {_fmt(c.p_on):>7} {_fmt(c.p_off):>7} {_fmt(c.p_choke):>7} "
              f"{_fmt(c.p_unchoke):>7} {_fmt(c.hysteresis):>6} "
              f"{_fmt(c.usable_range):>7} {_fmt(c.ratio, 2):>7}")
    if s.cycles:
        print("moyenne ± écart-type (Pa) : " + ", ".join(
            f"{k} {_fmt(s.mean[k])} ± {_fmt(s.std[k])}"
            for k in ("p_on", "p_off", "p_choke", "p_unchoke")))
    c, n, r2 = res.flow
    if c == c:
        print(f"débit quand l'anche sonne : q = {c:.3g} · p^{n:.2f} L/min "
              f"(r² {r2:.2f} ; 0,5 = orifice, 1 = visqueux)")
    if args.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2 if q is not None else 1, figsize=(11, 4), squeeze=False)
        a0 = ax[0, 0]
        rising = np.gradient(res.p, res.t) >= 0
        for m, lab, col in ((rising, "montée", "C3"), (~rising, "descente", "C0")):
            a0.plot(res.p[m], res.level_db[m], ".", ms=2, color=col, label=lab)
        for c_ in s.cycles:
            for v, ls in ((c_.p_on, "-"), (c_.p_off, "--"), (c_.p_choke, ":")):
                if v == v:
                    a0.axvline(v, color="k", ls=ls, lw=0.6)
        a0.set_xlabel("pression (Pa)"); a0.set_ylabel("niveau (dB)")
        a0.legend(); a0.set_title("niveau sonore et seuils")
        if q is not None:
            a1 = ax[0, 1]
            a1.plot(res.p[res.osc], res.q[res.osc], ".", ms=2, color="C2", label="sonne")
            a1.plot(res.p[~res.osc], res.q[~res.osc], ".", ms=2, color="0.6", label="muette")
            a1.set_xlabel("pression (Pa)"); a1.set_ylabel("débit (L/min)")
            a1.legend(); a1.set_title("consommation d'air")
        fig.tight_layout(); fig.savefig(args.png, dpi=150)
        print(f"figure → {args.png}")
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

    s = sub.add_parser("seuils",
                       help="seuils d'auto-entretien (export Seuils de l'onglet Banc)")
    s.add_argument("csv", help="seuils_*.csv exporté par l'onglet Banc")
    s.add_argument("--lag", type=float, default=0.0,
                   help="retard du capteur de pression à corriger (s)")
    s.add_argument("--clarte", type=float, default=0.8,
                   help="périodicité minimale pour dire « l'anche sonne » (0..1)")
    s.add_argument("--marge", type=float, default=6.0,
                   help="marge au-dessus du fond de souffle (dB)")
    s.add_argument("--maintien", type=float, default=0.15,
                   help="durée minimale d'un changement d'état (s)")
    s.add_argument("--min-rise", type=float, default=20.0,
                   help="amplitude minimale d'une rampe pour compter un cycle (Pa)")
    s.add_argument("--png", help="enregistrer la figure niveau/débit en fonction de p")
    s.set_defaults(func=_cmd_seuils)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
