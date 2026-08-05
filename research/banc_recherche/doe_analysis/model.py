"""Ajustement d'un modèle de plan d'expériences (façon Minitab « Analyze »).

Code les facteurs en [−1, +1], construit la matrice du modèle (constante + effets
principaux + interactions [+ termes quadratiques pour surface de réponse], ajuste
par moindres carrés, puis produit :
  - coefficients, erreurs-types, valeurs t, p-valeurs ;
  - **effets** (2 × coefficient en unités codées) ;
  - **ANOVA** (SS/df/MS/F/p par terme, régression, erreur, total ; manque
    d'ajustement + erreur pure si réplicats) ;
  - R², R²-ajusté, S, et **R²-prédit** (via PRESS).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from .stats import t_sf_two_sided, f_sf


@dataclass
class AnovaRow:
    source: str
    df: int
    ss: float
    ms: float
    f: float
    p: float


@dataclass
class FitResult:
    factors: list          # noms des facteurs
    terms: list            # termes (tuples d'indices ; () = constante)
    term_names: list
    coef: np.ndarray
    se: np.ndarray
    tvals: np.ndarray
    pvals: np.ndarray
    effects: np.ndarray    # NaN pour la constante
    anova: list            # list[AnovaRow]
    r2: float
    r2_adj: float
    r2_pred: float
    s: float
    centers: dict = field(default_factory=dict)
    scales: dict = field(default_factory=dict)

    def predict_coded(self, coded_row: dict) -> float:
        y = 0.0
        for name, t, c in zip(self.term_names, self.terms, self.coef):
            v = 1.0
            for i in t:
                v *= coded_row[self.factors[i]]
            y += c * v
        return y

    def predict(self, values: dict) -> float:
        coded = {f: (values[f] - self.centers[f]) / self.scales[f] for f in self.factors}
        return self.predict_coded(coded)


def _code(F: dict):
    centers, scales, coded = {}, {}, {}
    for name, col in F.items():
        col = np.asarray(col, dtype="float64")
        lo, hi = np.min(col), np.max(col)
        mid = 0.5 * (lo + hi)
        half = 0.5 * (hi - lo) or 1.0
        centers[name], scales[name] = mid, half
        coded[name] = (col - mid) / half
    return coded, centers, scales


def default_terms(nfac: int, interactions: bool = True, quadratic: bool = False):
    terms = [()]                                  # constante
    terms += [(i,) for i in range(nfac)]          # effets principaux
    if interactions:
        terms += [c for c in combinations(range(nfac), 2)]   # interactions 2 f.
    if quadratic:
        terms += [(i, i) for i in range(nfac)]    # termes quadratiques
    return terms


def _term_name(t, factors):
    if not t:
        return "Constante"
    if len(t) == 2 and t[0] == t[1]:
        return f"{factors[t[0]]}²"
    return "·".join(factors[i] for i in t)


def _design(coded, factors, terms):
    n = len(next(iter(coded.values())))
    X = np.ones((n, len(terms)))
    for j, t in enumerate(terms):
        col = np.ones(n)
        for i in t:
            col = col * coded[factors[i]]
        X[:, j] = col
    return X


def fit(F: dict, y, interactions: bool = True, quadratic: bool = False,
        terms=None) -> FitResult:
    """Ajuste le modèle. `F` : {nom_facteur: valeurs} ; `y` : réponse."""
    factors = list(F.keys())
    y = np.asarray(y, dtype="float64")
    n = y.size
    coded, centers, scales = _code(F)
    if terms is None:
        terms = default_terms(len(factors), interactions, quadratic)
    X = _design(coded, factors, terms)
    p = X.shape[1]

    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (X.T @ y)
    yhat = X @ beta
    resid = y - yhat
    sse = float(resid @ resid)
    df_res = max(n - p, 0)
    sst = float(((y - y.mean()) ** 2).sum())
    ssr = sst - sse
    mse = sse / df_res if df_res > 0 else float("nan")
    s = float(np.sqrt(mse)) if df_res > 0 else float("nan")

    safe = df_res > 0 and mse > 0
    cov = mse * XtX_inv
    se = np.sqrt(np.abs(np.diag(cov)))
    with np.errstate(divide="ignore", invalid="ignore"):
        tvals = np.where(se > 0, beta / se, np.nan)
    pvals = np.array([t_sf_two_sided(t, df_res) if (safe and np.isfinite(t)) else np.nan
                      for t in tvals])
    effects = np.array([2.0 * b if t else np.nan for b, t in zip(beta, terms)])

    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    r2_adj = 1.0 - (sse / df_res) / (sst / (n - 1)) if df_res > 0 and sst > 0 else float("nan")
    # R²-prédit via PRESS (résidus prédits par validation croisée « leave-one-out »).
    H = X @ XtX_inv @ X.T
    h = np.clip(np.diag(H), 0, 0.999999)
    press = float(((resid / (1.0 - h)) ** 2).sum())
    r2_pred = 1.0 - press / sst if sst > 0 else float("nan")

    # ANOVA : chaque terme (hors constante) = 1 ddl, SS = t²·MSE (SS ajustée).
    anova = []
    for name, t, tv in zip((_term_name(t, factors) for t in terms), terms, tvals):
        if not t:
            continue
        f = float(tv ** 2) if np.isfinite(tv) else float("nan")
        ss = float(f * mse) if safe else float("nan")
        pp = f_sf(f, 1, df_res) if (safe and np.isfinite(f)) else float("nan")
        anova.append(AnovaRow(name, 1, ss, ss, f, pp))
    ms_reg = ssr / (p - 1) if p > 1 else float("nan")
    f_reg = ms_reg / mse if safe else float("nan")
    anova.append(AnovaRow("Régression", p - 1, ssr, ms_reg, f_reg,
                          f_sf(f_reg, p - 1, df_res) if safe else float("nan")))
    anova += _lack_of_fit(coded, factors, y, yhat, sse, df_res, p)
    anova.append(AnovaRow("Erreur", df_res, sse, mse, np.nan, np.nan))
    anova.append(AnovaRow("Total", n - 1, sst, np.nan, np.nan, np.nan))

    names = [_term_name(t, factors) for t in terms]
    return FitResult(factors, terms, names, beta, se, tvals, pvals, effects,
                     anova, r2, r2_adj, r2_pred, s, centers, scales)


def _lack_of_fit(coded, factors, y, yhat, sse, df_res, p):
    """Décompose l'erreur en manque d'ajustement + erreur pure si réplicats."""
    keys = list(zip(*[np.round(coded[f], 9) for f in factors])) if factors else []
    groups = {}
    for i, key in enumerate(keys):
        groups.setdefault(key, []).append(i)
    ss_pe = 0.0
    df_pe = 0
    for idx in groups.values():
        if len(idx) > 1:
            yy = y[idx]
            ss_pe += float(((yy - yy.mean()) ** 2).sum())
            df_pe += len(idx) - 1
    if df_pe == 0:
        return []
    ss_lof = sse - ss_pe
    df_lof = df_res - df_pe
    if df_lof <= 0:
        return []
    ms_lof, ms_pe = ss_lof / df_lof, ss_pe / df_pe
    f = ms_lof / ms_pe if ms_pe > 0 else float("nan")
    return [
        AnovaRow("  Manque d'ajustement", df_lof, ss_lof, ms_lof, f, f_sf(f, df_lof, df_pe)),
        AnovaRow("  Erreur pure", df_pe, ss_pe, ms_pe, np.nan, np.nan),
    ]


def pareto_effects(res: FitResult):
    """Effets standardisés |t| triés (diagramme de Pareto des effets). Si la
    variance résiduelle est nulle (modèle saturé), on retombe sur |effet|."""
    items = []
    for n, t, e, term in zip(res.term_names, res.tvals, res.effects, res.terms):
        if not term:
            continue
        mag = abs(t) if np.isfinite(t) else abs(e)
        items.append((n, mag))
    return sorted(items, key=lambda x: x[1], reverse=True)


def normal_effects(res: FitResult):
    """(nom, effet, quantile normal) pour le tracé des effets normaux."""
    items = [(n, e) for n, e, term in zip(res.term_names, res.effects, res.terms) if term]
    items.sort(key=lambda x: x[1])
    m = len(items)
    out = []
    for rank, (n, e) in enumerate(items):
        pp = (rank + 0.5) / m
        out.append((n, e, _norm_ppf(pp)))
    return out


def _norm_ppf(p: float) -> float:
    """Quantile normal (approx. Acklam) — pour le graphe des effets."""
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = np.sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= ph:
        q = p - 0.5; r = q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = np.sqrt(-2 * np.log(1 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
