"""P4 (trous des tiges) et P5 (tiges + leviers) + ligament 3 mm de P1. Calcul seul (26/10/2026).
Ajoute les cles P4, P5, P1_ligament_3mm... a propositions.json. Reutilise calcul_propositions.py (sans relancer son main)."""
import sys, os, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "calcul_propositions.py"), encoding="utf-8").read().rsplit("\nmain()", 1)[0]
__file__ = os.path.join(HERE, "calcul_propositions.py")
exec(_src, globals())
import shapely
from shapely.geometry import Point, Polygon, MultiLineString, LineString

CIBLE, D = 1.05, 5.0
LIG = 3.0             # ligament mini (mm)
R_EYE = R_TROU + LIG  # 4.5 : oeil local D9
OUTSIDE_MAX = 3.0     # centre du trou autorise hors contour (l'oeil prolonge la piece) de 3 mm au plus
LB = (0.5, 1.5)       # biellette : L'/L dans [0,5 ; 1,5] (pas de biellette qui double)
DZ_VOISIN = 5.0       # voisin = tole dont |dZ| < 5 (strict)
TOP = 400
C = {n: chaine_def(n) for n in CHAINES}
ZC = {n: REL["chaines"][n]["z_plat_centre"] for n in CHAINES}
BASE0 = {n: calcule(C[n], C[n]["H"], D) for n in CHAINES}
SENS0 = {n: BASE0[n]["sens_queue"] for n in CHAINES}
TT = {n: theta_tige(C[n], D) for n in CHAINES}
PART = {n: ("B" if n[0] == "A" else "A") + n[1] for n in CHAINES}


def rap_vec(n, Tx, Ty, Hx, Hy):
    """rapport exact vectorise (meme cinematique que rapport_rapide) ; nan si pas de solution / mauvais sens."""
    c = C[n]
    tt = TT[n]
    px, py = c["piv"]
    cs, sn = math.cos(tt), math.sin(tt)
    T2x = px + (Tx - px) * cs - (Ty - py) * sn
    T2y = py + (Tx - px) * sn + (Ty - py) * cs
    L = np.hypot(Tx - Hx, Ty - Hy)
    R = np.hypot(Hx - PR[0], Hy - PR[1])
    Dd = np.hypot(T2x - PR[0], T2y - PR[1])
    with np.errstate(all="ignore"):
        cv = (R * R + Dd * Dd - L * L) / (2 * R * Dd)
        ok = np.abs(cv) <= 1
        ac = np.arccos(np.clip(cv, -1, 1))
        phi = np.arctan2(T2y - PR[1], T2x - PR[0])
        a0 = np.arctan2(Hy - PR[1], Hx - PR[0])
        c1 = phi - a0 + ac
        c2 = phi - a0 - ac
        c1 = np.arctan2(np.sin(c1), np.cos(c1))
        c2 = np.arctan2(np.sin(c2), np.cos(c2))
        tr = np.where(np.abs(c1) <= np.abs(c2), c1, c2)
        ok &= np.abs(tr) < 1.2
        dy = (c["cx"] - PR[0]) * np.sin(tr) + (Y_QUEUE - PR[1]) * np.cos(tr) + PR[1] - Y_QUEUE
        ratio = np.abs(dy) / D
        ok &= (dy < 0) == (SENS0[n] == "descend")
    return np.where(ok, ratio, np.nan)


def courbe(g, x0, x1, y0, y1, h):
    """points (x,y) ou g(x,y)=0 : changements de signe sur grille h (deux axes), affines par bissection."""
    xs = np.arange(x0, x1 + h, h)
    ys = np.arange(y0, y1 + h, h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    V = g(X, Y)
    pts = []
    for axe in (0, 1):
        A = V if axe == 0 else V.T
        a, b = A[:, :-1], A[:, 1:]
        m = np.isfinite(a) & np.isfinite(b) & (a * b <= 0)
        i, j = np.nonzero(m)
        if len(i) == 0:
            continue
        if axe == 0:
            fx = xs[i]
            lo, hi = ys[j].copy(), ys[j + 1].copy()
            gg = lambda t, fx=fx: g(fx, t)
        else:
            fy = ys[i]
            lo, hi = xs[j].copy(), xs[j + 1].copy()
            gg = lambda t, fy=fy: g(t, fy)
        flo = A[i, j].copy()
        for _ in range(32):
            mid = (lo + hi) / 2
            fm = gg(mid)
            same = (flo < 0) == (fm < 0)
            lo = np.where(same, mid, lo)
            flo = np.where(same, fm, flo)
            hi = np.where(same, hi, mid)
        t = (lo + hi) / 2
        pts.append(np.column_stack([fx, t]) if axe == 0 else np.column_stack([t, fy]))
    if not pts:
        return np.zeros((0, 2))
    P = np.vstack(pts)
    v = g(P[:, 0], P[:, 1])
    return P[np.isfinite(v) & (np.abs(v) < 1e-6)]


class Piece:
    def __init__(self, ext, ints, out_max=OUTSIDE_MAX):
        self.out_max = out_max
        self.ext = Polygon(ext)
        self.mat = Polygon(ext, ints)
        self.extb = self.ext.boundary
        self.intb = MultiLineString([LineString(list(i)) for i in ints]) if ints else None
        self.bounds = self.ext.bounds

    def analyse(self, pts):
        x, y = pts[:, 0], pts[:, 1]
        P = shapely.points(x, y)
        mat = shapely.contains_xy(self.mat, x, y)
        inext = shapely.contains_xy(self.ext, x, y)
        dext = shapely.distance(P, self.extb)
        dint = shapely.distance(P, self.intb) if self.intb is not None else np.full(len(x), 1e9)
        lig_ext = np.where(inext, dext, -dext) - R_TROU
        lig_int = dint - R_TROU
        noeye = mat & (lig_ext >= LIG - 1e-9) & (lig_int >= LIG - 1e-9)
        eye = (lig_int >= LIG - 1e-9) & (mat | ((~inext) & (dext <= self.out_max)))
        return dict(mat=mat, lig_ext=lig_ext, lig_int=lig_int, noeye=noeye, eye=eye)


def tige_piece(n):
    P = poly_tige_sans_attache(n, ZC[n], C[n]["T"])
    return Piece(list(P.exterior.coords), [list(i.coords) for i in P.interiors])


def levier_piece(r):
    ext, ints = contours(r)
    A, B = C["A" + r[1]]["H"], C["B" + r[1]]["H"]
    ints = [b for b in ints if dist(centre(b), A) >= 3.5 and dist(centre(b), B) >= 3.5]
    return Piece(ext, ints, out_max=0.0)  # le trou de r reste dans le contour du levier


TIGE = {n: tige_piece(n) for n in CHAINES}
PLEINE = {n: TIGE[n].ext for n in CHAINES}
LEV = {r: levier_piece(r) for r in ("r1", "r2", "r3")}
VOISINS = {}


def set_voisins(strict=True):
    for n in CHAINES:
        VOISINS[n] = [m for m in CHAINES if m != n and (abs(ZC[m] - ZC[n]) < DZ_VOISIN - 1e-9 if strict else abs(ZC[m] - ZC[n]) <= DZ_VOISIN + 1e-9)]


set_voisins(True)


def collision(n, pts, rayon):
    P = shapely.points(pts[:, 0], pts[:, 1])
    col = np.zeros(len(pts), bool)
    for m in VOISINS[n]:
        col |= shapely.distance(P, PLEINE[m]) < rayon - 1e-9
    return col


def mk(c_, T, H, d, an, i, eyeT=None, eyeH=None):
    return dict(T=(float(T[0]), float(T[1])), H=(float(H[0]), float(H[1])), disp=float(d),
                eye_T=eyeT, eye_H=eyeH, lig_ext=float(an["lig_ext"][i]), lig_int=float(an["lig_int"][i]),
                horscontour=bool(not an["mat"][i]))


def _tige_ok(n, pts, H):
    c = C[n]
    an = TIGE[n].analyse(pts)
    L = np.hypot(pts[:, 0] - H[0], pts[:, 1] - H[1])
    L0 = BASE0[n]["longueur_biellette"]
    eyeflag = ~an["noeye"]
    ok = an["eye"] & (L / L0 >= LB[0]) & (L / L0 <= LB[1])
    ok &= np.where(eyeflag, ~collision(n, pts, R_EYE), ~collision(n, pts, R_TROU))
    return an, eyeflag, ok


def cands_tige(n, h=0.2, win=None):
    """T mobile, H fixe, sur la droite H-X (courbe rapport exact 1,05)."""
    c = C[n]
    b = TIGE[n].bounds
    x0, y0, x1, y1 = (b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3) if win is None else win
    Hx, Hy = c["H"]
    pts = courbe(lambda X, Y: rap_vec(n, X, Y, Hx, Hy) - CIBLE, x0, x1, y0, y1, h)
    if len(pts) == 0:
        return [], None
    an, eyeflag, ok = _tige_ok(n, pts, c["H"])
    d = np.hypot(pts[:, 0] - c["T"][0], pts[:, 1] - c["T"][1])
    idx = np.nonzero(ok)[0]
    idx = idx[np.argsort(d[idx])]
    out = [mk(c, pts[i], c["H"], d[i], an, i, eyeT=bool(eyeflag[i]), eyeH=False) for i in idx[:TOP]]
    # meilleur ligament possible (pour le cas "impossible")
    return out, (float(np.nanmax(np.where(np.isfinite(an["lig_int"]), np.minimum(an["lig_ext"], an["lig_int"]), -1e9))) if len(pts) else None)


def _lev_ok(n, pts, T, partner_pt):
    c = C[n]
    an = LEV[c["r"]].analyse(pts)
    L = np.hypot(pts[:, 0] - T[0], pts[:, 1] - T[1])
    L0 = BASE0[n]["longueur_biellette"]
    ok = an["eye"] & (L / L0 >= LB[0]) & (L / L0 <= LB[1])
    if partner_pt is not None:
        ok &= np.hypot(pts[:, 0] - partner_pt[0], pts[:, 1] - partner_pt[1]) - D_TROU >= LIG - 1e-9
    return an, ~an["noeye"], ok


def cands_levier(n, partner_pt=None, h=0.25):
    """H mobile (le trou du levier r), T fixe."""
    c = C[n]
    b = LEV[c["r"]].bounds
    Tx, Ty = c["T"]
    pts = courbe(lambda X, Y: rap_vec(n, Tx, Ty, X, Y) - CIBLE, b[0] - 3, b[2] + 3, b[1] - 3, b[3] + 3, h)
    if len(pts) == 0:
        return []
    an, eyeflag, ok = _lev_ok(n, pts, c["T"], partner_pt)
    d = np.hypot(pts[:, 0] - c["H"][0], pts[:, 1] - c["H"][1])
    idx = np.nonzero(ok)[0]
    idx = idx[np.argsort(d[idx])]
    return [mk(c, c["T"], pts[i], d[i], an, i, eyeT=False, eyeH=bool(eyeflag[i])) | dict(lig_ext_H=float(an["lig_ext"][i])) for i in idx[:TOP]]


def cands_deux(n, partner_pt=None, hH=1.0, hT=0.25, centre_H=None, rayon_H=30.0, win_T=25.0):
    """H et T mobiles : H sur grille admissible ; pour chaque H, T sur sa courbe ; deplacement total minimal."""
    c = C[n]
    Pl = LEV[c["r"]]
    ch = c["H"] if centre_H is None else centre_H
    gx = np.arange(ch[0] - rayon_H, ch[0] + rayon_H + 1e-9, hH)
    gy = np.arange(ch[1] - rayon_H, ch[1] + rayon_H + 1e-9, hH)
    GX, GY = np.meshgrid(gx, gy, indexing="ij")
    HP = np.column_stack([GX.ravel(), GY.ravel()])
    an = Pl.analyse(HP)
    ok = an["eye"] & (np.hypot(HP[:, 0] - ch[0], HP[:, 1] - ch[1]) <= rayon_H)
    if partner_pt is not None:
        ok &= np.hypot(HP[:, 0] - partner_pt[0], HP[:, 1] - partner_pt[1]) - D_TROU >= LIG - 1e-9
    idxH = np.nonzero(ok)[0]
    res = []
    for k in idxH:
        Hx, Hy = HP[k]
        pts = courbe(lambda X, Y: rap_vec(n, X, Y, Hx, Hy) - CIBLE, c["T"][0] - win_T, c["T"][0] + win_T,
                     c["T"][1] - win_T, c["T"][1] + win_T, hT)
        if len(pts) == 0:
            continue
        anT, eyeflag, okT = _tige_ok(n, pts, (Hx, Hy))
        if not okT.any():
            continue
        dT = np.hypot(pts[:, 0] - c["T"][0], pts[:, 1] - c["T"][1])
        i = np.nonzero(okT)[0][np.argmin(dT[okT])]
        dH = math.hypot(Hx - c["H"][0], Hy - c["H"][1])
        r_ = mk(c, pts[i], (Hx, Hy), dT[i] + dH, anT, i, eyeT=bool(eyeflag[i]), eyeH=bool(not an["noeye"][k]))
        r_.update(dispT=float(dT[i]), dispH=float(dH), lig_ext_H=float(an["lig_ext"][k]), lig_int_H=float(an["lig_int"][k]), horscontour_H=bool(not an["mat"][k]))
        res.append(r_)
    res.sort(key=lambda r: r["disp"])
    return res[:TOP]


# ---------- combinaison par rang (A_k, B_k : meme levier r_k, memes Z de tole) ----------
def usesT(m):
    return "T" in m


def usesH(m):
    return "H" in m


def pair_ok(ca, ma, cb, mb):
    if usesH(ma) or usesH(mb):
        if dist(ca["H"], cb["H"]) - D_TROU < LIG - 1e-9:
            return False
    if usesT(ma) and usesT(mb):
        ra = R_EYE if ca["eye_T"] else R_TROU
        rb = R_EYE if cb["eye_T"] else R_TROU
        if dist(ca["T"], cb["T"]) < ra + rb - 1e-9:
            return False
    return True


def meilleure_paire(la, ma, lb, mb):
    best = None
    if not la or not lb:
        return None
    for ca in la:
        if best and ca["disp"] + lb[0]["disp"] >= best[0] - 1e-12:
            break
        for cb in lb:
            if best and ca["disp"] + cb["disp"] >= best[0] - 1e-12:
                break
            if pair_ok(ca, ma, cb, mb):
                best = (ca["disp"] + cb["disp"], ca, cb)
                break
    return best


def pieces_de(rang, ma, mb):
    s = set()
    if usesT(ma):
        s.add("tige A" + rang)
    if usesT(mb):
        s.add("tige B" + rang)
    if usesH(ma) or usesH(mb):
        s.add("levier r" + rang)
    return s


def fabrique_listes(rang, modes):
    """listes de candidats par chaine et par mode ; variante 'filtre partenaire' (partenaire immobile)."""
    L = {}
    for n in ("A" + rang, "B" + rang):
        p = PART[n]
        L[n] = {}
        if "T" in modes:
            L[n]["T"] = cands_tige(n)[0]
        if "H" in modes:
            L[n]["H_fixe"] = cands_levier(n, C[p]["H"])
            L[n]["H_libre"] = cands_levier(n, None)
        if "TH" in modes:
            L[n]["TH_fixe"] = cands_deux(n, C[p]["H"])
            L[n]["TH_libre"] = cands_deux(n, None)
    return L


def liste(L, n, m, autre_mode):
    if m == "T":
        return L[n]["T"]
    suff = "_libre" if usesH(autre_mode) else "_fixe"
    return L[n][m + suff]


def resout_rang(rang, modes):
    L = fabrique_listes(rang, modes)
    nA, nB = "A" + rang, "B" + rang
    best = None
    detail = []
    for ma in modes:
        for mb in modes:
            la, lb = liste(L, nA, ma, mb), liste(L, nB, mb, ma)
            r = meilleure_paire(la, ma, lb, mb)
            detail.append((ma, mb, None if r is None else r[0]))
            if r is None:
                continue
            key = (len(pieces_de(rang, ma, mb)), r[0])
            if best is None or key < best[0]:
                best = (key, ma, mb, r[1], r[2])
    return best, detail, L


def raffine_TH(n, cand, partner_final):
    """repasse fine autour de la solution (H et T) pour les modes a deux trous."""
    c = C[n]
    r = cands_deux(n, partner_final, hH=0.25, hT=0.1, centre_H=cand["H"], rayon_H=1.5, win_T=3.0 + 0.0)
    # fenetre T centree sur l'ancien T : elargie si la solution grossiere est plus loin
    return r


# ---------- enregistrements ----------
def enregistre(n, cand, mode):
    c = C[n]
    T, H = cand["T"], cand["H"]
    r = _res(c, T, H, D)
    okx = abs(r["rapport_exact"] - CIBLE) < 2e-3 and r["sens_queue"] == SENS0[n]
    dT, dH = dist(T, c["T"]), dist(H, c["H"])
    out = dict(r)
    nom = {"T": "tige " + n, "H": "levier " + c["r"], "TH": "tige %s + levier %s" % (n, c["r"])}[mode]
    out.update(bouge=nom, mode=mode, T=T, H=H, rapport_verifie=okx,
               ancienne_T=c["T"], nouvelle_T=T if usesT(mode) else None,
               ancienne_H=c["H"], nouvelle_H=H if usesH(mode) else None,
               deplacement_T=dT, deplacement_H=dH, deplacement_mm=dT + dH,
               longueur_avant=BASE0[n]["longueur_biellette"], longueur_apres=r["longueur_biellette"],
               rapport_longueur=r["longueur_biellette"] / BASE0[n]["longueur_biellette"],
               levee_avant=BASE0[n]["levee"], rapport_avant=BASE0[n]["rapport_exact"], effort_avant_g=BASE0[n]["effort_g"])
    if usesT(mode):
        out.update(oeil_tige=bool(cand["eye_T"]), ligament_tige=LIG if cand["eye_T"] else min(cand["lig_ext"] if mode == "T" else cand["lig_ext"], cand["lig_int"]),
                   ligament_tige_sans_oeil=cand["lig_ext"], tige_hors_contour=cand["horscontour"] if mode == "T" else None)
    if usesH(mode):
        leH = cand.get("lig_ext_H", cand["lig_ext"] if mode == "H" else None)
        out.update(oeil_levier=bool(cand["eye_H"]), ligament_levier=LIG if cand["eye_H"] else leH,
                   ligament_levier_sans_oeil=leH)
    if mode == "H":
        out["levier_hors_contour"] = cand["horscontour"]
    if mode == "TH":
        out["tige_hors_contour"] = cand["horscontour"]
        out["levier_hors_contour"] = cand.get("horscontour_H")
    out["oeil"] = bool(out.get("oeil_tige") or out.get("oeil_levier"))
    out["ligament"] = min([v for k, v in out.items() if k in ("ligament_tige", "ligament_levier") and v is not None] or [None])
    return out


def pieces_texte(res):
    t, lv, bi = [], set(), []
    for n in CHAINES:
        r = res.get(n)
        if r and r.get("mode") and usesT(r["mode"]):
            t.append("tige " + n)
        if r and r.get("mode") and usesH(r["mode"]):
            lv.add("levier " + C[n]["r"])
        if r and r.get("mode") and abs(r["longueur_apres"] - r["longueur_avant"]) > 0.05:
            bi.append("biellette " + n)
    return dict(tiges=t, leviers=sorted(lv), biellettes_longueur_change=bi,
                nb_pieces_hors_biellettes=len(t) + len(lv))


def main2():
    t0 = time.time()
    out = json.load(open(os.path.join(HERE, "propositions.json"), encoding="utf-8"))
    # ---- largeur de tole autour de l'attache actuelle ; ligament actuel
    larg = {}
    for n in CHAINES:
        an = TIGE[n].analyse(np.array([C[n]["T"]]))
        larg[n] = dict(ligament_bord_tole=float(an["lig_ext"][0]), ligament_trous_voisins=float(an["lig_int"][0]),
                       oeil_necessaire=not bool(an["noeye"][0]))
    out["largeur_tole_attache_actuelle"] = larg
    # ---- P4
    P4, imposs4 = {}, []
    info4 = {}
    for rang in "123":
        best, detail, L = resout_rang(rang, ["T"])
        nA, nB = "A" + rang, "B" + rang
        if best is None:
            for n in (nA, nB):
                P4[n] = dict(bouge="aucun (pas de point admissible)", mode=None)
                imposs4.append(n)
            continue
        _, ma, mb, ca, cb = best
        P4[nA], P4[nB] = enregistre(nA, ca, "T"), enregistre(nB, cb, "T")
        for n in (nA, nB):
            sans = [x for x in L[n]["T"] if not x["eye_T"]]
            P4[n]["alternative_sans_oeil_mm"] = sans[0]["disp"] if sans else None
            P4[n]["alternative_sans_oeil_T"] = sans[0]["T"] if sans else None
            P4[n]["nb_points_admissibles"] = len(L[n]["T"])
    # diagnostic des chaines impossibles : distance de la courbe (rapport exact 1,05, H fixe) au contour de la tige
    diag = {}
    for n in imposs4:
        c = C[n]
        Hx, Hy = c["H"]
        pts = courbe(lambda X, Y: rap_vec(n, X, Y, Hx, Hy) - CIBLE, 40, 230, -20, 100, 0.25)
        if len(pts):
            dd = shapely.distance(shapely.points(pts[:, 0], pts[:, 1]), PLEINE[n])
            i = int(np.argmin(dd))
            diag[n] = dict(nb_points_courbe=len(pts), distance_min_au_contour_tige=float(dd[i]), point_le_plus_proche=tuple(pts[i]))
        else:
            diag[n] = dict(nb_points_courbe=0)
    out["P4_diagnostic_impossibles"] = diag
    out["P4"] = P4
    out["P4_chaines_impossibles"] = imposs4
    out["P4_pieces"] = pieces_texte(P4)
    # sensibilite : voisin = |dZ| <= 5 (rangs adjacents inclus)
    set_voisins(False)
    P4b = {}
    for rang in "123":
        best, _, _ = resout_rang(rang, ["T"])
        for n in ("A" + rang, "B" + rang):
            P4b[n] = None
        if best is not None:
            P4b["A" + rang] = dict(T=best[3]["T"], disp=best[3]["disp"], eye=best[3]["eye_T"])
            P4b["B" + rang] = dict(T=best[4]["T"], disp=best[4]["disp"], eye=best[4]["eye_T"])
    out["P4_variante_voisin_dZ_inclus_5"] = P4b
    set_voisins(True)
    print("P4 fait %.0fs" % (time.time() - t0), flush=True)
    # ---- P5
    P5, imposs5, det5 = {}, [], {}
    for rang in "123":
        best, detail, L = resout_rang(rang, ["T", "H", "TH"])
        det5[rang] = [(a, b, None if d is None else round(d, 2)) for a, b, d in detail]
        nA, nB = "A" + rang, "B" + rang
        if best is None:
            for n in (nA, nB):
                P5[n] = dict(bouge="aucun", mode=None)
                imposs5.append(n)
            continue
        key, ma, mb, ca, cb = best
        # raffinement des modes a deux trous
        cands = {nA: (ca, ma), nB: (cb, mb)}
        for n, (cd, m) in list(cands.items()):
            if m == "TH":
                p = PART[n]
                pf = cands[p][0]["H"] if usesH(cands[p][1]) else C[p]["H"]
                fine = cands_deux(n, pf, hH=0.25, hT=0.1, centre_H=cd["H"], rayon_H=1.5, win_T=30.0)
                if fine and fine[0]["disp"] < cd["disp"]:
                    cands[n] = (fine[0], m)
        for n in (nA, nB):
            P5[n] = enregistre(n, cands[n][0], cands[n][1])
        # ne pas casser l'ecart A-B apres raffinement
        if not pair_ok(cands[nA][0], cands[nA][1], cands[nB][0], cands[nB][1]):
            for n in (nA, nB):
                P5[n] = enregistre(n, (ca, cb)[n == nB], (ma, mb)[n == nB])
        P5[nA]["nb_pieces_rang"], P5[nB]["nb_pieces_rang"] = key[0], key[0]
        P5[nA]["pieces_rang"] = sorted(pieces_de(rang, cands[nA][1], cands[nB][1]))
        P5[nB]["pieces_rang"] = P5[nA]["pieces_rang"]
    out["P5"] = P5
    out["P5_chaines_impossibles"] = imposs5
    out["P5_pieces"] = pieces_texte(P5)
    out["P5_detail_modes_deplacement"] = det5
    out["P4_P5_hypotheses"] = (
        "ligament >= 3 mm (bord de tole, trous palier D6 / goupille D2,2, trou voisin du levier) pour tout trou DEPLACE ; "
        "trou non deplace garde son ligament actuel ; oeil local D9 (R 4,5) si le bord est trop proche, centre du trou "
        "dans la matiere ou hors contour de 3 mm au plus (l'oeil prolonge la piece) ; voisin = tole avec |dZ| < 5 (A_k/B_k) ; "
        "collision = disque (R1,5 sans oeil, R4,5 avec oeil) contre le contour plein de la tige voisine et oeil contre oeil ; "
        "bande >= 3 mm entre les deux trous d'un meme levier ; biellette L'/L dans [0,5 ; 1,5] ; rapport exact 1,05 a course 5 ; "
        "meme sens de queue qu'avant ; pas de collision testee avec les autres pieces du conteneur")
    # ---- ligament 3 mm de P1
    l1 = {}
    for n in CHAINES:
        p1 = out["P1"][n]
        c = C[n]
        T, H = tuple(p1["T"]), tuple(p1["H"])
        e = dict(bouge=p1["bouge"], ligament_P1=p1.get("ligament"), seuil_P1=p1.get("seuil_ligament_mm"))
        if p1["bouge"].startswith("levier"):
            an = LEV[c["r"]].analyse(np.array([H]))
            pp = tuple(out["P1"][PART[n]]["H"])
            web = dist(H, pp) - D_TROU
            e.update(ligament_bord=float(an["lig_ext"][0]), ligament_trous=float(an["lig_int"][0]), bande_partenaire=web)
            e["tient_3mm"] = bool(min(an["lig_ext"][0], an["lig_int"][0], web) >= LIG - 1e-9)
            e["oeil_9mm_regle"] = bool(an["lig_int"][0] >= LIG - 1e-9 and web >= LIG - 1e-9)
        elif p1["bouge"].startswith("tige"):
            an = TIGE[n].analyse(np.array([T]))
            e.update(ligament_bord=float(an["lig_ext"][0]), ligament_trous=float(an["lig_int"][0]))
            e["tient_3mm"] = bool(min(an["lig_ext"][0], an["lig_int"][0]) >= LIG - 1e-9)
            e["oeil_9mm_regle"] = bool(an["lig_int"][0] >= LIG - 1e-9)
        l1[n] = e
    out["P1_ligament_3mm"] = l1
    json.dump(out, open(os.path.join(HERE, "propositions.json"), "w"), indent=1, ensure_ascii=False, default=float)
    # ---- affichage
    for cas in ("P4", "P5"):
        print(cas)
        for n in CHAINES:
            r = out[cas][n]
            if not r.get("mode"):
                print(" ", n, r["bouge"])
                continue
            print(" %s %s dT=%.2f dH=%.2f L %.2f->%.2f lig=%s oeilT=%s oeilH=%s rap=%.4f lev=%.2f F=%.0f T=%s H=%s" % (
                n, r["bouge"], r["deplacement_T"], r["deplacement_H"], r["longueur_avant"], r["longueur_apres"], r.get("ligament"),
                r.get("oeil_tige"), r.get("oeil_levier"), r["rapport_exact"], r["levee"], r["effort_g"],
                tuple(round(v, 2) for v in r["T"]), tuple(round(v, 2) for v in r["H"])))
        print(json.dumps(out[cas + "_pieces"], ensure_ascii=False), out[cas + "_chaines_impossibles"])
    print(json.dumps(out["largeur_tole_attache_actuelle"]))
    print(json.dumps(out["P1_ligament_3mm"], ensure_ascii=False))
    print(json.dumps(out["P4_variante_voisin_dZ_inclus_5"]))
    print(json.dumps(out["P5_detail_modes_deplacement"]))
    print("duree %.0fs" % (time.time() - t0))


main2()
