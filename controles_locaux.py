#!/usr/bin/env python3
"""Contrôles locaux : équivalent du job `test` de .github/workflows/pages.yml.

Lancer : J:\claude\venv\Scripts\python.exe controles_locaux.py
Sortie 0 seulement si tout est vert. Résumé Markdown à la fin.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent
NODE_ATTENDU = 22  # version du workflow (node-version: 22)


def lancer(cmd):
    return subprocess.run(cmd, cwd=RACINE).returncode


def main():
    lignes = []
    ok = True
    node = shutil.which("node")
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not node or not npm:
        print("node ou npm introuvable", file=sys.stderr)
        return 1
    version = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
    majeure = int(version.lstrip("v").split(".")[0])
    note = "" if majeure == NODE_ATTENDU else f" (le workflow utilisait Node {NODE_ATTENDU} : version différente)"
    if note:
        print("ATTENTION" + note, file=sys.stderr)
    lignes.append(("Version de Node " + version + note, "ok" if majeure == NODE_ATTENDU else "différente", 0.0))

    debut = time.time()
    code = lancer([npm, "test"])
    duree = time.time() - debut
    lignes.append(("npm test (tests de précision du moteur DSP)", "vert" if code == 0 else "ROUGE", duree))
    ok = code == 0

    print("\n| Étape | Statut | Durée |\n|---|---|---|")
    for nom, statut, d in lignes:
        print(f"| {nom} | {statut} | {d:.1f} s |")
    print("\nTout est vert." if ok else "\nContrôles rouges.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
