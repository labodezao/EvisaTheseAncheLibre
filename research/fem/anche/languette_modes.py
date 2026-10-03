"""Modes propres d'une languette d'anche par éléments finis 3D (Gmsh + Elmer).

Ce que fait ce script, en mots
------------------------------
1. Il lit la languette dans la banque d'anches (`anches_r12.yaml`, produit par
   `banque_anches.py` depuis le CSV d'Ewen) : tronçons de l'encastrement au bout,
   largeur et épaisseur au début et à la fin de chaque tronçon, matériau, masse au
   bout, position du rivet. C'est la MÊME description que le modèle semi-analytique
   (`banc_recherche/languette.py`) : une seule source de vérité.
2. Il construit le solide avec Gmsh (un volume par tronçon, face du dessous plane,
   le grattage est dessus) et le maille en hexaèdres du second ordre (20 nœuds),
   structurés : plusieurs éléments dans la largeur et dans l'épaisseur.
3. Il lance ElmerSolver (élasticité linéaire, `StressSolver`, valeurs propres) :
   fréquences et déformées des premiers modes, et le TYPE de chaque mode
   (flexion, torsion, flexion dans le plan).
4. Il en tire les paramètres du modèle semi-analytique pour le mode 1 : masse,
   raideur et projection modales (déformée normalisée à 1 au bout).

L'encastrement
--------------
- `rivet` (défaut) : le talon, du rivet au pied de la fente, est maillé ; il est
  appuyé sur la plaque (déplacement vertical nul sous le talon) et tenu en tout
  point sous la tête du rivet (une bande de 2 mm). C'est le montage réel, en
  linéaire : on suppose que le talon ne décolle pas de la plaque.
- `pied` : encastrement parfait au pied de la fente (la poutre des livres).
L'écart entre les deux dit combien la souplesse de la fixation pèse.

Hypothèses : acier élastique linéaire isotrope (E, rho, nu de `MATERIAUX`, ou
ceux de chaque tronçon) ; petits déplacements ; pas d'air (les modes « dans le
vide ») ; la masse au bout est collée à la languette (pas de jeu).

Usage
-----
  J:\\claude\\venv\\Scripts\\python.exe languette_modes.py --verif        les vérifications (poutre, anche de matrix.txt)
  ... --anches                                       toutes les anches de anches_r12.yaml
  ... --anches --ids R12-grave                       une seule
  ... --convergence                                  finesse du maillage
Sorties : `resultats/*.csv` et `resultats/modal_<id>.json` (ici) ; maillages et
journaux d'Elmer dans `J:\\claude\\calculs\\languette\\` (hors du Drive).
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
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))   # research/
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..")))         # research/fem
import elmer_outils  # noqa: E402
from banc_recherche.languette import (Languette, euler_bernoulli, materiau,  # noqa: E402
                                      parametres_modaux, rayleigh_ritz)

TRAVAIL = os.path.join(elmer_outils.CALCULS, "languette")
RESULTATS = os.path.join(ICI, "resultats")


# --- La géométrie, en tronçons (mm) ---------------------------------------------------------
def segments(lang: Languette, encastrement="rivet", rivet_mm=3.0, r_rivet_mm=1.0, l_masse_mm=2.0):
    """Liste des volumes à mailler, en mm : dict(x0, x1, b0, b1, t0, t1, z0 (bas), mat, role).

    Les masses ponctuelles de `lang.masses` deviennent des blocs de laiton posés sur
    le dessus, sur toute la largeur, longs de `l_masse_mm` (centrés sur leur position,
    rentrés si besoin) : les tronçons sont coupés à leurs bords pour garder un
    maillage structuré.
    """
    tr = []
    x = 0.0
    for t in lang.troncons:
        tr.append(dict(x0=x * 1e3, x1=(x + t.longueur) * 1e3, b0=t.largeur[0] * 1e3, b1=t.largeur[1] * 1e3,
                       t0=t.epaisseur[0] * 1e3, t1=t.epaisseur[1] * 1e3, z0=0.0,
                       mat=(t.E, t.rho, t.nu), role="languette"))
        x += t.longueur
    L = x * 1e3
    blocs = []
    for xm, m in lang.masses:
        a = min(max(xm * 1e3 - l_masse_mm / 2, 0.0), L - l_masse_mm)
        blocs.append((a, a + l_masse_mm, m))
    # coupe des tronçons aux bords des blocs
    for a, c, _ in blocs:
        for cut in (a, c):
            nouv = []
            for s in tr:
                if s["x0"] + 1e-9 < cut < s["x1"] - 1e-9:
                    u = (cut - s["x0"]) / (s["x1"] - s["x0"])
                    bc = s["b0"] + u * (s["b1"] - s["b0"]); tc = s["t0"] + u * (s["t1"] - s["t0"])
                    nouv.append(dict(s, x1=cut, b1=bc, t1=tc))
                    nouv.append(dict(s, x0=cut, b0=bc, t0=tc))
                else:
                    nouv.append(s)
            tr = nouv
    vols = list(tr)
    lt = materiau("laiton")
    for a, c, m in blocs:
        for s in tr:
            if s["x0"] >= a - 1e-9 and s["x1"] <= c + 1e-9:
                aire = 0.5 * (s["b0"] + s["b1"]) * (c - a) * 1e-6                # m2
                h = m / (lt["rho"] * aire) * 1e3                                  # mm
                vols.append(dict(x0=s["x0"], x1=s["x1"], b0=s["b0"], b1=s["b1"], t0=h, t1=h,
                                 z0=None, zb=(s["t0"], s["t1"]), mat=(lt["E"], lt["rho"], lt["nu"]),
                                 role="masse"))
    if encastrement == "rivet":
        p = tr[0]
        bande = (-(rivet_mm + r_rivet_mm), -(rivet_mm - r_rivet_mm))
        if bande[1] >= -0.2:
            raise ValueError("rivet trop près du pied de la fente (rivet_mm > r_rivet_mm + 0,2)")
        bornes = [bande[0] - 1.0, bande[0], bande[1], 0.0]
        for k in range(3):
            vols.append(dict(x0=bornes[k], x1=bornes[k + 1], b0=p["b0"], b1=p["b0"], t0=p["t0"], t1=p["t0"],
                             z0=0.0, mat=p["mat"], role="rivet" if k == 1 else "talon"))
    return vols


def _rect(occ, x, b, z0, z1):
    p = [occ.addPoint(x, -b / 2, z0), occ.addPoint(x, b / 2, z0), occ.addPoint(x, b / 2, z1),
         occ.addPoint(x, -b / 2, z1)]
    return occ.addWire([occ.addLine(p[i], p[(i + 1) % 4]) for i in range(4)])


def mailler(vols, fichier, hx=0.5, ny=7, nz=3, nzb=3, encastrement="rivet"):
    """Gmsh : un volume réglé par tronçon, fragmentés ensemble, maillage structuré en
    hexaèdres du second ordre. Renvoie la table des corps (matériaux) et le nombre de nœuds."""
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("languette")
    occ = gmsh.model.occ
    tags = []
    for v in vols:
        if v["role"] == "masse":
            (za0, za1) = v["zb"]
            w0, w1 = _rect(occ, v["x0"], v["b0"], za0, za0 + v["t0"]), _rect(occ, v["x1"], v["b1"], za1, za1 + v["t1"])
        else:
            w0, w1 = _rect(occ, v["x0"], v["b0"], 0.0, v["t0"]), _rect(occ, v["x1"], v["b1"], 0.0, v["t1"])
        out = occ.addThruSections([w0, w1], makeSolid=True, makeRuled=True)
        tags.append([t for d, t in out if d == 3][0])
    occ.synchronize()
    if len(tags) > 1:
        _, carte = occ.fragment([(3, t) for t in tags], [])
        occ.synchronize()
        nouveaux = [[t for d, t in m if d == 3] for m in carte[:len(tags)]]
    else:
        nouveaux = [tags]
    for d, c in gmsh.model.getEntities(1):
        xa, ya, za, xb, yb, zb = gmsh.model.getBoundingBox(1, c)
        dx, dy, dz = xb - xa, yb - ya, zb - za
        if dx > 1e-4:          # seules les arêtes « le long » changent de x (les autres sont dans x = cte)
            n = max(2, int(round(dx / hx)) + 1)
        elif dy >= dz:
            n = ny
        else:
            n = nz
        gmsh.model.mesh.setTransfiniteCurve(c, n)
    # arêtes verticales des blocs de masse : nzb nœuds
    for v, nv in zip(vols, nouveaux):
        if v["role"] == "masse":
            for t in nv:
                for d, c in gmsh.model.getBoundary([(3, t)], combined=False, recursive=True):
                    if d == 1:
                        xa, ya, za, xb, yb, zb = gmsh.model.getBoundingBox(1, abs(c))
                        if zb - za > max(xb - xa, yb - ya):
                            gmsh.model.mesh.setTransfiniteCurve(abs(c), nzb)
    for d, s in gmsh.model.getEntities(2):
        gmsh.model.mesh.setTransfiniteSurface(s)
        gmsh.model.mesh.setRecombine(2, s)
    for d, t in gmsh.model.getEntities(3):
        gmsh.model.mesh.setTransfiniteVolume(t)
    # corps : un par matériau
    corps = {}
    for v, nv in zip(vols, nouveaux):
        corps.setdefault(v["mat"], []).extend(nv)
    table = []
    for i, (mat, ts) in enumerate(corps.items(), start=1):
        gmsh.model.addPhysicalGroup(3, sorted(set(ts)), i)
        table.append(dict(corps=i, E=mat[0], rho=mat[1], nu=mat[2]))
    # frontières : 1 = tenu en tout point, 2 = appui vertical (talon sur la plaque)
    role_x = [(v["x0"], v["x1"], v["role"]) for v in vols if v["role"] in ("rivet", "talon")]
    bord = gmsh.model.getBoundary([(3, t) for d, t in gmsh.model.getEntities(3)], oriented=False, combined=True)
    tenu, appui = [], []
    tol = 1e-4                                            # mm (les boîtes d'OpenCASCADE ont du jeu)
    for d, s in bord:
        xa, ya, za, xb, yb, zb = gmsh.model.getBoundingBox(2, abs(s))
        if encastrement == "pied":
            if xb < tol and xa > -tol:
                tenu.append(abs(s))
        elif zb < tol:                                    # face du dessous
            xm = 0.5 * (xa + xb)
            for x0, x1, role in role_x:
                if x0 - tol <= xm <= x1 + tol:
                    (tenu if role == "rivet" else appui).append(abs(s))
    if not tenu:
        raise RuntimeError("aucune face d'encastrement trouvée")
    gmsh.model.addPhysicalGroup(2, tenu, 1)
    if appui:
        gmsh.model.addPhysicalGroup(2, appui, 2)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.SecondOrderIncomplete", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(3)
    n_noeuds = len(gmsh.model.mesh.getNodes()[0])
    gmsh.write(fichier)
    gmsh.finalize()
    return table, n_noeuds, bool(appui)


SIF_TETE = """Header
  Mesh DB "." "maillage"
End
Simulation
  Coordinate System = Cartesian 3D
  Coordinate Scaling = 0.001
  Simulation Type = Steady state
  Steady State Max Iterations = 1
  Output Intervals = 1
End
Equation 1
  Active Solvers(2) = 1 2
End
Solver 1
  Equation = "Linear elasticity"
  Procedure = "StressSolve" "StressSolver"
  Variable = -dofs 3 Displacement
  Eigen Analysis = True
  Eigen System Values = {n}
  Eigen System Select = Smallest Magnitude
  Linear System Solver = Direct
  Linear System Direct Method = Umfpack
End
Solver 2
  Exec Solver = After All
  Equation = "Sortie"
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = modes
  Output Format = vtu
  Ascii Output = True
End
Boundary Condition 1
  Target Boundaries(1) = 1
  Displacement 1 = Real 0
  Displacement 2 = Real 0
  Displacement 3 = Real 0
End
"""


def sif(table, n_modes, appui):
    s = SIF_TETE.format(n=n_modes)
    for c in table:
        s += (f"Body {c['corps']}\n  Equation = 1\n  Material = {c['corps']}\nEnd\n"
              f"Material {c['corps']}\n  Youngs Modulus = Real {c['E']:.6g}\n"
              f"  Poisson Ratio = Real {c['nu']:.4g}\n  Density = Real {c['rho']:.6g}\nEnd\n")
    if appui:
        s += "Boundary Condition 2\n  Target Boundaries(1) = 2\n  Displacement 3 = Real 0\nEnd\n"
    return s


# --- Lecture des déformées ------------------------------------------------------------------
def _tableau(texte, nom):
    m = re.search(r'<DataArray[^>]*Name="' + re.escape(nom) + r'"[^>]*>(.*?)</DataArray>', texte, re.S)
    return np.array(m.group(1).split(), float) if m else None


def lire_vtu(chemin):
    """(points en mm, liste des déplacements modaux (n, 3)) d'un .vtu texte d'Elmer."""
    t = open(chemin, encoding="utf-8", errors="replace").read()
    m = re.search(r"<Points>\s*<DataArray[^>]*>(.*?)</DataArray>", t, re.S)
    # Elmer écrit les coordonnées après « Coordinate Scaling = 0.001 », donc en mètres :
    # retour en mm (erreur corrigée le 03/10/2026 : les déformées étaient lues 1000 fois
    # trop petites, la forme modale valait 1 partout).
    pts = np.array(m.group(1).split(), float).reshape(-1, 3) * 1e3
    modes = []
    k = 1
    while True:
        a = _tableau(t, f"displacement EigenMode{k}")
        if a is None:
            break
        modes.append(a.reshape(-1, 3))
        k += 1
    return pts, modes


def decrire_mode(pts, U, L_mm):
    """Type du mode et profil de flexion a(x) (déplacement vertical moyen dans la largeur).

    flexion : u_z le même d'un bord à l'autre ; torsion : u_z change de signe avec y ;
    flexion dans le plan : u_y domine. Rang de flexion = nombre de nœuds de a(x) + 1."""
    x, y = pts[:, 0], pts[:, 1]
    uz, uy = U[:, 2], U[:, 1]
    libre = x > 1e-6
    e_tot = np.sum(U[libre] ** 2) + 1e-300
    part_y = np.sum(uy[libre] ** 2) / e_tot
    xs = np.round(x[libre], 4)
    cles, inv = np.unique(xs, return_inverse=True)
    a = np.bincount(inv, uz[libre]) / np.bincount(inv)
    # partie de u_z qui change de signe avec y (torsion)
    pente = np.bincount(inv, uz[libre] * y[libre]) / np.maximum(np.bincount(inv, y[libre] ** 2), 1e-30)
    e_flex = np.sum(a[inv] ** 2)
    e_tor = np.sum((pente[inv] * y[libre]) ** 2)
    if part_y > 0.5:
        genre = "flexion dans le plan"
    elif e_tor > e_flex:
        genre = "torsion"
    else:
        genre = "flexion"
    s = np.sign(a[np.abs(a) > 1e-3 * np.max(np.abs(a))])
    rang = int(np.sum(s[1:] != s[:-1])) + 1 if s.size else 0
    return genre, rang, cles, a


def modes_elmer(lang: Languette, nom, n_modes=6, encastrement="rivet", rivet_mm=3.0,
                hx=0.5, ny=7, nz=3, nzb=3):
    """Calcul complet pour une languette. Renvoie un dict : fréquences, types, profils,
    paramètres modaux du mode 1 (flexion)."""
    dossier = os.path.join(TRAVAIL, re.sub(r"[^\w.-]+", "_", nom))
    os.makedirs(dossier, exist_ok=True)
    t0 = time.time()
    lang = lang.adoucie()                 # marches -> rampes de 0,2 mm (maillage structuré)
    vols = segments(lang, encastrement=encastrement, rivet_mm=rivet_mm)
    table, n_noeuds, appui = mailler(vols, os.path.join(dossier, "languette.msh"), hx=hx, ny=ny, nz=nz,
                                     nzb=nzb, encastrement=encastrement)
    elmer_outils.elmergrid(dossier, "languette.msh")
    open(os.path.join(dossier, "modes.sif"), "w", encoding="utf-8").write(sif(table, n_modes, appui))
    log = elmer_outils.elmersolver(dossier, "modes.sif")
    lam = [l.real for l in elmer_outils.valeurs_propres(log)][:n_modes]
    f = [math.sqrt(abs(l)) / (2 * math.pi) for l in lam]
    vtu = os.path.join(dossier, "maillage", "modes_t0001.vtu")
    pts, U = lire_vtu(vtu)
    L_mm = lang.L * 1e3
    modes = []
    for k, (fk, Uk) in enumerate(zip(f, U), start=1):
        genre, rang, xs, a = decrire_mode(pts, Uk, L_mm)
        modes.append(dict(mode=k, f_Hz=fk, type=genre, rang_flexion=rang if genre == "flexion" else None,
                          x_mm=xs, profil=a))
    flex = [m for m in modes if m["type"] == "flexion"]
    p = None
    if flex:
        m1 = flex[0]
        xs, a = m1["x_mm"], m1["profil"]
        a = a / np.interp(L_mm, xs, a)
        p = parametres_modaux(lang, f_hz=m1["f_Hz"], forme=lambda x: np.interp(np.asarray(x) * 1e3, xs, a),
                              source=f"elmer {elmer_outils.version()}")
    return dict(nom=nom, frequences=f, modes=modes, parametres=p, noeuds=n_noeuds,
                duree_s=time.time() - t0, encastrement=encastrement, dossier=dossier)


def description(lang: Languette):
    """La languette en données simples (pour la clé du cache)."""
    return dict(troncons=[(t.longueur, t.largeur, t.epaisseur, t.E, t.rho, t.nu) for t in lang.troncons],
                masses=list(lang.masses))


def modes_elmer_cache(lang: Languette, nom, **kw):
    """`modes_elmer` avec cache (fem/cache.py) : un dict sérialisable.
    f_Hz, types, flexion (liste de {f_Hz, x_mm, profil normalisé au bout}),
    mode1 (paramètres modaux), noeuds, elmer."""
    import cache

    def calcul():
        r = modes_elmer(lang, nom, **kw)
        flex = [m for m in r["modes"] if m["type"] == "flexion"]
        p = r["parametres"]
        return dict(f_Hz=r["frequences"], types=[m["type"] for m in r["modes"]],
                    flexion=[dict(f_Hz=m["f_Hz"], x_mm=np.asarray(m["x_mm"]).tolist(),
                                  profil=(np.asarray(m["profil"]) / np.interp(lang.L * 1e3, m["x_mm"], m["profil"])).tolist())
                             for m in flex],
                    mode1=None if p is None else dict(f_hz=p.f_hz, m_eff=p.m_eff, k_eff=p.k_eff, gamma=p.gamma,
                                                      phi_moyen=p.phi_moyen),
                    noeuds=r["noeuds"], duree_s=r["duree_s"], elmer=elmer_outils.version())
    entrees = dict(languette=description(lang), options=kw, elmer=elmer_outils.version())
    return cache.en_cache("languette", entrees, calcul)


# --- Les vérifications ----------------------------------------------------------------------
def trois_methodes(lang, nom, n_modes=5, encastrement="pied", **kw):
    """Euler-Bernoulli exact, Rayleigh-Ritz (km.py, base de n_modes et de 20), Elmer : flexion.
    Les trois sur la même géométrie (marches adoucies en rampes de 0,2 mm, comme le
    maillage) ; `EB_marches_Hz` : Euler-Bernoulli sur les marches franches, pour voir
    ce que l'adoucissement change."""
    eb_marches = euler_bernoulli(lang, n_modes)
    lang = lang.adoucie()
    eb = euler_bernoulli(lang, n_modes)
    rr_km2 = rayleigh_ritz(lang, 2, n_base=2)[0]
    rr5 = rayleigh_ritz(lang, n_modes, n_base=n_modes)[0]
    rr20 = rayleigh_ritz(lang, n_modes, n_base=20)[0]
    fe = modes_elmer(lang, nom, n_modes=n_modes + 4, encastrement=encastrement, **kw)
    flex = [m for m in fe["modes"] if m["type"] == "flexion"]
    lignes = []
    for i in range(n_modes):
        f_fe = flex[i]["f_Hz"] if i < len(flex) else float("nan")
        lignes.append(dict(cas=nom, mode_flexion=i + 1,
                           EB_marches_Hz=round(eb_marches[i], 2) if i < len(eb_marches) else "",
                           EB_exact_Hz=round(eb[i], 2) if i < len(eb) else "",
                           RR_km2_Hz=round(rr_km2[i], 2) if i < 2 else "",
                           RR_5_Hz=round(rr5[i], 2), RR_20_Hz=round(rr20[i], 2),
                           Elmer_Hz=round(f_fe, 2),
                           ecart_Elmer_EB_pct=round(100 * (f_fe / eb[i] - 1), 2) if i < len(eb) else "",
                           ecart_RR5_EB_pct=round(100 * (rr5[i] / eb[i] - 1), 2) if i < len(eb) else ""))
    autres = [(m["mode"], round(m["f_Hz"], 1), m["type"]) for m in fe["modes"] if m["type"] != "flexion"]
    return lignes, fe, autres


def ecrire_csv(lignes, nom):
    os.makedirs(RESULTATS, exist_ok=True)
    cles = []
    for l in lignes:
        cles += [k for k in l if k not in cles]
    chemin = os.path.join(RESULTATS, nom)
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print("->", chemin, flush=True)
    return chemin


def ecrire_modal(res, id_anche):
    """Paramètres du mode 1 et déformées, pour le recalage et le modèle semi-analytique."""
    os.makedirs(RESULTATS, exist_ok=True)
    p = res["parametres"]
    d = dict(id=id_anche, elmer=elmer_outils.version(), encastrement=res["encastrement"],
             frequences_Hz=[round(f, 3) for f in res["frequences"]],
             types=[m["type"] for m in res["modes"]],
             mode1=None if p is None else dict(f_Hz=p.f_hz, m_eff_kg=p.m_eff, k_eff_N_m=p.k_eff,
                                               gamma_m2=p.gamma, phi_moyen=p.phi_moyen),
             noeuds=res["noeuds"])
    chemin = os.path.join(RESULTATS, f"modal_{re.sub(r'[^\w.-]+', '_', id_anche)}.json")
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    return chemin


def verif():
    """Poutre uniforme (formule), puis l'anche de matrix.txt (3 méthodes), puis le rivet."""
    from banc_recherche import material
    lignes = []
    U = Languette.uniforme(30e-3, 3.5e-3, 0.3e-3)
    l, fe, autres = trois_methodes(U, "poutre_uniforme_30x3.5x0.3")
    for i, li in enumerate(l):
        li["formule_Hz"] = round(material.resonance_frequency(2.1e11, 30e-3, 0.3e-3, 7800, i + 1), 2) if i < 4 else ""
    lignes += l
    print("poutre uniforme : autres modes", autres, flush=True)
    R = Languette.depuis_matrice(os.path.join(ICI, "..", "..", "reedgui", "matrix.txt"), nom="matrix.txt")
    l, fe, autres = trois_methodes(R, "matrix_txt_pied")
    lignes += l
    print("matrix.txt : autres modes", autres, flush=True)
    for li in lignes:
        print(li, flush=True)
    ecrire_csv(lignes, "verification_languette.csv")
    # encastrement au rivet, et finesse du maillage
    r = modes_elmer(R, "matrix_txt_rivet", n_modes=6, encastrement="rivet", rivet_mm=3.0)
    print("matrix.txt, encastrement au rivet (3 mm) :",
          [(round(m["f_Hz"], 2), m["type"]) for m in r["modes"]], flush=True)


def convergence():
    R = Languette.depuis_matrice(os.path.join(ICI, "..", "..", "reedgui", "matrix.txt"), nom="matrix.txt")
    lignes = []
    for hx, ny, nz in ((1.0, 5, 2), (0.5, 7, 3), (0.25, 9, 4)):
        r = modes_elmer(R, f"conv_{hx}_{ny}_{nz}", n_modes=6, encastrement="pied", hx=hx, ny=ny, nz=nz)
        flex = [m["f_Hz"] for m in r["modes"] if m["type"] == "flexion"]
        lignes.append(dict(hx_mm=hx, ny=ny, nz=nz, noeuds=r["noeuds"], f1_Hz=round(flex[0], 3),
                           f2_Hz=round(flex[1], 3), f3_Hz=round(flex[2], 3) if len(flex) > 2 else "",
                           duree_s=round(r["duree_s"], 1)))
        print(lignes[-1], flush=True)
    ecrire_csv(lignes, "convergence_languette.csv")


def anches(chemin_yaml, ids=None, n_modes=6):
    from banc_recherche.banque_anches import charger_yaml
    lignes = []
    for a in charger_yaml(chemin_yaml):
        if ids and a.id not in ids:
            continue
        r = modes_elmer(a.languette(), a.id, n_modes=n_modes, encastrement="rivet",
                        rivet_mm=a.valeur("rivet_mm"))
        print(a.id, [(round(m["f_Hz"], 1), m["type"]) for m in r["modes"]], flush=True)
        print("  ->", ecrire_modal(r, a.id), flush=True)
        eb = euler_bernoulli(a.languette(), 3)
        d = dict(id=a.id, note=a.valeur("note"), L_mm=round(a.languette().L * 1e3, 2),
                 f1_EB_Hz=round(eb[0], 2), f1_Elmer_Hz=round(r["parametres"].f_hz, 2) if r["parametres"] else "",
                 noeuds=r["noeuds"], duree_s=round(r["duree_s"], 1))
        for m in r["modes"]:
            d[f"mode{m['mode']}"] = f"{m['f_Hz']:.1f} Hz {m['type']}"
        lignes.append(d)
    ecrire_csv(lignes, "modes_languettes.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verif", action="store_true")
    ap.add_argument("--convergence", action="store_true")
    ap.add_argument("--anches", action="store_true")
    ap.add_argument("--yaml", default=os.path.join(ICI, "anches_r12.yaml"))
    ap.add_argument("--ids", nargs="*")
    a = ap.parse_args()
    print("Elmer", elmer_outils.version(), "dans", elmer_outils.elmer_home(), flush=True)
    if a.verif:
        verif()
    if a.convergence:
        convergence()
    if a.anches:
        anches(a.yaml, a.ids)


if __name__ == "__main__":
    main()
