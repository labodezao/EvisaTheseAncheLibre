# Figures des documents de `research/docs/`

Dossier de sortie des figures référencées par les documents voisins. Les images
ne sont pas produites ici : elles sont **générées par les scripts**, puis
versionnées une fois qu'elles sont bonnes.

| Figure | Produite par | Référencée dans |
|---|---|---|
| `osso_centroide.png` | `python3 ../../scripts/analyse_osso.py --figures` | `../analyse_acoustique_osso.md` §3.6 |

Pour l'étude OSSO, la génération suppose que tu disposes légalement des deux
enregistrements (non versionnés — voir l'en-tête du script) :

```bash
cd research
python3 scripts/analyse_osso.py --data ~/audio/osso --figures
```

Sans argument, `--figures` écrit dans ce dossier ; on peut lui passer un autre
chemin (`--figures /tmp/fig`).
