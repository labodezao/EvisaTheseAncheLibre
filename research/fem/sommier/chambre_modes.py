"""Modes acoustiques d'une chambre du sommier générique d'Ewen (Gmsh + Elmer).

Ce que fait ce script, en mots
------------------------------
1. Il lit les cotes du sommier générique (R12) dans le générateur ZW3D
   `J:\\claude\\business-os\\outils\\zw3d\\sommier.py` (TABLE_R12, PILOTES, NB_BASSES) :
   une seule source pour les cotes, pas de copie à tenir à jour.
2. Il construit l'air d'UNE chambre k : la case A et la case B (chacune en deux
   moitiés, la cloison centrale change de côté au milieu de la chambre, comme
   dans `sommier.py`), et le trou de la table d'harmonie posé dessus (le « col »).
3. Il maille avec Gmsh (tétraèdres du second ordre) et lance ElmerSolver
   (WaveSolver, analyse aux valeurs propres) : les fréquences propres de l'air.
4. Il compare avec la formule de Helmholtz (masse d'air du trou + ressort d'air
   de la chambre) et en déduit la longueur effective du trou vue par l'air.

Hypothèses (à garder en tête en lisant les résultats)
-----------------------------------------------------
- Parois rigides, plaques d'anche comprises ; fentes des anches fermées (anche au
  repos). Air à 20 °C, c = 343 m/s.
- Le bout du trou débouche sur un grand volume à pression nulle (soupape grande
  ouverte) ; la correction d'extrémité extérieure est ajoutée en longueur de trou
  (`corr_ext`, défaut 0,85 x rayon équivalent, bord bafflé). La soupape proche du
  trou l'allonge : c'est un paramètre à balayer.
- Pentes du dessus (3°) et du fond (5,16°) non reprises : le fond de chaque case
  est plat à HauteurSommier - LonCase. Le script signale les cases que la pente
  du fond entamerait.
- Les dimensions du trou de table (défaut 8 x 25 mm, table 8 mm) sont celles du
  modèle à constantes localisées `banc_recherche/coupled_reeds.py` : DEVINÉES,
  à remplacer par les cotes d'Ewen.

Validation (03/10/2026) : boîte rigide 50 x 15 x 10 mm, Elmer donne 3430,0 Hz
(c/2L = 3430 Hz) ; bout ouvert : 1715,0 / 5145,0 / 8575,0 Hz (c/4L, 3c/4L, 5c/4L).

Usage
-----
  J:\\claude\\venv\\Scripts\\python.exe chambre_modes.py                 toutes les chambres du R12
  ... --chambres 1 6 12                                         quelques chambres
  ... --trou 8 25 --table 8 --corr 0.85                          trou hx (le long du sommier) x hy, en mm
  ... --balayage                                                 petit plan : section et épaisseur du trou
Sorties : `resultats/*.csv` (ici) ; maillages et journaux Elmer dans TRAVAIL (sur J:).
"""
from __future__ import annotations

import argparse
import ast
import csv
import math
import os
import re
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
SOMMIER_PY = r"J:\claude\business-os\outils\zw3d\sommier.py"
ELMER = os.environ.get("ELMER_HOME", r"C:\Program Files\Elmer 9.0-Release")
TRAVAIL = os.environ.get("CHAMBRE_TRAVAIL", r"J:\claude\calculs\chambre_sommier")
C_SON = 343.0      # m/s, air à 20 °C


# --- Les cotes, lues dans le générateur ZW3D -------------------------------------------------
def cotes_sommier(chemin=SOMMIER_PY):
    """PILOTES, TABLE_R12, NB_BASSES, CONSTANTES lus (sans l'exécuter) dans sommier.py."""
    arbre = ast.parse(open(chemin, encoding="utf-8").read())
    v = {}
    for n in arbre.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            nom = n.targets[0].id
            if nom in ("PILOTES", "TABLE_R12", "NB_BASSES", "CONSTANTES"):
                v[nom] = ast.literal_eval(n.value)
    return v


class Chambre:
    """L'air de la chambre k (1 à n), mêmes équations que `sommier.py` (volume_modele)."""

    def __init__(self, k, cotes=None, trou=(8.0, 25.0), table=8.0, corr_ext=0.85):
        c = cotes or cotes_sommier()
        p, t, self.nb_basses = c["PILOTES"], c["TABLE_R12"], c["NB_BASSES"]
        self.k = k
        self.H, self.PasCav = p["HauteurSommier"], p["PasCav"]
        self.D, self.Lar, self.e = p["DemiLarSuppAnche"], p["LarSommier"], p["EpParoi"]
        self.Pas = self.PasCav + 2 * self.D
        retrait = self.Lar / 300
        demi_cloison = (self.e + self.e / 15) / 2
        prof = t["ProfCase"][k - 1]
        self.b = (self.Lar * 2 / 3) / 2 - retrait * (k - 1) if k <= self.nb_basses else prof + demi_cloison
        self.t = self.Lar / 2 - retrait * (k - 1)
        self.c0 = self.b - prof
        self.demi_cloison = demi_cloison
        self.fa = self.H - t["LonCaseA"][k - 1]
        self.fb = self.H - t["LonCaseB"][k - 1]
        self.x0 = (k - 1) * self.Pas + self.D          # début de la chambre le long du sommier
        self.trou = trou
        self.table = table
        self.a_eq = math.sqrt(trou[0] * trou[1] / math.pi)
        self.corr_ext = corr_ext * self.a_eq           # mm
        self.angle_fond = c["CONSTANTES"]["AngleFond"]
        self.x_pente = self.nb_basses * self.Pas + self.D

    def a1(self, z):
        return self.c0 + (self.demi_cloison - self.c0) * z / self.H

    def w(self, z):
        return self.b + (self.t - self.b) * z / self.H

    def demi_cases(self):
        """[(nom, x_debut, x_fin, z_fond, y_int(z), y_ext(z))], x local (0 = début de chambre)."""
        P, e = self.PasCav, self.e
        return [
            ("A1", 0.0, P / 2 + e / 2, self.fa, lambda z: self.a1(z), lambda z: self.w(z)),
            ("A2", P / 2 + e / 2, P, self.fa, lambda z: e - self.a1(z), lambda z: self.w(z)),
            ("B1", 0.0, P / 2 - e / 2, self.fb, lambda z: self.a1(z) - e, lambda z: -self.w(z)),
            ("B2", P / 2 - e / 2, P, self.fb, lambda z: -self.a1(z), lambda z: -self.w(z)),
        ]

    def pente_entame(self):
        """Hauteur (mm) dont la pente du fond du R12 entamerait le fond de la case A et B
        (0 si elle ne les touche pas). Le calcul, lui, garde un fond plat."""
        x_fin = self.x0 + self.PasCav
        z_pente = max(0.0, (x_fin - self.x_pente) * math.tan(math.radians(self.angle_fond)))
        return max(0.0, z_pente - self.fa), max(0.0, z_pente - self.fb)


# --- Géométrie et maillage (Gmsh, OpenCASCADE) ------------------------------------------------
def mailler(ch: Chambre, fichier_msh, h=1.2):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(f"chambre{ch.k}")
    occ = gmsh.model.occ
    vols, volumes_cases = [], {}
    for nom, xa, xb, zf, yi, ye in ch.demi_cases():
        pts = [(yi(zf), zf), (ye(zf), zf), (ye(ch.H), ch.H), (yi(ch.H), ch.H)]
        tags = [occ.addPoint(xa, y, z) for y, z in pts]
        lignes = [occ.addLine(tags[i], tags[(i + 1) % 4]) for i in range(4)]
        surf = occ.addPlaneSurface([occ.addCurveLoop(lignes)])
        ext = occ.extrude([(2, surf)], xb - xa, 0, 0)
        v = [t for d, t in ext if d == 3][0]
        vols.append((3, v))
        occ.synchronize()
        volumes_cases[nom] = occ.getMass(3, v)
    hx, hy = ch.trou
    L_col = ch.table + ch.corr_ext
    col = occ.addBox(ch.PasCav / 2 - hx / 2, -hy / 2, ch.H, hx, hy, L_col)
    occ.synchronize()
    fus, _ = occ.fuse(vols, [(3, col)])
    occ.synchronize()
    occ.removeAllDuplicates()
    occ.synchronize()
    vtags = [t for d, t in gmsh.model.getEntities(3)]
    volume_total = sum(occ.getMass(3, t) for t in vtags)
    gmsh.model.addPhysicalGroup(3, vtags, 1)
    bord = gmsh.model.getBoundary([(3, t) for t in vtags], oriented=False, combined=True)
    sortie, parois = [], []
    for d, t in bord:
        x, y, z = occ.getCenterOfMass(d, abs(t))
        (sortie if abs(z - (ch.H + L_col)) < 1e-6 else parois).append(abs(t))
    gmsh.model.addPhysicalGroup(2, parois, 1)
    gmsh.model.addPhysicalGroup(2, sortie, 2)
    gmsh.option.setNumber("Mesh.MeshSizeMax", h)
    gmsh.option.setNumber("Mesh.MeshSizeMin", h / 4)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3)
    n_noeuds = len(gmsh.model.mesh.getNodes()[0])
    gmsh.write(fichier_msh)
    gmsh.finalize()
    v_a = volumes_cases["A1"] + volumes_cases["A2"]
    v_b = volumes_cases["B1"] + volumes_cases["B2"]
    return dict(V_A_mm3=v_a, V_B_mm3=v_b, V_total_mm3=volume_total, noeuds=n_noeuds)


SIF = """Header
  Mesh DB "." "maillage"
End
Simulation
  Coordinate System = Cartesian 3D
  Coordinate Scaling = 0.001
  Simulation Type = Steady state
  Steady State Max Iterations = 1
  Output Intervals = 0
End
Body 1
  Equation = 1
  Material = 1
End
Material 1
  Sound Speed = Real {c}
End
Equation 1
  Active Solvers(1) = 1
End
Solver 1
  Equation = Wave
  Procedure = "WaveSolver" "WaveSolver"
  Variable = p
  Eigen Analysis = True
  Eigen System Values = {n}
  Eigen System Select = Smallest Magnitude
  Linear System Solver = Direct
  Linear System Direct Method = Umfpack
End
Boundary Condition 1
  Target Boundaries(1) = 1
End
Boundary Condition 2
  Target Boundaries(1) = 2
  p = Real 0.0
End
"""


def elmer(dossier, n_modes=4, c=C_SON):
    """ElmerGrid puis ElmerSolver dans `dossier` ; renvoie les fréquences propres (Hz)."""
    exe = lambda nom: os.path.join(ELMER, "bin", nom)
    env = dict(os.environ, ELMER_HOME=ELMER)
    subprocess.run([exe("ElmerGrid.exe"), "14", "2", "chambre.msh", "-autoclean", "-out", "maillage"],
                   cwd=dossier, env=env, capture_output=True, check=True)
    open(os.path.join(dossier, "modes.sif"), "w", encoding="utf-8").write(SIF.format(c=c, n=n_modes))
    r = subprocess.run([exe("ElmerSolver.exe"), "modes.sif"], cwd=dossier, env=env,
                       capture_output=True, text=True, errors="replace")
    open(os.path.join(dossier, "elmer.log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    lam = [float(m.group(1)) for m in re.finditer(r"EigenSolve:\s+\d+:\s+([-\d.E+]+)", r.stdout)]
    if not lam:
        raise RuntimeError(f"Elmer n'a rendu aucune valeur propre (voir {dossier}\\elmer.log)")
    return sorted(math.sqrt(abs(x)) / (2 * math.pi) for x in lam)


def helmholtz(ch: Chambre, V_mm3, corr_int=0.85):
    """Fréquence de Helmholtz (Hz) à constantes localisées : f = c/2pi sqrt(S/(V L_eff)),
    L_eff = épaisseur de table + correction intérieure + correction extérieure."""
    S = ch.trou[0] * ch.trou[1] * 1e-6
    L = (ch.table + corr_int * ch.a_eq) * 1e-3 + ch.corr_ext * 1e-3
    return C_SON / (2 * math.pi) * math.sqrt(S / (V_mm3 * 1e-9 * L))


def l_eff_fem(ch: Chambre, V_mm3, f1):
    """Longueur effective du trou (mm) qui redonne la fréquence Elmer avec la formule de
    Helmholtz : c'est la masse d'air du trou « vue par l'air », corrections comprises."""
    S = ch.trou[0] * ch.trou[1] * 1e-6
    w = 2 * math.pi * f1 / C_SON
    return S / (V_mm3 * 1e-9 * w * w) * 1e3


def note(f):
    """Nom de note (notation française, la3 = 440 Hz) et écart en cents."""
    noms = ["do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#", "la", "la#", "si"]
    m = 69 + 12 * math.log2(f / 440.0)
    n = round(m)
    return f"{noms[n % 12]}{n // 12 - 2}", 100 * (m - n)


def calculer(k, cotes, trou, table, corr, h, n_modes=4, etiquette=""):
    ch = Chambre(k, cotes, trou=trou, table=table, corr_ext=corr)
    dossier = os.path.join(TRAVAIL, f"ch{k:02d}{etiquette}")
    os.makedirs(dossier, exist_ok=True)
    t0 = time.time()
    g = mailler(ch, os.path.join(dossier, "chambre.msh"), h=h)
    f = elmer(dossier, n_modes)
    V_ch = g["V_A_mm3"] + g["V_B_mm3"]            # air des cases seules (sans l'air du trou)
    fH = helmholtz(ch, V_ch)
    nm, ct = note(f[0])
    ea, eb = ch.pente_entame()
    return dict(chambre=k, trou_hx_mm=trou[0], trou_hy_mm=trou[1], S_mm2=trou[0] * trou[1],
                table_mm=table, corr_ext=corr, LonCaseA=round(ch.H - ch.fa, 3),
                LonCaseB=round(ch.H - ch.fb, 3),
                V_A_cm3=round(g["V_A_mm3"] / 1000, 3), V_B_cm3=round(g["V_B_mm3"] / 1000, 3),
                V_cases_cm3=round(V_ch / 1000, 3), V_total_cm3=round(g["V_total_mm3"] / 1000, 3),
                noeuds=g["noeuds"],
                f1_Hz=round(f[0], 1), f2_Hz=round(f[1], 1), f3_Hz=round(f[2], 1),
                f4_Hz=round(f[3], 1) if len(f) > 3 else "",
                note_f1=f"{nm} {ct:+.0f} c", f_helmholtz_Hz=round(fH, 1),
                ecart_helmholtz_pct=round(100 * (fH / f[0] - 1), 1),
                L_eff_fem_mm=round(l_eff_fem(ch, V_ch, f[0]), 2),
                pente_entame_A_mm=round(ea, 2), pente_entame_B_mm=round(eb, 2),
                duree_s=round(time.time() - t0, 1))


def ecrire(lignes, nom):
    os.makedirs(os.path.join(ICI, "resultats"), exist_ok=True)
    chemin = os.path.join(ICI, "resultats", nom)
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lignes[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    return chemin


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chambres", type=int, nargs="*", default=None)
    ap.add_argument("--trou", type=float, nargs=2, default=(8.0, 25.0), metavar=("HX", "HY"))
    ap.add_argument("--table", type=float, default=8.0)
    ap.add_argument("--corr", type=float, default=0.85, help="correction extérieure / rayon équivalent")
    ap.add_argument("--h", type=float, default=2.0, help="taille de maille (mm) ; 2 mm : f1 à 0,1 %% près de 0,8 mm")
    ap.add_argument("--balayage", action="store_true", help="plan 3 x 2 x 2 : section, table, correction")
    a = ap.parse_args()
    cotes = cotes_sommier()
    n = len(cotes["TABLE_R12"]["ProfCase"])
    ks = a.chambres or list(range(1, n + 1))
    lignes = []
    if not a.balayage:
        for k in ks:
            r = calculer(k, cotes, tuple(a.trou), a.table, a.corr, a.h)
            lignes.append(r)
            print(f"chambre {k:2d}  V = {r['V_cases_cm3']:6.2f} cm3  f1 = {r['f1_Hz']:7.1f} Hz ({r['note_f1']})"
                  f"  f2 = {r['f2_Hz']:7.1f}  Helmholtz {r['f_helmholtz_Hz']:7.1f} ({r['ecart_helmholtz_pct']:+.1f} %)"
                  f"  {r['noeuds']} noeuds, {r['duree_s']} s", flush=True)
        print("->", ecrire(lignes, "modes_chambres_R12.csv"))
    else:
        for k in ks:
            for hx, hy in ((4.0, 12.5), (8.0, 25.0), (8.0, 12.5)):
                for table in (4.0, 8.0):
                    for corr in (0.6, 1.6):
                        et = f"_s{hx * hy:.0f}_t{table:.0f}_c{corr}"
                        r = calculer(k, cotes, (hx, hy), table, corr, a.h, etiquette=et)
                        lignes.append(r)
                        print(f"chambre {k:2d}  S = {hx * hy:5.0f} mm2  table {table:3.0f}  corr {corr}"
                              f"  f1 = {r['f1_Hz']:7.1f} Hz  Helmholtz {r['f_helmholtz_Hz']:7.1f}", flush=True)
        print("->", ecrire(lignes, "balayage_trou.csv"))


if __name__ == "__main__":
    main()
