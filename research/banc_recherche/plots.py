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


# ---- Graphes de bifurcation / stochastique ---------------------------------
def bifurcation_diagram(bd):
    """Diagramme de bifurcation : amplitude vs paramètre, branches montée/
    descente, seuils μ_on/μ_off marqués."""
    plt = _lazy_plt()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(bd.param_up, bd.amp_up, ".-", label="montée", ms=3)
    if len(bd.param_down):
        ax.plot(bd.param_down, bd.amp_down, ".-", label="descente", ms=3)
    for mu, lab in ((bd.mu_on, "μ_on"), (bd.mu_off, "μ_off")):
        if mu == mu:
            ax.axvline(mu, ls="--", lw=0.8)
            ax.text(mu, ax.get_ylim()[1] * 0.9, lab, fontsize=8)
    ax.set_xlabel("paramètre de contrôle (pression / vitesse)")
    ax.set_ylabel("amplitude (paramètre d'ordre)")
    ax.set_title(f"Bifurcation — {bd.kind} (hystérésis {bd.hysteresis:.3g})")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    return fig


def potential_plot(x, phi):
    """Potentiel effectif Φ(x) : un puits = monostable, deux = bistable."""
    plt = _lazy_plt()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x, phi)
    ax.set_xlabel("paramètre d'ordre x"); ax.set_ylabel("Φ(x)")
    ax.set_title("Potentiel effectif"); ax.grid(alpha=0.3)
    return fig


def drift_diffusion_plot(km):
    """Coefficients de Kramers-Moyal : drift D₁(x) (zéros = points fixes) et
    diffusion D₂(x)."""
    plt = _lazy_plt()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    a1.plot(km.x, km.drift, "o-"); a1.axhline(0, color="grey", lw=0.8)
    a1.set_xlabel("x"); a1.set_ylabel("D₁ (drift)"); a1.grid(alpha=0.3)
    a2.plot(km.x, km.diffusion, "o-")
    a2.set_xlabel("x"); a2.set_ylabel("D₂ (diffusion)"); a2.grid(alpha=0.3)
    return fig


def early_warning_plot(ew):
    """Précurseurs : variance et autocorrélation (AR1) vs paramètre."""
    plt = _lazy_plt()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    a1.plot(ew.param, ew.variance, "o-"); a1.set_ylabel("variance")
    a1.set_xlabel("paramètre"); a1.grid(alpha=0.3)
    a2.plot(ew.param, ew.autocorr1, "o-"); a2.set_ylabel("autocorr. (AR1)")
    a2.set_xlabel("paramètre"); a2.grid(alpha=0.3)
    fig.suptitle("Signaux précurseurs (ralentissement critique)")
    return fig


# ---- Graphes d'analyse DOE (façon Minitab) ---------------------------------
def main_effects_plot(df, response, factors):
    """Graphe des effets principaux : moyenne de la réponse par niveau de chaque
    facteur."""
    plt = _lazy_plt()
    fig, axes = plt.subplots(1, len(factors), figsize=(3.2 * len(factors), 3.6), sharey=True)
    if len(factors) == 1:
        axes = [axes]
    gmean = df[response].mean()
    for ax, f in zip(axes, factors):
        g = df.groupby(f)[response].mean()
        ax.plot(g.index, g.values, "o-")
        ax.axhline(gmean, ls="--", lw=0.8, color="grey")
        ax.set_xlabel(f)
    axes[0].set_ylabel(response)
    fig.suptitle(f"Effets principaux — {response}")
    return fig


def interaction_plot(df, response, f1, f2):
    """Graphe d'interaction f1×f2 : une courbe de réponse par niveau de f2."""
    plt = _lazy_plt()
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for lvl, g in df.groupby(f2):
        gg = g.groupby(f1)[response].mean()
        ax.plot(gg.index, gg.values, "o-", label=f"{f2}={lvl}")
    ax.set_xlabel(f1); ax.set_ylabel(response)
    ax.legend(fontsize=8, title=f2); ax.grid(alpha=0.3)
    ax.set_title(f"Interaction {f1}×{f2} — {response}")
    return fig


def pareto_plot(res):
    """Diagramme de Pareto des effets standardisés (barres horizontales triées)."""
    from .doe_analysis import model
    plt = _lazy_plt()
    items = model.pareto_effects(res)
    names = [n for n, _ in items][::-1]
    mags = [m for _, m in items][::-1]
    fig, ax = plt.subplots(figsize=(6, 0.5 * len(names) + 1.5))
    ax.barh(names, mags)
    ax.set_xlabel("|effet standardisé|")
    ax.set_title("Pareto des effets")
    return fig


def contour_plot(res, fx, fy, bounds, others=None, grid=40):
    """Contour de la réponse prédite dans le plan (fx, fy), autres facteurs fixés."""
    plt = _lazy_plt()
    xs = np.linspace(bounds[fx][0], bounds[fx][1], grid)
    ys = np.linspace(bounds[fy][0], bounds[fy][1], grid)
    Z = np.zeros((grid, grid))
    base = dict(others or {})
    for i, yv in enumerate(ys):
        for j, xv in enumerate(xs):
            vals = dict(base); vals[fx] = xv; vals[fy] = yv
            Z[i, j] = res.predict(vals)
    fig, ax = plt.subplots(figsize=(6, 5))
    cs = ax.contourf(xs, ys, Z, levels=14, cmap="viridis")
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel(fx); ax.set_ylabel(fy)
    ax.set_title("Réponse prédite")
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
