"""Analyse de plans d'expériences — équivalent Python de la suite DOE de Minitab.

- `model`   : ajustement factoriel / surface de réponse, ANOVA, effets, R²/R²aj/R²préd.
- `design`  : générateurs (factoriel complet/fractionnaire, Plackett-Burman, CCD, Box-Behnken).
- `optimize`: optimiseur de réponses par désirabilité.
- `stats`   : distributions t/F (p-valeurs) sans scipy.

Analyse depuis une DataFrame (`plan_exp.csv`) via `analyze_csv`, ou directement
avec des tableaux via `model.fit`.
"""
from . import model, design, optimize, stats


def analyze(df, response: str, factors: list, interactions: bool = True,
            quadratic: bool = False):
    """Ajuste un modèle DOE depuis une DataFrame. Renvoie un `model.FitResult`."""
    F = {f: df[f].to_numpy(dtype="float64") for f in factors}
    y = df[response].to_numpy(dtype="float64")
    return model.fit(F, y, interactions=interactions, quadratic=quadratic)


def summary(res) -> str:
    """Résumé texte type Minitab (coefficients, ANOVA, R²)."""
    lines = ["Terme            Effet    Coef   ErT     T       P"]
    for n, e, c, se, t, p in zip(res.term_names, res.effects, res.coef,
                                 res.se, res.tvals, res.pvals):
        eff = "      —" if n == "Constante" else f"{e:7.3f}"
        lines.append(f"{n:14s} {eff} {c:7.3f} {se:6.3f} {t:7.2f} {p:7.3f}")
    lines.append("")
    lines.append(f"S = {res.s:.4g}   R² = {res.r2*100:.2f}%   "
                 f"R²(aj) = {res.r2_adj*100:.2f}%   R²(préd) = {res.r2_pred*100:.2f}%")
    lines.append("")
    lines.append("ANOVA  Source                DF      SS      MS      F      P")
    for r in res.anova:
        f = "     —" if r.f != r.f else f"{r.f:6.2f}"       # NaN → —
        p = "    —" if r.p != r.p else f"{r.p:5.3f}"
        ms = "      —" if r.ms != r.ms else f"{r.ms:8.3g}"
        lines.append(f"       {r.source:20s} {r.df:3d} {r.ss:9.3g} {ms} {f} {p}")
    return "\n".join(lines)
