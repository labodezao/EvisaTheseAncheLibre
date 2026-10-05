"""Trou de table et levée de soupape d'une grosse basse (BB95) : ce que l'anche voit (Elmer).

La question (note du coffre « Lib RT — section de l'anche, trou de soupape et levée », 05/10/2026)
------------------------------------------------------------------------------------------------
Pour une chambre de basse à 3 voix (module BB95), quatre trous de table (8x12, 12x12, 15x15,
20x15 mm) et des levées de soupape de 1 à 6 mm : la chambre, le trou et le rideau d'air sous
la soupape, que renvoient-ils à l'anche ? La note l'a estimé avec des formules à constantes
localisées (inertance rho.l_eff/A, corrections de bout devinées). Ici Elmer calcule la même
chose sur la géométrie réelle, sans deviner les corrections de bout ni l'effet de la soupape
proche du trou.

Ce que fait ce script, en mots
------------------------------
1. Il construit l'air : la chambre du module BB95 (cotes lues dans le STL
   `module BB95 droit.STL`, 94 x 24 x 18 mm), la fente de l'anche sur une face (canal à
   travers la plaque, côté soufflet), le trou de la table (épaisseur `TABLE`), et le dehors :
   une boîte d'air au-dessus de la table dont on retire la soupape (plaque rigide 26 x 21 x 3 mm
   posée à `levee` mm au-dessus de la table). Les faces extérieures de la boîte absorbent les
   ondes (mot-clé Elmer `Wave Impedance 1 = c`, vérifié par `--verif` : Z = rho.c/S à 1e-6 ; rho.c serait faux)
   (condition de rayonnement plane, suffisante ici car la boîte
   est petite devant la longueur d'onde sous 2 kHz et le rayonnement y est quasi monopolaire).
2. Il impose un petit débit à l'entrée de la fente et résout Helmholtz (Elmer) à une liste de
   fréquences de 30 Hz à 3 kHz. Z(f) = p_fente / q : l'impédance que voit l'anche.
3. Il ajuste Z(f) sur le réseau de la note : Z = i.w.L_s + 1 / (i.w.C + 1/(R + i.w.L)),
   L_s masse d'air de la fente, C ressort d'air de la chambre, L masse d'air du trou ET du
   rideau de soupape (ensemble, c'est ce qu'Elmer voit), R la part réelle (rayonnement).
   On en tire la longueur effective l_eff = L.A_trou/rho, le volume effectif V = rho.c².C
   et la résonance f_H = 1/(2.pi.sqrt(L.C)).
4. Ces L, C, R vont dans `trou_soupape_jeu.py` (modèle temporel de l'anche : pertes
   d'orifice non linéaires, seuil, fréquence de jeu, pression perdue à la crête).

Ce que les éléments finis ne font PAS ici : les pertes d'orifice (rho.q|q|/(2 (Cd.A)²)), qui
sont non linéaires et portent la « pression perdue à la crête » de la note. Elmer donne la
partie LINÉAIRE (masses d'air, ressort, rayonnement), le modèle temporel ajoute les pertes.
Pas de couplage fluide-structure complet : la languette traverse sa plaque à chaque période
et le jet se décolle, ce qu'aucun solveur d'Elmer ne fait ; ce serait de la CFD à maillage
mobile (voir `research/cfd/`), hors de portée et inutile pour la question posée.

Hypothèses (à relire avant de croire un chiffre)
------------------------------------------------
- Cotes de la chambre : STL du module BB95 (`debit variable/bb95/module BB95 droit.STL`,
  rastérisé le 05/10/2026 : cadre ouvert 94 x 24 mm, 18 mm sous le dessus, fermé par les deux
  plaquettes BB95 25 x 105 collées sur les côtés). Volume 40,6 cm³ (la note avait pris 40).
- Épaisseur de table 5 mm (hypothèse : contreplaqué ou impression), plaquette 2,5 mm
  (hypothèse : plaquette de basse en dural), fente 74,1 x 8,1 mm (lame 74 x 8 mm, jeu 0,05 mm : Ewen).
- Soupape 26 x 21 mm (audit § 1), rigide, centrée sur le trou, rien d'autre autour
  (pas de caisse ni de grille : le dehors est libre). Une caisse fermée changerait R.
- Air sans pertes visqueuses : dans un rideau de 1 mm l'épaisseur de couche limite à 41 Hz
  est de 0,35 mm, les pertes visqueuses y comptent ; à 1 mm de levée R est donc sous-estimé.

Usage (depuis `research\\fem\\sommier\\`) :
  J:\\claude\\venv\\Scripts\\python.exe trou_soupape_bb95.py --verif        conduit à bout absorbant
  ... --convergence                                                      un cas, 3 maillages
  ... --plan                                                             4 trous x 6 levées
  ... --trou 12 12 --levee 2                                             un seul cas
Sorties : resultats/trou_soupape_bb95.csv (une ligne par cas), resultats/trou_soupape_bb95_Z.csv
(Z(f) de chaque cas), resultats/trou_soupape_bb95_convergence.csv.
Calculs bruts : J:\\claude\\calculs\\trou_soupape\\.
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
import elmer_outils  # noqa: E402

RHO, C_SON = 1.2, 343.0
TRAVAIL = os.path.join(elmer_outils.CALCULS, "trou_soupape")
RESULTATS = os.path.join(ICI, "resultats")

# --- Les cotes (mm) : trouvées ou hypothèses, voir l'en-tête -------------------------------
CHAMBRE = dict(L=94.0, l=24.0, H=18.0)          # STL module BB95 droit (05/10/2026)
TABLE = 5.0                                      # hypothèse
PLAQUE = 2.5                                     # hypothèse (plaquette de basse)
FENTE = (74.1, 8.1)                              # lame 74 x 8 mm, jeu 0,05 mm (Ewen, 05/10/2026)
SOUPAPE = (26.0, 21.0, 3.0)                      # audit § 1 ; épaisseur 3 mm (hypothèse)
DEHORS = (70.0, 70.0, 30.0)                      # boîte d'air absorbante au-dessus de la table
TROUS = {"8x12": (8.0, 12.0), "12x12": (12.0, 12.0), "15x15": (15.0, 15.0), "20x15": (20.0, 15.0)}
LEVEES = (1.0, 2.0, 3.0, 4.0, 6.0)
FREQS = [30, 41.2, 60, 90, 140, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1150, 1300, 1500,
         1800, 2200, 2600]

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
    Real
{table}
    End
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
{solveur}End
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
  Wave Impedance 1 = Real {zabs}
  Wave Impedance 2 = Real 0
End
Boundary Condition 3
  Target Boundaries(1) = 3
  Wave Flux 1 = Real 1.0
  Wave Flux 2 = Real 0.0
  Save Scalars = Logical True
End
"""
SOLVEURS = {
    "direct": "  Linear System Solver = Direct\n  Linear System Direct Method = Umfpack\n",
    "iteratif": ("  Linear System Solver = Iterative\n  Linear System Iterative Method = BiCGStabl\n"
                 "  BiCGStabl Polynomial Degree = 4\n  Linear System Preconditioning = ILU1\n"
                 "  Linear System Max Iterations = 3000\n  Linear System Convergence Tolerance = 1.0e-10\n"),
}


# --- Géométrie et maillage (Gmsh, OCC) --------------------------------------------------------
def geometrie(trou, levee, fichier, h=4.0, h_fin=1.0, h_dehors=6.0, chambre=None, table=TABLE,
              plaque=PLAQUE, fente=FENTE, soupape=SOUPAPE, dehors=DEHORS, avec_soupape=True):
    """Construit l'air et le maille. Renvoie S_fente (m²), nombre de nœuds, volume de chambre (m³).

    Groupes physiques : 1 parois rigides, 2 faces absorbantes (le dehors), 3 entrée de la fente."""
    import gmsh
    ch = chambre or CHAMBRE
    a, b = trou
    x0, y0 = ch["L"] / 2, ch["l"] / 2                       # le trou au milieu du dessus
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    corps = [occ.addBox(0, 0, 0, ch["L"], ch["l"], ch["H"])]
    # la fente : canal à travers la plaquette, sur la face y = 0, qui rentre de 0,5 mm
    corps.append(occ.addBox(x0 - fente[0] / 2, -plaque, (ch["H"] - fente[1]) / 2, fente[0], plaque + 0.5, fente[1]))
    # le trou de la table (rentre de 0,5 mm dans la chambre)
    corps.append(occ.addBox(x0 - a / 2, y0 - b / 2, ch["H"] - 0.5, a, b, table + 0.5))
    # le dehors : boîte d'air au-dessus de la table, moins la soupape
    z_t = ch["H"] + table
    dx, dy, dz = dehors
    boite = occ.addBox(x0 - dx / 2, y0 - dy / 2, z_t, dx, dy, dz)
    if avec_soupape:
        sa, sb, se = soupape
        soup = occ.addBox(x0 - sa / 2, y0 - sb / 2, z_t + levee, sa, sb, se)
        boite = occ.cut([(3, boite)], [(3, soup)])[0][0][1]
    corps.append(boite)
    out, _ = occ.fuse([(3, corps[0])], [(3, t) for t in corps[1:]])
    occ.synchronize()
    vtags = [t for d, t in out if d == 3]
    gmsh.model.addPhysicalGroup(3, vtags, 1)
    bord = gmsh.model.getBoundary([(3, t) for t in vtags], oriented=False, combined=True)
    parois, absorb, source, fines = [], [], [], []
    for d, t in bord:
        x, y, z = occ.getCenterOfMass(d, abs(t))
        if abs(y + plaque) < 1e-6:
            source.append(abs(t))
        elif (abs(z - (z_t + dz)) < 1e-6 or abs(x - (x0 - dx / 2)) < 1e-6 or abs(x - (x0 + dx / 2)) < 1e-6
              or abs(y - (y0 - dy / 2)) < 1e-6 or abs(y - (y0 + dy / 2)) < 1e-6):
            absorb.append(abs(t))
        else:
            parois.append(abs(t))
            # fin dans le rideau : dessous de la soupape, dessus de table sous son empreinte, col du trou
            if (abs(z - (z_t + levee)) < 1e-6 or (abs(z - z_t) < 1e-6 and abs(x - x0) < soupape[0] and abs(y - y0) < soupape[1])
                    or (ch["H"] - 1e-6 <= z <= z_t + 1e-6 and abs(x - x0) <= a and abs(y - y0) <= b)):
                fines.append(abs(t))
    if not source:
        raise RuntimeError("face d'entrée de la fente introuvable")
    S_fente = sum(occ.getMass(2, t) for t in source)
    gmsh.model.addPhysicalGroup(2, parois, 1)
    gmsh.model.addPhysicalGroup(2, absorb, 2)
    gmsh.model.addPhysicalGroup(2, source, 3)
    fd = gmsh.model.mesh.field
    f_dist = fd.add("Distance")
    fd.setNumbers(f_dist, "SurfacesList", fines)
    f_seuil = fd.add("Threshold")
    fd.setNumber(f_seuil, "InField", f_dist)
    fd.setNumber(f_seuil, "SizeMin", min(h_fin, levee if avec_soupape else h_fin))
    fd.setNumber(f_seuil, "SizeMax", h)
    fd.setNumber(f_seuil, "DistMin", 0.5)
    fd.setNumber(f_seuil, "DistMax", 3.0)
    # grossier loin dans le dehors
    f_box = fd.add("Box")
    fd.setNumber(f_box, "VIn", h_dehors)
    fd.setNumber(f_box, "VOut", h)
    fd.setNumber(f_box, "XMin", x0 - dx / 2); fd.setNumber(f_box, "XMax", x0 + dx / 2)
    fd.setNumber(f_box, "YMin", y0 - dy / 2); fd.setNumber(f_box, "YMax", y0 + dy / 2)
    fd.setNumber(f_box, "ZMin", z_t + 10.0); fd.setNumber(f_box, "ZMax", z_t + dz)
    f_min = fd.add("Min")
    fd.setNumbers(f_min, "FieldsList", [f_seuil, f_box])
    fd.setAsBackgroundMesh(f_min)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3)
    n = len(gmsh.model.mesh.getNodes()[0])
    gmsh.write(fichier)
    gmsh.finalize()
    return dict(S_fente_m2=S_fente * 1e-6, noeuds=n, V_chambre_m3=ch["L"] * ch["l"] * ch["H"] * 1e-9)


# --- Elmer -----------------------------------------------------------------------------------
def balayage(dossier, freqs, solveur="iteratif", zabs=C_SON):
    table = "\n".join(f"      {i + 1} {fi:.6f}" for i, fi in enumerate(freqs))
    with open(os.path.join(dossier, "z.sif"), "w", encoding="utf-8") as fh:
        fh.write(SIF.format(n=len(freqs), table=table, c=C_SON, rho=RHO, solveur=SOLVEURS[solveur], zabs=zabs))
    dat = os.path.join(dossier, "z.dat")
    if os.path.exists(dat):
        os.remove(dat)
    elmer_outils.elmersolver(dossier, "z.sif")
    d = np.loadtxt(dat, ndmin=2)
    if len(d) < len(freqs):
        raise RuntimeError(f"Elmer n'a rendu que {len(d)} fréquences sur {len(freqs)}")
    return np.asarray(freqs, float), d[:, 0] + 1j * d[:, 1]


def impedance(f, p, S_m2):
    """Z = i.omega.rho.p / (g.S) pour un flux de 1 Pa/m (débit entrant g.S/(i.omega.rho))."""
    return 1j * 2 * np.pi * f * RHO * p / S_m2


# --- Le réseau ajusté sur Z(f) ------------------------------------------------------------------
def z_reseau(f, L_s, C, R, L):
    w = 2 * np.pi * np.asarray(f, float)
    return 1j * w * L_s + 1.0 / (1j * w * C + 1.0 / (R + 1j * w * L))


def ajuster(f, Z, f_max=None):
    """L_s, C, R, L par moindres carrés sur log|Z| et phase, jusqu'à `f_max` (défaut :
    1,6 fois la résonance repérée). Départ : les formules à constantes localisées."""
    from scipy.optimize import least_squares
    f = np.asarray(f, float)
    i_max = int(np.argmax(np.abs(Z)))
    f_H0 = f[i_max]
    f_max = f_max or 1.6 * f_H0
    m = f <= f_max
    w = 2 * np.pi * f[m]
    # départ : C par la pente basse fréquence de Im(1/Z) ~ w.C - 1/(w.L)
    C0 = 40e-6 / (RHO * C_SON ** 2)
    L0 = 1.0 / ((2 * np.pi * f_H0) ** 2 * C0)
    x0 = np.log([1.0, C0, 1e4, L0])

    def res(x):
        Zm = z_reseau(f[m], *np.exp(x))
        return np.concatenate([np.log(np.abs(Zm) / np.abs(Z[m])), np.angle(Zm / Z[m])])

    sol = least_squares(res, x0, max_nfev=4000)
    L_s, C, R, L = np.exp(sol.x)
    f_H = 1.0 / (2 * np.pi * math.sqrt(L * C))
    ecart = float(np.median(np.abs(np.abs(z_reseau(f[m], L_s, C, R, L)) / np.abs(Z[m]) - 1)))
    return dict(L_fente_kg_m4=float(L_s), C_m3_Pa=float(C), V_eff_cm3=float(C * RHO * C_SON ** 2 * 1e6),
                R_Pa_s_m3=float(R), L_trou_kg_m4=float(L), f_H_Hz=float(f_H), f_max_ajust_Hz=float(f_max),
                ecart_median=ecart)


def formules_note(trou, levee, V_cm3=40.0, table=TABLE):
    """Les constantes localisées de la note du coffre (calcul_mecanique.py) : l_eff = table
    + 2 x 0,8 x rayon équivalent, inertance rho.l/A, f_H ; le rideau de la soupape : périmètre x levée."""
    a, b = trou
    A = a * b * 1e-6
    r_eq = math.sqrt(A / math.pi)
    l_eff = table * 1e-3 + 2 * 0.8 * r_eq
    L = RHO * l_eff / A
    C = V_cm3 * 1e-6 / (RHO * C_SON ** 2)
    P = 2 * (a + b) * 1e-3
    A_rideau = P * levee * 1e-3
    return dict(l_eff_mm=l_eff * 1e3, L_kg_m4=L, f_H_Hz=1 / (2 * math.pi * math.sqrt(L * C)),
                A_rideau_mm2=A_rideau * 1e6, levee_critique_mm=A / P * 1e3)


# --- Un cas -----------------------------------------------------------------------------------
def calculer(nom_trou, levee, h=4.0, h_fin=1.0, h_dehors=6.0, solveur="iteratif", freqs=FREQS,
             etiquette="", **kw):
    trou = TROUS[nom_trou] if isinstance(nom_trou, str) else nom_trou
    nom = nom_trou if isinstance(nom_trou, str) else f"{trou[0]:g}x{trou[1]:g}"
    dossier = os.path.join(TRAVAIL, f"{nom}_lev{levee:g}{etiquette}")
    os.makedirs(dossier, exist_ok=True)
    t0 = time.time()
    g = geometrie(trou, levee, os.path.join(dossier, "air.msh"), h=h, h_fin=h_fin, h_dehors=h_dehors, **kw)
    elmer_outils.elmergrid(dossier, "air.msh")
    t_m = time.time() - t0
    try:
        f, p = balayage(dossier, freqs, solveur)
    except RuntimeError:
        if solveur == "direct":
            raise
        solveur = "direct (repli)"
        f, p = balayage(dossier, freqs, "direct")
    Z = impedance(f, p, g["S_fente_m2"])
    fit = ajuster(f, Z)
    A = trou[0] * trou[1] * 1e-6
    note = formules_note(trou, levee)
    res = dict(trou=nom, trou_mm=list(trou), A_trou_mm2=A * 1e6, levee_mm=levee, noeuds=g["noeuds"],
               h_mm=h, h_fin_mm=h_fin, h_dehors_mm=h_dehors, solveur=solveur,
               duree_maillage_s=round(t_m, 1), duree_s=round(time.time() - t0, 1),
               l_eff_elmer_mm=fit["L_trou_kg_m4"] * A / RHO * 1e3, l_eff_note_mm=note["l_eff_mm"],
               L_elmer_kg_m4=fit["L_trou_kg_m4"], L_note_kg_m4=note["L_kg_m4"],
               f_H_elmer_Hz=fit["f_H_Hz"], f_H_note_Hz=note["f_H_Hz"],
               V_eff_cm3=fit["V_eff_cm3"], V_geom_cm3=g["V_chambre_m3"] * 1e6,
               R_Pa_s_m3=fit["R_Pa_s_m3"], L_fente_kg_m4=fit["L_fente_kg_m4"],
               A_rideau_mm2=note["A_rideau_mm2"], levee_critique_mm=note["levee_critique_mm"],
               ecart_ajust=fit["ecart_median"], elmer=elmer_outils.version())
    return res, f, Z


def ecrire_Z(lignes, nom):
    os.makedirs(RESULTATS, exist_ok=True)
    with open(os.path.join(RESULTATS, nom), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["trou", "levee_mm", "f_Hz", "Re_Z", "Im_Z", "abs_Z"])
        for trou, levee, f, Z in lignes:
            for fi, zi in zip(f, Z):
                w.writerow([trou, levee, f"{fi:.3f}", f"{zi.real:.6g}", f"{zi.imag:.6g}", f"{abs(zi):.6g}"])


def ecrire(res, nom):
    os.makedirs(RESULTATS, exist_ok=True)
    cles = list(res[0].keys())
    with open(os.path.join(RESULTATS, nom), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        for r in res:
            w.writerow({k: (json.dumps(v) if isinstance(v, list) else (f"{v:.6g}" if isinstance(v, float) else v))
                        for k, v in r.items()})


# --- Vérification : conduit à bout absorbant --------------------------------------------------
def verif():
    """Conduit 100 x 10 x 10 mm, flux au bout, bout opposé absorbant (Wave Impedance = rho.c) :
    Z vue de l'entrée doit valoir rho.c/S à toute fréquence (onde plane qui ne revient pas)."""
    import gmsh
    dossier = os.path.join(TRAVAIL, "verif_conduit")
    os.makedirs(dossier, exist_ok=True)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    v = occ.addBox(0, 0, 0, 100, 10, 10)
    occ.synchronize()
    gmsh.model.addPhysicalGroup(3, [v], 1)
    bord = gmsh.model.getBoundary([(3, v)], oriented=False, combined=True)
    parois, absorb, source = [], [], []
    for d, t in bord:
        x = occ.getCenterOfMass(d, abs(t))[0]
        (source if abs(x) < 1e-6 else absorb if abs(x - 100) < 1e-6 else parois).append(abs(t))
    gmsh.model.addPhysicalGroup(2, parois, 1)
    gmsh.model.addPhysicalGroup(2, absorb, 2)
    gmsh.model.addPhysicalGroup(2, source, 3)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 3.0)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3)
    gmsh.write(os.path.join(dossier, "air.msh"))
    gmsh.finalize()
    elmer_outils.elmergrid(dossier, "air.msh")
    S = 1e-4
    lignes = []
    for zabs, nom in ((RHO * C_SON, "rho.c"), (C_SON, "c")):
        f, p = balayage(dossier, [100, 300, 1000, 2000, 3000], "direct", zabs=zabs)
        Z = impedance(f, p, S)
        ecart = np.abs(Z / (RHO * C_SON / S) - 1)
        lignes.append((nom, ecart))
        print(f"Wave Impedance = {nom} : |Z| / (rho.c/S) = {np.abs(Z) / (RHO * C_SON / S)}, écart max {ecart.max():.2e}")
    return lignes


# --- Convergence -----------------------------------------------------------------------------
def convergence(nom_trou="12x12", levee=2.0):
    cas = [("grossier", dict(h=6.0, h_fin=1.5, h_dehors=9.0)),
           ("défaut", dict(h=4.0, h_fin=1.0, h_dehors=6.0)),
           ("fin", dict(h=2.5, h_fin=0.6, h_dehors=4.0))]
    res = []
    for nom, kw in cas:
        r, f, Z = calculer(nom_trou, levee, etiquette="_" + nom, **kw)
        r["maillage"] = nom
        res.append(r)
        print(f"{nom:9s} {r['noeuds']:7d} nœuds {r['duree_s']:6.0f} s  l_eff {r['l_eff_elmer_mm']:.2f} mm "
              f"V_eff {r['V_eff_cm3']:.2f} cm³ f_H {r['f_H_elmer_Hz']:.1f} Hz R {r['R_Pa_s_m3']:.3g}")
    ecrire(res, "trou_soupape_bb95_convergence.csv")
    return res


def plan(trous=None, levees=LEVEES, **kw):
    res, zs = [], []
    for nom in (trous or list(TROUS)):
        for lev in levees:
            r, f, Z = calculer(nom, lev, **kw)
            res.append(r)
            zs.append((nom, lev, f, Z))
            print(f"{nom:6s} levée {lev:3g} mm : {r['noeuds']:6d} nœuds, {r['duree_s']:5.0f} s, "
                  f"l_eff {r['l_eff_elmer_mm']:6.2f} mm (note {r['l_eff_note_mm']:5.2f}), "
                  f"f_H {r['f_H_elmer_Hz']:6.0f} Hz (note {r['f_H_note_Hz']:5.0f}), "
                  f"V_eff {r['V_eff_cm3']:5.1f} cm³, R {r['R_Pa_s_m3']:.3g}, ajust {r['ecart_ajust']:.3f}", flush=True)
            ecrire(res, "trou_soupape_bb95.csv")
            ecrire_Z(zs, "trou_soupape_bb95_Z.csv")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verif", action="store_true")
    ap.add_argument("--convergence", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--trou", nargs=2, type=float)
    ap.add_argument("--levee", type=float, default=3.0)
    ap.add_argument("--sans-soupape", action="store_true")
    a = ap.parse_args()
    if a.verif:
        verif()
    if a.convergence:
        convergence()
    if a.plan:
        plan()
    if a.trou:
        r, f, Z = calculer(tuple(a.trou), a.levee, avec_soupape=not a.sans_soupape)
        print(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
