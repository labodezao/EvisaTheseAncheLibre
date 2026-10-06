"""Couplage vibro-acoustique lame + air (Elmer) : la lame de la grosse basse BB95 dans son air.

La question (Ewen, 05/10/2026)
------------------------------
« Si on n'a pas un bon modèle, ça ne sert à rien d'avoir des réponses de transitoire. »
Avant de parler du temps de réponse, il faut savoir ce que l'air fait à la lame : de combien il
baisse sa fréquence (masse d'air entraînée, surtout dans les jeux étroits autour de la fente) et
combien il l'amortit (rayonnement), avec la vraie géométrie : soufflet en amont, lame levée de
1 mm au bout, fente, chambre du module BB95, trou de table, rideau de soupape, dehors.

La méthode, en mots
-------------------
1. La lame seule (dans le vide) : Elmer, élasticité 3D (`fem/anche/languette_modes.py`) contre
   Euler-Bernoulli exact. C'est la validation 1.
2. L'air : la lame est un creux dans l'air maillé (Gmsh), coupé en N bandes le long de sa longueur.
   On impose sur chaque bande la vitesse normale de la déformée du mode 1 (psi(x), 1 au bout) :
   dessous de la lame (côté plaquette) et dessus (côté soufflet) en sens opposés. Elmer résout
   Helmholtz (même solveur, mêmes conditions de rayonnement que `trou_soupape_bb95.py`) et rend la
   pression intégrée sur chaque bande. La force modale de l'air sur la lame donne l'impédance
   modale Z_m(f) = R_a + i.omega.m_a : m_a est la masse d'air entraînée, R_a l'amortissement par
   rayonnement (et par pompage à travers trou et soupape).
3. Le mode couplé : -omega².(m + m_a) + i.omega.(c + R_a) + k = 0, résolu en itérant sur f.
   C'est le couplage linéaire complet AU PREMIER ORDRE en m_a/m (projection sur le mode du
   vide : la déformée ne change pas, ce qui est juste tant que m_a/m reste petit ; on le vérifie).
4. Validation 2 (la méthode et ses signes) : la même lame seule dans un grand volume d'air libre
   (`--libre`) contre la masse ajoutée potentielle d'une bande, pi.rho.b²/4 par mètre (Lamb ;
   Sader 1998, limite non visqueuse), qu'une lame finie doit approcher par en dessous.

Ce que ce modèle ne fait pas : l'écoulement moyen (le jet), la lame qui entre dans la fente, la
viscosité dans les jeux de 0,05 mm (elle y compte : couche limite de 0,18 mm à 155 Hz ; elle
ajoute un amortissement que ce calcul ne voit pas). C'est la partie LINÉAIRE ; l'écoulement est
dans `trou_soupape_jeu.py`, qui reçoit m_a et R_a.

Usage (depuis `research\\fem\\sommier\\`) :
  J:\\claude\\venv\\Scripts\\python.exe couplage_lame_air.py --libre             validation 2
  ... --trou 12x12 --levee 3                                              un cas
  ... --plan                                                              les cas du tableau
  ... --convergence                                                       12x12, 3 mm, 2 maillages
Sortie : resultats/couplage_lame_air.csv ; calculs bruts : J:\\claude\\calculs\\couplage_lame_air\\.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))                              # research/fem
sys.path.insert(0, ICI)
import elmer_outils  # noqa: E402
import trou_soupape_bb95 as elm  # noqa: E402

RHO, C_SON = 1.2, 343.0
RHO_ACIER, E_ACIER = 7850.0, 210e9
TRAVAIL = os.path.join(elmer_outils.CALCULS, "couplage_lame_air")
RESULTATS = os.path.join(ICI, "resultats")

# --- La lame (Ewen, 05/10/2026) ---------------------------------------------------------------
LAME = dict(L=74.0, b=8.0, e=1.0)        # mm, lame nue
LEVEE_ANCHE = 1.0                        # mm, bout de la lame au-dessus de la plaquette au repos
JEU = 0.05                               # mm, jeu de chaque côté et au bout
TALON = 6.0                              # mm, talon rivé (creux rigide)
AMONT = 25.0                             # mm, profondeur d'air côté soufflet
F_VIDE_EB = 153.07                       # Hz, Euler-Bernoulli exact, 74 x 8 x 1 mm (validation 1)
BETA_L, SIGMA = 1.8751040687, 0.7340955137
FREQS = (140.0, 153.07, 170.0)

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
  Filename = "f.dat"
  Variable 1 = Pressure 1
  Operator 1 = boundary int
  Variable 2 = Pressure 2
  Operator 2 = boundary int
End
Boundary Condition 1
  Target Boundaries(1) = 1
End
Boundary Condition 2
  Target Boundaries(1) = 2
  Wave Impedance 1 = Real {c}
  Wave Impedance 2 = Real 0
End
{bandes}"""


def psi(xi):
    """Déformée du mode 1 d'une poutre encastrée-libre, 1 au bout (xi = x/L)."""
    b = BETA_L * np.asarray(xi, float)
    f = np.cosh(b) - np.cos(b) - SIGMA * (np.sinh(b) - np.sin(b))
    return f / 2.0                                   # la forme vaut 2 au bout


def masse_modale(L=LAME["L"], b=LAME["b"], e=LAME["e"]):
    """m_eff (kg) de la lame uniforme, déformée unité au bout : rho.b.e.L.int(psi²) = m/4."""
    xi = np.linspace(0, 1, 4001)
    return RHO_ACIER * b * e * L * 1e-9 * np.trapezoid(psi(xi) ** 2, xi)


# --- Géométrie --------------------------------------------------------------------------------
def geometrie(fichier, trou=(12.0, 12.0), levee=3.0, levee_anche=LEVEE_ANCHE, n_bandes=37, libre=False,
              h=4.0, h_lame=0.6, h_jeu=0.06, k_jeu=0.3, h_fin=1.0, h_dehors=6.0):
    """L'air autour de la lame (creux), maillé. Groupes : 1 parois, 2 rayonnement,
    3+2i dessous de la bande i (côté plaquette), 4+2i dessus (côté soufflet).
    `libre` : la lame seule (pas inclinée) au milieu d'un grand volume d'air."""
    import gmsh
    ch = elm.CHAMBRE
    Lb, bb, eb = LAME["L"], LAME["b"], LAME["e"]
    x0, zc = ch["L"] / 2, ch["H"] / 2
    pl = elm.PLAQUE
    xr = x0 - (Lb + JEU) / 2                          # pied de la lame = bout de la fente côté rivet
    y_pl = -pl                                        # dessus de la plaquette, côté soufflet
    theta = 0.0 if libre else math.asin(levee_anche / Lb)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    # la lame : N bandes + talon, posée sur la plaquette puis tournée autour de son pied
    creux = [occ.addBox(xr + i * Lb / n_bandes, y_pl - eb, zc - bb / 2, Lb / n_bandes, eb, bb) for i in range(n_bandes)]
    if not libre:
        occ.rotate([(3, t) for t in creux], xr, y_pl, 0, 0, 0, 1, -theta)
    creux.append(occ.addBox(xr - TALON, y_pl - eb, zc - bb / 2, TALON, eb, bb))
    if libre:
        R = 50.0
        boite = occ.addBox(xr - R, y_pl - eb / 2 - R, zc - R, Lb + 2 * R, 2 * R, 2 * R)
        air = occ.cut([(3, boite)], [(3, t) for t in creux])[0]
        ext = (xr - R, xr + Lb + R, y_pl - eb / 2 - R, y_pl - eb / 2 + R, zc - R, zc + R)
    else:
        a, b = trou
        corps = [occ.addBox(0, 0, 0, ch["L"], ch["l"], ch["H"])]
        corps.append(occ.addBox(xr, -pl, zc - (bb + 2 * JEU) / 2, Lb + JEU, pl + 0.5, bb + 2 * JEU))   # la fente
        y0 = ch["l"] / 2
        corps.append(occ.addBox(x0 - a / 2, y0 - b / 2, ch["H"] - 0.5, a, b, elm.TABLE + 0.5))         # le trou
        z_t = ch["H"] + elm.TABLE
        dx, dy, dz = elm.DEHORS
        dehors = occ.addBox(x0 - dx / 2, y0 - dy / 2, z_t, dx, dy, dz)
        sa, sb, se = elm.SOUPAPE
        soup = occ.addBox(x0 - sa / 2, y0 - sb / 2, z_t + levee, sa, sb, se)
        corps.append(occ.cut([(3, dehors)], [(3, soup)])[0][0][1])
        # le soufflet : sous la table (z <= H). Avant le 05/10/2026 au soir il montait à zc + 20 = 29,
        # au-dessus du dessus de table (23) : 8 610 mm³ communs avec le dehors, sans paroi, l'air
        # du soufflet passait au dehors sans traverser la fente (maquette ZW3D, J:\zw3d_travail\anche_calcul).
        amont = occ.addBox(xr - 12, y_pl - AMONT, zc - 20, Lb + 24, AMONT, ch["H"] - (zc - 20))
        corps.append(occ.cut([(3, amont)], [(3, t) for t in creux])[0][0][1])
        # fragment (pas fuse : fuse fond les faces des bandes en une seule)
        air = occ.fragment([(3, corps[0])], [(3, t) for t in corps[1:]])[0]
        ext = None
    occ.synchronize()
    vt = [t for d, t in air if d == 3]
    gmsh.model.addPhysicalGroup(3, vt, 1)
    bord = gmsh.model.getBoundary([(3, t) for t in vt], oriented=False, combined=True)
    c, s = math.cos(theta), math.sin(theta)
    tol = 1e-4
    parois, rayon, fines = [], [], []
    dessous, dessus = {}, {}
    for d, t in bord:
        t = abs(t)
        cx, cy, cz = occ.getCenterOfMass(2, t)
        # repère de la lame : u le long, v dans l'épaisseur (0 dessous, -e dessus)
        u = (cx - xr) * c - (cy - y_pl) * s
        v = (cx - xr) * s + (cy - y_pl) * c
        sur_lame = -tol <= u <= Lb + tol and abs(cz - zc) <= bb / 2 + tol
        if sur_lame and abs(v) < 1e-3:
            i = min(n_bandes - 1, int(u / (Lb / n_bandes)))
            dessous.setdefault(i, []).append(t)
            continue
        if sur_lame and abs(v + eb) < 1e-3:
            i = min(n_bandes - 1, int(u / (Lb / n_bandes)))
            dessus.setdefault(i, []).append(t)
            continue
        if libre:
            if (min(abs(cx - ext[0]), abs(cx - ext[1])) < tol or min(abs(cy - ext[2]), abs(cy - ext[3])) < tol
                    or min(abs(cz - ext[4]), abs(cz - ext[5])) < tol):
                rayon.append(t)
            else:
                parois.append(t)
            continue
        dx, dy, dz = elm.DEHORS
        y0 = ch["l"] / 2
        z_t = ch["H"] + elm.TABLE
        if (abs(cz - (z_t + dz)) < tol or abs(cx - (x0 - dx / 2)) < tol or abs(cx - (x0 + dx / 2)) < tol
                or abs(cy - (y0 - dy / 2)) < tol or abs(cy - (y0 + dy / 2)) < tol):
            rayon.append(t)                                          # le dehors
        elif (abs(cy - (y_pl - AMONT)) < tol or abs(cx - (xr - 12)) < tol or abs(cx - (xr + Lb + 12)) < tol
              or abs(cz - (zc - 20)) < tol):
            rayon.append(t)                                          # le soufflet (grand volume) ; son
            # dessus (z = H) est le dessous de la table : une paroi
        else:
            parois.append(t)
            if (abs(cz - (z_t + levee)) < tol or (abs(cz - z_t) < tol and abs(cx - x0) < elm.SOUPAPE[0]
                                                  and abs(cy - y0) < elm.SOUPAPE[1])
                    or (ch["H"] - 1e-6 <= cz <= z_t + 1e-6 and abs(cx - x0) <= trou[0] and abs(cy - y0) <= trou[1])):
                fines.append(t)
    if len(dessous) != n_bandes or len(dessus) != n_bandes:
        raise RuntimeError(f"bandes de la lame mal repérées : {len(dessous)} dessous, {len(dessus)} dessus")
    gmsh.model.addPhysicalGroup(2, parois, 1)
    gmsh.model.addPhysicalGroup(2, rayon, 2)
    aires = {}
    for i in range(n_bandes):
        gmsh.model.addPhysicalGroup(2, dessous[i], 3 + 2 * i)     # numéros suivis : ElmerGrid
        gmsh.model.addPhysicalGroup(2, dessus[i], 4 + 2 * i)      # renumérote sinon (-autoclean)
        aires[i] = (sum(occ.getMass(2, t) for t in dessous[i]), sum(occ.getMass(2, t) for t in dessus[i]))
    # tailles : fin le long des jeux (bords de la lame et de la fente), plus fin près du pied
    fd = gmsh.model.mesh.field
    lames = [t for faces in list(dessous.values()) + list(dessus.values()) for t in faces]
    f_lame = fd.add("Distance")
    fd.setNumbers(f_lame, "SurfacesList", lames)
    champs = []
    f_tl = fd.add("MathEval")
    if libre:
        fd.setString(f_tl, "F", f"Min({h_dehors}, {h_lame} + 0.25*F{f_lame})")
    else:
        bords = []
        for d, t in gmsh.model.getEntities(1):
            xa, ya, za, xb, yb, zb = gmsh.model.getBoundingBox(1, t)
            if (yb >= y_pl - eb - levee_anche - 0.1 and ya <= y_pl + 0.1 and xb - xa > 1.0
                    and min(abs(za - (zc - bb / 2)), abs(za - (zc + bb / 2)), abs(za - (zc - bb / 2 - JEU)),
                            abs(za - (zc + bb / 2 + JEU))) < 0.2):
                bords.append(t)
        f_b = fd.add("Distance")
        fd.setNumbers(f_b, "CurvesList", bords)
        fd.setNumber(f_b, "Sampling", 400)
        pente = levee_anche / Lb
        fd.setString(f_tl, "F", f"Min({h}, Min({h_lame} + 0.25*F{f_lame}, "
                                f"Max({h_jeu}, {k_jeu}*({JEU} + {pente}*(x - {xr}))) + 0.3*F{f_b}))")
        f_d = fd.add("Distance")
        fd.setNumbers(f_d, "SurfacesList", fines)
        f_s = fd.add("Threshold")
        fd.setNumber(f_s, "InField", f_d)
        fd.setNumber(f_s, "SizeMin", min(h_fin, levee))
        fd.setNumber(f_s, "SizeMax", h)
        fd.setNumber(f_s, "DistMin", 0.5)
        fd.setNumber(f_s, "DistMax", 3.0)
        champs.append(f_s)
    champs.append(f_tl)
    f_min = fd.add("Min")
    fd.setNumbers(f_min, "FieldsList", champs)
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
    xc = (np.arange(n_bandes) + 0.5) / n_bandes
    return dict(noeuds=n, n_bandes=n_bandes, xi=xc, aires_mm2=aires, theta_deg=math.degrees(theta))


# --- Elmer --------------------------------------------------------------------------------------
def sif_bandes(n_bandes, xi):
    """Flux imposé : g = i.omega.rho.v_entrant. Avec g = +psi dessous, -psi dessus, la lame
    avance vers la plaquette (dans la fente) à la vitesse V = 1/(i.omega.rho) au bout."""
    out = []
    k = 3
    for i in range(n_bandes):
        p = float(psi(xi[i]))
        for grp, signe in ((3 + 2 * i, 1.0), (4 + 2 * i, -1.0)):
            out.append(f"Boundary Condition {k}\n  Target Boundaries(1) = {grp}\n"
                       f"  Wave Flux 1 = Real {signe * p:.8e}\n  Wave Flux 2 = Real 0\n  Save Scalars = True\nEnd\n")
            k += 1
    return "".join(out)


def lancer(dossier, g, freqs, solveur="iteratif"):
    table = "\n".join(f"      {i + 1} {f:.6f}" for i, f in enumerate(freqs))
    texte = SIF.format(n=len(freqs), table=table, c=C_SON, rho=RHO, solveur=elm.SOLVEURS[solveur],
                       bandes=sif_bandes(g["n_bandes"], g["xi"]))
    with open(os.path.join(dossier, "f.sif"), "w", encoding="utf-8") as fh:
        fh.write(texte)
    dat = os.path.join(dossier, "f.dat")
    if os.path.exists(dat):
        os.remove(dat)
    elmer_outils.elmersolver(dossier, "f.sif")
    d = np.loadtxt(dat, ndmin=2)
    noms = open(dat + ".names", encoding="utf-8", errors="replace").read()
    return d, noms


def force_modale(d, noms, g):
    """Q = somme des psi_i.(-P_dessous_i + P_dessus_i) (force modale de l'air vers la fente),
    par fréquence. Les colonnes sont lues dans f.dat.names (« ... over bc k »)."""
    import re
    cols, var = {}, None
    for m in re.finditer(r"^\s*(\d+):\s*boundary int:\s*(pressure\s*(\d))?\s*over bc\s*(\d+)", noms, re.M | re.I):
        var = int(m.group(3)) if m.group(3) else var          # nom vide = même variable
        cols[(int(m.group(4)), var)] = int(m.group(1)) - 1
    if not cols:
        raise RuntimeError("colonnes introuvables dans f.dat.names :\n" + noms[:2000])
    Q = np.zeros(d.shape[0], complex)
    for i in range(g["n_bandes"]):
        p = psi(g["xi"][i])
        for k, signe in ((3 + 2 * i, -1.0), (4 + 2 * i, 1.0)):
            P = d[:, cols[(k, 1)]] + 1j * d[:, cols[(k, 2)]]
            Q += signe * p * P
    return Q


def mode_couple(freqs, Zm, f_vide=F_VIDE_EB, m_eff=None):
    """m_a(f) = Im(Z_m)/omega, R_a = Re(Z_m) ; fréquence du mode couplé par point fixe."""
    m_eff = m_eff or masse_modale()
    w = 2 * np.pi * np.asarray(freqs)
    m_a = Zm.imag / w
    R_a = Zm.real
    f = f_vide
    for _ in range(20):
        ma = float(np.interp(f, freqs, m_a))
        f = f_vide / math.sqrt(1 + ma / m_eff)
    ra = float(np.interp(f, freqs, R_a))
    zeta = ra / (2 * (m_eff + ma) * 2 * math.pi * f)
    return dict(f_couple_Hz=f, ecart_cents=1200 * math.log2(f / f_vide), m_a_g=ma * 1e3,
                m_a_sur_m=ma / m_eff, R_a_kg_s=ra, zeta_air=zeta, m_eff_g=m_eff * 1e3)


def calculer(nom, freqs=FREQS, solveur="iteratif", **kw):
    dossier = os.path.join(TRAVAIL, nom)
    os.makedirs(dossier, exist_ok=True)
    t0 = time.time()
    g = geometrie(os.path.join(dossier, "air.msh"), **kw)
    elmer_outils.elmergrid(dossier, "air.msh")
    t_m = time.time() - t0
    d, noms = lancer(dossier, g, freqs, solveur)
    Q = force_modale(d, noms, g)
    w = 2 * np.pi * np.asarray(freqs)
    Zm = -1j * w * RHO * Q                       # Z_m = -Q/V avec V = 1/(i.omega.rho)
    res = dict(cas=nom, noeuds=g["noeuds"], theta_deg=g["theta_deg"], duree_maillage_s=t_m,
               duree_s=time.time() - t0)
    res.update({f"m_a_g_{f:g}Hz": float(z.imag / wi * 1e3) for f, z, wi in zip(freqs, Zm, w)})
    res.update({f"R_a_{f:g}Hz": float(z.real) for f, z in zip(freqs, Zm)})
    res.update(mode_couple(np.asarray(freqs), Zm))
    return res


def relire(nom, n_bandes=37, freqs=FREQS):
    """Relit f.dat d'un calcul (même interrompu : les fréquences déjà faites)."""
    dossier = os.path.join(TRAVAIL, nom)
    d = np.loadtxt(os.path.join(dossier, "f.dat"), ndmin=2)
    noms = open(os.path.join(dossier, "f.dat.names"), encoding="utf-8", errors="replace").read()
    g = dict(n_bandes=n_bandes, xi=(np.arange(n_bandes) + 0.5) / n_bandes)
    Q = force_modale(d, noms, g)
    f = np.asarray(freqs[:len(Q)], float)
    w = 2 * np.pi * f
    Zm = -1j * w * RHO * Q
    res = dict(cas=nom, n_freqs=len(f))
    res.update({f"m_a_g_{fi:g}Hz": float(z.imag / wi * 1e3) for fi, z, wi in zip(f, Zm, w)})
    if len(f) == 1:                  # une seule fréquence : m_a et R_a tenues constantes autour
        m_a, R_a = Zm[0].imag / w[0], Zm[0].real
        f = np.array([50.0, 500.0])
        Zm = R_a + 1j * 2 * np.pi * f * m_a
    res.update(mode_couple(f, Zm))
    return res


def theorie_bande(L=LAME["L"], b=LAME["b"], e=LAME["e"]):
    """Masse ajoutée d'une bande infiniment longue, non visqueuse (Lamb ; Sader 1998, Gamma = 1) :
    pi.rho.b²/4 par mètre, pondérée par psi² comme la masse de la lame."""
    m_a = math.pi * RHO * (b * 1e-3) ** 2 / 4 * L * 1e-3 * 0.25
    m = masse_modale(L, b, e)
    return dict(m_a_g=m_a * 1e3, m_a_sur_m=m_a / m, ecart_cents=1200 * math.log2(1 / math.sqrt(1 + m_a / m)))


def ecrire(res, nom="couplage_lame_air.csv"):
    os.makedirs(RESULTATS, exist_ok=True)
    cles = []
    for r in res:
        for k in r:
            if k not in cles:
                cles.append(k)
    with open(os.path.join(RESULTATS, nom), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        for r in res:
            w.writerow({k: (f"{v:.5g}" if isinstance(v, float) else v) for k, v in r.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--libre", action="store_true")
    ap.add_argument("--trou")
    ap.add_argument("--levee", type=float, default=3.0)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--convergence", action="store_true")
    ap.add_argument("--solveur", default="iteratif", choices=list(elm.SOLVEURS))
    ap.add_argument("--relire", nargs="+", help="relire des calculs faits : nom:trou:levee:levee_anche")
    a = ap.parse_args()
    res = []
    if a.relire:
        for item in a.relire:
            nom, trou, lev, lan = (item.split(":") + ["", "", ""])[:4]
            r = relire(nom)
            if nom == "libre":
                r.update({f"theorie_bande_{k}": v for k, v in theorie_bande().items()})
            else:
                r.update(trou=trou, levee_soupape_mm=float(lev), levee_anche_mm=float(lan or LEVEE_ANCHE))
            res.append(r)
            print(r)
        ecrire(res)
        return
    if a.libre or a.plan:
        r = calculer("libre", libre=True, solveur=a.solveur)
        r.update({f"theorie_bande_{k}": v for k, v in theorie_bande().items()})
        res.append(r)
        print(r, flush=True)
        ecrire(res)
    cas = []
    if a.trou:
        cas = [(a.trou, a.levee, {})]
    if a.plan:
        cas = [(t, 3.0, {}) for t in elm.TROUS] + [("12x12", l, {}) for l in (1.0, 6.0)] + \
              [("12x12", 3.0, dict(levee_anche=0.5)), ("12x12", 3.0, dict(levee_anche=1.5))]
    if a.convergence:
        cas = [("12x12", 3.0, dict(h_jeu=0.1, k_jeu=0.5, h_lame=1.0, h=5.0)), ("12x12", 3.0, {}),
               ("12x12", 3.0, dict(h_jeu=0.04, k_jeu=0.2, h_lame=0.4, h=3.0))]
    for i, (t, l, kw) in enumerate(cas):
        nom = f"{t}_lev{l:g}" + "".join(f"_{k}{v:g}" for k, v in kw.items())
        r = calculer(nom, trou=elm.TROUS[t], levee=l, solveur=a.solveur, **kw)
        r.update(trou=t, levee_soupape_mm=l, levee_anche_mm=kw.get("levee_anche", LEVEE_ANCHE))
        res.append(r)
        print(r, flush=True)
        ecrire(res, "couplage_lame_air_convergence.csv" if a.convergence else "couplage_lame_air.csv")


if __name__ == "__main__":
    main()
