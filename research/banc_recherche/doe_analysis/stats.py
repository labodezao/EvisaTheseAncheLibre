"""Distributions Student-t et Fisher-F **sans scipy** (pour les p-valeurs DOE).

Repose sur la fonction bêta incomplète régularisée `I_x(a,b)` (fraction continue,
Numerical Recipes) et sur `gammaln` (Lanczos). Suffisant pour les tests t/F de
l'ANOVA. Vérifié : F(1;1,1)>1 → p=0.5 ; |t|>1, df=1 → p=0.5 (Cauchy).
"""
from __future__ import annotations

import math

_LANCZOS = (
    676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012,
    9.9843695780195716e-6, 1.5056327351493116e-7,
)


def gammaln(x: float) -> float:
    """ln Γ(x), x > 0 (approximation de Lanczos)."""
    if x < 0.5:
        return math.log(math.pi / math.sin(math.pi * x)) - gammaln(1.0 - x)
    x -= 1.0
    a = 0.99999999999980993
    t = x + 7.5
    for i, c in enumerate(_LANCZOS):
        a += c / (x + i + 1.0)
    return 0.5 * math.log(2 * math.pi) + (x + 0.5) * math.log(t) - t + math.log(a)


def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 200, 3e-14, 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Fonction bêta incomplète régularisée I_x(a, b), 0 ≤ x ≤ 1."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(gammaln(a + b) - gammaln(a) - gammaln(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_sf_two_sided(t: float, df: float) -> float:
    """p-valeur bilatérale d'un test de Student : P(|T| > |t|)."""
    if df <= 0:
        return float("nan")
    t2 = float(t) * float(t)
    return betai(df / 2.0, 0.5, df / (df + t2))


def f_sf(f: float, df1: float, df2: float) -> float:
    """Survie de Fisher : P(F > f) pour F ~ F(df1, df2)."""
    if f <= 0 or df1 <= 0 or df2 <= 0:
        return 1.0 if f <= 0 else float("nan")
    return betai(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * f))
