"""Calcul des propositions de leviers LibRT (26/10/2026). Calcul seul, rien n'est modifie."""
import json, math, os
BASE = r"J:\zw3d_travail\librt"
REL = json.load(open(BASE + r"\audit_leviers_20261026\releve_chaines.json"))
CON = json.load(open(BASE + r"\leviers_035\contours.json"))
OUT = os.path.dirname(os.path.abspath(__file__))
PR = tuple(REL["pivots"]["r1_r2_r3"]["xy"])
YP_CONTACT = 7.0
Y_QUEUE = 73.4
CX = {"r1": 126.0, "r2": 91.0, "r3": 56.0}
F_BASE = 177.0
D_TROU = 3.0
CHAINES = ["A1", "A2", "A3", "B1", "B2", "B3"]


def rot(p, c, th):
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(th) - y * math.sin(th), c[1] + x * math.sin(th) + y * math.cos(th))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def bisect(f, a, b):
    fa = f(a)
    for _ in range(100):
        m = (a + b) / 2
        fm = f(m)
        if (fa < 0) == (fm < 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def racine_proche_zero(f, lo=-1.0, hi=1.0, n=2000):
    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    best = None
    prev = f(xs[0])
    for i in range(1, n + 1):
        cur = f(xs[i])
        if prev == 0 or prev * cur < 0:
            r = bisect(f, xs[i - 1], xs[i])
            if best is None or abs(r) < abs(best):
                best = r
        prev = cur
    return best


def chaine_def(nom):
    ch = REL["chaines"][nom]
    r = "r" + nom[1]
    lv = REL["leviers_r"][r]
    H = tuple(lv["trou_autre"]["xy"]) if nom[0] == "A" else tuple(lv["trou_attache_B"]["xy"])
    return dict(nom=nom, r=r, piv=tuple(ch["pivot_xy"]), xb=ch["bouton"]["x"],
                bras_bouton=ch["bouton"]["bras_horizontal"], T=tuple(ch["attache_D3"]["xy"]),
                H=H, qx=lv["queue_pointe_x"], cx=CX[r])


def theta_tige(c, d):
    p0 = (c["xb"], YP_CONTACT)
    return racine_proche_zero(lambda t: rot(p0, c["piv"], t)[1] - YP_CONTACT - d, -1.2, 1.2)


def theta_r(H, T2, L):
    return racine_proche_zero(lambda t: dist(T2, rot(H, PR, t)) - L, -1.2, 1.2)


def perp(pt, a, b):
    ux, uy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(ux, uy)
    return abs((pt[0] - a[0]) * uy - (pt[1] - a[1]) * ux) / n


def calcule(c, H, d):
    T = c["T"]
    L = dist(T, H)
    tt = theta_tige(c, d)
    T2 = rot(T, c["piv"], tt)
    tr = theta_r(H, T2, L)
    q0 = (c["cx"], Y_QUEUE)
    q1 = rot(q0, PR, tr)
    dy = q1[1] - q0[1]
    lev = abs(dy)
    ratio = lev / d
    rp = (perp(c["piv"], T, H) / abs(c["bras_bouton"])) * (abs(PR[0] - c["cx"]) / perp(PR, T, H))
    p0 = (c["qx"], Y_QUEUE)

    def pos(dd, tt_, tr_):
        return dict(pivot_tige=c["piv"], pivot_r=PR,
                    contact_bouton=rot((c["xb"], YP_CONTACT), c["piv"], tt_), bout_piston=(c["xb"], 16.0 + dd),
                    attache_tige=rot(T, c["piv"], tt_), trou_r=rot(H, PR, tr_),
                    pointe_queue=rot(p0, PR, tr_), centre_queue=rot(q0, PR, tr_))
    return dict(H=H, rayon_trou=dist(H, PR), angle_trou_deg=math.degrees(math.atan2(H[1] - PR[1], H[0] - PR[0])),
                bras_perp_r=perp(PR, T, H), bras_perp_tige=perp(c["piv"], T, H),
                longueur_biellette=L, course=d, theta_tige_deg=math.degrees(tt), theta_r_deg=math.degrees(tr),
                levee=lev, sens_queue="descend" if dy < 0 else "monte", dy_queue=dy,
                rapport_exact=ratio, rapport_petits_angles=rp, effort_g=F_BASE * ratio,
                positions_relache=pos(0, 0, 0), positions_enfonce=pos(d, tt, tr))


def trou_radial(c, R):
    ang = math.atan2(c["H"][1] - PR[1], c["H"][0] - PR[0])
    return (PR[0] + R * math.cos(ang), PR[1] + R * math.sin(ang))


def ratio_pour_rayon(c, R, d=5.0):
    return calcule(c, trou_radial(c, R), d)["rapport_exact"]


def rayon_pour_rapport(c, cible, d=5.0):
    R0 = dist(c["H"], PR)
    sols, prev = [], None
    for i in range(0, 241):
        R = 10 + 0.5 * i
        try:
            v = ratio_pour_rayon(c, R, d) - cible
        except Exception:
            prev = None
            continue
        if prev is not None and prev[1] * v < 0:
            sols.append(bisect(lambda x: ratio_pour_rayon(c, x, d) - cible, prev[0], R))
        prev = (R, v)
    return min(sols, key=lambda s: abs(s - R0)) if sols else None


def course_pour_levee(c, H, cible=5.1):
    return bisect(lambda d: calcule(c, H, d)["levee"] - cible, 0.5, 20.0)


def echant(boucle, pas=0.1):
    pts = []
    for s in boucle:
        if s["t"] == "L":
            a, b = s["a"], s["b"]
            n = max(2, int(dist(a, b) / pas))
            pts += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
        else:
            c, r = s["c"], s["r"]
            a0 = math.atan2(s["a"][1] - c[1], s["a"][0] - c[0])
            a1 = math.atan2(s["b"][1] - c[1], s["b"][0] - c[0])
            if s["ccw"]:
                while a1 <= a0 + 1e-9:
                    a1 += 2 * math.pi
            else:
                while a1 >= a0 - 1e-9:
                    a1 -= 2 * math.pi
            n = max(4, int(abs(a1 - a0) * r / pas))
            pts += [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    return [(x, 84.9 - y) for x, y in pts]


def dans_poly(p, poly):
    x, y = p
    ins = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            ins = not ins
    return ins


def contours(r):
    bs = [echant(b) for b in CON[r]["boucles"]]

    def aire(p):
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    io = max(range(len(bs)), key=lambda i: aire(bs[i]))
    return bs[io], [b for i, b in enumerate(bs) if i != io]


def centre(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def faisabilite(r, dep, orig):
    ext, ints = contours(r)
    res = {}
    for lettre, H in dep.items():
        if H is None:
            continue
        obst = [b for b in ints if dist(centre(b), orig[lettre]) >= 3.5]
        d_ext = min(dist(H, p) for p in ext)
        dedans = dans_poly(H, ext)
        lig_ext = (d_ext if dedans else -d_ext) - D_TROU / 2
        lig_int = min([min(dist(H, p) for p in b) for b in obst] + [1e9]) - D_TROU / 2
        lig = min(lig_ext, lig_int)
        res[lettre] = dict(trou=H, dans_contour=dedans, ligament_contour=lig_ext, ligament_obstacles=lig_int,
                           ligament_min=lig, ok=lig >= 2.0, allonger_mm=max(0.0, 2.0 - lig_ext))
    a = dep.get("A") or orig["A"]
    b = dep.get("B") or orig["B"]
    res["ecart_A_B_bord_a_bord"] = dist(a, b) - D_TROU
    res["ecart_A_B_ok"] = res["ecart_A_B_bord_a_bord"] >= 2.0
    return res


# ---------------------------------------------------------------- P1 corrige (Thales) ----------
import numpy as np
from shapely.geometry import Point, Polygon

TIGES_STL = {"A1": "8858384", "A2": "8858531", "A3": "8858692", "B1": "8864762", "B2": "8864951", "B3": "8865177"}
CORPS = BASE + r"\comparaison_tiges\a_conteneur\corps"
LIG_MIN = 2.0
R_TROU = D_TROU / 2


def X_cible(c, cible):
    """Point X sur la droite pivot tige - pivot r tel que |XPt|/|XPr| = cible/(bras palette/bras bouton),
    du meme cote (entre les pivots / a l'exterieur) que l'intersection actuelle."""
    Pt = c["piv"]
    bp = abs(PR[0] - c["cx"])
    bb = abs(c["bras_bouton"])
    k = cible / (bp / bb)
    d = (PR[0] - Pt[0], PR[1] - Pt[1])
    T, H = c["T"], c["H"]
    e = (H[0] - T[0], H[1] - T[1])
    den = e[0] * d[1] - e[1] * d[0]
    t0 = ((Pt[0] - T[0]) * e[1] - (Pt[1] - T[1]) * e[0]) / den if abs(den) > 1e-12 else None
    interne = t0 is not None and 0 < t0 < 1
    t = k / (1 + k) if interne else k / (k - 1)
    return (Pt[0] + t * d[0], Pt[1] + t * d[1]), dict(k=k, t0=t0, t=t, interne=interne)


def poly_levier(r, orig_A, orig_B):
    """Polygone matiere du levier r : contour ext moins les trous, sans les trous A et B d'origine."""
    ext, ints = contours(r)
    ints = [b for b in ints if dist(centre(b), orig_A) >= 3.5 and dist(centre(b), orig_B) >= 3.5]
    return Polygon(ext, [b for b in ints])


def ligament_pt(P, pt):
    p = Point(pt)
    dd = P.boundary.distance(p)
    return (dd if P.contains(p) else -dd) - R_TROU


def poly_tige_sans_attache(nom, z, T0):
    import trimesh
    m = trimesh.load(CORPS + "\\" + TIGES_STL[nom] + ".stl")
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, _ = s.to_2D(to_2D=np.eye(4))
    pt = Point(T0)
    for Pg in p2.polygons_full:
        if not Polygon(Pg.exterior).contains(pt):
            continue
        ints = [ring for ring in Pg.interiors
                if not (Polygon(ring).contains(pt) or Polygon(ring).centroid.distance(pt) < 0.3)]
        return Polygon(Pg.exterior, ints)
    return None


def _res(c, T, H, d):
    cc = dict(c)
    cc["T"] = T
    return calcule(cc, H, d)


def _norm(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a <= -math.pi:
        a += 2 * math.pi
    return a


def _proche0(sols):
    sols = [_norm(x) for x in sols if abs(_norm(x)) < 1.2]
    return min(sols, key=abs) if sols else None


def rapport_rapide(c, T, H, d):
    """Meme cinematique que calcule(), en forme fermee (rapport exact, sens de la queue) ; None si pas de solution."""
    piv = c["piv"]
    ax, ay = c["xb"] - piv[0], YP_CONTACT - piv[1]
    K = YP_CONTACT + d - piv[1]
    rm = math.hypot(ax, ay)
    if abs(K) > rm:
        return None
    psi = math.atan2(ay, ax)
    tt = _proche0([math.asin(K / rm) - psi, math.pi - math.asin(K / rm) - psi])
    if tt is None:
        return None
    T2 = rot(T, piv, tt)
    L = dist(T, H)
    R = dist(H, PR)
    D = dist(T2, PR)
    cv = (R * R + D * D - L * L) / (2 * R * D)
    if abs(cv) > 1:
        return None
    phi = math.atan2(T2[1] - PR[1], T2[0] - PR[0])
    a0 = math.atan2(H[1] - PR[1], H[0] - PR[0])
    tr = _proche0([phi - a0 + math.acos(cv), phi - a0 - math.acos(cv)])
    if tr is None:
        return None
    q1 = rot((c["cx"], Y_QUEUE), PR, tr)
    dy = q1[1] - Y_QUEUE
    return abs(dy) / d, ("descend" if dy < 0 else "monte")


def cherche_trou(c, X, fixe, mobile0, mobile_est_H, Pmat, autres_cercles, cible, d, sens0):
    """Point mobile (trou de r si mobile_est_H, sinon attache de tige) : X glisse sur la droite des pivots, le point
    mobile est sur la droite fixe-X a la distance s de `fixe` ; pour chaque s on cale X pour que le rapport EXACT
    soit `cible` ; on garde le point (ligament >= LIG_MIN) le plus proche de mobile0."""
    Pt = c["piv"]
    dd = (PR[0] - Pt[0], PR[1] - Pt[1])
    t_nom = ((X[0] - Pt[0]) * dd[0] + (X[1] - Pt[1]) * dd[1]) / (dd[0] ** 2 + dd[1] ** 2)

    def mob(t, s):
        Xt = (Pt[0] + t * dd[0], Pt[1] + t * dd[1])
        u = (Xt[0] - fixe[0], Xt[1] - fixe[1])
        n = math.hypot(*u)
        return (fixe[0] + s * u[0] / n, fixe[1] + s * u[1] / n)

    def lig(pt):
        v = ligament_pt(Pmat, pt)
        for a in autres_cercles:
            v = min(v, dist(pt, a) - D_TROU)
        return v

    def rap(m):
        return rapport_rapide(c, c["T"], m, d) if mobile_est_H else rapport_rapide(c, m, c["H"], d)

    def modele(m):
        return _res(c, c["T"], m, d) if mobile_est_H else _res(c, m, c["H"], d)

    cands, best = [], None
    N = 61
    ts = [t_nom + (i - N // 2) * 0.01 for i in range(N)]
    for i in range(-1500, 1501):
        s = i * 0.1
        if abs(s) < 4:
            continue
        prev = None
        racine = None
        for t in sorted(ts, key=lambda x: abs(x - t_nom)):
            pass
        vals = []
        for t in ts:
            r = rap(mob(t, s))
            vals.append(None if r is None else r[0] - cible)
        bestroot = None
        for j in range(N - 1):
            if vals[j] is None or vals[j + 1] is None or vals[j] * vals[j + 1] > 0:
                continue
            lo, hi = ts[j], ts[j + 1]
            flo = vals[j]
            for _ in range(40):
                mid = (lo + hi) / 2
                r = rap(mob(mid, s))
                if r is None:
                    break
                fm = r[0] - cible
                if (flo < 0) == (fm < 0):
                    lo, flo = mid, fm
                else:
                    hi = mid
            tm = (lo + hi) / 2
            if bestroot is None or abs(tm - t_nom) < abs(bestroot - t_nom):
                bestroot = tm
        if bestroot is None:
            continue
        m = mob(bestroot, s)
        r = rap(m)
        if r is None or r[1] != sens0:
            continue
        v = lig(m)
        if best is None or v > best[0]:
            best = (v, m)
        if v >= LIG_MIN:
            cands.append((dist(m, mobile0), m, v))
    cands.sort(key=lambda x: x[0])
    for _, m, v in cands[:50]:
        r = modele(m)
        if abs(r["rapport_exact"] - cible) < 2e-3 and r["sens_queue"] == sens0:
            return dict(ok=True, point=m, ligament=v, res=r, lig_max_possible=best[0])
    return dict(ok=False, lig_max_possible=best[0] if best else None, point_lig_max=best[1] if best else None)


def p1_corrige(C, chaines, cible=1.05, d=5.0):
    """1) trou de r mobile (T fixe) ; 2) sinon attache de tige mobile (H fixe)."""
    out, nouveaux_H = {}, {}
    for n in chaines:
        c = C[n]
        r = c["r"]
        autre = ("B" if n[0] == "A" else "A") + n[1]
        base0 = calcule(c, c["H"], d)
        sens0 = base0["sens_queue"]
        X, info = X_cible(c, cible)
        Pmat = poly_levier(r, C["A" + n[1]]["H"], C["B" + n[1]]["H"])
        autre_pos = nouveaux_H.get(autre, C[autre]["H"])
        sol = cherche_trou(c, X, c["T"], c["H"], True, Pmat, [autre_pos], cible, d, sens0)
        rec = dict(X=X, info_X=info, rapport_avant=base0["rapport_exact"], levee_avant=base0["levee"])
        if sol["ok"]:
            H2 = sol["point"]
            nouveaux_H[n] = H2
            rec.update(bouge="levier " + r, ancienne=c["H"], nouvelle=H2, deplacement_mm=dist(c["H"], H2),
                       longueur_avant=base0["longueur_biellette"], longueur_apres=sol["res"]["longueur_biellette"],
                       ligament=sol["ligament"], res=sol["res"], T=c["T"], H=H2)
        else:
            rec["essai_r"] = dict(lig_max_possible=sol["lig_max_possible"], point_lig_max=sol["point_lig_max"])
            Pt_ = poly_tige_sans_attache(n, REL["chaines"][n]["z_plat_centre"], c["T"])
            if Pt_ is None:
                rec.update(bouge="aucun (contour tige non trouve)", res=base0, T=c["T"], H=c["H"])
            else:
                sol2 = cherche_trou(c, X, c["H"], c["T"], False, Pt_, [], cible, d, sens0)
                if sol2["ok"]:
                    rec.update(bouge="tige " + n, ancienne=c["T"], nouvelle=sol2["point"],
                               deplacement_mm=dist(c["T"], sol2["point"]), longueur_avant=base0["longueur_biellette"],
                               longueur_apres=sol2["res"]["longueur_biellette"], ligament=sol2["ligament"],
                               res=sol2["res"], T=sol2["point"], H=c["H"])
                else:
                    rec.update(bouge="aucun (ligament >= 2 impossible, ni r ni tige)", res=base0, T=c["T"], H=c["H"],
                               essai_tige=dict(lig_max_possible=sol2["lig_max_possible"], point_lig_max=sol2["point_lig_max"]))
        out[n] = rec
    return out


def verif_ecart_AB(P):
    return {"r" + k: dist(P["A" + k]["H"], P["B" + k]["H"]) - D_TROU for k in "123"}


def main():
    C = {n: chaine_def(n) for n in CHAINES}
    out = {"hypotheses": "plan XY mm ; A -> trou_autre, B -> trou_attache_B ; levee au centre de palette ; effort = 177 g x rapport exact ; biellette rigide |T-H| recalculee si H bouge"}

    def cas(trous, courses):
        return {n: calcule(C[n], trous.get(n, C[n]["H"]), courses[n]) for n in CHAINES}
    cinq = {n: 5.0 for n in CHAINES}
    out["AVANT"] = cas({}, cinq)
    rayons = {n: rayon_pour_rapport(C[n], 1.05) for n in ["A2", "B2", "A3", "B3", "B1"]}
    rayons["A1_pour_1.05"] = rayon_pour_rapport(C["A1"], 1.05)
    rayons["A1_ewen"] = 23.0
    tr1 = {n: trou_radial(C[n], rayons[n]) for n in ["A2", "B2", "A3", "B3", "B1"]}
    tr1["A1"] = trou_radial(C["A1"], 23.0)
    out["P1_radial_audit"] = cas(tr1, cinq)
    out["P1_radial_audit_rayons"] = dict(rayons=rayons, rayons_audit={"B2": 35.5, "A2": 27.5, "B3": 48.5, "A3": 36, "B1": 30, "A1": 23},
                            rayons_originaux={n: dist(C[n]["H"], PR) for n in CHAINES},
                            bras_perp_P1={n: out["P1_radial_audit"][n]["bras_perp_r"] for n in CHAINES})
    c2 = {n: round(course_pour_levee(C[n], C[n]["H"], 5.1), 1) for n in CHAINES}
    out["P2"] = cas({}, c2)
    out["P2_courses_audit_B"] = {"B1": 6.5, "B2": 4.2, "B3": 3.8}
    tr3 = {"A3": tr1["A3"], "B3": tr1["B3"]}
    c3 = dict(cinq)
    c3["A1"] = 6.5
    c3["B1"] = 6.5
    out["P3_radial_audit"] = cas(tr3, c3)

    def fz(trous):
        f = {}
        for r in ("r1", "r2", "r3"):
            dep = {"A": trous.get("A" + r[1]), "B": trous.get("B" + r[1])}
            if dep["A"] or dep["B"]:
                f[r] = faisabilite(r, dep, {"A": C["A" + r[1]]["H"], "B": C["B" + r[1]]["H"]})
        return f
    out["faisabilite_P1_radial_audit"] = fz(tr1)
    out["faisabilite_P3_radial_audit"] = fz(tr3)
    out["pieces_modifiees_radial_audit"] = {
        "AVANT": "aucune",
        "P1": "leviers r1, r2, r3 (trous A et B deplaces) ; les 6 biellettes (longueur change) ; butees inchangees (course 5)",
        "P2": "aucun trou ni biellette ; une butee de course par rang (6 chaines)",
        "P3": "levier r3 (trous A3, B3) ; biellettes A3 et B3 ; butee 6,5 pour A1 et B1, autres 5"}
    # ---- P1 corrige : rapport exact 1,05, Thales, trou de r puis attache de tige
    pc = p1_corrige(C, CHAINES)
    out["P1_strict_2mm"] = {}
    for n in CHAINES:
        rec = pc[n]
        d_ = dict(rec["res"])
        for k in ("bouge", "ancienne", "nouvelle", "deplacement_mm", "longueur_avant", "longueur_apres", "ligament",
                  "X", "info_X", "essai_r", "essai_tige", "rapport_avant", "levee_avant"):
            if k in rec:
                d_[k] = rec[k]
        d_["T"], d_["H"] = rec["T"], rec["H"]
        out["P1_strict_2mm"][n] = d_
    # tolerance : memes recherches avec ligament >= 1,5 mm (information, ne remplace pas P1)
    global LIG_MIN
    LIG_MIN = 1.5
    pt15 = p1_corrige(C, CHAINES)
    LIG_MIN = 2.0
    out["P1_tolerance_1_5"] = {}
    for n in CHAINES:
        rec = pt15[n]
        d_ = dict(rec["res"])
        for k in ("bouge", "ancienne", "nouvelle", "deplacement_mm", "longueur_avant", "longueur_apres", "ligament"):
            if k in rec:
                d_[k] = rec[k]
        d_["T"], d_["H"] = rec["T"], rec["H"]
        out["P1_tolerance_1_5"][n] = d_
    # P1 retenu : ligament >= 2 si un point existe, sinon le meilleur point a ligament >= 1,5 (niveau de l'attache actuelle)
    pcm = {}
    out["P1"] = {}
    for n in CHAINES:
        strict_ok = not pc[n]["bouge"].startswith("aucun")
        rec = pc[n] if strict_ok else pt15[n]
        pcm[n] = rec
        d_ = dict(rec["res"])
        for k in ("bouge", "ancienne", "nouvelle", "deplacement_mm", "longueur_avant", "longueur_apres", "ligament",
                  "X", "info_X", "rapport_avant", "levee_avant"):
            if k in rec:
                d_[k] = rec[k]
        d_["seuil_ligament_mm"] = 2.0 if strict_ok else 1.5
        d_["ligament_2mm_tenu"] = strict_ok
        d_["T"], d_["H"] = rec["T"], rec["H"]
        out["P1"][n] = d_
    # ligament des trous actuels (r : sans les trous A/B d'origine ; tige : sans l'attache)
    out["ligament_actuel"] = {}
    for n in CHAINES:
        c = C[n]
        autre = ("B" if n[0] == "A" else "A") + n[1]
        Pm = poly_levier(c["r"], C["A" + n[1]]["H"], C["B" + n[1]]["H"])
        lr = min(ligament_pt(Pm, c["H"]), dist(c["H"], C[autre]["H"]) - D_TROU)
        Pt_ = poly_tige_sans_attache(n, REL["chaines"][n]["z_plat_centre"], c["T"])
        out["ligament_actuel"][n] = dict(trou_r=lr, attache_tige=ligament_pt(Pt_, c["T"]) if Pt_ is not None else None)
    # P3 : seules A3 et B3 suivent P1 corrige ; A1 et B1 course 6,5
    def trio(n, c_):
        rec = pcm[n]
        cc = dict(C[n])
        cc["T"], H_ = rec["T"], rec["H"]
        return calcule(cc, H_, c_)
    out["P3"] = {}
    for n in CHAINES:
        c_ = 6.5 if n in ("A1", "B1") else 5.0
        if n in ("A3", "B3"):
            r_ = trio(n, c_)
            for k in ("bouge", "ancienne", "nouvelle", "deplacement_mm", "longueur_avant", "longueur_apres", "ligament"):
                if k in pcm[n]:
                    r_[k] = pcm[n][k]
            r_["seuil_ligament_mm"] = out["P1"][n]["seuil_ligament_mm"]
            r_["T"], r_["H"] = pcm[n]["T"], pcm[n]["H"]
        else:
            r_ = calcule(C[n], C[n]["H"], c_)
        r_.setdefault("bouge", "aucun (inchange)")
        out["P3"][n] = r_
    out["ecart_A_B_P1"] = verif_ecart_AB({n: dict(H=out["P1"][n]["H"]) for n in CHAINES})
    def pieces(cas, noms, course_txt):
        lev = sorted({out[cas][n]["bouge"].split()[1] for n in noms if out[cas][n]["bouge"].startswith("levier")})
        tig = [n for n in noms if out[cas][n]["bouge"].startswith("tige")]
        bie = [n for n in noms if abs(out[cas][n]["longueur_biellette"] - out["AVANT"][n]["longueur_biellette"]) > 0.05]
        non = [n for n in noms if out[cas][n]["bouge"].startswith("aucun")]
        return dict(leviers_modifies=lev, tiges_modifiees=tig, biellettes_longueur_change=bie, butees=course_txt,
                    chaines_sans_solution=non)
    out["pieces_modifiees"] = {
        "AVANT": "aucune",
        "P1": pieces("P1", CHAINES, "inchangees (course 5)"),
        "P2": "aucun trou ni biellette ; une butee de course par rang (6 chaines)",
        "P3": pieces("P3", ("A3", "B3"), "6,5 pour A1 et B1 ; 5 pour les autres")}
    json.dump(out, open(os.path.join(OUT, "propositions.json"), "w"), indent=1, ensure_ascii=False)
    for cs in ("AVANT", "P1", "P2", "P3"):
        print(cs)
        for n in CHAINES:
            r = out[cs][n]
            print(" %s R=%.2f perp=%.2f L=%.2f d=%s lev=%.2f rap=%.3f pa=%.3f F=%.0f %s" % (
                n, r["rayon_trou"], r["bras_perp_r"], r["longueur_biellette"], r["course"], r["levee"],
                r["rapport_exact"], r["rapport_petits_angles"], r["effort_g"], r["sens_queue"]))
    for n in CHAINES:
        r = out["P1"][n]
        print(n, r["bouge"], r.get("ancienne"), r.get("nouvelle"), "dep=%.2f" % r.get("deplacement_mm", 0), "Lav=%.2f Lap=%.2f lig=%s" % (r.get("longueur_avant", 0), r.get("longueur_apres", 0), r.get("ligament")), r.get("essai_r"), r.get("essai_tige"))
    print(out["ecart_A_B_P1"])
    print(json.dumps(out["ligament_actuel"]))
    for n in CHAINES:
        r = out["P1_tolerance_1_5"][n]
        print("tol1.5", n, r["bouge"], r.get("ancienne"), r.get("nouvelle"), "dep=%.2f" % r.get("deplacement_mm", 0), "lig=%s rap=%.3f lev=%.2f F=%.0f" % (r.get("ligament"), r["rapport_exact"], r["levee"], r["effort_g"]))
    print(json.dumps(out["pieces_modifiees"], ensure_ascii=False))


main()
