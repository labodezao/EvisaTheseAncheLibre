"""Tracés de synthèse d'une campagne (`plan_exp.csv`).

Reprend le rôle de `plotsmeasure.py` : à partir de la table de résultats
(sortie de `batch.analyse_campaign`), produit les vues usuelles — impédance et
Tresp en fonction de la pression, cartes Section×Pression. Renvoie des objets
Figure matplotlib (la GUI les intègre, ou on les enregistre en PNG).
"""
from __future__ import annotations

import numpy as np


def _lazy_plt():
    import matplotlib
    matplotlib.use("Agg")           # sûr hors écran ; la GUI passe un backend Qt
    import matplotlib.pyplot as plt
    return plt


def load_csv(csv_path: str):
    import pandas as pd
    return pd.read_csv(csv_path)


def impedance_vs_pressure(df, section=None):
    """Impédance P/Q en fonction de la pression, une courbe par section."""
    plt = _lazy_plt()
    fig, ax = plt.subplots(figsize=(8, 5))
    sub = df if section is None else df[df["S_plus"] == section]
    for s, g in sub.groupby("S_plus"):
        g = g.sort_values("Press_In_Mean")
        ax.plot(g["Press_In_Mean"], g["Impedence"], "o-", label=f"section {int(s)}")
    ax.set_xlabel("Pression moyenne [Pa]")
    ax.set_ylabel("Impédance P/Q")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return fig


def tresp_map(df):
    """Carte Tresp sur la grille Section × Pression (moyenne sur clapets/sens)."""
    plt = _lazy_plt()
    piv = df.pivot_table(index="S_plus", columns="P_plus", values="Tresp", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(piv.values, origin="lower", aspect="auto", cmap="afmhot")
    ax.set_xlabel("Pression (index)")
    ax.set_ylabel("Section (index)")
    fig.colorbar(im, ax=ax, label="Tresp [s]")
    return fig


def formants_vs_pressure(df):
    """Formants F1–F4 moyens en fonction de la pression."""
    plt = _lazy_plt()
    fig, ax = plt.subplots(figsize=(8, 5))
    g = df.groupby("P_plus")[["Form1", "Form2", "Form3", "Form4"]].mean()
    for col in ("Form1", "Form2", "Form3", "Form4"):
        ax.plot(g.index, g[col], "o-", label=col)
    ax.set_xlabel("Pression (index)")
    ax.set_ylabel("Fréquence formant [Hz]")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return fig
