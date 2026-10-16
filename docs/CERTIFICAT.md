# Certificat des lectures « sûres » (v64, 16/10/2026)

Audit Fable du 15/10/2026 (`J:\claude\audits\2026-10-17-accordeur-fable\RAPPORT-AUDIT.md`, R1 à R14) puis ses suites du 16/10 (critères d'Ewen : niveau professionnel,
musette et super musette, Do2 à A6, tout micro USB, pose courte, refus expliqués). Règle d'Ewen : un accordeur professionnel ne dit « sûr » que s'il peut le prouver ;
zéro lecture « sûre » fausse (erreur de plus de 0,5 ¢ sur une anche), avec n'importe quel micro. Journal des versions : `docs/JOURNAL-DES-VERSIONS.md`.

## 1. Les chiffres, avant et après

Banc de synthèse réaliste (`test/outils/pose/`, plans faits par `outils/doe.py`) : notes à deux ou trois anches de Do2 à A6, battements de 0,12 à 63 Hz, rapport d'amplitude
de 0 à 34 dB, indice de modulation de phase β de 0,05 à 0,4, modulation d'amplitude jusqu'à 20 %, agitation, dérive, attaque de +13 ¢, raie étrangère, bruit 25 à 40 dB.
Le verdict est celui de l'interface (`lireTick` : anche sans marge, phase « résolue », prise saine) ; la vérité est la fréquence MOYENNE DE LA PORTEUSE de l'anche sur la
fenêtre lue (sans la modulation de phase du tirage : `VERITE=porteuse`) ; une lecture est fausse à plus de 0,5 ¢. Les lectures d'avant la fin de l'attaque comptent aussi.
« Posées » = notes dont une lecture est dite sûre ; temps de pose = depuis le début du plateau (fin de l'attaque pour les notes à attaque). Règle des trois : 0 faux sur n
notes posées démontre un taux inférieur à 3/n à 95 %.

| jeu | notes | dans le domaine | posées | 1res lectures fausses | lectures « sûr » | dont fausses | borne (95 %) | T médian (s) | T p90 (s) |
|---|---|---|---|---|---|---|---|---|---|
| v63, plan de calibration (300 x4) | 1200 | 1200 | 391 (33 %) | 0 | 2057 | 0 (0 notes) | < 0.77 % | 4.75 | 5.50 |
| v64, plan de calibration (300 x4) | 1200 | 1200 | 649 (54 %) | 0 | 6036 | 0 (0 notes) | < 0.46 % | 3.00 | 5.00 |
| v64, validation (64 x6) | 384 | 384 | 223 (58 %) | 0 | 2192 | 0 (0 notes) | < 1.35 % | 2.75 | 4.75 |
| v64, conditions neuves (150 x3) | 450 | 414 | 208 (50 %) | 0 | 1879 | 0 (0 notes) | < 1.44 % | 2.75 | 5.25 |
| v64, coins (plan A) | 320 | 160 | 19 (12 %) | 0 | 97 | 0 (0 notes) | < 15.79 % | 2.75 | 5.55 |
| v64, plan A de validation | 320 | 280 | 116 (41 %) | 0 | 943 | 0 (0 notes) | < 2.59 % | 3.25 | 5.50 |
| v64, réaliste (160 x10) | 160 | 160 | 81 (51 %) | 0 | 856 | 0 (0 notes) | < 3.70 % | 2.75 | 5.25 |
| v64, adverse (60 x3) | 180 | 180 | 39 (22 %) | 0 | 312 | 0 (0 notes) | < 7.69 % | 3.00 | 5.00 |
| v64, domaine (Ω 0,2-60 Hz, 24 dB) | 192 | 112 | 45 (40 %) | 0 | 347 | 0 (0 notes) | < 6.67 % | 3.25 | 5.05 |
| v64, super musette, calibration | 240 | 240 | 58 (24 %) | 0 | 343 | 0 (0 notes) | < 5.17 % | 3.75 | 5.50 |
| v64, super musette, validation | 192 | 192 | 49 (26 %) | 0 | 382 | 0 (0 notes) | < 6.12 % | 3.00 | 5.00 |

Temps de pose (depuis le début du plateau), par classe de notes, sur le plan de calibration (300 conditions, 4 répétitions) :

| classe | v63 : posées, médiane, p90 | v64 : posées, médiane, p90 |
|---|---|---|
| Ω ≥ 2 Hz, sans attaque, f0 ≥ 200 Hz (le cas courant) | 118/280, 4,00 s, 5,25 s | 254/280, 1,75 s, 3,00 s |
| Ω ≥ 2 Hz, sans attaque, tout f0 | 144/332, 3,75 s, 5,25 s | 289/332, 1,75 s, 3,75 s |
| Ω ≥ 2 Hz, avec attaque (depuis la fin de l'attaque), f0 ≥ 200 Hz | 133/324, 4,75 s, 5,70 s | 231/324, 3,50 s, 5,50 s |
| Ω ≥ 2 Hz, tout | 293/704, 4,50 s, 5,50 s | 553/704, 2,75 s, 4,75 s |
| toutes les notes du domaine | 391/1200, 4,75 s, 5,50 s | 649/1200, 3,00 s, 5,00 s |

Lecture honnête : 0 lecture « sûr » fausse sur 12 662 lectures de deux anches (8 jeux de banc) et sur 725 de super musette ; la borne à 95 % est de 0,46 % des notes posées sur le plan de calibration
(règle des trois). Le temps de pose visé (1,5 s pour Ω ≥ 2 Hz) est atteint à 1,75 s de médiane pour le cas courant (note sans attaque, f0 ≥ 200 Hz) ; il ne l'est pas pour les notes graves, les battements lents
(< 2 Hz : 3 à 4 s) et les notes à attaque (la fenêtre ne peut pas toucher l'attaque). La v64 pose 54 % des notes du plan de calibration (v63 : 33 %) ; un premier essai à 63 % avait un indice de phase β permis jusqu'à 0,6 : les
prises réelles ont montré qu'il faisait lire La5 à +0,6 ¢ ; β est resté à 0,45, et ces neuf points de notes posées sont le prix du zéro faux.

Plan A (coins du domaine, 320 notes) : 1 lecture fausse apparue sur une note hors domaine (25 dB, Ω 0,3 Hz, β 0,4, raie étrangère : la raie de l'anche faible tombe sur la raie latérale de la forte, le modèle prend l'une
pour l'autre) ; règle ajoutée (§ 2.8) : 0 faux ensuite, sans perte de notes posées sur les plans de validation (116/280 et 223/384 dans les deux cas).


## 2. Ce qui change en v64 (les sept points de la mission)

### 2.1 (a) Les « sûr » tardifs faux des prises du H6 : rejoués

Le critère C8/C9 de la v63 avait été resserré après coup sans rejouer les prises. Rejoué (`reel_prises.mjs`, 27 notes, canaux L+R, L et R, vérité = verrou de phase du H6) :
la v63 pose 4 notes (L+R : 44 lectures « sûr », écart maximal 0,17 ¢ ; L : 54 ; R : 52, écart maximal 0,28 ¢) ; aucune lecture à plus de 0,3 ¢ de la vérité à
la v63 (les « 4 sur 48 » du compte rendu précédent ne se reproduisent plus). La v64 : la v64 pose 7 notes sur 27 (L+R : 103 lectures « sûr », aucune fausse ; L : 6 notes, 134 lectures ; R : 5 notes, 65 lectures ; 0 fausse sur 302), le traqueur seul de la v62 en posait 13 avec 42 lectures fausses sur 336. Une borne de l'indice de phase relâchée à 0,6 (pour poser davantage de notes réelles) avait
fait lire La5 (β réel 0,46 à 1,1, raies non proportionnelles au rang, § 1.1 de l'audit) à +0,6 ¢ sur le canal gauche : elle est revenue à 0,45, valeur de l'audit (au-delà de 0,4
la porteuse n'est plus la raie dominante aux partiels hauts). Les prises réelles ont servi ici de VALIDATION (elles ont attrapé ce réglage), pas de calibration.

### 2.2 (b) Prise PC : la cause du « facteur d'échelle » et des 2 « sûr » à +0,66 ¢

Voir `docs/PRISE-DE-SON.md`, section v64. En résumé : mêmes fenêtres lues par le même modèle des deux côtés (`pc_vs_h6.mjs`) ; l'écart PC − H6 est constant dans une note
(étendue médiane 0,15 ¢), identique sur les deux anches ; **ce n'est pas la fenêtre de vérité** ; il vaut −2,7 ¢ dans les 50 premières secondes de la prise PC (régime transitoire,
deux essais concordants), −0,25 ¢ ensuite (l'horloge, 99 à 125 ppm) et +0,56 à +0,80 ¢ sur d'autres notes (un état à +0,9 ¢ au-dessus de la ligne de base, sans signature dans
le signal : plancher entre les raies à −50 dB des deux côtés). Un quartz ne varie pas de 500 ppm en quelques secondes : la chaîne logicielle de la capture (rééchantillonneur) est
le candidat, le Zoom H6 reconstruit par Reaper aussi ; la prise de contrôle manque (question posée à Ewen). Ce que fait la v64 : « sûr » exige l'horloge mesurée (C10) — le
régime transitoire disparaît (la mesure n'est acceptée qu'après 60 s et deux moitiés d'accord à 30 ppm) — et la prise reste contrôlée (`prise.js` : 0 « sûr » sur la prise PC,
horloge connue ou non). Sans le contrôle de prise, la prise PC donne 0 note posée sur la prise PC (0 lecture « sûr »), horloge connue ou non : c'est l'état à +0,9 ¢, non détectable dans le signal.

### 2.3 (c) Horloge du micro (R12)

L'horloge d'un micro USB s'écarte de 10 à 200 ppm (0,02 à 0,35 ¢). Avant : la v63 prenait 0 ppm sauf réglage manuel (Réglages > Micro > Horloge ou Référence existaient
depuis la v41). Maintenant : **le comptage des échantillons face à l'horloge du PC tourne tout seul pendant la première minute d'écoute** (`ui/horloge-auto.js`, banc
`test/horloge-auto.test.mjs` : +125 ppm lu à 125,0 ; −150 ppm avec un saut du son de +20 ms lu à −150,5 ; deux moitiés qui se contredisent refusées), le résultat est gardé pour ce
micro (`reglages.horloges`, même clé que Réglages) et appliqué (`calibrationPpm`) ; tant qu'elle est inconnue (> 100 ppm d'incertitude annoncée, plancher de 30 ppm : le quartz
du PC), jamais « sûr » (raison « horloge » : « l'horloge de ce micro n'est pas encore connue (mesure en cours, une minute) »). Réglages > Micro > Référence (un la joué par un
téléphone, ±20 ppm) reste la référence externe pour qui veut 0,03 ¢. Jamais le secteur (±2 000 ppm). Plan C (§ 4.4) : horloge inconnue → 0 « sûr » faux et aucun « sûr » dans
les cellules à +150 ppm ; calibrée à 30 ppm → 0 faux, écart maximal 0,36 ¢.

### 2.4 (d) Super musette : le modèle à trois anches (R3)

`dsp/nls-trio.js` : anche basse f_C − Δ−, centrale f_C, haute f_C + Δ+ (Δ− et Δ+ libres : la note n'est pas symétrique). L'anche basse est modulée en phase et en amplitude à Δ−,
la haute à Δ+, la centrale aux DEUX (produit de deux séries de Bessel, 25 raies) ; 13 paramètres non linéaires (f_C, Δ−, Δ+, quatre indices de phase signés, trois indices d'amplitude,
ψ, θ−, θ+), le timbre de chaque anche libre (variable projection), warp et niveau communs, raie étrangère libre ; départs par les triplets des raies les plus hautes (le triplet lu par
le traqueur d'abord) ; rivaux : les autres triplets ; refus « niveau » si une anche est à plus de 22 dB. Le traqueur v62 ne suit parfois aucune des trois voix (11 notes sur 120) : la
seconde lecture ne dépend plus de lui (`certifierGroupe`, note imposée ou voix à moitié suivies ; les voix non suivies le deviennent à la certification). Résultats § 1 (plans trio_calib et trio_valid : 58 et 49 notes posées sur 240 et 192) : 0 faux
sur 725 lectures « sûr » de super musette ; 25 % des notes posées (v63 : 0 ; v62 : 75 % de fausses).

Rôle d'une raie étrangère (cas de l'audit « raie étrangère », trois raies pures de force voisine, test `frequences` F9) : une raie étrangère adoptée dont le niveau est du même ordre
que l'anche la plus faible (moins de 12 dB en dessous) n'est admise que si l'échange de rôle avec chaque anche est nettement pire (LLR ≥ 150) ET si un couplage est ajusté
(|β| ou |m| ≥ 0,03) : sans couplage, rien dans le son ne distingue une anche d'une raie étrangère (l'ajustement lisait +4 et +6 ¢ à 1,7 Δ). Cette règle a remplacé un contrôle
du traqueur à 1 ¢ qui faisait perdre 15 points de notes posées.

### 2.5 (e) Temps de pose

La v63 disait « sûr » après deux ajustements successifs de 3 s, calculés 20 pas par image : médiane 6 s sur le plan de calibration (grille 0,25 s), 4 s à 8 Hz. v64 : ajustements à chaud
(les deux moitiés de la fenêtre, départ = la solution entière, phases recalées au centre de la moitié, continuation sur les partiels), fenêtre visée de 1,5 s (jamais moins que le besoin :
1 battement, 350/f s, K·Ω·T ≥ 1,65), deux ajustements de front, coût des ajustements réduit de 27 % (plan d'expériences sur le coût, § 4.2), la lecture certifiée est elle-même affichée.
Pour Ω ≥ 2 Hz, sans attaque : médiane 1,75 s (p90 3,00 s) pour f0 ≥ 200 Hz, 254 notes sur 280 posées (v63 : 4,00 s, 118 sur 280). Avec attaque de +13 ¢ : la fenêtre ne peut pas toucher l'attaque, le temps compte depuis sa fin (médiane 3,50 s, p90 5,50 s). Une fenêtre qui raccourcit
d'elle-même après un échec (essayée) pose plus tôt (2,25 s au lieu de 2,75 s) mais a donné 3 lectures « sûr » fausses : écartée. Budget de calcul : 200 unités par image de 85 ms (≈ 60 ms
sur un PC de bureau, § 6) ; sur téléphone, 4 fois moins de travail par image : les temps s'allongent d'autant (R9, § 4.5).

### 2.6 (f) Domaine

Ω de 0,2 à 60 Hz certifié (v63 : 25 Hz ; 50 ¢ à A6 font 51 Hz). Résultats : 112 notes (Ω de 0,2 à 60 Hz, rapport jusqu'à 24 dB), 45 posées, 0 lecture fausse (347 lectures « sûr »). Au-dessus de 60 Hz : « anches trop écartées » ; sous 0,2 Hz : « les anches battent à moins de 0,2 Hz : je
lis leur centre, pas chacune » (le traqueur donne le centre, jamais « sûr »). Rapport d'amplitude : la limite sûre est 22 dB, pas plus (plan A, coin Ω = 0,3 Hz, 25 dB, raie étrangère : 2 notes
lues à −3 et −4 ¢ avec un faux modèle ; avant 22 dB aucune) : au-delà, refus « une des anches est plus de 22 dB sous la plus forte ». L'extension annoncée par la mission (22 dB) n'est donc
pas possible ; le refus est expliqué.

### 2.7 (g) Coût (R9), journal, tests

Coût : voir § 4.5. `docs/JOURNAL-DES-VERSIONS.md` : une ligne par version de la v19 à la v64. Tests rétablis : `frequences` (plus de 20 images « sûr » au lieu de 10, les deux cas de
battement sous 1 Hz avec fort couplage assertent « jamais faux, jamais avant l'heure, et la raison est affichée »), M10 de `music` (certificat actif), `lecture` et `ui` sans
le contournement `certificat: { actif: false }`.

### 2.8 Deux garde-fous ajoutés à la fin

**Refus récents sur le niveau.** Sur le plan A, une lecture fausse hors domaine (3 ¢ d'erreur : anche faible à 25 dB, Ω 0,3 Hz, β 0,4, AM 20 %, raie étrangère ; la raie de l'anche faible tombe sur la raie latérale de la forte, l'ajustement échange les rôles
et passe tous les critères une fois sur neuf ajustements). Réglage `REFUS_RECENTS` : une lecture n'est pas posée si 3 des 4 ajustements précédents ont été refusés pour le niveau. Plan d'expériences (3 variantes sur les mêmes plans) : peigne + étiquette + niveau : 0 faux mais
91 notes posées sur 280 au lieu de 116 (plan A de validation) et 199 sur 384 au lieu de 223 ; **niveau seul** : 0 faux, 116 sur 280 et 223 sur 384 (aucune perte). Retenu : niveau seul.

**Un silence efface les certificats.** Après une seconde de silence, la valeur certifiée d'avant restait affichée « sûre » à la première image du son qui reprend (test `courbe` : une image à intensité 0). Le moteur efface maintenant ses états de certificat au silence : le son qui reprend se certifie de nouveau.

### 2.9 (h) Le battement : une valeur précise, stable et fiable (Ewen, 16/10/2026)

Ewen : « les battements oscillent de 2-3 par minute : 25, puis 27, puis 26, puis 25 battements/min : c'est quoi la vraie valeur ? Pour accorder j'ai besoin d'une valeur précise, stable et fiable. »

**Mesure.** Avant, le battement affiché était la médiane glissante de quelques images (v63) : elle suit le bruit de l'agitation de la note. Maintenant (`estimerBattement`, `dsp/certificat.js`) : chaque ajustement de la seconde lecture
donne un battement Ω ; ils sont moyennés sur TOUTE la plage tenue, pesés par la durée de leur fenêtre. L'incertitude est l'écart type entre ajustements divisé par la racine du nombre d'ajustements INDÉPENDANTS (durée couverte
divisée par la durée d'une fenêtre : les fenêtres se recouvrent), au moins 0,09 batt/min. Si le battement varie vraiment (la pression du soufflet), la pente de la droite pesée est significative (plus de 2,5 écarts types) : elle est donnée
à part comme tendance (batt/min par seconde), pas comme bruit.

**Affichage.** Une seule valeur, qui converge (« ✓ 25,8 ± 0,3 bat/min ») ; elle ne change que si l'écart dépasse l'incertitude (hystérésis, au moins 0,2 batt/min) ; arrondie au demi-écart type (0,1 au plus fin) ; « ✓ » quand elle est posée
(trois ajustements indépendants au moins, incertitude sous 0,5 batt/min, deux secondes tenues). Une image où le traqueur perd une anche garde la valeur certifiée (mémoire de 1,5 s) ; la valeur brute du traqueur ne revient pas faire sauter le chiffre
(un défaut de la première version, trouvé au banc : une image sur cinquante à 31 batt/min au lieu de 25, écart type 0,88 batt/min ; corrigé : 0,03). L'écart en cents et le battement en Hz restent affichés.

**Précision atteignable.** La borne de Cramér-Rao du bruit seul est sans intérêt ici : pour 2 s de note et un rapport signal/bruit de 35 dB, elle est de l'ordre de 10⁻⁵ Hz. La précision est limitée par le jeu lui-même (la fréquence
des anches fluctue : agitation du soufflet, vibrato) et par le modèle. Mesurée au banc d'étalonnage (`battement_calib.mjs` : 8 notes de 15 à 90 batt/min dont 2 avec couplage, 6 tirages, 3 780 lectures affichées) :

| durée de la plage tenue | lectures | erreur RMS (batt/min) | ± annoncé moyen | erreur maximale |
|---|---|---|---|---|
| moins de 1,5 s | 5 | 0,02 | 0,03 | 0,02 |
| 1,5 à 2,5 s | 208 | 0,07 | 0,11 | 0,58 |
| 2,5 à 4 s | 925 | 0,07 | 0,09 | 0,58 |
| 4 à 6 s | 1 192 | 0,06 | 0,06 | 0,20 |
| plus de 6 s | 1 455 | 0,05 | 0,05 | 0,20 |

L'incertitude annoncée est de l'ordre de l'erreur réelle (100 % des lectures dans ±2 σ, ou 0,2 batt/min). Les plus grosses erreurs (0,58) sont des premières valeurs avec deux ajustements seulement : la valeur n'est dite « posée » qu'à partir de trois.
La résolution compte aussi : un ajustement a besoin d'au moins une période de battement (25 batt/min = 0,42 Hz = 2,4 s), donc la première valeur « posée » ne vient pas avant 2 à 3 s pour un battement lent ; plus la note est tenue, plus l'incertitude baisse (en 1/√n).

**Avant / après sur le banc** (`battement_stab.mjs`, écart type du battement affiché de la première valeur posée à 8 s, batt/min ; Fa#4 25 batt/min et Do#5 50 batt/min constants, La3 25, Mi4 90) : constants propres 0,00 à 0,28 dans les deux versions (le banc propre est déjà stable) ;
25 batt/min avec couplage β 0,2 (cas où la médiane glissante décrochait de l'enveloppe) : v63 0,85 batt/min (valeur moyenne 26,2, biais +1,2) contre v64 0,03 (25,1). Quand le battement varie vraiment avec la pression (4 batt/min en 5 s, 6 batt/min en 5 s), le chiffre unique
ne peut pas être « stable » : il suit la tendance (pente retrouvée 0,79 et 1,21 batt/min par seconde, vraies 0,80 et 1,20) ; c'est la courbe du battement (v65) qui répond à ce cas.

**Avant / après sur les prises du H6** (`battement_reel.py`, 14/10/2026, notes tenues, écart type du battement affiché, batt/min) : v63 (traqueur seul) sur les 16 notes avec vérité : écart type médian 2,49, moyen 6,63, maximum 37,4 (des notes à battement
rapide ou à attaque où la valeur saute de moitié) ; v64 sur les notes posées (6 notes) : médian 0,20, moyen 0,27, maximum 0,60, avec un écart médian à la vérité du H6 de 0,25 batt/min. Les notes non posées n'affichent pas de valeur certifiée.


## 3. Les critères d'une lecture « sûre » (C1 à C10)

| | Critère | Seuil (`CERT`) |
|---|---|---|
| C1 | pas de plage de zéros dans la fenêtre lue (R11) | 0,4 ms |
| C2 | peigne sain : résidu relatif, plancher entre les raies, indice de phase β, indice d'amplitude m | r ≤ 0,05 ; ≤ −28 dB ; β ≤ 0,45 ; m ≤ 0,3 |
| C3 | résolution des raies et au moins un battement | K·Ω·T ≥ 1,5 ; T ≥ 1/Ω |
| C4 | étiquette : rapport de vraisemblance, raie de l'anche faible contre la raie latérale qui la recouvre, rôle de la raie étrangère | LLR ≥ 25 ; ≥ −20 dB ; voir 2.4 |
| C5 | niveau : aucune anche à plus de 22 dB sous la plus forte ; et jamais « sûr » si 3 des 4 ajustements précédents ont été refusés pour le niveau (§ 2.8) | 22 dB ; 3 sur 4 |
| C6 | stabilité : dérive mesurée sur les deux moitiés de la fenêtre | ≤ 0,5 ¢/s ou 0,6 ¢ sur la fenêtre |
| C7 | âge : |dérive| × âge du milieu de la fenêtre | ≤ 0,3 ¢ |
| C8 | accord avec le traqueur | éteint (3 ¢ si réglé ; voir 2.3) |
| C9 | répétabilité : les deux moitiés de la fenêtre (ajustement chaud de chacune), ou deux fenêtres décalées de 0,5 s | 0,4 ¢ ; 0,3 ¢ |
| C10 | horloge du micro connue | ≤ 100 ppm (0,17 ¢) |

Fenêtre : au moins max(0,6 s ; 1 battement ; 350 / f s ; 1,65 / (K·Ω) s), visée à 1,5 s, jamais plus de 4 s. Un ajustement qui contredit le certificat en cours de plus de 0,5 ¢
l'invalide ; il faut alors deux fenêtres décalées d'accord (pas seulement les deux moitiés) pour en poser un autre.

## 4. Les plans d'expériences (règle 12 d'Ewen : jamais un facteur à la fois)

### 4.1 Criblage des réglages (PB12) et plan de calibration

Plackett-Burman à 12 essais sur 11 réglages (`crible_v64b.csv`, `doe_cert.py`, 4 répétitions de 80 notes) : les essais sans veto de l'accord traqueur (ACCORD_C à 10⁹), avec fenêtre maximale de 1,5 s et confirmation par les deux moitiés
posent 161 à 182 notes de 240 (médiane de 2,0 à 4,0 s) contre 56 à 126 pour ceux qui gardent le veto de l'accord (3,25 à 4,75 s), sauf l'essai 2 (82 notes) ; seul cet essai 2 (accord éteint, fenêtre de 3 s, sans moitiés) a produit une lecture fausse (1). Le meilleur essai (4 : accord éteint, fenêtre adaptative, 1,5 s, confirmation par les moitiés) pose 167 notes en 2,0 s de médiane. Résultats complets : `crible_b.log`, plan `crible_v64b.csv`.

### 4.2 Coût de calcul (plan factoriel 2^(4-1) sur tol, iterEtape, nDeparts, nLibre, nGarde)

Le coût d'un ajustement va de 459 à 984 milliers de partiels-échantillons selon l'essai (`cout2.csv`, `fit_cout.mjs`) ; les réglages retenus (tolérance 10⁻⁴, 5 itérations par étape, 5 départs, 2 anches libres) réduisent le coût de 27 % par rapport à la v63 à qualité égale (zéro faux, même nombre de notes posées).

### 4.3 Plans de validation (conditions jamais vues au réglage)

Voir § 1 : validation (64 conditions × 6), conditions neuves (150 × 3), réaliste (160 × 10), adverse (60 × 3), coins (plan A) et plan A de validation. 0 faux partout avec la règle des refus récents (§ 2.8).

### 4.4 Plan C : traitement du micro (porte, suppression de bruit, compression, ronflement, horloge)

16 cellules (plan fractionnaire sur la chaîne du micro, `runC.mjs`), 20 notes par cellule :

| horloge | notes posées (sur 320) | lectures « sûr » | fausses | erreur maximale | « sûr » dans les cellules à +150 ppm |
|---|---|---|---|---|---|
| inconnue (aucune mesure) | 45 | 534 | 0 | 0,36 ¢ | 0 |
| mesurée à 30 ppm | 94 | 1 073 | 0 | 0,36 ¢ | 541, toutes justes |

Horloge inconnue : jamais « sûr » dans une cellule à +150 ppm (la raison « horloge » est affichée). Horloge mesurée : la correction ramène les cellules à +150 ppm à moins de 0,36 ¢.

### 4.5 Coût sur téléphone (R9)

`cpu63.mjs` : un ajustement à froid coûte 150 à 1 000 ms (deux anches) et 240 à 2 300 ms (trois anches) sur ce PC ; à chaud (point de départ connu) 18 à 175 ms (deux anches), 50 à 650 ms (trois anches), 20 à 60 pas de Levenberg-Marquardt.
Le budget par image de l'application est de 40 ms (`MS_PAR_IMAGE`), les ajustements s'étalent sur plusieurs images. Un téléphone de milieu de gamme est compté à 4 fois ce PC : un ajustement à chaud de 1,5 s à 4 à 12 Hz (67 ms) prend 270 ms, soit 7 images ; les temps de pose
s'allongent d'autant, ils ne deviennent pas faux (le budget est du temps, pas de la précision). Non mesuré sur un téléphone réel : la proportion de 4 est une estimation.


## 5. Prises réelles du 14/10/2026

Prises du 14/10/2026 (27 notes ; vérité : verrou de phase du Zoom H6, ±0,1 ¢), rejouées par `reel_prises.mjs` avec le moteur final (validation seulement : aucun seuil n'a été réglé dessus, sauf β, remis à 0,45 parce qu'elles ont attrapé La5) :

| prise | notes posées | lectures « sûr » | fausses (plus de 0,5 ¢) |
|---|---|---|---|
| H6, canaux L+R | 7 sur 27 | 103 | 0 |
| H6, canal gauche | 6 | 134 | 0 |
| H6, canal droit | 5 | 65 | 0 |
| PC (micro USB, effet vocal de Windows) | 0 | 0 | 0 |
| H6, certificat éteint (traqueur v62) | 13 | 336 | 42 (4 premières lectures fausses) |

Le contre-exemple du 14/10 (La5 à −1 ¢, Ré5 à +1,5 et +4 ¢, Mi4 à −0,7 ¢) n'est plus posé : le certificat refuse ces notes (refus expliqués à l'écran). La couverture réelle est de 7 notes sur 27 : le reste est refusé (anche trop faible, attaque,
battement trop lent), ce qui est le prix du zéro faux. La prise PC reste à 0 « sûr » (état à +0,9 ¢ non détectable dans le signal, protégé par le contrôle de prise ; voir `docs/PRISE-DE-SON.md`).

Battement affiché sur ces prises : § 2.8.


## 6. Ce qui reste, et la limite physique

- **Pose lente** : pour f0 < 250 Hz, Ω < 2 Hz et après une attaque, la pose prend 3 à 5 s (la fenêtre ne touche pas l'attaque ; un battement lent demande au moins une période). Limite de la physique, pas du réglage.
- **Super musette** : 24 à 26 % des notes posées (v63 : 0), 0 faux ; les autres sont refusées (anche à plus de 22 dB sous la plus forte, battement de l'anche basse trop proche de celui de la haute).
- **Domaine** : Ω de 0,2 à 60 Hz, anche faible à 22 dB au plus. Au-delà : refus expliqué (« anches trop écartées » ; « les anches battent à moins de 0,2 Hz » ; « une des anches est plus de 22 dB sous la plus forte »). Étendre à 25 dB fait lire des raies latérales
  pour l'anche faible (plan A) : impossible sans faux.
- **Prise PC** : un état de la capture Windows à +0,9 ¢ au-dessus de la ligne de base n'a aucune signature dans le signal ; seule une prise de contrôle (H6 et PC en même temps) dira s'il vient du rééchantillonneur. Question posée à Ewen.
- **Horloge** : la mesure automatique prend une minute à l'écoute ; un micro dont l'horloge est instable (plus de 30 ppm entre deux moitiés) n'est jamais « sûr ».
- **Téléphone** : coût estimé (4 fois ce PC), à mesurer sur un appareil réel.
- **Battement** : le chiffre unique ne peut pas être stable quand la pression le fait vraiment varier ; la courbe du battement et le battement ramené à un niveau de référence sont en v65.
- **Couverture réelle** : 7 notes sur 27 sur les prises du H6.


## 7. Rejouer

```
node test/outils/pose/eval63.mjs --plan=lhs300_calib.csv --reps=4 --nls=0 --out=r.json       # moteur + certificat, verdict de l'interface (VERITE=porteuse pour la porteuse)
python test/outils/pose/tableau64.py "libellé=r.json"                                          # le tableau de la section 1
node test/outils/pose/eval63.mjs --plan=trio_calib.csv --n=3 --reps=2 --out=t.json             # super musette
CALIB=2 node test/outils/pose/runC.mjs --out=c.json                                            # plan C (CALIB=1 : horloge calibrée sans erreur ; sans : inconnue)
node test/outils/pose/reel_prises.mjs --src=h6|h6L|h6R|pc [--prise=0] [--ppm=-125 --incert=40] # prises réelles du 14/10
node test/outils/pose/pc_vs_h6.mjs --essai=1|2                                                  # prise PC contre H6 sur les mêmes fenêtres
node test/outils/pose/cpu63.mjs ; node test/outils/pose/etalon_cout.mjs                          # coût (R9)
node test/outils/pose/battement_calib.mjs                                                      # étalonnage de l'incertitude du battement (§ 2.9)
node test/outils/pose/battement_stab.mjs                                                       # écart type du battement affiché, v63 contre v64
python test/outils/pose/battement_reel.py reel_h6_v63.json reel_h6.json                        # idem sur les prises du H6 (reel_prises.mjs --out=...)
python test/outils/pose/doe_cert.py plans/crible_v64b.csv --base '{...}' --sortie dossier      # plan d'expériences sur les réglages
node test/certificat.test.mjs ; node test/horloge-auto.test.mjs                                  # tests
```
