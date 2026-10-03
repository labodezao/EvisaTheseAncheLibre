# Les modèles MATLAB et Scilab de l'anche (2015 à 2022)

## D'où ça vient

`D:\GoogleDrive\Ingénierie et recherche\Projets\Thèse anche libre\` :

- `acomdelGUI/` : `modeles\anches models\anches\libre\acomdelGUI\`. Interface MATLAB (GUIDE,
  2015) du modèle d'accordéon : `accomodel.m/.fig`, base d'anches `reeddatabase.m/.fig`,
  modèle Simulink `Motionreed.mdl`, paramètres `Paramètres_problème.m`, anches décrites par
  tronçons dans les petits `.mat` (`anche.mat`, `reed.mat`, `test*trc.mat`).
- `matlab_acco/` : `modeles\anches models\anches\libre\matlab acco\`.
  `RK4ode45cavity_reed_socket.m` (modèle anche + cavité + socle, porté en Python dans
  `banc_recherche/reed_model.py`), `modelsimple.m`, `matkm.m` et sa traduction Scilab
  `matkm.sci` (modes propres, porté dans `banc_recherche/modal.py`), `fleche*.m`,
  `isofreq.m`, et **`data_measurements.m`** (voir plus bas).
- `anche_double/` : `modeles\anches models\anches\doubles\matlabdoublereed\` (modèle de Bonin).
- `acoustique_2019/` : `acoustique\` (petits scripts 2 ddl, Helmholtz, FFT, `formules.lyx`).

Les fichiers sont en Windows-1252 (accents), copiés tels quels.

Non copiés, restés sur le Drive : `PVS111.mat`, `PVS121.mat`, `PVS131.mat` (3,5 Mo
chacun, sorties simulées du modèle RK4 : position, vitesse, débit, pression, volume de
cavité), `MatRes.mat`, `Resanche.mat`, `ltfat-2.3.1.tar.gz`.

## Deux choses à savoir

1. **`data_measurements.m` analyse des mesures de 2011** : position de l'anche au
   vibromètre laser, pression de la cavité (capteur Kulite), plusieurs volumes de cavité
   et plusieurs pressions. Il lit des fichiers `.vna` dans
   `D:\science ewen\acco\ewen 2011\large_reed\`. Ce dossier **n'est ni sur le Drive, ni sur
   E:, ni sur J:**. Ce sont les mesures du projet EVISA au laboratoire MWL (KTH), décrites
   dans `InnoVaDys\Ressources\presensations\presentation evisa-en [Compatibility Mode].pdf`.
2. **Une erreur probable dans `RK4ode45cavity_reed_socket.m`** (lignes 30 et 35) :
   `bmoy = sum(Properties_mat(:,3))/length(Properties_mat(1,:))`. La somme porte sur les
   3 tronçons (lignes) mais elle est divisée par le nombre de **colonnes** (5). La largeur
   et l'épaisseur moyennes sont donc trop petites d'un facteur 3/5. Elles servent dans la
   section de fuite `S_Inter` et dans les pertes de charge. Les sorties `PVS*.mat` en
   héritent. Le port Python (`reed_model.py`) ne reprend pas ce calcul.

## Comment relancer

MATLAB (ou Octave pour les scripts sans GUIDE ni Simulink) : se placer dans le dossier,
lancer `accomodel` (interface) ou `RK4ode45cavity_reed_socket`. Scilab : `exec matkm.sci`.
