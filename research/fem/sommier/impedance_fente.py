"""Ce que voit l'anche : l'impédance d'entrée de la chambre, vue depuis sa fente (Elmer).

La question
-----------
Quand la languette pousse un petit débit d'air q à travers sa fente, quelle pression p
la chambre lui renvoie-t-elle ? Le rapport Z(f) = p / q (en Pa.s/m3) est l'impédance
d'entrée : c'est TOUT ce que la chambre, le trou de table et le dehors font à l'anche,
fréquence par fréquence. Grande impédance = la chambre « répond » fort.

Ce que fait ce script, en mots
------------------------------
1. Il construit l'air d'une chambre du sommier R12 (comme `chambre_modes.py`, mêmes cotes)
   et lui ajoute la fente d'une anche : un canal rectangulaire (longueur et largeur de la
   fente) à travers la plaque (son épaisseur), posé sur la face extérieure de la case A.
2. Il impose un petit débit à l'entrée de la fente (côté soufflet) et résout l'équation
   de Helmholtz (Elmer, `HelmholtzSolve`) de 50 Hz à 4 kHz ; parois rigides, pression
   nulle au bout du trou de table (comme pour les modes propres).
3. Z(f) = i.omega.rho.p_moyenne / (flux . S_fente) : Elmer impose dp/dn sur la fente,
   vérifié sur un conduit (Elmer = rho.c.tan(kL)/S à 1e-8 près, `--verif`).
4. Il resserre Z(f) en une somme de résonateurs (forme de Foster, sans pertes) :
       Z(f) = i.omega.[ L_fente + somme_n a_n / (omega_n^2 - omega^2) ]
   Chaque terme est un résonateur « volume + masse d'air » ; le premier donne au modèle
   semi-analytique son volume effectif V = rho.c^2 / a_1 et la longueur effective du trou
   l = (a_1 / omega_1^2).S_trou / rho. Ce sont les paramètres « éléments finis » du réseau
   de `coupled_reeds` (au lieu de la formule de Helmholtz et de sa correction devinée).

Ce que les éléments finis ne font PAS ici, dit simplement
---------------------------------------------------------
L'air qui passe dans la fente, entre la languette et la plaque, est un jet : il ne suit
pas l'acoustique linéaire (pertes, décollement, sens unique). Elmer ne le calcule pas
ici : il donne la réponse PASSIVE de l'air de la chambre. Le jet, la languette qui
s'ouvre et se ferme, l'auto-oscillation restent dans le modèle semi-analytique
(`banc_recherche/coupled_reeds.py`), qui reçoit ces paramètres.

Hypothèses : parois et plaque rigides, l'autre fente et la case B fermées (anches au
repos), air sans pertes à 20 °C (pics infiniment fins : les pertes réelles les
arrondiront), soupape loin (correction d'extrémité du trou comme `chambre_modes.py`).
Position de la fente sur la plaque : centrée par défaut (à mesurer, avec la pointe de
l'anche côté trou ou côté fond).

Usage
-----
  J:\\claude\\venv\\Scripts\\python.exe impedance_fente.py --verif        conduit (formule) et boîte 50x15x10 (3430 Hz)
  ... --chambre 1 --fente 37.4 4.32 --plaque 0.83                  une chambre, une fente (mm)
  ... --yaml ../anche/anches_r12.yaml                               les anches de la banque (chambre et fente)
Sorties : resultats/impedance_ch<k>_<id>.csv (f, Re, Im, |Z|) et .json (résonateurs).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))                              # research/fem
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))    # research/
import elmer_outils  # noqa: E402
from chambre_modes import C_SON, Chambre, air_occ, cotes_sommier  # noqa: E402

RHO = 1.2
TRAVAIL = os.path.join(elmer_outils.CALCULS, "impedance")
RESULTATS = os.path.join(ICI, "resultats")

SIF = """Header
  Mesh DB "." "maillage"
End
Simulation
  Coordinate System = Cartesian 3D
  Coordinate Scaling = 0.001
  Simulation Type = Scanning
  Timestep Intervals = {n}
  Timestep Sizes = 1
  Output Intervals = 0
  Steady State Max Iterations = 1
  Frequency = Variable Time
    Real MATC "{f0}*({r})^(tx-1)"
End
Body 1
  Equation = 1
  Material = 1
End
Material 1
  Sound Speed = Real {c}
  Density = Real {rho}
End
Equation 1
  Active Solvers(2) = 1 2
End
Solver 1
  Equation = Helmholtz
  Procedure = "HelmholtzSolve" "HelmholtzSolver"
  Variable = -dofs 2 Pressure
  Linear System Solver = Direct
  Linear System Direct Method = Umfpack
End
Solver 2
  Exec Solver = After Timestep
  Equation = SaveScalars
  Procedure = "SaveData" "SaveScalars"
  Filename = "z.dat"
  Variable 1 = Pressure 1
  Operator 1 = boundary int mean
  Variable 2 = Pressure 2
  Operator 2 = boundary int mean
End
Boundary Condition 1
  Target Boundaries(1) = 1
End
Boundary Condition 2
  Target Boundaries(1) = 2
  Pressure 1 = Real 0
  Pressure 2 = Real 0
End
Boundary Condition 3
  Target Boundaries(1) = 3
  Wave Flux 1 = Real 1.0
  Wave Flux 2 = Real 0.0
  Save Scalars = Logical True
End
"""


def balayage(dossier, f0, f1, n, c=C_SON):
    """Lance Elmer sur `dossier/maillage` ; renvoie (f, p complexe moyenne sur la source)."""
    r = (f1 / f0) ** (1.0 / (n - 1))
    with open(os.path.join(dossier, "z.sif"), "w", encoding="utf-8") as fh:
        fh.write(SIF.format(n=n, f0=f0, r=r, c=c, rho=RHO))
    elmer_outils.elmersolver(dossier, "z.sif")
    d = np.loadtxt(os.path.join(dossier, "z.dat"), ndmin=2)
    f = f0 * r ** np.arange(len(d))
    return f, d[:, 0] + 1j * d[:, 1]


def impedance(f, p, S_m2):
    """Z = i.omega.rho.p / (g.S) pour un flux de 1 Pa/m (débit entrant g.S/(i.omega.rho))."""
    return 1j * 2 * np.pi * f * RHO * p / S_m2


# --- La fente sur la case A ------------------------------------------------------------------
def fente_occ(ch: Chambre, longueur, largeur, plaque, x_centre=None, z_centre=None, rentree=0.5):
    """Un canal rectangulaire perpendiculaire à la face extérieure de la case A
    (y = w(z)), de `plaque` mm de long, qui rentre de `rentree` mm dans l'air de la case
    pour une fusion propre. Renvoie (fonction pour air_occ, normale, centre de la sortie)."""
    s = (ch.t - ch.b) / ch.H                                   # pente de la face : dy/dz
    nrm = np.array([0.0, 1.0, -s]) / math.hypot(1.0, s)        # normale sortante
    tau = np.array([0.0, s, 1.0]) / math.hypot(1.0, s)         # le long de la face (vers le haut)
    zc = z_centre if z_centre is not None else 0.5 * (ch.fa + ch.H)
    xc = x_centre if x_centre is not None else ch.PasCav / 2
    C = np.array([xc, ch.w(zc), zc])
    if zc - longueur / 2 < ch.fa or zc + longueur / 2 > ch.H:
        raise ValueError(f"fente de {longueur} mm trop longue pour la case A ({ch.H - ch.fa:.1f} mm)")

    def construire(occ):
        base = C - rentree * nrm
        coins = [base + sx * largeur / 2 * np.array([1.0, 0, 0]) + sz * longueur / 2 * tau
                 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        pts = [occ.addPoint(*p) for p in coins]
        lignes = [occ.addLine(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        surf = occ.addPlaneSurface([occ.addCurveLoop(lignes)])
        ext = occ.extrude([(2, surf)], *((plaque + rentree) * nrm))
        return [t for d, t in ext if d == 3]

    return construire, nrm, C + plaque * nrm


def mailler(ch, fente, fichier, h=2.0, h_fin=None, rayon=6.0):
    """`h_fin` : maillage adapté, fin (h_fin) dans la fente, le col du trou et à moins de
    `rayon` mm d'eux, puis grossissant jusqu'à `h` (champs Distance + Threshold de Gmsh)."""
    import gmsh
    construire, nrm, sortie_fente = fente
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    vtags, vol_cases, L_col = air_occ(ch, occ, gmsh, extra=construire)
    gmsh.model.addPhysicalGroup(3, vtags, 1)
    bord = gmsh.model.getBoundary([(3, t) for t in vtags], oriented=False, combined=True)
    parois, sortie, source = [], [], []
    for d, t in bord:
        x, y, z = occ.getCenterOfMass(d, abs(t))
        if abs(z - (ch.H + L_col)) < 1e-6:
            sortie.append(abs(t))
        elif abs(np.dot(np.array([x, y, z]) - sortie_fente, nrm)) < 1e-6:
            source.append(abs(t))
        else:
            parois.append(abs(t))
    if not source:
        raise RuntimeError("face d'entrée de la fente introuvable")
    S_fente = sum(occ.getMass(2, t) for t in source)
    gmsh.model.addPhysicalGroup(2, parois, 1)
    gmsh.model.addPhysicalGroup(2, sortie, 2)
    gmsh.model.addPhysicalGroup(2, source, 3)
    gmsh.option.setNumber("Mesh.MeshSizeMax", h)
    gmsh.option.setNumber("Mesh.MeshSizeMin", (h_fin or h) / 6)
    if h_fin:
        fines = list(source) + list(sortie)
        for d, t in bord:
            c = np.array(occ.getCenterOfMass(d, abs(t)))
            pres_fente = np.linalg.norm(c - sortie_fente) < 30 and np.dot(c - sortie_fente, nrm) > -3.0
            if (c[2] > ch.H - 1e-6 or pres_fente) and abs(t) not in fines:
                fines.append(abs(t))
        fd = gmsh.model.mesh.field
        f_dist = fd.add("Distance")
        fd.setNumbers(f_dist, "SurfacesList", fines)
        f_seuil = fd.add("Threshold")
        fd.setNumber(f_seuil, "InField", f_dist)
        fd.setNumber(f_seuil, "SizeMin", h_fin)
        fd.setNumber(f_seuil, "SizeMax", h)
        fd.setNumber(f_seuil, "DistMin", 0.5)
        fd.setNumber(f_seuil, "DistMax", rayon)
        fd.setAsBackgroundMesh(f_seuil)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3)
    n = len(gmsh.model.mesh.getNodes()[0])
    gmsh.write(fichier)
    gmsh.finalize()
    V = (sum(vol_cases.values())) * 1e-9
    return dict(S_fente_m2=S_fente * 1e-6, V_cases_m3=V, noeuds=n)


# --- Résonateurs (forme de Foster) -----------------------------------------------------------
def poles(f, Z):
    """Fréquences où Im Z saute de + à - (pôles), estimées entre deux points."""
    y = Z.imag
    out = []
    for i in range(len(f) - 1):
        if y[i] > 0 and y[i + 1] < 0:
            out.append(math.sqrt(f[i] * f[i + 1]))
    return out


def ajuster(f, Z, n_poles=None, f_max=None):
    """Ajuste Im Z / omega = L + somme a_n / (omega_n^2 - omega^2) (moindres carrés,
    résidu relatif). Renvoie dict(L, poles=[(f_n, a_n)], rms_rel)."""
    from scipy.optimize import least_squares
    p0 = poles(f, Z)
    if n_poles is not None:
        p0 = p0[:n_poles]
    if f_max is None:
        f_max = f[-1]
    m = f <= f_max
    w = 2 * np.pi * f[m]
    y = Z.imag[m] / w

    def modele(x):
        L = x[0]
        out = np.full_like(w, L)
        for k in range(len(p0)):
            wn, a = x[1 + 2 * k], x[2 + 2 * k]
            out += a / (wn ** 2 - w ** 2)
        return out

    def res(x):
        return (modele(x) - y) / (np.abs(y) + np.median(np.abs(y)))

    # départ : omega_n des pôles, a_n et L par moindres carrés linéaires
    wn0 = [2 * np.pi * fp for fp in p0]
    A = np.column_stack([np.ones_like(w)] + [1 / (wn ** 2 - w ** 2) for wn in wn0])
    sol = np.linalg.lstsq(A / (np.abs(y) + np.median(np.abs(y)))[:, None],
                          y / (np.abs(y) + np.median(np.abs(y))), rcond=None)[0]
    x0 = [sol[0]]
    for k, wn in enumerate(wn0):
        x0 += [wn, sol[1 + k]]
    r = least_squares(res, x0, x_scale="jac", max_nfev=2000)
    x = r.x
    return dict(L_fente=float(x[0]),
                poles=[(float(x[1 + 2 * k] / (2 * np.pi)), float(x[2 + 2 * k])) for k in range(len(p0))],
                rms_rel=float(np.sqrt(np.mean(res(x) ** 2))))


def parametres_reseau(fit, S_trou_m2, c=C_SON):
    """Le premier résonateur en paramètres du réseau de `coupled_reeds` : volume effectif
    (m3) et longueur effective du trou (m)."""
    f1, a1 = fit["poles"][0]
    w1 = 2 * np.pi * f1
    V = RHO * c * c / a1
    L_h = a1 / w1 ** 2                                         # inertance (kg/m4)
    return dict(f1_Hz=f1, V_eff_m3=V, L_trou_kg_m4=L_h, l_eff_trou_m=L_h * S_trou_m2 / RHO,
                L_fente_kg_m4=fit["L_fente"])


# --- Méthode rapide : pôles par les modes propres, résidus par quelques fréquences ----------
SOLVEURS = {
    "direct": "  Linear System Solver = Direct\n  Linear System Direct Method = Umfpack\n",
    "iteratif": ("  Linear System Solver = Iterative\n  Linear System Iterative Method = BiCGStabl\n"
                 "  BiCGStabl Polynomial Degree = 4\n  Linear System Preconditioning = ILU1\n"
                 "  Linear System Max Iterations = 3000\n  Linear System Convergence Tolerance = 1.0e-10\n"),
}
DIRECT = "  Linear System Solver = Direct\n  Linear System Direct Method = Umfpack\n"


def poles_elmer(dossier, n=4, c=C_SON):
    """Pôles de Z (Hz) : modes propres de l'air, fente fermée (même maillage), WaveSolver."""
    from chambre_modes import SIF as SIF_MODES
    with open(os.path.join(dossier, "modes.sif"), "w", encoding="utf-8") as fh:
        fh.write(SIF_MODES.format(c=c, n=n))
    return elmer_outils.frequences(elmer_outils.elmersolver(dossier, "modes.sif"))


def frequences_utiles(poles, f0, f_max, n=14, garde=0.04):
    """n fréquences en progression géométrique entre f0 et f_max, à plus de `garde` des pôles."""
    f = np.geomspace(f0, f_max, 4 * n)
    ok = [x for x in f if all(abs(x / p - 1) > garde for p in poles)]
    idx = np.linspace(0, len(ok) - 1, n).round().astype(int)
    return np.array(ok)[idx]


def balayage_liste(dossier, freqs, solveur="direct", c=C_SON):
    """Réponse harmonique aux fréquences données (table de valeurs dans le .sif)."""
    table = "\n".join(f"      {i + 1} {fi:.6f}" for i, fi in enumerate(freqs))
    sif = SIF.format(n=len(freqs), f0=1.0, r=1.0, c=c, rho=RHO)
    debut = sif.index("  Frequency = Variable Time")
    fin = sif.index("End", debut)
    sif = sif[:debut] + "  Frequency = Variable Time\n    Real\n" + table + "\n    End\n" + sif[fin:]
    sif = sif.replace(DIRECT, SOLVEURS[solveur.split(" ")[0]])
    with open(os.path.join(dossier, "z.sif"), "w", encoding="utf-8") as fh:
        fh.write(sif)
    elmer_outils.elmersolver(dossier, "z.sif")
    d = np.loadtxt(os.path.join(dossier, "z.dat"), ndmin=2)
    return np.asarray(freqs)[:len(d)], d[:, 0] + 1j * d[:, 1]


def ajuster_poles_fixes(f, Z, poles):
    """Im Z / omega = L + somme a_n / (omega_n^2 - omega^2), omega_n fixés : linéaire."""
    w = 2 * np.pi * np.asarray(f)
    y = Z.imag / w
    A = np.column_stack([np.ones_like(w)] + [1 / ((2 * np.pi * p) ** 2 - w ** 2) for p in poles])
    pds = 1 / (np.abs(y) + np.median(np.abs(y)))
    x = np.linalg.lstsq(A * pds[:, None], y * pds, rcond=None)[0]
    res = (A @ x - y) * pds
    return dict(L_fente=float(x[0]), poles=[(float(p), float(a)) for p, a in zip(poles, x[1:])],
                rms_rel=float(np.sqrt(np.mean(res ** 2))))


def z_foster(f, fit):
    w = 2 * np.pi * np.asarray(f)
    return 1j * w * (fit["L_fente"] + sum(a / ((2 * np.pi * p) ** 2 - w ** 2) for p, a in fit["poles"]))


# --- Calcul pour une chambre et une fente ----------------------------------------------------
def calculer(k, longueur, largeur, plaque, etiquette="", trou=(8.0, 25.0), table=8.0, corr=0.85,
             x_centre=None, z_centre=None, h=2.0, f0=50.0, f1=4000.0, n=70, methode="rapide",
             h_fin=None, solveur="iteratif", cotes=None):
    """`methode` : « rapide » (pôles par les modes propres, 14 fréquences harmoniques pour les
    résidus, puis Z(f) par la forme de Foster) ou « balayage » (n fréquences harmoniques)."""
    ch = Chambre(k, cotes or cotes_sommier(), trou=trou, table=table, corr_ext=corr)
    dossier = os.path.join(TRAVAIL, f"ch{k:02d}{etiquette}")
    os.makedirs(dossier, exist_ok=True)
    t0 = time.time()
    fente = fente_occ(ch, longueur, largeur, plaque, x_centre, z_centre)
    g = mailler(ch, fente, os.path.join(dossier, "air.msh"), h=h, h_fin=h_fin)
    elmer_outils.elmergrid(dossier, "air.msh")
    t_maillage = time.time() - t0
    if methode == "balayage":
        f, p = balayage(dossier, f0, f1, n)
        Z = impedance(f, p, g["S_fente_m2"])
        fit = ajuster(f, Z)
    else:
        pl = [x for x in poles_elmer(dossier, 4) if x > 1.0]
        pl_bas = [x for x in pl if x < f1]
        f_haut = 0.97 * pl[len(pl_bas)] if len(pl) > len(pl_bas) else f1
        fh = frequences_utiles(pl, f0, min(f1, f_haut))
        try:
            fh_, ph = balayage_liste(dossier, fh, solveur)
        except RuntimeError:
            if solveur == "direct":
                raise
            solveur = "direct (repli : l'itératif n'a pas convergé)"
            fh_, ph = balayage_liste(dossier, fh, "direct")
        fit = ajuster_poles_fixes(fh_, impedance(fh_, ph, g["S_fente_m2"]), pl_bas)
        f = f0 * (f1 / f0) ** (np.arange(n) / (n - 1))
        Z = z_foster(f, fit)
    S_trou = trou[0] * trou[1] * 1e-6
    res = dict(chambre=k, fente_mm=[longueur, largeur, plaque], trou_mm=list(trou), table_mm=table,
               corr_ext=corr, V_cases_cm3=g["V_cases_m3"] * 1e6, noeuds=g["noeuds"],
               poles_Hz=[pf for pf, _ in fit["poles"]], ajustement=fit,
               reseau=parametres_reseau(fit, S_trou) if fit["poles"] else None,
               elmer=elmer_outils.version(), duree_s=time.time() - t0, duree_maillage_s=t_maillage,
               methode=methode, h_mm=h, h_fin_mm=h_fin, solveur=solveur)
    return res, f, Z


def ecrire(res, f, Z, nom):
    os.makedirs(RESULTATS, exist_ok=True)
    base = os.path.join(RESULTATS, nom)
    with open(base + ".csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["f_Hz", "Re_Z_Pa_s_m3", "Im_Z_Pa_s_m3", "abs_Z_Pa_s_m3"])
        for fi, zi in zip(f, Z):
            w.writerow([f"{fi:.3f}", f"{zi.real:.6g}", f"{zi.imag:.6g}", f"{abs(zi):.6g}"])
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("->", base + ".csv / .json", flush=True)
    return base + ".json"


# --- Vérifications ---------------------------------------------------------------------------
def verif():
    """1) conduit 100 x 10 x 10 mm, source au bout, p = 0 à l'autre : Z = i.rho.c.tan(kL)/S ;
    2) boîte rigide 50 x 15 x 10 mm : premier mode c/2L = 3430 Hz (WaveSolver), sur la
    version d'Elmer choisie (et sur la 9.0 si elle est là)."""
    import gmsh
    lignes = []
    # 1) conduit
    dossier = os.path.join(TRAVAIL, "verif_conduit")
    os.makedirs(dossier, exist_ok=True)
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    v = occ.addBox(0, -5, -5, 100, 10, 10); occ.synchronize()
    gmsh.model.addPhysicalGroup(3, [v], 1)
    groupes = {1: [], 2: [], 3: []}
    for d, s in gmsh.model.getBoundary([(3, v)], oriented=False):
        x, _, _ = occ.getCenterOfMass(2, s)
        groupes[3 if abs(x) < 1e-6 else 2 if abs(x - 100) < 1e-6 else 1].append(s)
    for k, ss in groupes.items():
        gmsh.model.addPhysicalGroup(2, ss, k)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 4); gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3); gmsh.write(os.path.join(dossier, "air.msh")); gmsh.finalize()
    elmer_outils.elmergrid(dossier, "air.msh")
    f, p = balayage(dossier, 100.0, 3000.0, 12)
    Z = impedance(f, p, 1e-4)
    k_ = 2 * np.pi * f / C_SON
    Zt = 1j * RHO * C_SON * np.tan(k_ * 0.1) / 1e-4
    err = float(np.max(np.abs(Z.imag - Zt.imag) / np.abs(Zt.imag)))
    print(f"conduit : écart relatif max Elmer / i.rho.c.tan(kL)/S = {err:.2e} (12 fréquences, 100 à 3000 Hz)")
    lignes.append(dict(cas="conduit 100x10x10, Z vue du bout", elmer=elmer_outils.version(),
                       attendu="i.rho.c.tan(kL)/S", ecart_max_rel=f"{err:.2e}"))
    # 2) boîte 50 x 15 x 10 (modes propres, WaveSolver)
    from chambre_modes import SIF as SIF_MODES
    for home in [elmer_outils.elmer_home()] + [c for c in elmer_outils.CANDIDATS
                                               if c != elmer_outils.elmer_home() and os.path.isdir(c)]:
        dossier = os.path.join(TRAVAIL, "verif_boite_" + elmer_outils.version(home))
        os.makedirs(dossier, exist_ok=True)
        gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
        v = gmsh.model.occ.addBox(0, 0, 0, 50, 15, 10); gmsh.model.occ.synchronize()
        gmsh.model.addPhysicalGroup(3, [v], 1)
        faces = [s for d, s in gmsh.model.getBoundary([(3, v)], oriented=False)]
        gmsh.model.addPhysicalGroup(2, faces, 1)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 2); gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.mesh.generate(3); gmsh.write(os.path.join(dossier, "boite.msh")); gmsh.finalize()
        elmer_outils.elmergrid(dossier, "boite.msh", home=home)
        sif = SIF_MODES.format(c=C_SON, n=4).replace("Boundary Condition 2\n  Target Boundaries(1) = 2\n  p = Real 0.0\nEnd\n", "")
        sif = sif.replace("Eigen System Select = Smallest Magnitude",
                          "Eigen System Select = Smallest Magnitude\n  Eigen System Shift = Real 1.0e6")
        open(os.path.join(dossier, "modes.sif"), "w", encoding="utf-8").write(sif)
        fr = elmer_outils.frequences(elmer_outils.elmersolver(dossier, "modes.sif", home=home))
        f1 = [x for x in fr if x > 10][0]
        print(f"boîte 50x15x10, Elmer {elmer_outils.version(home)} : premier mode {f1:.1f} Hz (c/2L = 3430,0)")
        lignes.append(dict(cas="boîte rigide 50x15x10, mode 1", elmer=elmer_outils.version(home),
                           attendu="3430.0 Hz", obtenu=f"{f1:.1f} Hz"))
    os.makedirs(RESULTATS, exist_ok=True)
    with open(os.path.join(RESULTATS, "verification_elmer.csv"), "w", newline="", encoding="utf-8") as fh:
        cles = []
        for l in lignes:
            cles += [k for k in l if k not in cles]
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader(); w.writerows(lignes)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verif", action="store_true")
    ap.add_argument("--chambre", type=int)
    ap.add_argument("--fente", type=float, nargs=2, metavar=("LONGUEUR", "LARGEUR"))
    ap.add_argument("--plaque", type=float, default=1.2)
    ap.add_argument("--trou", type=float, nargs=2, default=(8.0, 25.0))
    ap.add_argument("--table", type=float, default=8.0)
    ap.add_argument("--yaml", help="anches_r12.yaml : chambre et fente de chaque anche")
    ap.add_argument("--h", type=float, default=2.0)
    a = ap.parse_args()
    print("Elmer", elmer_outils.version(), flush=True)
    if a.verif:
        verif()
    if a.chambre and a.fente:
        res, f, Z = calculer(a.chambre, a.fente[0], a.fente[1], a.plaque, trou=tuple(a.trou), table=a.table, h=a.h)
        print(json.dumps({k: res[k] for k in ("poles_Hz", "reseau")}, ensure_ascii=False, indent=1))
        ecrire(res, f, Z, f"impedance_ch{a.chambre:02d}")
    if a.yaml:
        from banc_recherche.banque_anches import charger_yaml
        for an in charger_yaml(a.yaml):
            k = an.valeur("chambre")
            if not k:
                print(an.id, ": pas de chambre, sauté")
                continue
            res, f, Z = calculer(int(k), an.valeur("fente_longueur_mm"), an.valeur("fente_largeur_mm"),
                                 an.valeur("plaque_mm"), etiquette="_" + an.id, trou=tuple(a.trou),
                                 table=a.table, h=a.h)
            res["id"] = an.id
            print(an.id, "pôles", [round(x, 1) for x in res["poles_Hz"]], "réseau", res["reseau"], flush=True)
            ecrire(res, f, Z, f"impedance_{an.id}")


if __name__ == "__main__":
    main()
