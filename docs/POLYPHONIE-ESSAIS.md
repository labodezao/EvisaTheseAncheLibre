# Polyphonie sur enregistrements réels : essais du 06/10/2026

Moteur v30 (gelé, phase 1), rejoué hors navigateur sur les enregistrements d'Ewen.
Question : L'accordeur sépare-t-il juste 2 ou 3 anches d'une même note (16'+8', unisson
ouvert, quinte), à l'établi ? Chaque défaut a un test de synthèse qui échoue :
`test/polyphonie.test.mjs` (`npm run test:poly`, hors de `npm test`).

## 1. Enregistrements trouvés

| Fichier | Durée | Contenu | Utilisé |
|---|---|---|---|
| `EvisaTheseAncheLibre/test/session-2026-09-25-23-58-20.zip` (D:\GoogleDrive\Ingénierie et recherche\Projets\Thèse anche libre\) | WAV 600 s, 48 kHz, mono, 16 bits ; CSV et JSON de ce que la v27 a affiché | 0-106 s : notes main droite, une anche, inversions du soufflet ; 103-145 s : voix chantée (pas d'accordéon) ; 145-540 s : main gauche, basses 16'+8', quintes, Do3 et Do#3 à deux anches ; 540-600 s : notes seules | oui, 17 passages |
| `J:\Archive multimédia\Audio transcrit\2025\2025-02-05 essai acoustique - basses, mi 0.aac` | 35,2 s, AAC 44,1 kHz | « Burning bass Mi 0 » : Mi1 (41,2 Hz) tenu, deux paliers (11-15 s, 17-21 s) | oui, P17 (converti par `ffmpeg -i … -ac 1 -c:a pcm_s16le essai-basses-mi0.wav`) |
| idem, `2025-02-05 essai acoustique - basses 1.aac` | 33,4 s | basse très grave Mi1, paliers de 2 à 4 s | non (même registre que P17) |
| idem, `2026\2026-01-29 essai acoustique - sans les garnitures.aac` | 13,6 s | coups brefs, aucun palier de 1,5 s | non |
| `Thèse anche libre\acoustique\anches libres\acco\anches\reed1.WAV` (2019) | 28 s, 44,1 kHz | niveau qui fluctue sans cesse, aucun palier | non |
| `reed.wav` (0,66 s ; 0,32 s à 123 kHz), `carre/sinus/dentscie/tri*.wav` | — | trop court, ou formes d'onde de synthèse | non |

Historique git de la thèse : seul le ZIP ci-dessus est un son d'anche (les `.m4a` OSSO sont
de la musique). `J:\multimedia à tier\INBOX` : aucun son d'anche. Aucun fichier personnel ouvert.

## 2. Vérité terrain, hors moteur

`test/outils/verite_poly.py` : spectre long, puis pour chaque amas de raies une bande de base
(hétérodynage, Butterworth aller-retour, décimation) et ESPRIT (Roy et Kailath 1989,
IEEE Trans. ASSP 37(7), doi:10.1109/29.32276). Une anche est périodique : ses partiels k
donnent la même hauteur f/k ; on regroupe les composantes dont f/k concordent à 0,35 ¢
près, de façon gloutonne (l'anche qui explique le plus d'amplitude d'abord ; rangs premiers
entre eux, sinon c'est un sous-multiple). Hauteur : moyenne de f/k pondérée par (A k)² ;
incertitude u : écart entre partiels / √(n−1). Le secteur (50 Hz du micro, −73 dB) est écarté.

Validation sur synthèse (vibrato ±0,4 ¢, bruit à 30 dB, ronflement) : basse 16'+8'+4',
quinte avec octaves, musette 2 et 3 anches, Mi1+Mi2 : 13 anches sur 14 trouvées, erreur
≤ 0,04 ¢ ; 3 fantômes faibles (−24 à −36 dB, 2 ou 3 partiels), écartés à la comparaison
(au moins 3 partiels, moins de 24 dB sous la plus forte). Limite : une anche à la douzième
juste d'une autre (3:1 à 0,05 ¢) est indiscernable ; une octave juste à moins de 0,6 ¢ aussi
(notée « octave juste »).

Point de méthode décisif : les anches réelles bougent (soufflet, attaque) de 0,5 à 3 ¢ dans
une fenêtre de 2,7 s. La vérité est donc calculée image par image, **sur la fenêtre même du
moteur** (W/srd, au moins 1 s ; `test/outils/compare_poly.py`). Écart affiché = moteur − vérité.

## 3. Le moteur, passage par passage

Réglages : Automatique ; le registre juste (LM = 16'+8', MM, Q = quinte, M) ; Auto-anches avec
sous-espaces (`subspace`, octaves 0 et +1 pour les basses). Écarts sur les 40 % finaux du
palier (médiane, max). 1re : première valeur fine après l'attaque ; sép. : toutes les anches
à 1 ¢ dans 80 % des images suivantes (registre juste). M : « confondu avec l'octave ».

| Passage (session, s) | Vérité (¢, ±u) | Automatique | Registre juste | Auto-anches | 1re / sép. |
|---|---|---|---|---|---|
| P01 Fa2 157,7-161,3 | 16' +12,5 ±0,02 ; 8' octave juste | max 0,44 | 16' max 0,19 ; 8' M | 8' max 0,59 ; 4' maintenu, −1,8 | 0,35 / 2,23 s |
| P02 Fa2 181,5-185,6 | 16' +15,1 ; 8' +17,0 (−11 dB, dérive 2 ¢) | +1,5 (mélange), alerte à 2,0 s | 16' max 0,26 ; 8' ±0,16 mais M | 8' max 0,83 ; 4' σ 0,79 | 0,44 / 2,06 s |
| P03 Ré#2 195,3-198,3 | 16' +8,9 ±0,02 ; 8' +10,5 | +1,1 (mélange), alerte 6/41 images | 16' max 0,14 ; 8' max 0,21, M | 8' max 0,20 ; **4' absent** | 0,44 / 1,80 s |
| P04 La#2 345,0-350,4 | 16' +5,32 ±0,01 ; 8' +12,31 ±0,01 | lu +10 à +15 ¢ : ni 16' ni 8', alerte | 16' max 0,17 ; **8' σ 0,22, max 0,38** (1,4 avant 2,6 s) | 8' max 0,10 ; **4' absent** | 0,44 / 1,12 s |
| P05 La#2 370,6-374,9 | 16' +5,0 ; 8' +11,8 | mélange, alerte | 16' max 0,17 ; **8' max 0,45** (1,6 à 2,5 s) | **4' absent** | 0,35 / 1,21 s |
| P06 Ré#2 375,0-378,9 | 16' −0,4 ; 8' +16,3 (−8 dB, glisse de +34 à +16 ¢) | octave fausse | **note une octave trop haut toute la note** : 16' = le 8', 8' = rien | note Ré#3, 16' affiché en 8'−, fantôme +23 | 0,69 / jamais |
| P07 Fa2 385,9-389,8 | 16' +12,6 ; 8' octave juste | max 0,33 | 16' max 0,26 ; 8' M | 8' max 0,91 | 0,35 / 2,06 s |
| P08 Ré2 414,3-417,7 | 16' +9,7 (−9 dB) ; 8' +8,5 | une image | **note une octave trop haut** : vrai 16' jamais affiché | Ré3 max 0,32 | 0,61 / jamais |
| P09 Mi2 429,4-432,9 | 16' +12,0 ; 8' +10,7 (−1,3 ¢ sur l'octave) | −1,4 (mélange), alerte 8/46 | 16' méd −0,30 ; **8' −1,3 à −3,0, maintenu** | 8' max 0,60 ; 4' +1,6, M | 0,69 / jamais |
| P10 Do#3 468,3-470,8 | +7,40 ±0,01 ; +31,1 ±0,03 (−5 dB) | forte, max 0,11 | MM 8' max 0,05 ; 8'+ max 0,51 | 0,09 ; 0,46 | 0,35 / 1,38 s |
| P11 Do3 390,0-392,9 | +6,4 ; +31 à +33 (−11 à −16 dB, glisse) | max 0,19 | MM 0,54 ; 0,38 | 0,17 ; 0,31 | 0,61 / 1,46 s |
| P12 Ré#4+La#4 255,4-258,4 | +5,00 ±0,05 ; +15,74 ±0,01 | **Ré#3 +13,8 / +31 (fantôme)**, alerte | Q : 1 max 0,12 ; 5 max 0,06 | **Ré#3 (octave), fantôme 8'+ +13,8** | 0,44 / 1,38 s |
| P13 idem 258,5-262,8 (inversion 261,27) | +0,8 / +20,4 puis +4,0 / +16,2 | **Mi3 −47,7 (fantôme)** | Q max 0,26 ; voir § 3.2 | octave | 0,35 / 1,29 s |
| P14 La#3+Fa4 475,5-478,2 | +5,38 ; −1,96 | La#2 (octave, cents justes) | Q : 0,09 ; 0,01 | La#2 (octave) | 0,69 / ≤ 1,9 s |
| P15 Fa#3 seul 89,5-93,5 | +2,54 ±0,01 | max 0,09 | M max 0,07 | **disparaît après 2,4 s** | 0,52 / 1,04 s |
| P16 Ré#4 seul 557,2-559,6 | +0,19 ±0,01 | max 0,03 | M max 0,05 | **−0,25 (méd), max 0,28** | 0,52 / 1,46 s |
| P17 Mi1 (essai basses mi 0) 16,5-21,3 | −3 à −5 (dérive ±1,5 ¢, AAC) | méd −0,72, max 2,2 | 16' σ 0,82 ; 8' M | σ 0,56 | 0,89 / 2,38 s |
| P18 Fa2 177,9-181,5 | 16' +12,5 ; 8' octave juste ; glisse de +15,6 à +12,5 ¢ en 2,5 s | max 0,19 | 16' max 0,15 ; 8' M | 8' max 0,50 | 0,69 / 2,49 s |

Bruit blanc ajouté à 20 et 10 dB (sur tout le passage) : aucun changement au-delà de 0,05 ¢
sur les cas justes. Seuls changent les cas déjà fautifs (P06 : à 10 dB la note est juste,
signe d'une course à l'attaque). Un bruit blanc large bande ne pèse presque rien dans une
case de 0,37 Hz (−58 dB à 10 dB de RSB) : ce n'est pas un vrai test de bruit d'atelier.

### 3.1 Ce qui marche, chiffres à l'appui

- Anche seule (Automatique, M) : max 0,09 ¢ et 0,05 ¢ sur palier ; 1re valeur 0,52 s.
- Quinte en registre Q : 0,01 à 0,12 ¢ (P12, P14) ; même après une inversion, 0,26 ¢ au pire.
- Unisson très ouvert (24 à 27 ¢, MM ou Auto-anches) : l'anche forte à 0,05-0,09 ¢ ; la faible
  (−5 à −16 dB, qui glisse encore après l'attaque) à 0,3-0,5 ¢.
- 16' des basses (LM) : 0,14 à 0,26 ¢ ; mesuré sur un partiel impair, il ne se mêle pas au 8'.
- Inversion du soufflet sans silence (P13, quinte) : vue, traqueurs repartis, pas de valeur
  de l'ancien sens ; 1re valeur 0,43 s après, 1 ¢ à 0,5-0,8 s, 0,1 ¢ à 1,1 s.
- Automatique sur deux anches : l'alerte « partiels en désaccord » vient vers 2 s quand
  l'écart dépasse 1,5 ¢ (P02, P04, P05, P12, P13).
- Fa2 à 178 s : la v27 (CSV de la session) montrait le 8' entre +6,8 et +21,3 ¢, 20 sauts
  de plus de 1 ¢. La v30 : 6 sauts, tous dans les 2,5 premières secondes, où l'anche glisse
  vraiment de +15,6 à +12,5 ¢ ; ensuite le 16' est à 0,15 ¢ (P18).

### 3.2 Inversion du soufflet (P13)

Creux de 12 dB, 80 ms, à 261,27 s. Hors moteur (pente de phase sur 0,2 s) : Ré#4 remonte de
+1,0 à +4,0 ¢ en 0,4 s, La#4 est à +16,2 dès 0,25 s. Moteur (Q) : premières valeurs −0,4 et
+14,9 ¢ (fenêtre de 0,34 s qui garde le creux et le glissement), +3,97 et +16,24 à 1,1 s.
Le retard suit surtout un glissement réel : pas de défaut de séparation ici. En 16'+8', en
revanche, le 8' met plus de 2 s (D7).

## 4. Défauts, mécanismes, tests (`test/polyphonie.test.mjs`)

| Défaut | Vu sur | Mécanisme (lignes du moteur v30) | Test |
|---|---|---|---|
| **D1** 8' lu à 0,2-3 ¢ en 16'+8' | P04, P05 (8' à +7 ¢ de l'octave : max 0,38-1,6 ¢), P09 (−1,3 ¢ : erreur −1,3 à −3 ¢) | `plan.js` l. 256-271 : collisions testées en fréquences NOMINALES ; à l'octave chaque partiel k du 8' tombe sur 2k du 16', la boucle va jusqu'à K_MAX et garde k = 1, le pire : l'écart réel 8' − 2×16' y est minimal (0,9 Hz pour La#2, 0,16 Hz pour Mi2) ; l'amas de phase (`appariement.js` clusterRefine) est coupé à mi-chemin | La#2 +5/+12 et Mi2 +12,1/+10,4 : 8' à 0,81 et 0,82 ¢ (16' à 0,04) |
| **D2** Auto-anches efface l'anche d'octave | P03, P04, P05 (4' jamais affiché) | trois filtres anti-fantôme plus larges que la résolution : `engine.js` l. 439-442 (le partiel 8 de l'anche grave, plus fort, prend la bande du 4' ; raie « revendiquée » donc effacée), l. 725-736 (à moins de 8 ¢ de k fois une anche plus forte = harmonique), l. 716-721 (plancher −25 dB qui compte les traqueurs cachés) ; relevé sur une copie instrumentée | La#2 et Ré#2 : 4' juste sur 0/29 images |
| **D3** Automatique mêle 16' et 8' sans alerte | P03 (+1,1 ¢, alerte 6/41), P09, P02 | `plan.js` l. 221 : note grave mesurée sur k = ceil(150/f) = 2, qui EST la fondamentale du 8' à 0,13 Hz ; fusion `engine.js` l. 568-620 sur les partiels 2 et 4, partagés ; alerte à 1,5 ¢ (DISAGREE_CENTS) | Ré#2 +9/+10,6 : lu +10,13, 0 alerte, 0/29 juste |
| **D4** 16'+8' : note bloquée une octave trop haut | P06 (toute la note), P08 (16' 9 dB plus faible, vu seulement après 1,9 s) | le 8' (petite anche, croissance plus rapide) parle d'abord : note = son octave ; `engine.js` l. 304-309, garde d'octave du registre : tant qu'une voix est mesurée « à sa place » (le 16' posé sur le vrai 8'), la note juste est refusée (trace : 48 refus) | 16' arrivé 0,7 s après : note Ré#4 au lieu de Ré#3, 0/29 (0,4 s : se corrige) |
| **D5** Quinte en Automatique et Auto-anches | P12, P13, P14 | la fondamentale spectrale (`coarse.js`) explique tout par la période commune, une octave sous la basse ; La#4 = 3 × Ré#3 (+13,8 ¢ dans cette note), dans la bande d'unisson (±35 ¢), prend une case ; rien ne vérifie l'énergie propre de cette fondamentale | Ré#4+La#4 : 46 et 23 valeurs fausses |
| **D6** Auto-anches : une anche seule disparaît | P15 (rien de 2,4 s à la fin) | partiel de mesure choisi s'il est à moins de 30 dB du plus fort (`plan.js` l. 63), anche effacée à plus de 25 dB (`engine.js` l. 716-721, plancher qui compte les traqueurs cachés, l. 636-639) ; P15 : partiel 5 à 27 dB sous les partiels 3-4 | Fa#3, partiel 5 à −27 dB : 30/41 images |
| **D7** 16'+8' : 8' juste après plus de 1,5 s | P02, P03 (8' à 1,6-1,8 ¢ de l'octave : 1 ¢ atteint à 2,1 et 1,8 s), P09 (jamais) ; P04, P05 jamais à 0,1 ¢ | après une attaque ou une inversion (`engine.js` l. 341, RESUME_KEEP) la fenêtre repart de 85 ms ; le 8', sur sa fondamentale (D1), ne se sépare du partiel 2 du 16' qu'au-delà de 1,4 s ; absent puis faux de 2 ¢ | 8' à 2,41 ¢ 2,29 s après l'inversion |
| **D9** Auto-anches lit une anche seule sur UN partiel faible | P16 (−0,25 ¢ ; Automatique +0,01) | `plan.js` unisonHarmonic choisit le plus haut partiel qui sépare des anches supposées (±35 ¢), sans regarder sa force ; hors moteur : k1 +0,19, k3 −0,09, k4 +0,13, k5 +0,18 ¢ : le partiel 3 (−17 dB) est dévié ; Automatique fond k1-k4 pondérés (A k)² | raie à 0,3 Hz de 3f, −25 dB : 0,30 ¢ (Automatique 0,05) |
| **D8** cas dégénéré noté le 06/10 | — | 440 + 442 Hz égaux, sans bruit, partiels 1/n : **non reproduit** (réglages de cfgMoteur, normal, précis, sous-espaces, MMM ; 6 à 49 partiels ; phases nulles ou au hasard ; 2 et 3 s : écart ≤ 0,01 ¢) ; test gardé, il passe | garde |

Non expliqués, à creuser avant d'écrire un test : P09, 16' de Mi2 à −0,30 ¢ constant (9 images) ;
P02 et P03, 8' séparé de 1,6 à 1,8 ¢ mais marqué « confondu » (drapeau seul, valeur juste).

Les tests D1 à D7 et D9 échouent sur le moteur v30 (11 vérifications en échec, 2 passent :
D8, et D9 en Automatique). Synthèse : timbre à −3,5 dB par partiel avec ±2 dB de hasard
(basse : −1,5 dB, 20 partiels), vibrato de pression commun ±0,1 ¢ à 0,8 Hz, bruit blanc à
40 dB, graines fixes.

### 4.1 Corrections (moteur v33, 06/10/2026)

Chaque correction part du mécanisme, vérifié dans le code et sur le passage réel ; ses tests sont
passés de `test/polyphonie.test.mjs` à `test/dsp.test.mjs` (scénarios 44 à 50), où ils échouent sur
la v31 et passent. Mesure avant/après : `compare_poly.py` sur les 18 passages, lue par
`avant_apres_poly.py` (médiane / max de l'écart à la vérité, en ¢, sur les 40 % finaux du palier).

| Défaut | Mécanisme réel (écarts à la description ci-dessus) | Correction | Test | Réel, avant → après |
|---|---|---|---|---|
| **D4** corrigé | comme décrit : la garde d'octave (`regOct`) refusait toute la note la note juste, plus grave | garde à sens unique : une note proposée plus bas dont les partiels impairs 1, 3, 5 sont présents (seuil de `partialPresent`) est acceptée ; lâcher une anche ne fait jamais apparaître une fondamentale plus grave | 44 | P06 registre : couverture 0 → 44 %, 16' 0,75/1,82 → 0,05/0,21 ; P08 : note juste, 16' et 8' affichés |
| **D1** corrigé | k = 1 gardé par la boucle des collisions, ET l'amas de phase (±5 Hz) qui n'était coupé qu'aux autres voix du même groupe : il avalait la raie du 16', et la pente de phase lisait la plus forte. Aucun partiel fixé d'avance ne convient : sur P03, P04, P09 (ESPRIT), le rapport 16'/8' saute de −28 à +8 dB d'un partiel au suivant (formants) ; « le plus haut partiel » dégradait P03 de 0,09 à 1,9 ¢ | groupe marqué `octaveClash` ; `clusterRefine` coupe l'amas à mi-chemin des raies connues de l'autre anche ; `octaveFuse` lit le 8' sur ses partiels (base et stroboscope) séparés d'au moins 2 cases de la raie connue du 16', poids (A k)² ; sinon (fenêtre trop courte), base et raies distinctes du 16' en A², marqué M, ou la raie commune (erreur bornée par l'écart réel) | 45 | 8' : P04 0,21/0,38 → 0,01/0,04 ; P05 0,18/0,45 → 0,03/0,12 ; P09 1,70/2,99 → 0,29/0,90 (couv. 11 → 78 %) ; P03 0,09/0,21 → 0,07/0,11 ; P02 0,94 → 0,65 |
| **D7** corrigé | même cause que D1, vue après l'inversion | même correction | 46 | synthèse : 2,41 ¢ à 2,3 s → 0,06 ¢ dès 1,5 s |
| **D2** corrigé | le rejet harmonique à 8 ¢ (cause principale) ; la raie revendiquée de l'anche grave prenait la case du 4' dans l'appariement ; l'amas avalait cette raie (7 dB plus forte, 3,8 Hz plus bas). Le plancher n'y était pour rien sur ce son | rejet borné par la résolution (2 cases de la fenêtre dans la bande mesurée) ; raie revendiquée hors appariement pour une octave ajoutée ; amas coupé aux raies connues ; `rankReeds` garde le drapeau M | 47 | Auto-anches : P04 4' absent → 0,02/0,05 (couv. 0 → 100 %) ; P05 → 0,04/0,17 (0 → 100 %) ; octaves justes (P01, P07, P18) inchangées |
| **D6** corrigé | comme décrit : le plancher −25 dB comptait les traqueurs cachés ; l'anche était plus faible que ses propres partiels | le plancher compare des anches, chacune avec son partiel le plus fort | 48 | P15 Auto-anches : couverture 0 → 100 % |
| **D9** corrigé | comme décrit | une anche seule dans son groupe d'Auto-anches est lue comme en Automatique : partiels fondus en (A k)², porte 0,5 à 1,5 ¢ | 49 | P16 0,25/0,28 → 0,01/0,03 ; P15 0,02/0,09 ; médianes des basses en baisse (P07 0,26 → 0,15) |
| **D3** corrigé | comme décrit | en Automatique, une note grave (k ≥ 2) se mesure sur un partiel impair ; ses pairs ne comptent que s'ils concordent à 0,5 ¢, sinon ils déclenchent l'alerte | 50 | Automatique : P02 1,49 → 0,04 ; P03 1,12/1,32 → 0,04/0,14 ; P08 1,26 → 0,23 ; P09 1,41 → 0,10 ; P17 0,72/2,20 → 0,12/1,68 ; P04, P05, P06 enfin mesurés (0,03 à 0,09) |
| **D5** reste dans le moteur, contourné par l'interface | vérifié : `coarse.js` retient la période commune (rangs 2, 3, 4, 6… seulement) ; ET la NSDF, ancre d'octave, trouve elle aussi cette période (clarté 1,00) et remplace la valeur spectrale. Essai : « pas de raie aux rangs 1, 5, 7 → c'est une période commune, la note est 2 f0 » (les rangs plus hauts ne prouvent rien : la tolérance y atteint 5 %), plus « la NSDF ne remplace pas une période commune » : Automatique juste, mais Auto-anches garde 23 fantômes, et le test 31 casse : l'alerte « deux anches ? » sur une quinte venait justement de la mauvaise note. Il faut une alerte « quinte » (proposer Q, pas LM) côté interface (`ui/modes.js`). Essai retiré. **Contourné le 06/10 côté interface** (moteur inchangé) : alerte « quinte ? » | `ui/modes.js` (`quinteVue`, `alerteQuinte`, `creerAlertes`) : dans le spectre de l'image (`t.coarseSpectrum`), la plus grave des composantes fortes (à moins de 20 dB) et une autre à 3/2 (±35 ¢), rien aux rangs 1, 5, 7 de la période commune ; 4 images d'affilée ; en Automatique et Auto-anches ; « oui, registre Q », « non » ; passe devant « deux anches ? » | `modes.test.mjs` M 8 (vrai moteur) ; test 31 et `polyphonie.test.mjs` D5 inchangés | synthèse : Do4 −4 ¢ + Sol4 +3 ¢ en Automatique → « quinte ? », jamais « deux anches ? » ; après « oui » : −4,000 et +3,000 ¢ (≤ 0,12) ; 0 image sur une anche seule (Do2 à Do7, fondamental faible compris), une octave, un unisson, LMH, un accord, une quarte, une tierce, une sixte |

Ce qui bouge sans être une dégradation du moteur (tableau complet dans la PR) :
- P08 : la note était une octave trop haut (D4) ; l'étiquette « 16' » porte maintenant le vrai 16',
  9 à 13 dB plus faible, que la vérité elle-même ne trouve qu'une fenêtre sur deux (0,67 ¢).
- P03, P08 en Auto-anches : notes de 3 s, octave à 1,2 à 1,8 ¢ : le 4' est inséparable dans le temps
  de la note (il faut 2/(k δ) s) ; il manque, il n'est pas faux.
- Maxima qui montent de 0,03 à 0,10 ¢ (P01, P04, P09, P17 Auto-anches ; P10 Automatique) : images où
  la vérité se dédouble (ESPRIT coupe une raie en deux, ±0,5 ¢) ; les médianes baissent.
- P02 Automatique : pic de 2,6 ¢ au passage d'un vrai saut de 2,8 ¢ (soufflet) vers 2,9 s ; avant,
  toute la note était fausse de 1,5 ¢. P07 Automatique : 0,11 → 0,16 ¢, dans les ±0,4 ¢ où bouge la
  vérité d'une fenêtre à l'autre.
- Charge DSP (ms de calcul par seconde de son, LM, MMM, Automatique, Auto-anches) et
  `test/bench_poly.mjs` : inchangés.

### 4.2 Anche confondue : sa justesse quand même, avec sa marge (moteur v37, 06/10/2026)

Demande d'Ewen : « on peut quand même avoir la valeur de cette note-là, en termes de justesse ».
Le 8' confondu reçoit une estimation et une marge (`web/js/dsp/confondu.js`) ; sa mesure
(`fMeas`, `dCents`, `merged`) ne change pas, tout est dans des champs à part (`confondu`,
`fEstimee`, `centsEstimes`, `centsEstimesCible`, `margeCents`, `methode`, `signeConnu`).

**Physique.** Le 8' est à f8 = 2 f16 + δ. Sur son partiel k, sa raie et celle du 16' (2k f16) sont
à k δ Hz : la fenêtre de T s ne les sépare qu'au-delà de 2/(k δ) s. Le 16' est mesuré à part, sur un
partiel impair : sa raie est connue.

- **Par l'octave** : centre 2 f16, marge ±1/T (Hz, à la fondamentale du 8'). L'erreur du centre est
  exactement δ. Mesuré sur synthèse (7 800 images confondues, 8' de −10 à +6 dB, 16' au timbre riche
  ou pauvre) : |δ| T ≤ 0,82, jamais au-delà. La raie commune n'est pas un meilleur centre, contrairement
  à l'intuition « elle est entre 2 f16 et f8 » : la phase d'une somme de deux sinusoïdes proches
  déborde de cet intervalle (biais jusqu'à δ ρ/(1 − ρ), ρ = rapport des amplitudes) ; mesuré : 1,45 ¢
  d'erreur pour un 8' à 1 ¢ de l'octave. Limite : un 8' plus de 12 dB sous le 16' sur tous ses
  partiels n'est pas couvert (il faudrait 4/T).
- **Par le battement** : la bande du partiel k du 8', démodulée par la phase du 16' (lue sur son
  partiel impair m, multipliée par 2k/m : les partiels d'une anche sont verrouillés en phase ; la
  dérive du soufflet part avec), devient y_k(t) = g(t) (C_k + B_k e^(i 2π k δ t)) : un cercle autour de
  la raie du 16', parcouru à la vitesse k δ. La vitesse donne |δ|, le **sens de rotation donne le
  signe**, sur toute la note depuis l'attaque (8 s au plus), pas seulement la fenêtre. Moindres carrés
  (C_k, B_k linéaires, δ commun aux partiels, balayé), g(t) = enveloppe du 16'. Marge =
  √(A² + B² + S²) : A = 0,2 / (k_max T) (systématique : attaque, modulations qui ne sont pas communes),
  B = écart entre les deux moitiés de la note, ou entre la note et la fenêtre (un δ qui bouge),
  S = intervalle statistique à 95 % ; plus 0,1 ¢ pour la mesure du 16' (en quadrature).
- On garde l'estimation de plus petite marge. Le battement prend la main dès 1 s de son.
- **Passage à la mesure normale** : les premières images séparées sont parfois fausses de 1 à 15 ¢.
  L'anche reste dite confondue (1 s au plus) tant que sa mesure séparée sort de la marge de
  l'estimation : pas de saut. (v39 : la vraie cause, une raie séparée non confirmée, est corrigée à la
  source ; la tenue reste en garde-fou, § 4.3.)

**Synthèse** (`test/dsp.test.mjs`, tests 52 à 55 ; grille d'exploration : Ré#2, Fa2, La#2, La3 ;
8' à ±0,3, ±1, +3 ¢ de l'octave ; −10 à +6 dB ; dérives commune et différentielle, soufflet en
hauteur et en volume, bruit à 35 dB ; notes de 1,5 à 6 s ; 17 084 images confondues) :

| | Par l'octave (avant 1 s de son) | Par le battement |
|---|---|---|
| Vérité dans la marge | 100 % | 99,98 % (test 52 : 610/610) |
| Erreur au 95e centile | 3,0 ¢ | 0,09 ¢ |
| Marge (médiane) | ±14 ¢ (honnête : rien à dire si tôt) | 1,5 s : ±0,68 ¢ ; 3 s : ±0,14 ¢ ; 4,5 à 6 s : ±0,12 à 0,13 ¢ |
| Part de la confusion, en 1/T (test 53) | — | 0,76 ¢ vers 1,5 s, 0,125 vers 3 s, 0,052 vers 6 s |
| Signe | inconnu | juste dans 99,9 à 100 % des images à −10, −4, 0 et +6 dB ; dit connu dans 94 % ; jamais connu et faux |
| Passage à la mesure normale (test 54) | — | 236 passages, aucun saut hors de la marge d'avant |

**Réel** (`test/outils/confondu_poly.py`, registre LM, vérité ESPRIT sur la même fenêtre ; « raie
commune » = la valeur affichée jusqu'à la v36) :

| Passage | Images comparées | Estimation : erreur méd / max | Marge méd | Dans la marge | Raie commune : méd / max |
|---|---|---|---|---|---|
| P03 Ré#2 (8' à +1,6 ¢ de l'octave) | 11 | 0,14 / 0,28 ¢ | ±0,87 | 100 % | 0,14 / 0,62 ¢ |
| P08 Ré2 (8' 13 dB au-dessus du 16') | 15 | 0,54 / 1,10 ¢ | ±2,17, signe inconnu le plus souvent | 100 % | 0,09 / 0,86 ¢ |
| P09 Mi2 (8' à −1,3 ¢) | 12 | 0,20 / 0,62 ¢ | ±0,26 | 83 % | 0,95 / 1,44 ¢ |
| P17 Mi1 | 1 | 0,65 ¢ | ±5,8 | 100 % | 0,42 ¢ |

- P03 : fin de note +10,86 ±0,68 ¢ pour +10,61 vrais ; la première seconde, « par l'octave » ±16 à 32 ¢.
- P08 : quand le 8' domine de 13 dB, la raie commune est presque le 8' (ρ petit) et reste meilleure ;
  l'estimation est plus prudente (marge 2 ¢) mais juste dans sa marge. Piste : borner le biais de la
  raie commune par ρ. Fin de note : +8,45 ±0,70 ¢ pour +8,49 vrais. (Fait en v39, § 4.3 : ρ lu sur
  le cercle des points, pas sur l'ajustement à δ constant ; P08 0,54 → 0,28 ¢.)
- P09 : les deux images hors marge sont celles où la vérité ESPRIT saute de 0,5 ¢ d'une fenêtre à la
  suivante (85 ms plus tard, 94 % de son en commun : la vérité se dédouble, cf. § 4.1) ; la raie
  commune y était fausse de 1 à 1,4 ¢.
- Octave presque juste (P01, P07, P18) : ESPRIT ne sépare pas non plus (octave à moins de 0,6 ¢) ;
  l'estimation dit 8' +11,9 ±0,5, +12,9 ±1,4 et +12,7 ±0,7 ¢ pour un 16' à +12,5 / +12,6 / +12,5 :
  cohérent avec « octave juste à 0,6 ¢ près ».
- P02, P04 à P06 : quelques images confondues seulement, en début de note ou après un saut
  (« par l'octave », marge large) ; aucune vérité sur ces fenêtres.

**Interface.** Accorder : le chiffre est l'estimation, plus fin, contour en pointillé, et dessous
« ±0,14 ¢ · par le battement » (« · signe inconnu » si le sens n'est pas sûr) ; dans la tolérance sans
que toute la marge y tienne : « juste à ±2,6 ¢ près », couleur « proche », jamais le vert ; validée
seulement si |estimation| + marge < tolérance ; pastilles et témoins selon toute la marge. L'anche :
la carte lecture en fait autant. Le carnet et son CSV gardent la marge (`marge_cents`, `methode`).
Tests : UI 18, L 8, DONNÉES 9. `rejoue.mjs --images` : identique octet pour octet à la v36 sur les
18 passages et les 3 modes (54 sorties, 2 715 images, dont 212 avec un 8' « M » : aucun champ
existant ne change). Charge DSP sur un 16'+8' confondu de 8 s : 64,6 → 73,9 ms par seconde de son,
pire image 7 → 10 ms ; rien ne change quand aucune anche n'est confondue.

### 4.3 Saut à la séparation, 8' qui domine (moteur v39, 06/10/2026)

Deux défauts relevés au § 4.2 : juste après la séparation, la mesure séparée du 8' était parfois
fausse de 1 à 15 ¢ (l'écran gardait l'estimation 1 s pour masquer le saut) ; sur P08 (8' 9 à 13 dB
au-dessus du 16'), l'estimation était moins bonne que la raie commune.

**Saut à la séparation : le mécanisme.** Rejoué sur synthèse (grille `confondu_grille.mjs
separation` : Ré#2, Fa2, La#2, Mi3 ; 8' de ±0,3 à +7 ¢ de l'octave ; −10 à +13 dB ; deux timbres du
16' ; 280 notes, 12 864 images) et sur P03, P08, P09, partiel par partiel. Le 8' passait pour séparé
dès qu'UN partiel avait sa raie à 2 cases de celle du 16'. Or ce seuil prouve que la raie n'est
pas le 16', pas qu'elle est le 8' :
- une raie parasite (repli de la décimation, −30 dB, 20 Hz à côté) franchissait le seuil sur un
  partiel faible : La#3 à −0,3 ¢ de l'octave, 8' lu à −24 à −26 ¢ pendant toute la note
  (séparé dès le début : la tenue d'1 s ne s'appliquait même pas) ; P09 (430,89 s) : partiel 5 du
  8', 18 dB sous les autres, à 7,5 cases, lu +34 ¢ (caché par la tenue) ;
- la lecture de la raie commune, que le battement pousse au-delà de sa vraie place (dépassement
  de phase), franchissait le seuil sur un seul partiel quand la vraie raie n'en était qu'à 0,5 à
  1 case : Ré#3, −8,6 ¢ ;
- une raie fausse (partiel 7 accroché à −22 ¢, juste au plancher de −30 dB) entrait dans la
  fusion des partiels séparés : −0,8 ¢ pendant 0,3 s.

Hypothèses écartées : la fenêtre qui contiendrait encore des images d'avant la séparation (les
erreurs durent des secondes, et la raie juste, quand elle est confirmée, est bonne dès sa première
image) ; un traqueur qui partirait d'une fréquence fausse (le traqueur zoom n'a pas d'état : une
FFT par image) ; le Matrix Pencil (pas utilisé en registre). Le biais de la pente de phase à
2 cases (doc v37) existe, mais il ne pèse que sur la toute première image, et seulement avec une
fenêtre courte (0,34 à 1,4 s).

**Correction (à la source, `appariement.js`, `octaveFuse`).** Une anche est périodique : la raie
séparée d'un partiel n'est retenue que si un AUTRE partiel du 8', distinct de la raie du 16' (un
témoin), dit la même hauteur à leurs biais près (Hz, à la fondamentale : 1/(2kT) pour une raie
séparée, une case 1/(kT) pour un témoin pas encore séparé). Sinon l'anche reste confondue, avec son
estimation. Test 56 (échoue sur la v38 : 26,25 ¢ ; passe : 0,10 ¢).

| Lectures séparées du 8' (synthèse), erreur médiane / 95e centile / max (images au-delà de 1 ¢) | v38 | v39 |
|---|---|---|
| Première image | 0,04 / 0,77 / 26,3 ¢ (10) | 0,04 / 0,32 / 3,3 ¢ (3) |
| 0 à 0,4 s après | 0,05 / 0,23 / 26,2 (21) | 0,04 / 0,14 / 0,48 (0) |
| 0,4 à 1 s après | 0,05 / 0,19 / 24,1 (33) | 0,04 / 0,16 / 0,31 (0) |
| Après 1 s (plus de tenue) | 0,03 / 0,09 / 24,2 (81) | 0,03 / 0,08 / 0,51 (0) |

**La tenue d'1 s reste, comme garde-fou.** Reste un biais de 1 à 3,3 ¢ sur la toute première image
séparée (3 images sur 211), quand la fenêtre est courte (W de 32 à 128) ; sans tenue, 7 passages sur
192 sortiraient de la marge d'avant (jusqu'à 1 ¢). La tenue ne cache plus d'erreurs de 24 ¢ ; elle
couvre ce biais-là.

**8' qui domine (P08) : le mécanisme.** Sur P08, le 16' monte de 2,5 ¢ en 1,5 s sous un 8' qui ne
bouge pas : l'écart à l'octave δ change de signe pendant la note. Le battement suppose δ constant ;
sur synthèse (grille `derive` : Ré2, La#2 ; 16' qui monte ou descend de 0,3 à 0,8 ¢/s sous le 8' ;
−10 à +16 dB), sa marge ne contenait la vérité que dans 87 % des images (v38) : l'ajustement de la
note entière sortait de l'intervalle de ses deux moitiés (note −1,4 ¢, moitiés +0,5 et −0,2), et
B ne regardait que l'écart entre les moitiés. L'ajustement à δ constant sous-estime aussi ρ
(0,33 pour 0,55 vrais).

**Corrections (`confondu.js`).**
1. B compte l'écart entre la note entière et chacune de ses moitiés : la marge redevient honnête.
2. Estimation « par la raie commune » : quand le 8' domine un partiel (ρ = A16/A8 ≤ 0,5), la raie
   commune est le 8' à un biais près, borné par min(|δ| ρ/(1−ρ), 3 asin ρ/(2π k L)) (la pente de
   moindres carrés est une moyenne de la dérivée de phase, et un terme borné par asin ρ a une pente
   d'au plus 3 asin ρ/L), plus le bruit de la lecture. ρ est lu sur le **cercle** des points
   démodulés (centre = la raie du 16', rayon = celle du 8') : il ne suppose pas δ constant, il faut
   seulement que l'arc ait tourné (R̄ ≤ 0,8). Deux partiels forts au moins ; si les bornes sont
   justes, la vraie hauteur est dans chacun des intervalles : on donne leur intersection (centre,
   demi-largeur), rien si elle est vide. L'écran dit « par la raie commune ». Test 57 (échoue sur
   la v38 : 85,8 % dans la marge ; passe : 100 %).

| Synthèse, 8' confondu | v38 : dans la marge | v39 : dans la marge | Erreur méd v38 → v39 |
|---|---|---|---|
| δ qui bouge, −10 à +16 dB (4 865 / 4 942 images) | 87,0 % | 99,6 % | 0,23 → 0,20 ¢ (8' ≥ +6 dB : 0,23 → 0,18) |
| dont « par la raie commune » | — | 712 images, 100 %, 95e centile 0,10 ¢, marge méd ±0,16 | |
| δ constant, −10 à +13 dB (3 171 / 3 282) | 100 % | 100 % (raie : 204 images, 95e centile 0,06 ¢) | 0,04 → 0,04 ¢ |

À +16 dB avec un 16' au timbre pauvre, la note est lue une octave trop haut (16' invisible) : v38 et
v39 pareils, hors de ce travail ; ces images sont écartées.

**Réel** (`confondu_poly.py`, vérité ESPRIT sur la même fenêtre) :

| Passage | v38 : erreur méd / max, marge méd, dans la marge | v39 |
|---|---|---|
| P03 Ré#2 | 0,14 / 0,28 ¢, ±0,87, 100 % (11 images) | 0,09 / 0,22 ¢, ±0,47, 100 % (11) |
| P08 Ré2, mêmes 15 images | 0,54 / 1,10 ¢, ±2,17, 100 % | 0,28 / 1,10 ¢, ±1,35, 100 % |
| P08, toutes les images confondues | (15) | 0,40 / 2,66 ¢, ±1,86, 100 % (19) |
| P09 Mi2 | 0,20 / 0,62 ¢, ±0,26, 83 % (12) | 0,20 / 0,62 ¢, ±0,34, 83 % (12) |
| P02 Fa2 | aucune image confondue | 0,39 / 0,50 ¢, ±1,45, 100 % (2) |
| P17 Mi1 | 0,65 ¢, ±5,8 (1) | inchangé |

- P08 : 4 images de plus sont confondues (416,0 à 416,3 s) : la v38 y montrait un 8' « séparé » sur
  une seule raie non confirmée, 0,8 ¢ trop bas, sans marge ; la v39 montre l'estimation, ±5 ¢. Sur
  4 des 15 images, la raie commune passe devant le battement (±0,57 à ±0,60).
- P03 : la raie commune prend la main dès 197,5 s (±0,3 à ±0,5 au lieu de ±0,8 à ±1).
- P09 : inchangé ; la raie commune n'y est jamais prise (deux partiels forts où le 8' domine n'y sont pas réunis).

**Avant/après sur les 18 passages** (`avant_apres_poly.py`, 3 réglages) : tout est identique, sauf
P02 registre, 8' : une image, 0,65 → 0,76 ¢. C'est la valeur brute (`fMeas`) d'une image où le 8'
n'est plus dit séparé (sa raie séparée n'était pas confirmée) ; l'écran y montre l'estimation, à
0,28 ¢ de la vérité, ±1,03. `npm run test:poly` : sortie identique. Charge DSP (16'+8' confondu de
8 s, médiane de 5) : 69,5 → 68,7 ms par seconde de son, pire image 9 → 8 ms ; 8' qui domine :
63 → 63 ms.

## 5. Verdict

**Utilisable à l'établi aujourd'hui** (avec le registre juste choisi à la main) :
- une anche seule : 0,05-0,09 ¢ ;
- une quinte (registre Q) : ≤ 0,12 ¢, ≤ 0,26 ¢ autour d'une inversion ;
- le 16' d'une basse 16'+8' : ≤ 0,26 ¢ ;
- un unisson ouvert (MM) : l'anche forte ≤ 0,1 ¢, la faible à 0,5 ¢ près.

**Pas encore** (v30 ; corrigé en v33 sauf D5, contourné par l'alerte « quinte ? », cf. § 4.1) :
- le 8' d'une basse 16'+8' : 0,2 à 3 ¢ d'erreur (D1, D7), et des basses lues une octave
  trop haut sans rien dire (D4 ; 2 basses sur 11). Un luthier accorderait la mauvaise anche ;
- Auto-anches sur les basses (anche d'octave effacée, D2) et même sur une anche seule (D6, D9) ;
- Automatique sur plusieurs anches : mélange, l'alerte manque sous 1,5 ¢ d'écart (D3, D5).

**Après la v33** : le 8' d'une basse est juste dès que la fenêtre peut le séparer du 16'
(0,01 à 0,3 ¢ en médiane), et « confondu » avec une erreur bornée avant ; depuis la v37, le
8' confondu a quand même sa justesse, avec sa marge (±0,14 ¢ vers 3 s, par le battement, § 4.2) ;
depuis la v39, un 8' n'est dit séparé que si deux de ses partiels le confirment (plus d'erreurs de 8
à 26 ¢ à la séparation) et le 8' qui domine se lit sur la raie commune (§ 4.3) ; la note n'est plus
bloquée une octave trop haut ; Auto-anches montre l'anche d'octave et une anche seule à 0,01-0,02 ¢ ;
Automatique lit la note grave d'une basse sur ses partiels impairs (0,04 à 0,2 ¢). Reste D5 (quinte
en Automatique et Auto-anches) : jouer une quinte en registre Q. Depuis le 06/10, l'interface le
dit : alerte « quinte ? », « oui, registre Q » (une douzième seule, 3:1, ne se distingue pas d'une
anche seule dans le spectre : pas d'alerte ; essayée, elle sortait aussi sur des octaves et des MM).

Musette main droite à 3 anches, tremolo 8'+8' serré, 16'+8'+4' : **non jugés**, rien dans les
enregistrements (seule la synthèse les couvre, tests 23, 26, 38, 39 de `dsp.test.mjs`).

**Ordre des corrections** (phase 2, un test à la fois) :
1. D4 : la note une octave trop haut est l'erreur la plus dangereuse (silencieuse, toute la note).
2. D1 puis D7 : choisir le partiel du 8' sur l'écart RÉEL au partiel du 16', pas nominal.
3. D2 et D6 : seuils d'Auto-anches cohérents (choix du partiel et plancher), résolution en Hz
   au lieu de 8 ¢.
4. D3 : en Automatique sur une basse, ne pas mesurer sur un partiel pair ; alerte plus tôt.
5. D9 puis D5 : fusion de plusieurs partiels en Auto-anches ; vérifier qu'une fondamentale
   commune (quinte) a une énergie à elle.

## 6. Ce qu'il faut enregistrer (protocole de 20 minutes)

But : couvrir ce qui manque (musette main droite, 3 anches, 16'+8'+4', basses isolées) et avoir
une vérité par anche. Même accordéon, micro immobile à 15 cm du soufflet de la main droite puis de
la main gauche, pièce calme ; l'accordeur en mode recherche, « Exporter la session » (ZIP) à la fin.
Une feuille avec l'ordre, rien à dire au micro.

| Min | Quoi | Comment |
|---|---|---|
| 0-1 | silence 10 s, puis La4 en M | bruit de la pièce ; 8 s poussé, 8 s tiré, inversion sans silence |
| 1-9 | main droite : Fa3, La4, Mi5, La5 | pour chaque note : chaque anche seule si les registres le permettent (8', 16', 4'), puis MM, MMM, LM, LMH ; 6 s poussé + 6 s tiré, soufflet le plus régulier possible |
| 9-16 | main gauche : 4 basses (Mi, La, Ré, Sol, la plus grave d'abord), 2 contre-basses, 2 accords | registres de basse du plus petit (1 ou 2 voix) au plus grand (5 voix) : chaque voix ajoutée donne la vérité de la suivante ; 6 s + 6 s |
| 16-18 | attaques | La4 en MMM et une basse 16'+8' : 5 attaques franches de 3 s, silence de 1 s entre |
| 18-20 | soufflet vivant | La4 MMM : crescendo-decrescendo lent sur 8 s (hauteur selon la pression) |

Les registres d'une seule voix donnent la hauteur de chaque anche seule (vérité directe, sans
séparation) ; on mesure ensuite la même anche dans le registre complet. C'est le test qui manque.

## 7. Refaire ces essais

```
python test/outils/compare_poly.py test/outils/passages_poly.json <dossier des WAV> sortie.json --bruit
python test/outils/resume_poly.py sortie.json --frise
python test/outils/avant_apres_poly.py avant.json apres.json
python test/outils/confondu_poly.py test/outils/passages_poly.json <dossier des WAV> P03 P08 P09
node test/outils/confondu_grille.mjs separation | derive | stable
node test/outils/images.mjs son.wav '{"mode":"register","register":"LM"}' 345 350.4 [bruit_dB]
python test/outils/verite_poly.py son.wav 345.5 350.3
npm run test:poly
```

Python 3 avec numpy et scipy ; Node ≥ 18. Durée : 5 min pour les 18 passages, 15 min avec le bruit.
Sources : Hua et Sarkar (1990), IEEE Trans. ASSP 38(5), doi:10.1109/29.56027 (Matrix Pencil,
celui du moteur) ; Roy et Kailath (1989), cité plus haut (ESPRIT, la vérité terrain).
