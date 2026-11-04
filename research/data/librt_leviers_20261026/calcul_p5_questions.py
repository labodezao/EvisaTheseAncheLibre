"""P5 : 3 solutions chiffrees pour A2 et B1, trou toujours centre sur l'axe de la bande, ligament >= 1 mm, contour inchange
(sauf solution c : toute la tige decalee le long de son axe local). Importe le modele existant (modele.py), ne le recopie pas.
Controle : relance calcul_p5_axe.py et verifie que p5_axe.json est identique avant tout calcul."""
import os, sys, json, math, subprocess
import numpy as np
HERE_Q = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE_Q)
PY = r"J:\claude\venv\Scripts\python.exe"
ROOT = r"J:\zw3d_travail\librt\propositions_leviers_20261026"


def controle_axe():
    ref = json.load(open(os.path.join(ROOT, "p5_axe.json")))
    subprocess.run([PY, os.path.join(ROOT, "calcul_p5_axe.py")], cwd=ROOT, check=True, capture_output=True)
    new = json.load(open(os.path.join(ROOT, "p5_axe.json")))
    if new != ref:
        sys.exit("ARRET : calcul_p5_axe.py ne redonne pas p5_axe.json")
    return True


if __name__ == "__main__" and "--sans-controle" not in sys.argv:
    controle_axe()

import modele
from shapely.geometry import Point, Polygon
from shapely.affinity import translate
g = modele.g
C, _res, D, SENS0, TIGE, PLEINE, ZC, BASE0, CIBLE, R_TROU = (g[k] for k in ("C", "_res", "D", "SENS0", "TIGE", "PLEINE", "ZC", "BASE0", "CIBLE", "R_TROU"))
CHAINES, VOISINS, collision, axe_local, calcule, bisect = (g[k] for k in ("CHAINES", "VOISINS", "collision", "axe_local", "calcule", "bisect"))
LIG_MIN = 1.0


def lig_trou(n, q):
    a = TIGE[n].analyse(np.array([q]))
    return float(min(a["lig_ext"][0], a["lig_int"][0]))


def regard(n):
    c = C[n]
    T, H = np.array(c["T"]), tuple(c["H"])
    u, mil, larg = axe_local(TIGE[n], T)
    if u[1] < 0:
        u = -u
    return c, T, H, u


def scan_T(n, c, T, H, u, d=D):
    """Meilleur t (rapport le plus proche de 1,05) avec ligament >= 1 mm."""
    best = None
    for t in np.round(np.arange(-25, 25.001, 0.01), 2):
        q = T + t * u
        try:
            r = _res(c, tuple(q), H, d)
        except Exception:
            continue
        if r["sens_queue"] != SENS0[n] or not np.isfinite(r["rapport_exact"]):
            continue
        lig = lig_trou(n, q)
        if lig < LIG_MIN - 1e-9:
            continue
        k = (abs(r["rapport_exact"] - CIBLE), abs(t))
        if best is None or k < best[0]:
            best = (k, float(t), r, lig)
    return best


def rap_s(n, c, T, H, u, s, d=D):
    return _res(c, tuple(T + s * u), H, d)["rapport_exact"]


def solve_s(n, c, T, H, u, cible=CIBLE, d=D):
    ss = np.arange(-30, 30.01, 0.25)
    v = []
    for s in ss:
        try:
            v.append(rap_s(n, c, T, H, u, s, d) - cible)
        except Exception:
            v.append(np.nan)
    sols = [bisect(lambda x: rap_s(n, c, T, H, u, x, d) - cible, ss[i], ss[i + 1]) for i in range(len(ss) - 1)
            if np.isfinite(v[i]) and np.isfinite(v[i + 1]) and v[i] * v[i + 1] < 0]
    return min(sols, key=abs) if sols else None


def effets_decalage(n, c, T, u, s):
    """Ce que change le decalage s de toute la tige (contour + trou T), palier de pivot fixe."""
    P = TIGE[n]
    sh = s * u
    ext0, ext1 = P.ext, translate(P.ext, *sh)
    pv = Point(c["piv"])
    rings = [Polygon(r) for r in P.mat.interiors]
    ring = [r for r in rings if r.centroid.distance(pv) < 0.3][0]
    rp = math.sqrt(ring.area / math.pi)
    autres0 = [r for r in rings if r.centroid.distance(pv) >= 0.3]

    def lig_pivot(ext, autres):
        d = ext.exterior.distance(pv)
        dd = min([a.distance(pv) for a in autres] + [1e9])
        return ((d if ext.contains(pv) else -d) - rp, dd - rp)
    l0 = lig_pivot(ext0, autres0)
    l1 = lig_pivot(ext1, [translate(a, *sh) for a in autres0])
    voisins = {}
    for m in CHAINES:
        if m == n:
            continue
        voisins[m] = dict(dZ=round(ZC[m] - ZC[n], 2), dans_modele=bool(m in VOISINS[n]),
                          dist_avant=round(float(ext0.distance(PLEINE[m])), 2), dist_apres=round(float(ext1.distance(PLEINE[m])), 2),
                          recouvre_apres=bool(ext1.intersects(PLEINE[m])))
    col1 = bool(collision(n, np.array(ext1.exterior.coords), 1.0).any())
    col0 = bool(collision(n, np.array(ext0.exterior.coords), 1.0).any())
    return dict(pied_decale=[round(float(sh[0]), 2), round(float(sh[1]), 2)],
                pivot_ligament_avant=[round(l0[0], 2), round(l0[1], 2)], pivot_ligament_apres=[round(l1[0], 2), round(l1[1], 2)],
                pivot_trou_rayon=round(rp, 2), voisins=voisins, collision_modele_1mm_avant=col0, collision_modele_1mm_apres=col1,
                biellette_sur_L0=round(float(math.dist(T + sh, c["H"]) / BASE0[n]["longueur_biellette"]), 3))


def sol_c(n, c, T, H, u, s, r, extra=None):
    e = effets_decalage(n, c, T, u, s)
    lt = lig_trou(n, T)
    return dict(solution="c", description="toute la tige (contour + trou T) decalee le long de son axe, palier de pivot fixe",
                s=round(float(s), 2), course=D, rapport=round(r["rapport_exact"], 3), levee=round(r["levee"], 2),
                ligament_mini=round(min(lt, *e["pivot_ligament_apres"]), 2), ligament_trou_T=round(lt, 2),
                ce_qui_bouge=["contour de la tige", "trou T", "pied sous le bouton : monte de %.2f mm" % e["pied_decale"][1],
                              "ligament du trou de pivot (palier fixe)"], effets=e, **(extra or {}))


def chaine_A2():
    n = "A2"
    c, T, H, u = regard(n)
    r0 = _res(c, tuple(T), H, D)
    out = [dict(solution="a", description="ne rien changer", t=0.0, course=D, rapport=round(r0["rapport_exact"], 3),
                levee=round(r0["levee"], 2), ligament_mini=round(lig_trou(n, T), 2), ce_qui_bouge=[])]
    k, t, r, lig = scan_T(n, c, T, H, u)
    out.append(dict(solution="b", description="trou T sur l'axe au plus loin, ligament >= 1 mm", t=round(t, 2), course=D,
                    rapport=round(r["rapport_exact"], 3), levee=round(r["levee"], 2), ligament_mini=round(lig, 2),
                    ce_qui_bouge=["trou T de la tige (le long de l'axe)"],
                    biellette_sur_L0=round(r["longueur_biellette"] / BASE0[n]["longueur_biellette"], 3),
                    collision_trou_modele=bool(collision(n, np.array([T + t * u]), R_TROU).any())))
    s = solve_s(n, c, T, H, u)
    out.append(sol_c(n, c, T, H, u, s, _res(c, tuple(T + s * u), H, D)))
    return dict(chaine=n, axe_u=[round(float(x), 4) for x in u], T=[float(x) for x in T], H=[float(x) for x in H], solutions=out)


def chaine_B1():
    n = "B1"
    c, T, H, u = regard(n)
    k, t, r, lig = scan_T(n, c, T, H, u)
    out = [dict(solution="a", description="meilleur trou T sur l'axe, ligament >= 1 mm", t=round(t, 2), course=D,
                rapport=round(r["rapport_exact"], 3), levee=round(r["levee"], 2), ligament_mini=round(lig, 2),
                ce_qui_bouge=["trou T de la tige (le long de l'axe)"],
                biellette_sur_L0=round(r["longueur_biellette"] / BASE0[n]["longueur_biellette"], 3))]
    cc = dict(c)
    cc["T"] = tuple(T + t * u)
    d2 = bisect(lambda d: calcule(cc, H, d)["levee"] - 5.25, 0.5, 20.0)
    r2 = calcule(cc, H, d2)
    a1 = C["A1"]
    ra = calcule(a1, a1["H"], d2)
    out.append(dict(solution="b", description="trou T comme (a) + course du bouton du rang 1 portee a la valeur qui donne levee 5,25",
                    t=round(t, 2), course=round(d2, 2), rapport=round(r2["rapport_exact"], 3), levee=round(r2["levee"], 2),
                    ligament_mini=round(lig, 2), ce_qui_bouge=["trou T de la tige", "course du bouton rang 1 : %.2f mm au lieu de 5" % d2],
                    effet_A1_geometrie_actuelle=dict(course=round(d2, 2), rapport=round(ra["rapport_exact"], 3), levee=round(ra["levee"], 2))))
    s15 = solve_s(n, c, T, H, u)
    atteint = False
    extra = {}
    if s15 is not None:
        e15 = effets_decalage(n, c, T, u, s15)
        dv = min([v["dist_apres"] for v in e15["voisins"].values() if v["dans_modele"]] + [99])
        ok15 = min(e15["pivot_ligament_apres"]) >= LIG_MIN and dv >= LIG_MIN
        extra["s_pour_1_05"] = dict(s=round(float(s15), 2), ligament_pivot=e15["pivot_ligament_apres"][0], distance_voisine_modele=dv, admissible=bool(ok15))
        atteint = bool(ok15)
        s = s15
    if not atteint:
        best = None
        for x in np.round(np.arange(-30, 30.001, 0.05), 2):
            try:
                rx = _res(c, tuple(T + x * u), H, D)
            except Exception:
                continue
            if rx["sens_queue"] != SENS0[n]:
                continue
            ex = effets_decalage(n, c, T, u, x)
            dv = min([v["dist_apres"] for v in ex["voisins"].values() if v["dans_modele"]] + [99])
            if min(ex["pivot_ligament_apres"]) < LIG_MIN or dv < LIG_MIN:
                continue
            k = (abs(rx["rapport_exact"] - CIBLE), abs(x))
            if best is None or k < best[0]:
                best = (k, float(x))
        s = best[1]
    extra["atteint_1_05"] = atteint
    out.append(sol_c(n, c, T, H, u, s, _res(c, tuple(T + s * u), H, D), extra))
    return dict(chaine=n, axe_u=[round(float(x), 4) for x in u], T=[float(x) for x in T], H=[float(x) for x in H], solutions=out)


if __name__ == "__main__":
    res = dict(controle_p5_axe="p5_axe.json retrouve a l'identique" if "--sans-controle" not in sys.argv else "non relance",
               A2=chaine_A2(), B1=chaine_B1())
    json.dump(res, open(os.path.join(HERE_Q, "p5_questions.json"), "w"), indent=1, ensure_ascii=False)
    for n in ("A2", "B1"):
        for s_ in res[n]["solutions"]:
            print(n, {k: v for k, v in s_.items() if k not in ("effets", "description", "ce_qui_bouge")})
        print(n, json.dumps(res[n]["solutions"][2]["effets"], ensure_ascii=False))
