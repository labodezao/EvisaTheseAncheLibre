"""Coupe 2D en travers de la lame BB95 : l'air qui passe autour d'elle, et la force qu'il lui donne.

La question (Ewen et l'audit Fable, 05/10/2026)
-----------------------------------------------
Le modèle temporel (`trou_soupape_jeu.py`) donne à la lame une force qui ne dépend QUE de sa
position : gamma.part(x).dp. Sans chambre, une telle force ne fournit aucun travail sur un cycle.
Or l'air qui converge vers l'écart a de l'inertie : quand la lame ferme l'écart, le débit baisse,
l'air qui arrive ralentit, et la pression monte sur la face amont de la lame PENDANT qu'elle
avance. C'est un amortissement négatif (un moteur). L'audit l'estime à la main
(Lambda_F = rho.b/(2.pi), à un facteur 2 près). Ce script le MESURE.

La méthode, en mots
-------------------
1. Une coupe en travers de la lame (8 x 1 mm), dans sa fente (jeu 0,05 mm de chaque côté),
   dans une plaquette de 2,5 mm ; l'air au-dessus (côté soufflet, pression P) et au-dessous
   (dehors, pression 0). Moitié du domaine (symétrie au milieu de la lame).
2. Elmer : FlowSolve (Navier-Stokes incompressible, laminaire, stabilisé) et MeshSolve (le
   maillage suit la lame : ALE).
3. Validation, écoulement stationnaire, lame immobile : débit dans le jeu contre Poiseuille (lame
   dans la fente), et contre Bernoulli avec contraction (lame au-dessus de la plaquette) ; trois
   maillages.
4. La lame (corps rigide) oscille de X = 0,02 mm à 155 Hz autour d'une position : au-dessus de la
   plaquette (« entrée »), dans la fente (« plaquette »), sous la plaquette (« sortie »). On
   enregistre la force verticale de l'air sur la lame et le débit ; on les décompose en une part
   en phase avec le déplacement (raideur) et une part en phase avec la vitesse (amortissement).
   c_aero < 0 : l'air pousse la lame à vibrer.
5. Les quasi-statiques (lame immobile à x0 +- dx) donnent la raideur seule ; la différence avec
   la part en phase du calcul dynamique est la masse d'air ajoutée.

Conventions : x = déplacement de la lame VERS LA PLAQUETTE (vers l'aval, comme dans le modèle
temporel) ; F = force de l'air sur la lame, positive vers l'aval ; tout par mètre d'envergure
(le long de la lame), la lame ENTIÈRE (les deux bords), sauf mention.

Ce que la coupe ne fait pas : le bout de la lame (le jet du bout), la variation de l'écart le
long de la lame (on calcule une section représentative), l'écoulement 3D loin de la lame. Le loin
compte : en 2D, l'inertie de l'air qui converge croît comme ln(R) (R : taille du domaine) ; en
3D elle est bornée par la longueur de la lame. On le traite par deux tailles de domaine et un
calcul de potentiel 3D (voir `inertie_3d`).

Usage (depuis `research\\fem\\sommier\\`) :
  J:\\claude\\venv\\Scripts\\python.exe coupe_2d_lame.py --validation         débits stationnaires
  ... --dynamique --position entree --pression 2000                  un cas oscillant
  ... --plan                                                         3 positions x 3 pressions
Calculs bruts : J:\\claude\\calculs\\coupe_2d\\ ; résultats : resultats/coupe_2d_*.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))                              # research/fem
import elmer_outils  # noqa: E402

RHO, MU = 1.2, 1.8e-5                    # air, kg/m³ et Pa.s (nu = 1,5e-5 m²/s)
TRAVAIL = os.path.join(elmer_outils.CALCULS, "coupe_2d")
RESULTATS = os.path.join(ICI, "resultats")

# --- La géométrie (mm ; Ewen, 05/10/2026) -------------------------------------------------------
B = 8.0                                  # largeur de la lame
E = 1.0                                  # épaisseur de la lame
JEU = 0.05                               # jeu latéral, de chaque côté
EP = 2.5                                 # épaisseur de la plaquette
A_FENTE = B / 2 + JEU                    # demi-largeur de la fente
F_LAME = 155.0                           # Hz
X_AMP = 0.02                             # mm, amplitude de l'oscillation imposée
# position = y du dessous de la lame (repère : dessus de la plaquette y = 0, amont y > 0)
POSITIONS = {
    "entree": 0.5,                       # 0,5 mm au-dessus de la plaquette
    "plaquette": -1.5,                   # dans la fente : dessus de la lame 0,5 mm sous le haut
    "sortie": -EP - 0.5 - E,             # dessus de la lame 0,5 mm sous la plaquette
}
PRESSIONS = (300.0, 1000.0, 2000.0)


# --- Maillage ------------------------------------------------------------------------------------
def maillage(fichier, y_lame, R=20.0, Rd=None, h_min=0.01, k=0.12, h_max=1.0):
    """Le demi-domaine (x >= 0), la lame en creux. Groupes de lignes :
    1 entrée haut, 2 entrée côté, 3 parois de la plaquette, 4 symétrie, 5 dessus de la lame,
    6 flanc de la lame, 7 dessous de la lame, 8 sortie bas, 9 sortie côté."""
    import gmsh
    Rd = R if Rd is None else Rd
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    haut = occ.addRectangle(0, 0, 0, R, R)
    fente = occ.addRectangle(0, -EP, 0, A_FENTE, EP)
    bas = occ.addRectangle(0, -EP - Rd, 0, R, Rd)
    air = occ.fuse([(2, haut)], [(2, fente), (2, bas)])[0]
    lame = occ.addRectangle(0, y_lame, 0, B / 2, E)
    air = occ.cut(air, [(2, lame)])[0]
    occ.synchronize()
    surf = [t for d, t in air if d == 2]
    gmsh.model.addPhysicalGroup(2, surf, 1)
    groupes = {i: [] for i in range(1, 10)}
    tol = 1e-6
    for d, t in gmsh.model.getBoundary([(2, s) for s in surf], oriented=False, combined=True):
        t = abs(t)
        xa, ya, _, xb, yb, _ = gmsh.model.getBoundingBox(1, t)
        cx, cy = (xa + xb) / 2, (ya + yb) / 2
        if abs(xa) < tol and abs(xb) < tol:
            g = 4
        elif abs(ya - (y_lame + E)) < tol and abs(yb - ya) < tol and xb <= B / 2 + tol:
            g = 5
        elif abs(xa - B / 2) < tol and abs(xb - B / 2) < tol and y_lame - tol <= ya and yb <= y_lame + E + tol:
            g = 6
        elif abs(ya - y_lame) < tol and abs(yb - ya) < tol and xb <= B / 2 + tol:
            g = 7
        elif abs(ya - R) < tol and abs(yb - R) < tol:
            g = 1
        elif abs(xa - R) < tol and cy > 0:
            g = 2
        elif abs(ya - (-EP - Rd)) < tol and abs(yb - ya) < tol:
            g = 8
        elif abs(xa - R) < tol and cy < -EP:
            g = 9
        else:
            g = 3
        groupes[g].append(t)
    for g, ts in groupes.items():
        if not ts:
            raise RuntimeError(f"groupe {g} vide (y_lame = {y_lame})")
        gmsh.model.addPhysicalGroup(1, ts, g)
    # tailles : fin autour de la lame et le long de la fente (jeu et arêtes)
    fd = gmsh.model.mesh.field
    pres = groupes[5] + groupes[6] + groupes[7]
    fente_l = []
    for t in groupes[3]:
        xa, ya, _, xb, yb, _ = gmsh.model.getBoundingBox(1, t)
        if xa <= A_FENTE + 0.5 and ya >= -EP - 0.01 and yb <= 0.01:
            fente_l.append(t)
        elif xa <= A_FENTE + tol and xb > A_FENTE:          # dessus / dessous de plaquette, près de l'arête
            fente_l.append(t)
    f1 = fd.add("Distance")
    fd.setNumbers(f1, "CurvesList", pres)
    fd.setNumber(f1, "Sampling", 2000)
    pts = []
    for (px, py) in ((A_FENTE, 0.0), (A_FENTE, -EP)):
        pts += [t for d, t in gmsh.model.getEntities(0)
                if abs(gmsh.model.getValue(0, t, [])[0] - px) < tol and abs(gmsh.model.getValue(0, t, [])[1] - py) < tol]
    f2 = fd.add("Distance")
    fd.setNumbers(f2, "PointsList", pts)
    # la paroi de la fente (x = A_FENTE) : fine sur toute sa hauteur
    paroi = [t for t in groupes[3] if abs(gmsh.model.getBoundingBox(1, t)[0] - A_FENTE) < tol
             and abs(gmsh.model.getBoundingBox(1, t)[3] - A_FENTE) < tol]
    f3 = fd.add("Distance")
    fd.setNumbers(f3, "CurvesList", paroi)
    fd.setNumber(f3, "Sampling", 500)
    f = fd.add("MathEval")
    fd.setString(f, "F", f"Min({h_max}, {h_min} + {k}*Min(F{f1}, Min(F{f2}, F{f3})))")
    fd.setAsBackgroundMesh(f)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(2)
    n = len(gmsh.model.mesh.getNodes()[0])
    gmsh.write(fichier)
    gmsh.finalize()
    return n


# --- Elmer ---------------------------------------------------------------------------------------
TETE = """Header
  Mesh DB "." "maillage"
End
Constants
End
Body 1
  Equation = 1
  Material = 1
  Initial Condition = 1
End
Initial Condition 1
  Velocity 1 = 0
  Velocity 2 = 0
  Pressure = {p_init}
End
Material 1
  Density = Real {rho}
  Viscosity = Real {mu}
End
"""

FLOW = """Solver {n}
  Equation = Navier-Stokes
  Procedure = "FlowSolve" "FlowSolver"
  Variable = Flow Solution[Velocity:2 Pressure:1]
  Stabilization Method = Stabilized
  Nonlinear System Max Iterations = {nl_max}
  Nonlinear System Convergence Tolerance = {nl_tol}
  Nonlinear System Newton After Iterations = {newton_apres}
  Nonlinear System Newton After Tolerance = 1.0e-3
  Nonlinear System Relaxation Factor = {relax}
  Linear System Solver = Direct
  Linear System Direct Method = UMFPack
  Steady State Convergence Tolerance = 1.0e-9
End
"""

MESH = """Solver {n}
  Equation = Mesh Update
  Procedure = "MeshSolve" "MeshSolver"
  Variable = -dofs 2 Mesh Update
  Linear System Solver = Direct
  Linear System Direct Method = UMFPack
  Steady State Convergence Tolerance = 1.0e-9
End
"""

FORCE = """Solver {n}
  Exec Solver = After Timestep
  Equation = ForceCompute
  Procedure = "FluidicForce" "ForceCompute"
  Calculate Viscous Force = True
  Sum Forces = True
End
"""

SAVE = """Solver {n}
  Exec Solver = After Timestep
  Equation = SaveScalars
  Procedure = "SaveData" "SaveScalars"
  Filename = "f.dat"
  Variable 1 = Pressure
  Operator 1 = boundary int
  Variable 2 = Velocity 1
  Operator 2 = boundary int
  Variable 3 = Velocity 2
  Operator 3 = boundary int
End
"""


def sif_bc(P, y_amp=0.0, w=0.0, t0=0.0):
    """Conditions aux limites. y_amp (m) : amplitude du mouvement VERTICAL (vers le haut) de la lame,
    y(t) = y_amp.sin(w.(t - t0)) pour t > t0 (lame immobile avant : l'écoulement s'établit)."""
    out = []

    def bc(i, corps):
        out.append(f"Boundary Condition {i}\n  Target Boundaries(1) = {i}\n{corps}End\n")

    fixe = "  Mesh Update 1 = 0\n  Mesh Update 2 = 0\n"
    # FlowSolve : « External Pressure = -P » donne p = +P (vérifié le 05/10/2026 : avec +P, la
    # pression lue à l'entrée valait -P et l'air remontait)
    bc(1, f"  External Pressure = Real {-P}\n  Velocity 1 = 0\n{fixe}  Save Scalars = True\n")
    bc(2, f"  External Pressure = Real {-P}\n  Velocity 2 = 0\n{fixe}  Save Scalars = True\n")
    bc(3, f"  Velocity 1 = 0\n  Velocity 2 = 0\n{fixe}")
    bc(4, "  Velocity 1 = 0\n  Mesh Update 1 = 0\n")
    if y_amp:
        mu_ = (f'  Mesh Update 1 = 0\n  Mesh Update 2 = Variable Time\n'
               f'    Real MATC "(tx > {t0!r})*{y_amp!r}*sin({w!r}*(tx-{t0!r}))"\n')
        vel = (f'  Velocity 1 = 0\n  Velocity 2 = Variable Time\n'
               f'    Real MATC "(tx > {t0!r})*{y_amp * w!r}*cos({w!r}*(tx-{t0!r}))"\n')
    else:
        mu_, vel = fixe, "  Velocity 1 = 0\n  Velocity 2 = 0\n"
    for i in (5, 6, 7):
        bc(i, f"{vel}{mu_}  Save Scalars = True\n  Calculate Fluidic Force = True\n")
    bc(8, f"  External Pressure = Real 0\n  Velocity 1 = 0\n{fixe}  Save Scalars = True\n")
    bc(9, f"  External Pressure = Real 0\n  Velocity 2 = 0\n{fixe}  Save Scalars = True\n")
    return "".join(out)


def sif_transitoire(P, dt, n_pas, y_amp=0.0, w=0.0, t0=0.0, nl_max=40, nl_tol=1e-7, bdf=2):
    """Un seul calcul : lame immobile jusqu'à t0 (l'écoulement s'établit), puis elle oscille.
    dt et n_pas peuvent être des listes (pas d'établissement, puis pas de l'oscillation).
    Tolérance non linéaire 1e-7 : mêmes forces qu'à 1e-9 à 2e-6 près (essai du 05/10/2026)."""
    dt = list(dt) if isinstance(dt, (list, tuple)) else [dt]
    n_pas = list(n_pas) if isinstance(n_pas, (list, tuple)) else [n_pas]
    s = TETE.format(p_init=P / 2, rho=RHO, mu=MU)
    s += f"""Simulation
  Coordinate System = Cartesian 2D
  Coordinate Scaling = 0.001
  Simulation Type = Transient
  Timestepping Method = BDF
  BDF Order = {bdf}
  Timestep Sizes({len(dt)}) = {" ".join(repr(v) for v in dt)}
  Timestep Intervals({len(n_pas)}) = {" ".join(str(v) for v in n_pas)}
  Steady State Max Iterations = 1
  Output Intervals({len(dt)}) = {" ".join("0" for _ in dt)}
End
Equation 1
  Active Solvers(4) = 1 2 3 4
End
"""
    s += MESH.format(n=1)
    s += FLOW.format(n=2, nl_max=nl_max, nl_tol=nl_tol, newton_apres=3, relax=1.0)
    s += FORCE.format(n=3)
    s += SAVE.format(n=4).replace("End\n", "  Variable 4 = Time\nEnd\n", 1)
    s += sif_bc(P, y_amp, w, t0)
    return s


def lire(dossier):
    """f.dat et ses noms -> dict {nom de colonne: valeurs}. Noms : « pressure|5 » (boundary int
    sur la bc 5), « res: fluid force 2 », « time »."""
    d = np.loadtxt(os.path.join(dossier, "f.dat"), ndmin=2)
    noms = open(os.path.join(dossier, "f.dat.names"), encoding="utf-8", errors="replace").read()
    cols, var = {}, None
    for m in re.finditer(r"^\s*(\d+):\s*(.*?)\s*$", noms.split("Variables in columns")[-1], re.M):
        j, txt = int(m.group(1)) - 1, m.group(2)
        b = re.match(r"boundary int:\s*(.*?)\s*over bc\s*(\d+)", txt, re.I)
        if b:
            var = b.group(1).strip().lower() or var
            cols[f"{var}|{b.group(2)}"] = d[:, j]
        else:
            nom = re.sub(r"^value:\s*", "", txt, flags=re.I).strip().lower()
            cols["time" if nom.startswith("time") else nom] = d[:, j]
    return cols, noms


def grandeurs(cols):
    """Force verticale de l'air sur la lame entière (N/m, positive VERS L'AVAL) et débits (m²/s,
    lame entière : deux moitiés)."""
    F_p = 2 * (cols["pressure|5"] - cols["pressure|7"])   # dessus pousse vers l'aval, dessous vers l'amont
    q_e = 2 * (-cols["velocity 2|1"] - cols["velocity 1|2"])
    q_s = 2 * (-cols["velocity 2|8"] + cols["velocity 1|9"])
    out = dict(F_pression=F_p, q_entree=q_e, q_sortie=q_s)
    ff = [k for k in cols if "fluid force 2" in k]
    if ff:
        out["F_fluidic"] = -2 * cols[ff[0]]               # signe calé sur F_pression (voir validation)
    if "time" in cols:
        out["t"] = cols["time"]
    return out


def preparer(nom, y_lame, **km):
    dossier = os.path.join(TRAVAIL, nom)
    os.makedirs(dossier, exist_ok=True)
    n = maillage(os.path.join(dossier, "air.msh"), y_lame, **km)
    elmer_outils.elmergrid(dossier, "air.msh")
    return dossier, n


def lancer(nom, y_lame, P, dt, n_pas, y_amp=0.0, t0=0.0, f=F_LAME, km=None, **ks):
    """Maille, écrit le .sif, lance Elmer ; renvoie les séries (dict de tableaux) et des infos."""
    t_debut = time.time()
    dossier, n = preparer(nom, y_lame, **(km or {}))
    with open(os.path.join(dossier, "dyn.sif"), "w", encoding="utf-8") as fh:
        fh.write(sif_transitoire(P, dt, n_pas, y_amp * 1e-3, 2 * math.pi * f, t0, **ks))
    if os.path.exists(os.path.join(dossier, "f.dat")):
        os.remove(os.path.join(dossier, "f.dat"))
    elmer_outils.elmersolver(dossier, "dyn.sif")
    cols, _ = lire(dossier)
    g = grandeurs(cols)
    np.savez(os.path.join(dossier, "series.npz"), **g)
    info = dict(cas=nom, noeuds=n, duree_s=time.time() - t_debut, P_Pa=P, y_lame_mm=y_lame, dt_s=dt,
                n_pas=n_pas, X_mm=y_amp, t0_s=t0, f_Hz=f, **(km or {}))
    with open(os.path.join(dossier, "info.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)
    return g, info


# --- Décomposition ------------------------------------------------------------------------------
def decomposer(t, y, t0, Y, w, n_fen):
    """y(t) sur les n_fen dernières périodes = dérive (1, t, t²) + A_s.sin(w(t-t0)) + A_c.cos(w(t-t0)).
    Renvoie A_s, A_c, l'écart type du résidu et l'incertitude (1 sigma) sur A_s et A_c."""
    T = 2 * math.pi / w
    m = t >= t[-1] - n_fen * T - 1e-12
    tt = t[m] - t[m].mean()
    ph = w * (t[m] - t0)
    M = np.column_stack([np.ones(tt.size), tt / T, (tt / T) ** 2, np.sin(ph), np.cos(ph),
                         np.sin(2 * ph), np.cos(2 * ph)])          # harmonique 2 : la non-linéarité
    c, *_ = np.linalg.lstsq(M, y[m], rcond=None)
    r = y[m] - M @ c
    s2 = r @ r / max(1, tt.size - M.shape[1])
    cov = s2 * np.linalg.inv(M.T @ M)
    return dict(A_s=c[3], A_c=c[4], moyenne=c[0], residu=math.sqrt(s2),
                dA_s=math.sqrt(cov[3, 3]), dA_c=math.sqrt(cov[4, 4]))


def analyser(g, info, n_fen=3):
    """Raideur et amortissement aérauliques (par m d'envergure, lame entière), pente du débit Q',
    retard du débit, Lambda_F = -c/Q'. Conventions du modèle temporel : x vers l'aval."""
    w = 2 * math.pi * info["f_Hz"]
    Y = info["X_mm"] * 1e-3
    t0 = info["t0_s"]
    t = g["t"]
    out = dict(cas=info["cas"], P_Pa=info["P_Pa"], y_lame_mm=info["y_lame_mm"], X_mm=info["X_mm"],
               noeuds=info["noeuds"], dt_s=info["dt_s"][-1] if isinstance(info["dt_s"], list) else info["dt_s"],
               duree_min=info["duree_s"] / 60)
    av = t <= t0 + 1e-12                               # établissement (lame immobile) : validation
    out.update(F0_N_m=float(g["F_pression"][av][-1]), F0_total_N_m=float(g.get("F_fluidic", g["F_pression"])[av][-1]),
               q0_m2_s=float(g["q_sortie"][av][-1]))
    if av.sum() > 4:
        T = 2 * math.pi / w
        m = (t <= t0 + 1e-12) & (t >= t0 - T)
        out["derive_q_par_periode"] = float((g["q_sortie"][m][-1] - g["q_sortie"][m][0]) / max(abs(out["q0_m2_s"]), 1e-30))
    if Y == 0:
        return out
    ydot = Y * w * np.cos(w * (t - t0)) * (t > t0)
    sigma = g["q_sortie"] + B * 1e-3 * ydot             # débit dans l'écart (sans le volume balayé)
    for nom, serie in (("F", g.get("F_fluidic", g["F_pression"])), ("Fp", g["F_pression"]), ("q", sigma)):
        d = decomposer(t, serie, t0, Y, w, n_fen)
        out.update({f"{nom}_{k}": v for k, v in d.items()})
    # F_aval = F0 - (A_s/Y).x - (A_c/(Y.w)).x'  (x = -y)
    out["k_aero_N_m2"] = out["F_A_s"] / Y              # raideur ajoutée par l'air (N/m par m) ; < 0 : assouplit
    out["c_aero_N_s_m2"] = out["F_A_c"] / (Y * w)      # amortissement (N.s/m par m) ; < 0 : moteur
    out["dc_aero"] = out["F_dA_c"] / (Y * w)
    out["c_aero_pression"] = out["Fp_A_c"] / (Y * w)
    out["Qp_m_s"] = out["q_A_s"] / Y                   # Q' = -d(sigma)/dx : la lame qui avance ferme
    out["q_retard_rad"] = math.atan2(out["q_A_c"], out["q_A_s"]) if out["q_A_s"] else float("nan")
    out["Lambda_F_kg_m"] = -out["c_aero_N_s_m2"] / out["Qp_m_s"] if abs(out["Qp_m_s"]) > 1e-6 else float("nan")
    return out


def cas_dynamique(nom, position, P, X=X_AMP, par_periode=50, n_osc=5, t_etab=0.02, km=None, y_lame=None,
                  jumeau=True, **ks):
    """Le cas oscillant ET son jumeau à lame immobile (même maillage, mêmes pas de temps).
    L'écoulement aval s'établit lentement (la force moyenne dérive de ~0,1 N/m par période, trente
    fois le signal cherché) : on analyse la DIFFÉRENCE des deux calculs, qui ne garde que la réponse
    au mouvement. Un calcul déjà fait (series.npz présent) n'est pas refait."""
    T = 1 / F_LAME
    dt_e = T / 50                                       # T/20 diverge au démarrage depuis le repos
    deja = os.path.join(TRAVAIL, nom, "info.json")
    if os.path.exists(deja) and os.path.exists(os.path.join(TRAVAIL, nom, "series.npz")):
        i0 = json.load(open(deja, encoding="utf-8"))      # le cas oscillant est fait : mêmes pas pour le jumeau
        n_e, n_o = i0["n_pas"]
        dt_e, dt_o = i0["dt_s"]
        par_periode = int(round(T / dt_o))
        n_osc = n_o // par_periode
        t_etab = n_e * dt_e
    n_e = int(round(t_etab / dt_e))
    t0 = n_e * dt_e
    y = POSITIONS[position] if y_lame is None else y_lame
    km = km or MAILLAGE
    series = {}
    for suffixe, amp in (("", X), ("_ref", 0.0)) if jumeau else (("", X),):
        d = os.path.join(TRAVAIL, nom + suffixe)
        if os.path.exists(os.path.join(d, "series.npz")) and os.path.exists(os.path.join(d, "info.json")):
            g = dict(np.load(os.path.join(d, "series.npz")))
            info = json.load(open(os.path.join(d, "info.json"), encoding="utf-8"))
        else:
            g, info = lancer(nom + suffixe, y, P, [dt_e, T / par_periode], [n_e, n_osc * par_periode], y_amp=amp,
                             t0=t0, km=km, **ks)
        series[suffixe] = (g, info)
    g, info = series[""]
    info = dict(info, X_mm=X, t0_s=t0)
    if jumeau:
        g_ref, info_ref = series["_ref"]
        if info_ref["noeuds"] != info["noeuds"] or len(g_ref["t"]) != len(g["t"]):
            raise RuntimeError("le jumeau n'a pas le même maillage ou les mêmes pas")
        g = {k: (v - g_ref[k] if k != "t" else v) for k, v in g.items()}
        stat = analyser(g_ref, dict(info_ref, X_mm=0.0, t0_s=t0))   # l'établissement (validation)
    info.update(position=position)
    r = analyser(g, info)
    if jumeau:
        for k in ("F0_N_m", "F0_total_N_m", "q0_m2_s", "derive_q_par_periode"):
            r[k] = stat.get(k)
        r["duree_min"] = (info["duree_s"] + info_ref["duree_s"]) / 60
    r.update(position=position, par_periode=par_periode, jumeau=jumeau)
    with open(os.path.join(TRAVAIL, nom, "analyse.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, indent=1, default=float)
    return r


MAILLAGE = dict(h_min=0.01, k=0.15, h_max=1.0, R=20.0)


# --- Du 2D au 3D et au mode de la lame -------------------------------------------------------------
L_LAME = 74.0                            # mm, longueur de la fente (et de la lame)
BETA_L, SIGMA_M = 1.8751040687, 0.7340955137


def psi(xi):
    """Déformée du mode 1 encastré-libre, 1 au bout (xi = z/L)."""
    b = BETA_L * np.asarray(xi, float)
    return (np.cosh(b) - np.cos(b) - SIGMA_M * (np.sinh(b) - np.sin(b))) / 2.0


def correction_3d(R=20.0, Rd=None, d=None, n=2000, faces=2):
    """Le loin : la coupe 2D met la pression de référence à la distance R (amont) et Rd (aval) ; en
    3D, l'air qui va vers l'écart vient d'un demi-espace, depuis les deux côtés de la lame (74 mm)
    et son bout (8 mm). Potentiel d'un puits de débit Q au ras d'une paroi : Q/(2.pi.r) ; en 2D, par
    mètre : (sigma/pi).ln(R/r). Pour une modulation de débit répartie comme la déformée (sigma(z)
    = Q'_bord.psi(z).x par bord), on calcule au milieu de la face de la lame (distance d des bords)
    G(z) = [potentiel 3D] - [potentiel 2D tronqué à R], par unité de Q'_bord.x, et l'intégrale
    modale J = int G(z).psi(z) dz (en m). La correction d'amortissement MODAL est alors
        dc = -rho . b . Q'_bord . faces . J
    (faces = 2 : le loin amont et le loin aval, de même signe). J > 0 : le 3D a PLUS d'inertie que
    la coupe ; J < 0 : moins. Hypothèses : écoulement potentiel, la lame et la plaquette ne gênent
    pas le loin (distances > b), la plaquette est une paroi infinie (anche montée dans un sommier ;
    plaquette seule dans l'air : le loin amont et aval se rejoignent autour d'elle, J plus petit)."""
    Rd = R if Rd is None else Rd
    d = (B / 2 + JEU) if d is None else d
    L = L_LAME
    z = (np.arange(n) + 0.5) / n * L                    # points d'évaluation (mm)
    zp = z.copy()                                       # sources le long des bords
    dz = L / n
    ps = psi(zp / L)
    # deux bords latéraux, chacun à distance d du milieu de la face
    r = np.sqrt(d * d + (z[:, None] - zp[None, :]) ** 2)
    phi3 = 2 * (ps[None, :] / r).sum(axis=1) * dz / (2 * math.pi)
    # le bout : de x = -d à +d, en z = L, intensité psi(1) = 1
    xb = (np.arange(200) + 0.5) / 200 * 2 * d - d
    rb = np.sqrt(xb[None, :] ** 2 + (L - z[:, None]) ** 2 + 0.25)   # +0,25 mm² : régularise au ras
    phi3 += (1.0 / rb).sum(axis=1) * (2 * d / 200) / (2 * math.pi)
    phi2 = lambda RR: 2 * psi(z / L) * np.log(RR / d) / math.pi     # deux bords, 2D tronqué
    G = phi3 - 0.5 * (phi2(R) + phi2(Rd))
    J = float((G * psi(z / L)).sum() * dz) * 1e-3       # m
    # longueur 2D équivalente : R tel que le 2D tronqué donne la même intégrale modale
    I2 = float((psi(z / L) ** 2).sum() * dz)            # mm
    I3 = float((phi3 * psi(z / L)).sum() * dz)
    R_eq = d * math.exp(I3 / I2 * math.pi / 2)
    return dict(J_m=J, R_equivalent_mm=R_eq, int_psi2_mm=I2, faces=faces)


def vers_modal(c_2d, Qp_2d, R=20.0, Rd=None, faces=2):
    """Amortissement aéraulique MODAL de la lame (N.s/m, au bout) depuis la coupe 2D :
    c_2d (N.s/m par m d'envergure) appliqué le long de la lame avec la pondération psi² (la
    modulation locale du débit suit psi, la force projetée aussi), plus le bout (un bord de 8 mm,
    psi = 1 : la moitié de la coupe par mètre de bord), plus la correction du loin 3D."""
    c3 = correction_3d(R, Rd, faces=faces)
    I2 = c3["int_psi2_mm"] * 1e-3
    c_local = c_2d * (I2 + 0.5 * B * 1e-3)
    dc = -RHO * B * 1e-3 * (Qp_2d / 2) * faces * c3["J_m"]
    return dict(c_modal_2d=c_local, dc_3d=dc, c_modal=c_local + dc, R_equivalent_mm=c3["R_equivalent_mm"])


def par_face(nom, n_fen=3):
    """Relit f.dat d'un cas et de son jumeau : raideur et amortissement par face de la lame (dessus,
    dessous : pression ; flancs et reste : total - pression = viscosité)."""
    d = os.path.join(TRAVAIL, nom)
    info = json.load(open(os.path.join(d, "info.json"), encoding="utf-8"))
    cols, _ = lire(d)
    ref = lire(d + "_ref")[0] if os.path.exists(os.path.join(d + "_ref", "f.dat")) else None
    w = 2 * math.pi * info["f_Hz"]
    Y = info["X_mm"] * 1e-3
    t = cols["time"]
    ff = [k for k in cols if "fluid force 2" in k][0]
    series = {"dessus": lambda c: 2 * c["pressure|5"], "dessous": lambda c: -2 * c["pressure|7"],
              "total": lambda c: -2 * c[ff]}
    out = {}
    for face, f in series.items():
        y = f(cols) - (f(ref) if ref is not None else 0.0)
        r = decomposer(t, y, info["t0_s"], Y, w, n_fen)
        out[f"k_{face}"] = r["A_s"] / Y
        out[f"c_{face}"] = r["A_c"] / (Y * w)
        out[f"dc_{face}"] = r["dA_c"] / (Y * w)
    out["c_visqueux"] = out["c_total"] - out["c_dessus"] - out["c_dessous"]
    return out


def theorie_stationnaire(position, P):
    """Débits de référence (m²/s, lame entière, deux jeux) pour la validation.
    Lame au-dessus ou au-dessous de la plaquette : Bernoulli avec contraction, écart g entre l'arête
    de la lame et celle de la fente (g = sqrt(h² + jeu²)), Cd = pi/(pi+2) = 0,611 (fente plane à
    arêtes vives, jet libre : von Mises 1917). Lame dans la fente : Poiseuille dans les deux jeux de
    0,05 mm sur l'épaisseur de la lame (1 mm), seul, puis avec la perte d'entrée et de sortie
    (K = 1,5 hauteurs dynamiques)."""
    v0 = math.sqrt(2 * P / RHO)
    y = POSITIONS[position]
    j = JEU * 1e-3
    if position == "plaquette":
        Lj = E * 1e-3
        u_p = P * j ** 2 / (12 * MU * Lj)
        a, b, c = 1.5 * RHO / 2, 12 * MU * Lj / j ** 2, -P             # P = K.rho.u²/2 + 12.mu.L.u/j²
        u = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
        return dict(q_poiseuille=2 * u_p * j, q_poiseuille_pertes=2 * u * j, q_bernoulli_cd1=2 * j * v0,
                    Re_jeu=RHO * u * j / MU)
    h = (y if y > 0 else -(y + E + EP)) * 1e-3
    g = math.sqrt(h * h + j * j)
    return dict(q_bernoulli_0611=2 * 0.611 * g * v0, q_bernoulli_cd1=2 * g * v0, g_mm=g * 1e3,
                Re_ecart=RHO * 0.611 * v0 * g / MU)


C_STRUCT = 2 * 0.004 * math.sqrt(1093.96 * 1.1451e-3)    # N.s/m, lame de ré# (zeta 0,004, m_eff, k_eff)


def synthese(noms, sortie="coupe_2d_modal.csv"):
    """Pour chaque cas : les coefficients par face (2D, par m), puis la lame entière (mode 1) :
    - dessus (inertie de l'air qui converge, côté soufflet) : psi² le long des côtés + le bout
      (un bord de 8 mm, psi = 1), plus la correction 3D du loin côté soufflet (une face) ;
    - dessous : psi² le long des côtés, sans correction du loin : la coupe montre que la face aval
      ne sent pas l'inertie de l'aval (le jet décolle aux arêtes et découple la lame du loin aval ;
      un premier maillage trop grossier y voyait un frein, +0,43 N.s/m par m, qui disparaît en
      raffinant : -0,005 +- 0,022) ;
    - c_jet = (c_dessous + visqueux)_modal / v_jet (kg/m), retenu seulement s'il dépasse deux fois
      son incertitude ; Lambda_F' = -c_dessus / Q' (kg/m, par m).
    N0_sans_chambre = moteur / (c_struct + frein), sans chambre, zeta = 0,004 (> 1 : la lame part)."""
    res = []
    for nom in noms:
        d = os.path.join(TRAVAIL, nom)
        a = json.load(open(os.path.join(d, "analyse.json"), encoding="utf-8"))
        info = json.load(open(os.path.join(d, "info.json"), encoding="utf-8"))
        f = par_face(nom)
        R = float(info.get("R", 20.0))
        P = float(a["P_Pa"])
        v_j = math.sqrt(2 * P / RHO)
        Qp = float(a["Qp_m_s"])
        c3 = correction_3d(R, R, faces=1)
        I2 = c3["int_psi2_mm"] * 1e-3
        dc_loin = -RHO * B * 1e-3 * (Qp / 2) * c3["J_m"]          # une face, signe de Q'
        c_dessus = f["c_dessus"] * (I2 + 0.5 * B * 1e-3) + dc_loin
        c_dessous_ch = f["c_dessous"] * I2
        c_dessous_ouv = c_dessous_ch
        c_visq = f["c_visqueux"] * I2
        r = dict(cas=nom, position=a["position"], P_Pa=P, R_mm=R, h_min=info.get("h_min"), k=info.get("k"),
                 X_mm=a["X_mm"], noeuds=a["noeuds"], q0_m2_s=a["q0_m2_s"], F0_N_m=a["F0_N_m"], Qp_m_s=Qp,
                 k_total_N_m2=f["k_total"], c_total_2d=f["c_total"], c_dessus_2d=f["c_dessus"],
                 c_dessous_2d=f["c_dessous"], c_visqueux_2d=f["c_visqueux"], dc_2d=f["dc_total"],
                 dc_dessous_2d=f["dc_dessous"],
                 Lambda_F_2d_kg_m=(-f["c_dessus"] / Qp) if abs(Qp) > 1 else float("nan"),
                 c_dessous_sur_rho_b_vjet=f["c_dessous"] / (RHO * B * 1e-3 * v_j),
                 R_equivalent_3d_mm=c3["R_equivalent_mm"], dc_loin_modal=dc_loin,
                 c_dessus_modal=c_dessus, c_dessous_modal_chambre=c_dessous_ch, c_dessous_modal_ouvert=c_dessous_ouv,
                 c_visqueux_modal=c_visq,
                 c_jet_kg_m=((c_dessous_ch + c_visq) / v_j) if abs(f["c_dessous"]) > 2 * f["dc_dessous"] else 0.0,
                 c_aero_modal_sans_chambre=c_dessus + c_dessous_ouv + c_visq)
        moteur = -min(0.0, c_dessus) - min(0.0, c_dessous_ouv)
        frein = max(0.0, c_dessus) + max(0.0, c_dessous_ouv) + c_visq
        r["N0_sans_chambre"] = moteur / (C_STRUCT + frein)
        res.append(r)
    ecrire(res, sortie)
    return res


def ecrire(res, nom):
    os.makedirs(RESULTATS, exist_ok=True)
    cles = []
    for r in res:
        cles += [k for k in r if k not in cles]
    with open(os.path.join(RESULTATS, nom), "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        wr.writeheader()
        for r in res:
            wr.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def ajouter(r, nom):
    """Ajoute une ligne à un CSV de résultats (relit l'existant ; un cas refait remplace l'ancien)."""
    chemin = os.path.join(RESULTATS, nom)
    res = []
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fh:
            res = [x for x in csv.DictReader(fh, delimiter=";") if x.get("cas") != r["cas"]]
    res.append(r)
    ecrire(res, nom)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--cas", nargs="+", help="nom:position:pression[:par_periode[:h_min[:R[:X]]]]")
    ap.add_argument("--sortie", default="coupe_2d_dynamique.csv")
    a = ap.parse_args()
    if a.cas:
        for item in a.cas:
            champs = item.split(":")
            nom, pos, P = champs[0], champs[1], float(champs[2])
            pp = int(champs[3]) if len(champs) > 3 and champs[3] else 50
            km = dict(MAILLAGE)
            if len(champs) > 4 and champs[4]:
                km["h_min"] = float(champs[4])
            if len(champs) > 5 and champs[5]:
                km["R"] = float(champs[5])
            X = float(champs[6]) if len(champs) > 6 and champs[6] else X_AMP
            r = cas_dynamique(nom, pos, P, X=X, par_periode=pp, km=km)
            print(json.dumps(r, default=float), flush=True)
            ajouter(r, a.sortie)
