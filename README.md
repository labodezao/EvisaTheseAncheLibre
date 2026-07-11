# Accordeur Anche Libre Pro

Accordeur professionnel multiplateforme pour **accordéon** et instruments à
anche libre similaires : harmonica diatonique, concertina, bandonéon,
mélodica, orgue à anches. Conçu pour l'accordage de précision et pour l'étude
scientifique de l'anche libre.

## Fonctionnalités

- **Précision < 0,1 cent** en temps réel (vérifiée par les tests : < 0,001 Hz
  sur ton stable), plage **Mi0 → Do9**.
- **Suivi harmonique** (comme le mode harmonique d'APTuner) : détection de
  note par appariement des partiels — pas d'erreurs d'octave ni de quinte,
  même sur les basses à fondamentale faible. La détection est **robuste à
  l'inharmonicité** : les partiels étirés (non accordés au multiple exact,
  fréquents sur les anches réelles) sont écartés par médiane pondérée et ne
  biaisent pas la fondamentale (vérifié jusqu'à +30 cents d'étirement).
- **Suivi individuel des harmoniques** (jusqu'à H8) : chaque partiel reçoit
  son propre traqueur zoom et est mesuré à sa **fréquence réelle** — l'écart
  de chaque harmonique au multiple exact (l'inharmonicité de l'anche) devient
  une trace sur la courbe d'accordage, mesurée à < 0,1 cent. Combinable avec
  le mode « notes définies » pour suivre plusieurs notes à la fois.
- **Mesure polyphonique multi-anches** : tremolo 8'+8', musette 3 voix,
  registres 16'+8'+4'… mesurés *simultanément*, sans neutraliser d'anches et
  sans ouvrir la caisse. L'utilisateur définit le registre (ou les notes de
  l'accord) pour guider l'analyse.
- **Battements** mesurés entre anches et comparés à la **liste de battements**
  cible (courbe exponentielle + écrasements par note). Copie possible des
  battements d'un instrument existant vers la liste cible.
- **Enregistrement & rapport** : mémorisation de chaque anche, tableau des
  écarts, rapport imprimable, export CSV / JSON.
- La4 réglable **430–450 Hz**, **transposition**, **tempéraments** historiques
  (égal, Pythagore, mésotonique 1/4 comma, Werckmeister III, Kirnberger III,
  Vallotti), calibration de la carte son (ppm).
- **Lecture numérique** : sélection par cases d'une ou plusieurs anches/harmoniques,
  affichées en grands caractères (justesse en cents, fréquence et écart en Hz,
  battement) — la valeur exacte sans interpréter la courbe, couleurs cohérentes
  avec les traces, sélection mémorisée.
- **Courbe d'accordage** : écart en cents de chaque anche au fil du temps
  (fenêtre glissante de 15 s, échelle ±5 à ±50 ¢), marqueurs de changement de
  note pour lire les transitions, gel par bouton ou clic sur la courbe,
  lecture des valeurs au survol. Plus stroboscope, spectre 20 Hz–10 kHz,
  **zoom spectral** montrant chaque anche individuellement, générateur de
  sons au timbre d'anche.
- **Faible latence** : capture AudioWorklet (blocs de 512 échantillons),
  analyse dans un Worker dédié (jamais bloquant pour l'audio ni l'affichage),
  spectres transférés sans copie, affichage 60 fps. Charge DSP affichée en
  direct (typiquement ~7 % d'un cœur).
- **Flux d'accordage professionnel** : témoin ✔/↑/↓ à tolérance réglable, gel
  automatique quand la mesure est lisible et reprise à la prochaine attaque du
  soufflet, verrouillage de note, grille de progression (anche × note × sens
  du soufflet), sens tirer/pousser mémorisés séparément, raccourcis clavier,
  calibrage du micro depuis une référence connue. Voir [`web/aide.html`](web/aide.html).
- **Interface en onglets** (Accordage / Analyse / Réglages / Rapport) : l'en-tête
  (note, témoin, boutons) reste toujours visible, chaque onglet tient sur un
  seul écran sans avoir à faire défiler toute la page — pensé pour l'usage à
  l'établi comme sur mobile.
- **Thème clair par défaut**, sombre en option (bouton dans le bandeau,
  mémorisé) — toutes les couleurs, y compris celles dessinées sur les
  graphiques (courbe, spectre, zoom, phase), viennent d'un même jeu de
  variables CSS par thème.
- **Analyse physique** (voir [ANALYSE.md](ANALYSE.md)) : export CSV de la
  courbe (120 s : fréquence, écart ¢, intensité dB par voix), temps de
  réponse de l'anche à chaque attaque (10→90 %, résolution 10,7 ms),
  **diagrammes de phase** à axes choisis (f–I, portraits de phase df/dt…),
  **gel automatique du temps** sous un seuil d'intensité réglable, détecteur
  de **bifurcation sous-harmonique** (bandes f/2 et 3f/2), verrouillage
  manuel de la note, plein écran par panneau, registre 5 anches.

## Utilisation

### Navigateur (le plus simple)

```bash
node server.mjs
# puis ouvrir http://localhost:8173  (Chrome, Edge, Firefox, Safari récents)
```

Guide d'utilisation complet : ouvrez [`web/aide.html`](web/aide.html) (lien
« guide d'utilisation » en bas de l'accordeur).

### Android (Termux)

`npm` ne fonctionne pas dans `/storage/emulated/0/...` (stockage partagé sans
permissions Unix) — d'où l'erreur `EACCES`. Copiez le projet dans le home de
Termux ; aucun `npm install` n'est nécessaire pour le mode navigateur :

```bash
cp -r /storage/emulated/0/Download/tuner ~/tuner
cd ~/tuner && node server.mjs
# puis Chrome Android → http://localhost:8173  (autoriser le micro)
```

Le plus simple sur mobile : le dossier `web/` est publié sur **GitHub Pages**
(workflow `.github/workflows/pages.yml`) — ouvrez l'URL Pages directement, sans
Termux ni serveur. Une connexion `https://` est requise pour le micro.

### Application de bureau (Windows / macOS / Linux)

```bash
npm install
npm start          # lancement direct
npm run dist:win   # installateur Windows (NSIS)
npm run dist:mac   # image disque macOS (DMG) — à lancer depuis un Mac
```

### Tests de précision du moteur

```bash
npm test
```

Sept scénarios de synthèse vérifient : précision < 0,1 cent sur anche isolée,
séparation d'un tremolo à 2,3 Hz d'écart, note grave à fondamentale faible,
harmonique 2 dominante, registre 16'+8', accord Do-Mi-Sol, convergence
< 0,02 cent.

## Architecture du traitement du signal

```
micro → AudioWorklet (thread audio, blocs 512) ─┐ MessagePort
                                                ▼
                                   Worker DSP (engine.js)
                 ┌──────────────────────────────┴───────────────────────┐
                 ▼                                                      ▼
     Analyse grossière (coarse.js)                       Traqueurs zoom (zoom.js)
     FFT 32768, pics, appariement                        1 par groupe d'octave :
     harmonique → note + octave                          hétérodynage e^{-j2πfc t},
     (Mi0→Do9, anti-erreur d'octave)                     décimation ×512, FFT en
                 │                                       bande de base ±42 Hz,
                 └── choisit les cibles ────────────────▶ raffinement par phase
                                                          → chaque anche : f, ¢, Hz,
                                                            battements
```

Points clés :

- **Zoom hétérodyne** : autour de chaque note, le signal est ramené en bande
  de base (bande ±42 Hz, résolution 0,08–0,37 Hz selon la réactivité choisie),
  puis la fréquence de chaque pic est raffinée par la **différence de phase**
  entre deux fenêtres décalées — précision finale ~0,001 Hz sur ton stable.
- **Notes graves** : la mesure se fait sur un partiel supérieur (k·f₀ ≥ 150 Hz)
  puis est divisée par k ; l'écart entre anches y est multiplié par k, ce qui
  améliore encore la séparation des basses tremblées.
- **Harmoniques revendiquées** : la 2ᵉ harmonique du 16' est prédite à partir
  de la mesure du 16' et exclue de la mesure du 8' (appariement par
  programmation dynamique préservant l'ordre fréquentiel).
- **Réactivité / précision** : la fenêtre d'analyse glisse en continu ;
  l'affichage réagit en ~100 ms et la précision converge pendant que l'anche
  sonne (indicateur « convergence »). Rapide ≈ 1,4 s, Normale ≈ 2,7 s,
  Précise ≈ 5,5 s de fenêtre.
- **Limite physique** : deux composantes distantes de δf Hz exigent ~1/δf s
  d'observation pour être séparées, quel que soit l'algorithme. Si l'anche 8'
  coïncide à < 0,2 Hz avec l'harmonique 2 du 16', utilisez le mode « Précise »
  ou mesurez le registre 8' seul.

## Mode test sans micro

Ajoutez `?gen=440.2` (ou `?gen=440,442.5` pour un tremolo) à l'URL : des
oscillateurs internes remplacent le micro — utile pour valider l'installation.

## Structure du dépôt

```
web/            application (HTML/CSS/JS, modules ES, sans dépendance)
  js/dsp/       moteur : fft.js, coarse.js, zoom.js, engine.js, worker.js
  js/music.js   notes, tempéraments, registres, listes de battements
  js/report.js  enregistrement & rapport
electron/       enveloppe application de bureau
test/           tests de précision du moteur (Node)
```
