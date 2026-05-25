# EvisaTheseAncheLibre

Base de travail pour reprendre la rédaction de thèse sur le **jet flow** et l’**acoustique des anches libres**.

## Structure actuelle

- `these/main.tex` : fichier principal LaTeX
- `these/chapitres/` : chapitres de rédaction
- `these/biblio/references.bib` : base bibliographique initiale

## Lancer une compilation locale

Depuis la racine du dépôt :

```bash
cd these
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Priorités de travail

1. Consolider l’état de l’art (jet flow + interaction anche/colonne d’air)
2. Finaliser le plan d’expérience (facteurs, niveaux, mesures, répétitions)
3. Structurer les campagnes expérimentales et la traçabilité des résultats
