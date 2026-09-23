# Perces d'Ewen — fichiers TUTT `.dat`

Les perces réelles d'Ewen, récupérées de son Google Drive, versées ici avec
son accord explicite (« oui tout dans le dépôt, mets tout »). Ce sont ses
propres instruments, ses propres cotes, son propre travail de facteur — à
la différence des sources TUTT (`../tutt/`), qui sont celles de B.B.
« Ninob » et restent créditées comme telles.

## `bombarde_ewen_daviau/`

- `bombarde_sol_finale.dat` — la version aboutie, 22 tronçons, 438 mm,
  8 trous, 29 doigtés. C'est le fichier utilisé dans
  `research/docs/modele_hybride_generalise.md` §10 pour la première
  confrontation d'une vraie perce au modèle : les naturelles du premier
  registre tiennent dans 16 cents, les fourches restent hautes de 50 à
  60 cents (chantier ouvert).
- `bombarde_en_sol.dat` — une version antérieure de la même bombarde,
  quasi identique (la comparaison des deux montre l'évolution de la perce
  au cours de l'affinage).
- `tronc_de_cone.dat` — un fichier d'essai minimal, un seul tronçon
  conique, pour tester le solveur isolément.

## `clarinette_folk_ewen_daviau/`

- `clarifolk.dat` — 17 tronçons, 456 mm, 27 doigtés.
- `clarifolk_sol_intrpol.dat` — une variante interpolée par TuttEdit
  (`factdiaA=1.111`, `faclongA=0.891` dans l'en-tête du fichier) : c'est
  l'exemple concret de ce que fait l'« interpolation » de TuttEdit, une
  question posée et restée ouverte jusqu'à ce que ce fichier y réponde.
- `clarifolk_retouche_moule.dat` — une retouche de la précédente, cotes de
  moule ajustées.

## Les utiliser

```
banc-recherche-cli justesse research/scripts/legacy/perces/bombarde_ewen_daviau/bombarde_sol_finale.dat
```

ou en Python :

```python
from banc_recherche import tutt
dat = tutt.read_dat('research/scripts/legacy/perces/bombarde_ewen_daviau/bombarde_sol_finale.dat')
table = tutt.justesse(dat)
```
