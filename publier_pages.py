#!/usr/bin/env python3
"""Publie le contenu de web/ (+ .nojekyll) à la racine de la branche gh-pages.

Remplace le job `deploy` de .github/workflows/pages.yml (Actions coupé le 12/11/2026).
  --essai : commit local créé et contenu listé, rien poussé.
  sans option : pousse gh-pages (à ne lancer qu'au clic d'Ewen).
Aucun changement de l'arbre de travail : index temporaire + git commit-tree.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent
BRANCHE = "gh-pages"
COMMANDE_PAGES = ('gh api -X PUT repos/labodezao/EvisaTheseAncheLibre/pages -f build_type=legacy '
                  '-f "source[branch]=gh-pages" -f "source[path]=/"')


def git(*args, env=None, check=True):
    r = subprocess.run(["git", *args], cwd=RACINE, capture_output=True, text=True, env=env)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)} : {r.stderr.strip()}")
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    essai = ap.parse_args().essai

    if subprocess.run([sys.executable, str(RACINE / "controles_locaux.py")]).returncode:
        sys.exit("Contrôles rouges : abandon.")

    git("fetch", "origin", check=False)
    parent = git("rev-parse", "--verify", "-q", f"refs/remotes/origin/{BRANCHE}", check=False)

    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"),
                   GIT_WORK_TREE=str(RACINE / "web"))
        git("add", "-A", "-f", ".", env=env)
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=RACINE,
                              input="", capture_output=True, text=True).stdout.strip()
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},.nojekyll", env=env)
        arbre = git("write-tree", env=env)

    if parent and git("rev-parse", f"{parent}^{{tree}}") == arbre:
        print("Rien à publier : gh-pages est déjà à jour.")
        return 0
    base = git("rev-parse", "HEAD")[:7]
    cmd = ["commit-tree", arbre, "-m", f"Publication de web/ (source {base})"]
    if parent:
        cmd += ["-p", parent]
    commit = git(*cmd)
    git("update-ref", f"refs/heads/{BRANCHE}", commit)

    fichiers = git("ls-tree", "-r", "-l", commit).splitlines()
    taille = sum(int(l.split()[3]) for l in fichiers)
    print(f"\nCommit {commit[:10]} sur {BRANCHE} : {len(fichiers)} fichiers, {taille / 1024:.0f} Ko")
    for l in fichiers:
        print("  " + l.split("\t")[1])

    if essai:
        print("\nEssai : rien poussé.")
    else:
        git("push", "origin", f"{BRANCHE}:{BRANCHE}")
        print("\nPoussé sur origin/gh-pages.")
    print("\nRéglage Pages (pour Ewen, à lancer une seule fois) :\n  " + COMMANDE_PAGES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
