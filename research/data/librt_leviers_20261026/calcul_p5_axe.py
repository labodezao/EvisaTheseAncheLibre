"""P5 sous la contrainte d'Ewen (26/10) : trou SANS oeil, centré sur l'axe de la bande, déplacé seulement le long de cet axe.
Pour chaque chaîne : trou de la tige (T) le long de l'axe local de la tige, ou trou du levier r (H) le long de l'axe local du levier."""
import os, sys, json, math
import numpy as np
HERE = r"J:\zw3d_travail\librt\propositions_leviers_20261026"
src = open(os.path.join(HERE, "calcul_p4_p5.py"), encoding="utf-8").read().rsplit("\nmain2()", 1)[0]
g = {"__file__": os.path.join(HERE, "calcul_p4_p5.py"), "__name__": "p45"}
exec(compile(src, "calcul_p4_p5.py", "exec"), g)
C, TIGE, LEV, D, CIBLE, SENS0, _res = g["C"], g["TIGE"], g["LEV"], g["D"], g["CIBLE"], g["SENS0"], g["_res"]


def axe_local(piece, p, r=8.0):
    """Axe de la bande autour de p : direction principale des points du contour à moins de r, et point milieu de la bande (projection)."""
    b = np.array(piece.ext.exterior.coords)
    seg = []
    for a, c in zip(b[:-1], b[1:]):
        for t in np.linspace(0, 1, max(2, int(np.linalg.norm(c - a) / 0.2))):
            seg.append(a + t * (c - a))
    P = np.array(seg)
    P = P[np.linalg.norm(P - p, axis=1) < r]
    m = P.mean(0)
    w, v = np.linalg.eigh(np.cov((P - m).T))
    u = v[:, -1]
    n_ = np.array([-u[1], u[0]])
    off = (P - m) @ n_
    centre = m + n_ * (off.max() + off.min()) / 2       # ligne médiane de la bande
    return u, centre, (off.max() - off.min())


def balayage(n, quoi):
    c = C[n]
    T, H = np.array(c["T"]), np.array(c["H"])
    piece = TIGE[n] if quoi == "T" else LEV[c["r"]]
    p = T if quoi == "T" else H
    u, mil, larg = axe_local(piece, p)
    lat = float((p - mil) @ np.array([-u[1], u[0]]))       # le trou d'origine est-il centré ?
    best = None
    for t in np.arange(-25, 25.01, 0.05):
        q = p + t * u
        TT_, HH_ = (tuple(q), tuple(H)) if quoi == "T" else (tuple(T), tuple(q))
        try:
            r = _res(c, TT_, HH_, D)
        except Exception:
            continue
        if r["sens_queue"] != SENS0[n] or not np.isfinite(r["rapport_exact"]):
            continue
        a = piece.analyse(np.array([q]))
        lig = float(min(a["lig_ext"][0], a["lig_int"][0]))
        if lig < 0:
            continue
        k = (abs(r["rapport_exact"] - CIBLE), abs(t))
        if best is None or k < best[0]:
            best = (k, dict(t=round(float(t), 2), rapport=round(r["rapport_exact"], 3), levee=round(r["levee"], 2), ligament=round(lig, 2)))
    base = _res(c, tuple(T), tuple(H), D)
    return dict(chaine=n, trou=quoi, largeur_bande=round(larg, 2), decal_lateral_origine=round(lat, 2),
                rapport_avant=round(base["rapport_exact"], 3), **(best[1] if best else {"t": None}))


out = [balayage(n, q) for n in g["CHAINES"] for q in ("T", "H")]
for o in out:
    print(o)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p5_axe.json"), "w"), indent=1)
