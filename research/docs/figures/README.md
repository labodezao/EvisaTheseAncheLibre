# Figures des documents de `research/docs/`

Dossier de sortie des figures référencées par les documents voisins. Les images
ne sont pas produites ici : elles sont **générées par les scripts**, puis
versionnées une fois qu'elles sont bonnes.

| Figure | Produite par | Référencée dans |
|---|---|---|
| `osso_centroide.png` | `python3 ../../scripts/analyse_osso.py --figures` | `../analyse_acoustique_osso.md` §3.6 |
| `elmer_maillage_languette.png` | `fem/figures_these.py` (depuis `research/fem/`) | `../design_theory.lyx`, Finite element model |
| `pince_modes_synthese.png` | `fem/figures_these.py` | `../design_theory.lyx`, Experimental model updating |
| `mecanique_compensations_{fr,en}.png`, `mecanique_tiroir_{fr,en}.png` | `python ../../scripts/figures_mecanique.py` | `../design_practical.lyx` et `_fr`, partie Left-hand mechanism |
| `pratique_levee_{fr,en}.png`, `pratique_joint_{fr,en}.png`, `pratique_soufflet_{fr,en}.png` | `python ../../scripts/figures_pratique.py` (calculs de `outils_atelier.py`) | `../design_practical.lyx` et `_fr` : clavier, fuites, soufflet |

Pour l'étude OSSO, la génération suppose que tu disposes légalement des deux
enregistrements (non versionnés — voir l'en-tête du script) :

```bash
cd research
python3 scripts/analyse_osso.py --data ~/audio/osso --figures
```

Sans argument, `--figures` écrit dans ce dossier ; on peut lui passer un autre
chemin (`--figures /tmp/fig`).
