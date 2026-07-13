# Analyse physique de l'anche libre — guide et feuille de route

Ce document accompagne l'accordeur : audit de l'outil, mode d'emploi des
fonctions d'analyse physique, et feuille de route pour l'étude des systèmes
stochastiques et des bifurcations non linéaires des anches libres.

## 1. Audit de l'outil (état actuel)

### Chaîne de mesure

| Étage | Implémentation | Résolution / latence |
|---|---|---|
| Capture | AudioWorklet, blocs de 512 échantillons | ~10,7 ms à 48 kHz |
| Enveloppe (intensité) | RMS par bloc | 10,7 ms |
| Détection de note | FFT 32768 + appariement harmonique **et** NSDF (méthode McLeod) comme ancre d'octave | fenêtre 341 ms (spectral) / 85 ms (NSDF), glissante toutes les 85 ms |
| Mesure fine | hétérodynage + décimation ×512 + FFT en bande de base + raffinement de phase | < 0,001 Hz sur ton stable ; fenêtre 1,4 / 2,7 / 5,5 s |
| Historique | 120 s conservées, 11,7 points/s par voix | export CSV |

### Vérifié par les tests (11 scénarios)

- < 0,1 cent sur anche isolée, convergence < 0,02 cent en mode précis ;
- séparation d'un tremolo à 2,3 Hz, battement à ±0,0003 Hz ;
- notes graves via partiel supérieur, pas d'erreurs d'octave ;
- fondamentale non biaisée par des partiels étirés jusqu'à +30 cents ;
- chaque harmonique mesurée individuellement à < 0,1 cent ;
- registre 16'+8' avec exclusion de l'harmonique 2 du 16' ;
- temps de réponse d'attaque (10→90 %) à ±25 ms ;
- détection d'énergie sous-harmonique (f/2, 3f/2).

### Limites connues (à garder en tête pour la thèse)

1. **Résolution spectrale ↔ temps** : séparer deux composantes distantes de
   δf exige ~1/δf secondes d'observation — limite physique, pas
   algorithmique. Le mode « précis » (5,5 s) sépare ~0,4 Hz.
2. **Horloge de la carte son** : la précision absolue dépend du quartz de
   l'interface audio (typiquement ±20 ppm ≈ ±0,03 cent). Le réglage
   « calibration ppm » permet de la corriger contre une référence connue
   (GPS, générateur étalonné).
3. **Intensité en dB relatifs** : le micro n'étant pas étalonné, les niveaux
   sont relatifs (pas de dB SPL absolus). Les *variations* sont fiables.
4. **Pression et débit non mesurés** : l'outil est purement acoustique. La
   caractéristique fréquence–intensité (diagramme de phase X = I, Y = ¢)
   sert de proxy : à embouchure fixe, l'intensité croît de façon monotone
   avec la pression d'alimentation, donc f(I) reproduit la forme de f(p).
   Pour une vraie caractéristique f(p)/I(p)/débit, synchroniser l'export CSV
   (colonne temps) avec un capteur de pression externe échantillonné à part.
5. **Points à 85 ms** : les dynamiques plus rapides que ~6 Hz (transitoires
   d'attaque fins) sont sous-échantillonnées dans l'historique ; le temps de
   réponse est lui mesuré sur l'enveloppe à 10,7 ms.

## 2. Outils d'analyse disponibles

- **Courbe d'accordage** (15 s) : fréquence de chaque anche/harmonique dans
  le temps, marqueurs de transition de note, gel par clic/bouton/seuil.
- **Gel automatique du temps** : sous le seuil d'intensité choisi (−80 à
  −40 dB), l'horloge s'arrête — les silences ne polluent ni la courbe ni
  les statistiques exportées.
- **Temps de réponse de l'anche** : montée 10→90 % du régime établi,
  mesurée à chaque attaque (résolution 10,7 ms) — sensible au réglage du
  larron, à la hauteur de languette, au vent.
- **Diagramme de phase** : trajectoire de la voix suivie dans un plan au
  choix parmi {temps, écart ¢, fréquence, intensité dB, df/dt, dI/dt}.
  Usages types :
  - X = I, Y = ¢ : caractéristique fréquence–amplitude (flattening de
    l'anche avec la pression) ;
  - X = ¢, Y = df/dt : portrait de phase de la dynamique de fréquence
    (point fixe = anche stable, cycle = oscillation entretenue de la
    fréquence, ex. couplage entre anches) ;
  - X = I, Y = dI/dt : portrait de phase de l'enveloppe (attaques, extinctions).
- **Détecteur de bifurcation sous-harmonique** : bandes f/2 et 3f/2
  surveillées en continu ; l'apparition d'énergie y est la signature du
  doublement de période (anche qui « râle », régime biphonique).
- **Export CSV de la courbe** : 120 s × (fréquence, écart ¢, intensité dB)
  par voix + note — prêt pour Python/R/Matlab.

## 2 bis. Modèle physique implémenté (mesures reliées à l'expérience)

- **Fusion multi-harmonique cohérente** (mode auto) : une anche en régime
  établi est strictement périodique → partiels exactement harmoniques ; les
  partiels 2–4 sont suivis en interne et fusionnés (poids ∝ (A·k)², variance
  en 1/k²), seuls les partiels < 1,5 cent de la fondamentale participant
  (les partiels étirés sont écartés). Précision accrue sous bruit et
  fondamentale faible, convergence plus rapide.
- **Caractéristique pression–hauteur f(I)** : régression en direct de
  l'écart (¢) sur l'intensité (dB) à partir de l'estimateur *rapide* (la
  mesure fine traîne derrière un balayage et biaiserait la pente vers zéro).
  Affichée sous le diagramme de phase : pente en ¢/dB, R², plage. Protocole :
  note tenue, crescendo/decrescendo ≥ 3 dB.
- **Taux de croissance exponentiel σ de l'attaque** : le démarrage d'une
  anche est une instabilité linéaire (A·e^{σt}) ; σ est ajusté par moindres
  carrés sur ln(RMS) dans la zone de montée 10→90 % (vérifié à ±1 % sur
  attaque synthétique à 25 s⁻¹). Affiché avec le temps de réponse.
- **Alerte de verrouillage par injection** : deux anches accrochées
  oscillent à la même fréquence — une seule composante là où deux anches
  devraient battre (voix tremblée non détectée, mesure convergée, référence
  présente) → « ⚠ verrouillé ? » dans le tableau. Second cas signalé :
  battement mesuré quasi nul contre une cible non nulle.
- **Plancher d'appariement −30 dB** : un pic à plus de 30 dB sous le plus
  fort du groupe est une fuite spectrale, pas une anche.
- **Détection temporelle NSDF (méthode McLeod)** : autocorrélation normalisée
  `NSDF(τ) = 2·Σ x[j]·x[j+τ] / Σ (x[j]²+x[j+τ]²)` (McLeod & Wyvill, 2005),
  calculée par FFT (fenêtre 85 ms). Complète la détection spectrale sur deux
  points : (1) **ancre d'octave** — quand la NSDF est franche (clarté ≥ 0,9)
  et que la fondamentale spectrale tombe sur un multiple/sous-multiple entier
  de la hauteur NSDF, la hauteur NSDF est adoptée (élimine erreurs d'octave
  et de douzième, y compris à fondamentale manquante) ; (2) **suivi continu**
  — la NSDF (fenêtre courte, robuste à l'octave) alimente le repli « suivi
  rapide » d'une hauteur en mouvement (chant, glissando), plus réactive que
  la FFT de 341 ms. La NSDF étant monophonique, elle est désactivée en mode
  registre (anches à l'unisson). Elle **ne remplace pas** la mesure fine
  (zoom hétérodyne < 0,001 Hz) ni la séparation polyphonique. La « clarté »
  (valeur du pic NSDF, indice de périodicité ∈ [0,1]) est affichée sous la
  mesure en suivi rapide comme indicateur de qualité du signal.

- **Déviation d'Allan σ(τ)** (onglet Analyse) : stabilité de fréquence de la
  voix suivie en fonction du temps d'intégration τ, calculée en overlapping
  sur la plus longue plage récente à note constante, tracée en log-log.
  Lecture : pente −½ = bruit blanc de fréquence (moyenner améliore) ;
  plancher puis remontée = marche aléatoire / dérive (turbulence du souffle,
  thermique) ; le creux donne le τ d'intégration optimal (σ min affiché avec
  son τ, plus σ(1 s)). Estimateur validé sur bruit blanc (pente mesurée
  −0,494 pour −0,5 théorique).

## 3. Feuille de route : stochastique et bifurcations

Fonctionnalités proposées (par ordre coût/bénéfice croissant), toutes
réalisables sur l'architecture actuelle :

1. **Histogrammes de fluctuation** : PDF de f et I sur fenêtre glissante ;
   la variance de fréquence est un précurseur de bifurcation (ralentissement
   critique : σ² diverge à l'approche du seuil).
2. **Déviation d'Allan σ_y(τ)** : stabilité de fréquence en fonction du temps
   d'intégration — sépare le bruit blanc de phase, la marche aléatoire (flux
   turbulent) et les dérives (thermique). Directement calculable depuis le
   CSV actuel ; à intégrer comme panneau.
3. **Diagramme de bifurcation piloté** : balayage lent de pression par le
   musicien ; l'outil trace f et le taux sous-harmonique en fonction de I
   (paramètre de contrôle) et repère le seuil de doublement de période.
4. **Cartes de premier retour** : T_{n+1} = g(T_n) sur les périodes
   instantanées (nécessite une mesure de période par passage à zéro dans le
   worklet, ~jour de travail) — met en évidence doublement de période et
   intermittence.
5. **Reconstruction d'attracteur (Takens)** : plongement {x(t), x(t−τ),
   x(t−2τ)} du signal audio brut autour d'une attaque — visualisation 3D du
   cycle limite et de ses déstabilisations.
6. **Exposant de Lyapunov local & dimension de corrélation** sur les données
   plongées (algorithme de Rosenstein / Grassberger–Procaccia) — quantifie
   le caractère chaotique d'un régime d'anche forcée.
7. **Statistiques de temps de séjour** : dans un régime bistable
   (bruit + deux attracteurs), histogramme des durées entre transitions —
   lois de Kramers, mesure de la hauteur de barrière effective.
8. **Enregistrement audio brut synchronisé** (WAV + CSV partageant l'horloge)
   pour analyses hors ligne exactes.

## 4. Utilisation sous Android (Termux)

`npm` ne fonctionne pas dans `/storage/emulated/…` (stockage partagé sans
permissions Unix). Copier le projet dans le home de Termux ; aucun `npm
install` n'est nécessaire pour le mode navigateur :

```bash
cp -r /storage/emulated/0/Download/tuner ~/tuner
cd ~/tuner
node server.mjs
# puis Chrome Android → http://localhost:8173 (autoriser le micro)
```
