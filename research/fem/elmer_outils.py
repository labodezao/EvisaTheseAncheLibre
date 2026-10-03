"""Lancer Elmer depuis les scripts de `research/fem/` : un seul endroit pour le chemin.

Quel Elmer : la variable `ELMER_HOME` (système, 26.2 depuis le 03/10/2026), puis
`ELMER_DOSSIER`, puis Elmer 26.2 à son chemin par défaut (9.0 en dernier secours).
Une variable qui pointe vers un dossier sans ElmerSolver.exe est ignorée. Le PATH
de Windows n'est pas utilisé : on donne toujours le chemin complet.

Les calculs (maillages, journaux, résultats bruts) vont sous `J:\\claude\\calculs\\`
(variable `CALCULS`), jamais sur C:.
"""
from __future__ import annotations

import math
import os
import re
import subprocess

CANDIDATS = [
    r"C:\Program Files\Elmer 26.2-Release",
    r"C:\Program Files\Elmer 9.0-Release",
]
CALCULS = os.environ.get("CALCULS", r"J:\claude\calculs")


def elmer_home():
    """Dossier d'Elmer : ELMER_HOME, ELMER_DOSSIER, sinon 26.2, sinon 9.0."""
    for var in ("ELMER_HOME", "ELMER_DOSSIER"):
        env = os.environ.get(var)
        if env and os.path.isfile(os.path.join(env, "bin", "ElmerSolver.exe")):
            return env
    for c in CANDIDATS:
        if os.path.isfile(os.path.join(c, "bin", "ElmerSolver.exe")):
            return c
    raise FileNotFoundError("Elmer introuvable : installer Elmer ou définir ELMER_DOSSIER")


def disponible():
    try:
        elmer_home()
        return True
    except FileNotFoundError:
        return False


def _env(home):
    return dict(os.environ, ELMER_HOME=home,
                PATH=os.path.join(home, "bin") + os.pathsep + os.environ.get("PATH", ""))


def version(home=None):
    home = home or elmer_home()
    r = subprocess.run([os.path.join(home, "bin", "ElmerSolver.exe"), "-v"], capture_output=True,
                       text=True, errors="replace", env=_env(home))
    m = re.search(r"\(v\s*([\d.]+)\)|Version:\s*(\S+)", r.stdout + r.stderr)
    return (m.group(1) or m.group(2)) if m else "?"


def elmergrid(dossier, msh, sortie="maillage", home=None):
    """Gmsh (.msh 2.2) -> maillage Elmer (dossier `sortie`)."""
    home = home or elmer_home()
    subprocess.run([os.path.join(home, "bin", "ElmerGrid.exe"), "14", "2", msh, "-autoclean",
                    "-out", sortie], cwd=dossier, env=_env(home), capture_output=True, check=True)


def elmersolver(dossier, sif, home=None):
    """Lance ElmerSolver ; journal dans `elmer.log` ; renvoie la sortie texte."""
    home = home or elmer_home()
    r = subprocess.run([os.path.join(home, "bin", "ElmerSolver.exe"), sif], cwd=dossier,
                       env=_env(home), capture_output=True, text=True, errors="replace")
    log = r.stdout + r.stderr
    with open(os.path.join(dossier, "elmer.log"), "w", encoding="utf-8") as fh:
        fh.write(log)
    if "ALL DONE" not in log:
        raise RuntimeError(f"ElmerSolver n'a pas fini (voir {os.path.join(dossier, 'elmer.log')})")
    return log


def valeurs_propres(log):
    """Valeurs propres lues dans le journal (lignes « EigenSolve: i: lambda »)."""
    return [complex(float(m.group(1)), float(m.group(2) or 0.0))
            for m in re.finditer(r"EigenSolve:\s+\d+:\s+([-\d.E+]+)(?:\s+([-\d.E+]+))?", log)]


def frequences(log):
    """Fréquences propres (Hz) triées, depuis les valeurs propres omega^2."""
    return sorted(math.sqrt(abs(l.real)) / (2 * math.pi) for l in valeurs_propres(log))
