# Anciens scripts (référence)

Scripts d'origine de la chaîne PC + Pyboard, **pour référence** pendant le
portage vers `banc_recherche/`. Ils ne sont **pas exécutés** par le nouveau
package. La correspondance ancien → nouveau est décrite dans `../../README.md`.

## Présents ici (récupérés du Google Drive)

| Fichier | Rôle | Porté dans |
|---|---|---|
| `MesAnche.py` | firmware Pyboard : actionneurs + capteurs, `Mes_Full_Mes` (≤150 Hz), `Move_to_Pos`, `Set_Press` (DAC turbine) | `firmware/` (soufflet) + `banc_recherche.bench_link` |
| `Mesures.py` | orchestration DOE PC (rshell) : grille 8×8×8 Section×Pression×Clapet ×2 sens, HDF5, shutdown/restore, `record()` pyaudio | `banc_recherche.doe` + `banc_recherche.storage` |
| `mes_seuil_autoentretien.py` | seuil d'auto-entretien : rampe de pression montée/descente, hystérésis | `banc_recherche.seuil` |

## À récupérer si besoin (IDs Google Drive)

Ces scripts complètent le portage ; `read_file_content` ne lit pas le
`text/x-python`, utiliser `download_file_content` (base64) puis décoder.

| Fichier | Drive fileId | Rôle | Porté dans |
|---|---|---|---|
| `Data_analysis.py` | `1R5-170W11_EZN0qpik_ILX93DteTyr8Q` | Praat : `Tresp`, formants F1–F4, impédance P/Q, P·Q | `analysis` + `impedance` |
| `ValControl.py` | `1Kny_SBrjxNTdCn6hoAO73UwsXhd1I2hl` | contrôle vanne/pression (Pyboard #2) | `bench_link` |
| `valvecontrol.py` | `1Kld5Vfi0fug0krGenzBu1Xxh0XHNJiOG` | idem, version en service | `bench_link` |
| `enveloppepraat.py` | `1fJVZfy98XzRimtYnByC-NWdlahzYC1Vx` | enveloppe d'attaque (Praat) | `analysis.envelope` |
| `plotsmeasure.py` | `1MlrlpaUPSEksoMP4Ticzpd7Dsn0vg8VZ` | tracés des mesures | `gui/app` (pyqtgraph) |
| `step.py` | `1KNM9XCVACs6tQIcqbweuYyfXeOhMGLIg` | classe `Stepper` (Pyboard) | `firmware/drivers/actuators` |

## Constantes confirmées (du Drive) et reprises dans le scaffold

- **Surface** = `position_mm × 15` (`LargeurTrouSection = 15 mm`) → `config.SECTION_WIDTH_MM = 15`.
- **Grille DOE** : Section 4→12 mm, Clapet 2→22°, `Offset_Press = 300`,
  `Max_pression = 3500` (0–4095 DAC) → repris dans `config.DoeConfig`.
- **Acquisition** : audio `RATE = 48000`, pneumatique `sampling = 100–150 Hz`,
  `RECORD_SECONDS = 3` → `config.AudioConfig` / `config.DoeConfig`.
