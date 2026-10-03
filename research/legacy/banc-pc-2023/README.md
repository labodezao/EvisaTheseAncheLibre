# Les scripts PC du banc de mesure (2022-2024), versions complètes

## D'où ça vient

`D:\GoogleDrive\Ingénierie et recherche\Ressources\python\Mesure anches\` (dates des
fichiers : 2022 à septembre 2023), et `ValControl.py`, `valvecontrol_init.py` de
`...\Ressources\micropythonn code\`.

`research/scripts/legacy/README.md` les listait « à récupérer si besoin » par leur
identifiant Drive. Les voici :

- `Data_analysis.py` : version **complète** (20/09/2023), avec la boucle sur le HDF5.
  Le dépôt n'en avait qu'un extrait.
- `enveloppepraat.py`, `praatscripts.py`, `praatformants.py`, `testpraat.py` : analyse
  Praat (enveloppe d'attaque, formants).
- `plotsmeasure.py`, `testmeas.py`, `analysis temp.py`, `h5tutor.py`, `testhd5.py` : tracés
  et lecture des HDF5.
- `testsweepfres mano.py` (11/12/2020) : balayage de pression par le Pyboard (rshell) avec
  enregistrement audio.
- `ValControl.py`, `valvecontrol_init.py` : commande de la vanne (Pyboard).

`Mesures.py` et `mes_seuil_autoentretien.py` sont identiques à ceux de
`research/scripts/legacy/` : pas recopiés.

## Comment relancer

Python 3 avec numpy, h5py, parselmouth, matplotlib, pyaudio. Ces scripts attendent les
dossiers de mesure à côté d'eux (`data\`, `data_d1_L\`...), qui restent sur le Drive.
Ils ne sont pas exécutés par `banc_recherche` : ce sont des références pour le portage.
