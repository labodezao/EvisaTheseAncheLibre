import numpy as np

from banc_recherche.doe_analysis import model, design, optimize, stats


# ---- stats (p-valeurs sans scipy) ------------------------------------------
def test_beta_symmetry():
    assert abs(stats.betai(0.5, 0.5, 0.5) - 0.5) < 1e-9


def test_f_and_t_known_values():
    # F(1;1,1) > 1 → p = 0.5 ; |t|>1 avec df=1 (Cauchy) → p = 0.5.
    assert abs(stats.f_sf(1.0, 1, 1) - 0.5) < 1e-6
    assert abs(stats.t_sf_two_sided(1.0, 1) - 0.5) < 1e-6
    assert stats.t_sf_two_sided(0.0, 5) == 1.0 or abs(stats.t_sf_two_sided(0.0, 5) - 1.0) < 1e-9


# ---- model (ajustement factoriel, ANOVA, effets) ---------------------------
def test_factorial_recovers_effects_and_significance():
    base = design.two_level(3)
    X = np.vstack([base, base])                 # 2 réplicats → 16 runs
    A, B, C = X[:, 0], X[:, 1], X[:, 2]
    rng = np.random.default_rng(0)
    y = 10 + 3 * A + 2 * A * C + rng.normal(0, 0.3, len(A))   # B sans effet
    res = model.fit({"A": A, "B": B, "C": C}, y, interactions=True)
    coef = dict(zip(res.term_names, res.coef))
    pval = dict(zip(res.term_names, res.pvals))
    assert abs(coef["A"] - 3.0) < 0.3
    assert abs(coef["A·C"] - 2.0) < 0.3
    assert abs(coef["B"]) < 0.3
    assert pval["A"] < 0.01 and pval["A·C"] < 0.01
    assert pval["B"] > 0.1                       # facteur inerte : non significatif
    assert res.r2 > 0.9
    # effet = 2 × coefficient
    eff = dict(zip(res.term_names, res.effects))
    assert abs(eff["A"] - 2 * coef["A"]) < 1e-9


def test_pareto_sorted_desc():
    base = design.two_level(3)
    A, B, C = base[:, 0], base[:, 1], base[:, 2]
    y = 5 + 4 * A + 1 * B
    res = model.fit({"A": A, "B": B, "C": C}, y, interactions=False)
    par = model.pareto_effects(res)
    assert par[0][0] == "A"                       # A domine
    assert all(par[i][1] >= par[i + 1][1] for i in range(len(par) - 1))


# ---- design (générateurs) --------------------------------------------------
def test_full_and_fractional():
    assert design.full_factorial(3).shape == (8, 3)
    fr = design.fractional_factorial(3, {3: (0, 1, 2)})
    assert fr.shape == (8, 4)
    assert np.allclose(fr[:, 3], fr[:, 0] * fr[:, 1] * fr[:, 2])   # D = A·B·C


def test_plackett_burman_balanced():
    pb = design.plackett_burman(12)
    assert pb.shape == (12, 11)
    assert np.allclose(pb.sum(axis=0), 0.0)       # colonnes équilibrées


def test_ccd_and_bbd_shapes():
    ccd = design.central_composite(2, n_center=4)
    assert ccd.shape == (4 + 4 + 4, 2)
    assert np.isclose(np.abs(ccd).max(), 2 ** 0.5)   # α rotatable = 4^0.25
    bbd = design.box_behnken(3, n_center=3)
    assert bbd.shape == (3 * 4 + 3, 3)


# ---- optimize (désirabilité) -----------------------------------------------
def test_desirability_functions():
    assert optimize.d_max(5, 0, 10) == 0.5
    assert optimize.d_min(5, 0, 10) == 0.5
    assert optimize.d_max(-1, 0, 10) == 0.0 and optimize.d_max(11, 0, 10) == 1.0


def test_optimizer_finds_maximum():
    g = optimize.Goal(predict=lambda v: v["x"], kind="max", low=0, high=10)
    r = optimize.optimize([g], {"x": (0, 10)}, grid=11)
    assert abs(r.best["x"] - 10) < 1e-9
    assert abs(r.composite - 1.0) < 1e-9
