# -*- coding: utf-8 -*-
"""Analyses rapides sur mesures_2023.csv (produit par extraire_mesures.py).

Figures dans journal\\recherche\\figures, résumé chiffré dans analyses_rapides.txt.
1. f0 en fonction de la pression (abaissement de la fréquence avec le souffle).
2. Carte des régimes : où l'anche parle (section x pression), niveau sonore.
3. Contenu harmonique en fonction de la pression.
4. Répétabilité (PPos0 contre PPos1, mêmes réglages) et dérive pendant la séance.
"""
import csv, os, datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = r"J:\claude\business-os\journal\recherche"
FIG = os.path.join(R, "figures")
os.makedirs(FIG, exist_ok=True)
rows = list(csv.DictReader(open(os.path.join(R, "mesures_2023.csv"), encoding="utf-8")))
num = lambda r, k: float(r[k]) if r[k] not in ("", "nan") else np.nan
CAMPS = sorted({r["campagne"] for r in rows})
COUL = plt.cm.viridis(np.linspace(0, 0.9, 8))
txt = []
say = lambda *a: (print(*a), txt.append(" ".join(str(x) for x in a)))

SEUIL_HARM = 0.6  # part d'énergie sur les harmoniques de f0 au-dessus de laquelle on dit « l'anche parle »


def parle(r):
    return num(r, "harmonicite") >= SEUIL_HARM


def pv(r):
    """Pneumatique exploitable : série horodatée correcte ET valeurs physiquement plausibles."""
    return r["pneu_valide"] == "1" and num(r, "p_fin") > 20 and 10 < num(r, "T_fin") < 45 and num(r, "q_fin") > 0


def cents(f, fref):
    return 1200 * np.log2(f / fref)


# ---------- 0. bilan par campagne
for c in CAMPS:
    rc = [r for r in rows if r["campagne"] == c]
    ok = [r for r in rc if parle(r)]
    rv = [r for r in rc if pv(r)]
    f0 = np.array([num(r, "f0") for r in ok])
    T = np.array([num(r, "T_fin") for r in rv])
    p = np.array([num(r, "p_fin") for r in rv])
    say(f"[{c}] enregistrements {len(rc)} ; pneumatique lisible {len(rv)} ; anche qui parle {len(ok)} ({100*len(ok)/len(rc):.0f} %)")
    say(f"   f0 médiane {np.median(f0):.2f} Hz (min {f0.min():.2f}, max {f0.max():.2f}) ; pression fin {np.nanmin(p):.0f} à {np.nanmax(p):.0f} ; T {np.nanmin(T):.1f} à {np.nanmax(T):.1f} °C")
    t = [datetime.datetime.fromisoformat(r["horodatage"]) for r in rc]
    say(f"   début {min(t)} fin {max(t)} durée {(max(t)-min(t))}")

# ---------- 1. f0(p)
fig, axs = plt.subplots(1, len(CAMPS), figsize=(5 * len(CAMPS), 4.2), sharey=True)
for ax, c in zip(axs, CAMPS):
    ok = [r for r in rows if r["campagne"] == c and parle(r) and pv(r)]
    p = np.array([num(r, "p_fin") for r in ok]); f = np.array([num(r, "f0") for r in ok])
    s = np.array([int(r["isec"]) for r in ok])
    fref = np.median(f[p <= np.percentile(p, 15)])
    y = cents(f, fref)
    for i in range(8):
        m = s == i
        if m.any():
            ax.scatter(p[m], y[m], s=6, color=COUL[i], label=f"{ok[np.where(m)[0][0]]['section_mm2']} mm²")
    A = np.vstack([p, np.ones_like(p)]).T
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    r2 = 1 - res[0] / np.sum((y - y.mean()) ** 2) if res.size else np.nan
    xx = np.linspace(p.min(), p.max(), 10)
    ax.plot(xx, coef[0] * xx + coef[1], "k--", lw=1)
    ax.set_title(f"{c}\nf_ref = {fref:.2f} Hz ; pente {100*coef[0]:.2f} cents / 100 u.p.", fontsize=9)
    ax.set_xlabel("pression en régime établi (unité du capteur, Pa probable)")
    ax.grid(alpha=0.3)
    say(f"[f0(p)] {c} : f_ref {fref:.2f} Hz, pente {100*coef[0]:.2f} cents par 100 unités de pression, R2 {r2:.2f}, n {len(ok)}")
    # pente par section (clapet confondu)
    pentes = []
    for i in range(8):
        m = s == i
        if m.sum() > 10:
            ci = np.polyfit(p[m], y[m], 1)
            pentes.append(100 * ci[0])
    say(f"   pentes par section (cents/100) : {np.round(pentes, 2).tolist()}")
axs[0].set_ylabel("écart de f0 (cents)")
axs[0].legend(fontsize=7, markerscale=2, title="section", title_fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "1_f0_pression.png"), dpi=130); plt.close(fig)

# ---------- 2. carte des régimes + niveau
fig, axs = plt.subplots(2, len(CAMPS), figsize=(5 * len(CAMPS), 8))
for j, c in enumerate(CAMPS):
    rc = [r for r in rows if r["campagne"] == c]
    M = np.full((8, 8), np.nan); N = np.zeros((8, 8))
    for r in rc:
        i, k = int(r["isec"]), int(r["ipress"])
        M[i, k] = (0 if np.isnan(M[i, k]) else M[i, k]) + parle(r); N[i, k] += 1
    F = np.where(N > 0, M / np.maximum(N, 1), np.nan)
    ax = axs[0, j]
    im = ax.imshow(F, origin="lower", vmin=0, vmax=1, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(8)); ax.set_yticks(range(8))
    ax.set_yticklabels([60, 75, 90, 105, 120, 135, 150, 180])
    ax.set_xlabel("niveau de commande du ventilateur (0 à 7)", fontsize=8); ax.set_ylabel("section (mm²)")
    ax.set_title(f"{c}\npart des essais où l'anche parle", fontsize=9)
    for i in range(8):
        for k in range(8):
            if N[i, k]:
                ax.text(k, i, f"{int(N[i,k])}", ha="center", va="center", fontsize=6)
    # seuils : plus petit niveau où l'anche parle, par (section, clapet, ppos)
    seuils = {}
    for r in rc:
        key = (r["isec"], r["iclap"], r["ppos"])
        seuils.setdefault(key, []).append((int(r["ipress"]), parle(r), num(r, "p_fin")))
    s0 = []
    for key, L in seuils.items():
        L.sort()
        on = [x for x in L if x[1]]
        s0.append(on[0][0] if on else 99)
    s0 = np.array(s0)
    say(f"[seuil] {c} : niveau de pression du premier son, réparti sur {len(s0)} séries : "
        + ", ".join(f"niveau {v}: {int((s0==v).sum())}" for v in sorted(set(s0.tolist()))) + " (99 = jamais)")
    ax = axs[1, j]
    for r in rc:
        if not pv(r):
            continue
        ax.scatter(num(r, "p_fin"), 20 * np.log10(num(r, "rms_fin")), s=5,
                   color=COUL[int(r["isec"])] if parle(r) else "lightgray")
    ax.set_xlabel("pression en régime établi (unité du capteur)"); ax.set_ylabel("niveau micro (dB pleine échelle)")
    ax.set_title("niveau sonore ; gris = l'anche ne parle pas", fontsize=9); ax.grid(alpha=0.3)
fig.colorbar(im, ax=axs[0, :].tolist(), shrink=0.8)
fig.savefig(os.path.join(FIG, "2_carte_regimes.png"), dpi=130, bbox_inches="tight"); plt.close(fig)

# ---------- 3. harmoniques
fig, axs = plt.subplots(1, len(CAMPS), figsize=(5 * len(CAMPS), 4.2), sharey=True)
for ax, c in zip(axs, CAMPS):
    ok = [r for r in rows if r["campagne"] == c and parle(r) and pv(r)]
    ip = np.array([int(r["ipress"]) for r in ok]); p = np.array([num(r, "p_fin") for r in ok])
    for k, col in zip(range(1, 7), plt.cm.plasma(np.linspace(0, 0.85, 6))):
        h = np.array([num(r, f"H{k}_dB") for r in ok])
        xs, ys = [], []
        for lv in sorted(set(ip)):
            m = ip == lv
            if m.sum() > 5:
                xs.append(np.median(p[m])); ys.append(np.median(h[m]))
        ax.plot(xs, ys, "o-", color=col, label=f"H{k}")
    cen = [np.median([num(r, "centroide_harm") for r in ok if int(r["ipress"]) == lv]) for lv in sorted(set(ip))]
    say(f"[harmoniques] {c} : rang du centre de gravité harmonique par niveau de pression : {np.round(cen, 2).tolist()}")
    ax.set_title(c, fontsize=9); ax.set_xlabel("pression (unité du capteur)"); ax.grid(alpha=0.3)
axs[0].set_ylabel("amplitude relative au plus fort harmonique (dB)"); axs[0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "3_harmoniques_pression.png"), dpi=130); plt.close(fig)

# ---------- 4. répétabilité et dérive
fig, axs = plt.subplots(2, len(CAMPS), figsize=(5 * len(CAMPS), 7.5))
for j, c in enumerate(CAMPS):
    rc = [r for r in rows if r["campagne"] == c]
    d = {}
    for r in rc:
        if parle(r):
            d[(r["ppos"], r["isec"], r["ipress"], r["iclap"])] = r
    diffs, dp = [], []
    for (pp, s, p, cl), r in d.items():
        if pp == "0" and ("1", s, p, cl) in d:
            r1 = d[("1", s, p, cl)]
            diffs.append(cents(num(r1, "f0"), num(r, "f0")))
            dp.append(num(r1, "p_fin") - num(r, "p_fin"))
    ax = axs[0, j]
    if diffs:
        diffs = np.array(diffs); dp = np.array(dp)
        ax.hist(diffs, bins=40, color="steelblue")
        say(f"[répétabilité] {c} : {len(diffs)} paires PPos0/PPos1 ; écart f0 médian {np.median(diffs):+.2f} cents, "
            f"écart-type {np.std(diffs):.2f} cents, 90 % entre {np.percentile(diffs,5):+.1f} et {np.percentile(diffs,95):+.1f} ; "
            f"écart de pression médian {np.nanmedian(dp):+.0f}")
        ax.set_title(f"{c}\nf0 (2e passage) - f0 (1er passage), mêmes réglages", fontsize=9)
        ax.set_xlabel("cents")
    else:
        ax.text(0.5, 0.5, "pas de 2e passage", ha="center", transform=ax.transAxes); ax.set_axis_off()
        say(f"[répétabilité] {c} : pas de second passage")
    ax = axs[1, j]
    t0 = min(datetime.datetime.fromisoformat(r["horodatage"]) for r in rc)
    tt = np.array([(datetime.datetime.fromisoformat(r["horodatage"]) - t0).total_seconds() / 60 for r in rc])
    T = np.array([num(r, "T_fin") if pv(r) else np.nan for r in rc])
    ax.plot(tt, T, ".", ms=2, color="firebrick"); ax.set_ylabel("température (°C)", color="firebrick")
    ax.set_xlabel("minutes depuis le début de la séance")
    ax2 = ax.twinx()
    ok = np.array([parle(r) for r in rc]); f = np.array([num(r, "f0") for r in rc])
    ax2.plot(tt[ok], f[ok], ".", ms=2, color="navy", alpha=0.5); ax2.set_ylabel("f0 (Hz)", color="navy")
    m = ~np.isnan(T)
    say(f"[dérive] {c} : température de {np.nanmin(T):.1f} à {np.nanmax(T):.1f} °C ; "
        f"corrélation T / temps {np.corrcoef(tt[m], T[m])[0,1]:.2f}")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "4_repetabilite_derive.png"), dpi=130); plt.close(fig)

# ---------- 5. caractéristique de la source (E1 de experiences_a_mener.md) : p contre q à commande fixe
fig, axs = plt.subplots(1, len(CAMPS), figsize=(5 * len(CAMPS), 4.2), sharey=True)
for ax, c in zip(axs, CAMPS):
    rc = [r for r in rows if r["campagne"] == c and pv(r)]
    pentes = []
    for lv, col in zip(range(8), plt.cm.cividis(np.linspace(0, 0.95, 8))):
        m = [r for r in rc if int(r["ipress"]) == lv]
        if len(m) < 10:
            continue
        q = np.array([num(r, "q_fin") for r in m]); p = np.array([num(r, "p_fin") for r in m])
        g = ~(np.isnan(q) | np.isnan(p))
        ax.scatter(q[g], p[g], s=5, color=col, label=f"niveau {lv}")
        if np.ptp(q[g]) > 3:
            a = np.polyfit(q[g], p[g], 1)
            rr = np.corrcoef(q[g], p[g])[0, 1]
            pentes.append((lv, round(a[0], 1), round(rr, 2), round(np.median(p[g])), round(np.median(q[g]), 1)))
    say(f"[source p(q)] {c} : (niveau, pente dp/dq en unités p par l/min, r, p médiane, q médian) = {pentes}")
    ax.set_title(c, fontsize=9); ax.set_xlabel("débit en régime établi (l/min, SFM3000)"); ax.grid(alpha=0.3)
axs[0].set_ylabel("pression en régime établi (unité du capteur)"); axs[0].legend(fontsize=6, markerscale=2)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "5_source_pression_debit.png"), dpi=130); plt.close(fig)

open(os.path.join(R, "analyses_rapides.txt"), "w", encoding="utf-8").write("\n".join(txt) + "\n")
