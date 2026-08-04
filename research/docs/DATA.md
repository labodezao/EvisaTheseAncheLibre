# Données & fichiers Drive — manifeste

Ce qui vit **dans le dépôt** vs. ce qui reste **sur le Google Drive**, et
pourquoi. Objectif : « tout est traçable », sans casser le dépôt avec des
binaires de plusieurs Go.

## Dans le dépôt (versionné)

- **Code** : firmware ESP32 (`firmware/`), accordeur web (`web/`), banc de
  recherche (`research/banc_recherche/`).
- **Sources d'origine** vendorisées : `research/scripts/legacy/` (`MesAnche.py`,
  `Mesures.py`, `mes_seuil_autoentretien.py`, `Data_analysis.py` [extrait
  PraatCalcs], `step.py`, `valvecontrol.py`).
- **Manuscrits LyX** : `research/docs/design_theory.lyx`,
  `research/docs/design_practical.lyx`.

## Sur le Drive (NON versionné) — et pourquoi

GitHub **refuse tout fichier > 100 Mo** et le dépôt n'est pas fait pour des
binaires lourds. Les fichiers ci-dessous restent donc sur le Drive ; on les
récupère à la demande (ou via **Git LFS** si on décide de les suivre).

### Campagnes de mesures (`.npy`, très lourds)

| Fichier | Taille | fileId |
|---|---|---|
| `d_Mesures_Press_Acoustique.npy` | **2,3 Go** | `1tl1cWoqDNVmL39bipoW8gR2cUvjlcisD` |
| `d_Mesures_Press_Acoustique.npy` (autre run) | 384 Mo | `1N9pq7VCqR8xsgRjIIIPAi0V2TP9kaCEU` |
| `d_Mesures_Accelerations.npy` | 384 Mo | `1RItdh8omwwb8LZRlVZ4GyutdEryEfnvh` |
| `d_Mesures_Press.npy` | 4,9 Mo | `1tlYFXKNBi8rKhgue-_YkOFgoPa37YkMe` |
| `d_Mesures_Debit.npy` | 4,9 Mo | `1ti5ACegNi2MNd0u4tmIUGFyLlTtZGJSy` |
| `d_MesuresTemperature.npy` | 4,9 Mo | `1tkAew8BjyK5BxKAmL7kvASFM6KM53IB1` |
| `d_Mesures_Press_Pos.npy` | 64 Ko | `1thUsphbq5sV4ssQy-BbIyjNPJ7Ku7rW8` |

→ relire avec `banc_recherche.campaigns.load_npy` (mmap, ne charge pas les 2 Go
en RAM). L'onglet **Campagnes** de la GUI ouvre plutôt les HDF5.

### Mécanique / CAO (SolidWorks, STL, 3MF, LightBurn)

`banc soufflet.SLDPRT`, `banc mesure soufflet/` (dossier), `SOUFFLET.SLDPRT`,
`SOUFFLET 1voix.SLDPRT`, `pince soufflet.SLDPRT` + `pince soufflet accordage/`,
`th24 essais plans exp anche basse.SLDPRT`, `cadre soufflet*.SLDPRT`,
`CadreSOufflet210320.3mf`, `soup basse accord air.STL/.3mf`,
`cadre soufflet.lbrn2`, `soufflet-*.png`. → binaires, gardés sur Drive.

### Documents / données tabulaires

- `paramètres d'anche du quatuor de cromornes + expériences sur les anches
  lestées v5.xls` — `1NPHDHS8znffCvt1OGA-XIxk4kr3fkP-v`
- PDFs de référence : `Fly_-_Anche_doubles.pdf`, `Soufflet S Barbe.pdf`,
  `Ref_10 Enveloppe Soleau Polyphonium.pdf`, etc.

### Autres scripts d'origine (sur Drive, portés dans `banc_recherche`)

| Fichier | fileId | Porté dans |
|---|---|---|
| `ValControl.py` | `1Kny_SBrjxNTdCn6hoAO73UwsXhd1I2hl` | `bench_link` |
| `valvecontrol_init.py` | `1KonTFnoUDFrZKeaWOF-1AtvI6Qp3szDi` | `bench_link` |
| `enveloppepraat.py` | `1fJVZfy98XzRimtYnByC-NWdlahzYC1Vx` | `analysis` |
| `enveloppe.py` | `1N7iN6WaTSEfhQJpZgmTbDazpYzvuiy5b` | `analysis` |
| `enveloppe_frac.py` | `1N3Lb88copxcapw5iIR-702lLPRYg7jYf` | `analysis` |
| `plotsmeasure.py` | `1MlrlpaUPSEksoMP4Ticzpd7Dsn0vg8VZ` | `gui` (pyqtgraph) |
| `Data_analysis.py` (complet) | `1R5-170W11_EZN0qpik_ILX93DteTyr8Q` | `analysis` + `impedance` |

## Récupérer un fichier

Les fichiers Drive `text/x-python` ne se lisent pas en clair (le lecteur ne
gère pas ce type) : les télécharger en **base64** puis décoder. Pour les gros
`.npy`, préférer un téléchargement direct hors dépôt et pointer
`banc_recherche.config` dessus.

## Suivre les binaires quand même ? → Git LFS

Si on veut versionner CAO/PDF (pas les 2 Go), initialiser Git LFS :

```bash
git lfs install
git lfs track "*.SLDPRT" "*.STL" "*.3mf" "*.pdf"
git add .gitattributes
```

Les `.npy` de plusieurs centaines de Mo à 2 Go restent hors LFS (quotas) :
Drive reste la source.
