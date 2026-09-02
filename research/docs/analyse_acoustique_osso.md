# Analyse acoustique computationnelle de deux pièces du duo OSSO
### Transposition électronique du couple de sonneurs : approche par descripteurs de signal

> Étude annexe au manuscrit *Conceptual accordion design*. Script reproductible :
> [`../scripts/analyse_osso.py`](../scripts/analyse_osso.py). Références
> bibliographiques : [`references.bib`](references.bib). Les enregistrements
> analysés **ne sont pas versionnés** (droits d'auteur) — voir §Annexe A.

---

## Résumé

Cette étude propose une analyse acoustique computationnelle de deux pièces du duo breton OSSO (*Oscillateurs Sonneurs*), formation qui transpose le dispositif traditionnel du couple biniou-bombarde à un instrumentarium électronique analogique. À partir de descripteurs spectraux, de l'analyse de modulation d'enveloppe et de mesures effectuées sous Praat, nous montrons que : (1) la stéréophonie encode une répartition fonctionnelle des rôles instrumentaux, la basse monophonique étant strictement centrée ; (2) les modulations d'amplitude sont verrouillées sur la grille métrique avec une précision inférieure à 0,3 %, révélant une synchronisation systématique des LFO sur la pulsation de danse ; (3) une ouverture progressive de filtre statistiquement significative structure l'une des deux pièces sur toute sa durée (+5,17 Hz/s, R² = 0,298, p < 0,001) tandis qu'elle est absente de l'autre, indiquant un choix dramaturgique différencié plutôt qu'une signature de groupe. Nous montrons enfin que l'analyse du spectre de modulation permet de corriger une erreur d'octave métrique commise par les algorithmes standards d'estimation de tempo.

**Mots-clés** : musique traditionnelle bretonne, fest-noz, synthèse analogique, descripteurs acoustiques, spectre de modulation, Praat, MIR

---

## 1. Contexte et problématique

### 1.1 Le couple de sonneurs et sa transposition

La pratique bretonne du *couple de sonneurs* associe deux instruments aux fonctions complémentaires : la bombarde, hautbois populaire au timbre perçant qui porte la mélodie, et le biniou kozh, cornemuse dont le chalumeau double cette mélodie à l'octave supérieure tout en maintenant un bourdon continu. Cette configuration produit une texture dense, légèrement battante du fait des écarts d'accord entre les deux instruments, et une continuité sonore permise par la réserve d'air du sac — dispositif conçu pour la sonorisation acoustique du bal en plein air.

Le duo OSSO revendique explicitement cette filiation : leur dénomination — *oscillateurs sonneurs* — substitue au terme organologique traditionnel celui de l'électronique analogique, tout en conservant la fonction. La question posée ici est celle des moyens acoustiques concrets de cette transposition : quels paramètres du signal assurent la continuité fonctionnelle avec le modèle traditionnel, et quels paramètres relèvent au contraire de l'idiome électronique ?

### 1.2 Pertinence pour l'étude de l'accordéon diatonique

Cette question intéresse directement l'organologie de l'accordéon dans les musiques à danser. L'accordéon partage avec le biniou deux propriétés déterminantes : la production sonore par anche libre alimentée par un réservoir d'air, autorisant des tenues indéfinies, et la capacité polyphonique permettant de superposer mélodie et accompagnement. Il occupe donc structurellement une position intermédiaire entre les deux rôles du couple traditionnel. Comprendre comment un dispositif électronique redistribue ces rôles fournit un point de comparaison pour analyser les stratégies de l'accordéoniste en formation réduite.

---

## 2. Corpus et méthodologie

### 2.1 Corpus

| | Pièce 1 | Pièce 2 |
|---|---|---|
| Titre | *Ordre étant* | *Duderc'h* |
| Danse | Hanter-dro | Scottish |
| Durée | 296,9 s | 240,4 s |
| Source | Diffusion Bandcamp | Diffusion Bandcamp |

Les deux pièces constituent l'intégralité du matériel diffusé publiquement par le duo au moment de l'étude. Cette taille de corpus (n = 2) interdit toute généralisation statistique et impose de traiter les résultats comme des observations de cas, non comme des propriétés établies du style.

### 2.2 Instrumentarium documenté

La fiche technique du duo permet d'identifier partiellement le dispositif :

- deux synthétiseurs repris en paire stéréophonique (modèles non spécifiés) ;
- un **Moog Minitaur**, synthétiseur analogique monophonique de basse, à filtre en échelle ;
- un **Boss RC-505 mkII**, station de bouclage assurant la couche rythmique ;
- une console Behringer XR18 avec compression insérée sur chaque ligne.

Cette documentation est essentielle : elle transforme certaines inférences acoustiques en vérifications, et permet d'attribuer les composantes du signal à des sources identifiées.

### 2.3 Chaîne d'analyse

L'analyse a été conduite en Python (librosa 1.0.0 [McFee *et al.* 2015], parselmouth 0.4.7 [Jadoul *et al.* 2018] interfaçant Praat [Boersma & Weenink], scipy, numpy). Les fichiers ont été décodés à 44 100 Hz en préservant la stéréophonie, puis décomposés en composantes *mid* (M = (L+R)/2) et *side* (S = (L−R)/2).

Descripteurs calculés :

- **Spectraux** : centroïde, rolloff à 85 %, largeur de bande, platitude spectrale, répartition d'énergie en neuf bandes.
- **Temporels** : séparation harmonique/percussive (HPSS par filtrage médian [Fitzgerald 2010], marge 3,0), détection d'attaques, estimation et stabilité du tempo (suivi de battement par programmation dynamique [Ellis 2007]).
- **Praat** : rapport harmonique-sur-bruit (HNR, méthode d'autocorrélation croisée [Boersma 1993]), intensité, suivi de formants (méthode de Burg, 4 formants, plafond 5 000 Hz).
- **Modulation d'enveloppe** : transformée de Fourier de l'enveloppe d'énergie, calculée séparément sur quatre bandes de fréquence.
- **Tonalité** : corrélation du profil chroma avec les profils de Krumhansl-Schmuckler [Krumhansl & Kessler 1982 ; Krumhansl 1990].

### 2.4 Limites méthodologiques

Ces limites doivent être explicitées avant toute interprétation.

**Format source.** Les fichiers proviennent du flux de diffusion Bandcamp, encodé en MP3 avec perte. L'encodage perceptuel altère prioritairement les composantes de faible énergie et les hautes fréquences. Les mesures au-dessus de 15 kHz et les valeurs de platitude spectrale doivent être considérées comme indicatives. Les descripteurs de basse et moyenne fréquence, ainsi que les mesures temporelles, sont peu affectés.

**Traitement de la chaîne de diffusion.** Le signal analysé inclut la compression de la console, le mixage et la masterisation. Les mesures de dynamique caractérisent donc le produit fini, non le jeu instrumental.

**Application de Praat hors de son domaine.** Praat a été conçu pour l'analyse de la parole. Le suivi de formants suppose un modèle source-filtre à résonances vocaliques ; appliqué à un signal de synthèse, il détecte des maxima spectraux qui ne sont pas des formants au sens phonétique. Nous interprétons ces valeurs comme des **pics de résonance** attribuables au filtrage, et non comme des formants. De même, le HNR suppose une source quasi-périodique unique ; sur un mixage polyphonique, il mesure la périodicité globale de la texture, ce qui reste interprétable mais n'a pas la signification qu'il aurait sur une voix isolée.

**Estimation de hauteur.** Le suivi de f₀ sur un signal polyphonique ne restitue pas les hauteurs individuelles mais un compromis dépendant de la saillance relative des sources.

---

## 3. Résultats

### 3.1 Organisation stéréophonique et distribution des rôles

La décomposition mid/side révèle une répartition très asymétrique de l'énergie.

| | Mid | Side |
|---|---|---|
| *Ordre étant* | 93,9 % | 6,1 % |
| *Duderc'h* | 94,5 % | 5,5 % |

Cette dominance du canal central est attendue. L'information déterminante apparaît lorsqu'on ventile cette énergie par bande de fréquence.

**Répartition spectrale (% de l'énergie totale de chaque composante)**

*Ordre étant* (hanter-dro)

| Bande (Hz) | Mid | Side |
|---|---|---|
| 20–60 | 11,0 | 1,2 |
| 60–120 | 9,2 | 2,2 |
| 120–250 | 8,2 | 8,2 |
| 250–500 | 9,6 | 11,2 |
| 500–1000 | 14,2 | 16,3 |
| 1000–2000 | 19,2 | 25,2 |
| 2000–4000 | 14,6 | 20,7 |
| 4000–8000 | 8,6 | 11,5 |
| 8000–16000 | 5,0 | 3,2 |

*Duderc'h* (scottish)

| Bande (Hz) | Mid | Side |
|---|---|---|
| 20–60 | 11,1 | 3,4 |
| 60–120 | 11,4 | 6,2 |
| 120–250 | 14,8 | 12,9 |
| 250–500 | 13,4 | 18,2 |
| 500–1000 | 10,7 | 12,1 |
| 1000–2000 | 13,7 | 16,0 |
| 2000–4000 | 12,1 | 12,0 |
| 4000–8000 | 9,0 | 11,7 |
| 8000–16000 | 3,7 | 7,1 |

Le rapport mid/side dans la bande 20–60 Hz atteint **9,2** sur la première pièce et **3,3** sur la seconde, alors qu'il s'inverse dans la bande 1000–2000 Hz (0,76 et 0,86 respectivement). L'extrême grave est donc strictement centré, tandis que le médium est étalé dans le champ stéréophonique.

Cette observation confirme acoustiquement la structure documentée par la fiche technique : le Minitaur, monophonique par construction, occupe le centre ; les deux synthétiseurs, repris en paire stéréo, occupent les latéraux. La stéréophonie n'est pas ici un simple élargissement esthétique mais **encode la distribution fonctionnelle des rôles**.

On notera l'analogie structurelle avec le couple traditionnel : le bourdon du biniou, invariable, occupe une position sonore fixe, tandis que la mélodie de la bombarde se détache. La spatialisation électronique matérialise dans le champ stéréophonique une séparation qui, dans le dispositif acoustique, s'opérait par le registre et le timbre.

### 3.2 Nature du timbre : mesures de bruit et de périodicité

| Descripteur | *Ordre étant* | *Duderc'h* |
|---|---|---|
| Platitude spectrale (moyenne) | 0,0033 | 0,0029 |
| Platitude spectrale (p90) | 0,0002 | 0,0001 |
| HNR moyen (Praat) | 4,77 dB | 2,19 dB |
| Énergie harmonique (HPSS) | 98,1 % | 91,2 % |
| Énergie percussive (HPSS) | 1,9 % | 8,8 % |
| Rolloff 85 % | 3 194 Hz | 3 018 Hz |
| Largeur de bande moyenne | 2 220 Hz | 2 189 Hz |

Les valeurs de platitude spectrale, de trois ordres de grandeur inférieures à l'unité, caractérisent un signal fortement tonal. Le contenu bruité est marginal : les générateurs de bruit blanc dont disposent ces instruments ne sont pas exploités de manière significative, et surtout, **aucune saturation forte n'est appliquée** — la distorsion produit mécaniquement une élévation de la platitude spectrale par génération de composantes inharmoniques.

Le rolloff à 85 % situé autour de 3 kHz confirme un spectre resserré vers le grave et le médium. La proportion d'énergie au-dessus de 8 kHz (5,0 % et 3,7 % dans le canal mid) est faible. Le timbre est donc **rond et filtré**, non brillant.

Ce résultat est notable au regard des attentes stylistiques. L'imaginaire de la « transposition électronique » d'une musique traditionnelle évoque volontiers la saturation et l'agressivité timbrale ; les mesures indiquent au contraire un traitement conservateur du contenu harmonique, où la caractérisation passe par le filtrage soustractif plutôt que par l'enrichissement par distorsion.

L'écart d'énergie percussive entre les deux pièces (facteur 4,6) constitue le principal contraste timbral du corpus, et sera discuté en 3.5.

### 3.3 Pics de résonance et récurrence du réglage de filtrage

Le suivi de formants sous Praat, interprété comme détection de maxima spectraux (cf. 2.4), donne :

| | *Ordre étant* | *Duderc'h* |
|---|---|---|
| R1 | 963 Hz (σ = 282) | 957 Hz (σ = 460) |
| R2 | 1 974 Hz (σ = 383) | 2 134 Hz (σ = 430) |
| R3 | 3 162 Hz (σ = 439) | 3 454 Hz (σ = 498) |

La proximité des premiers pics de résonance entre les deux pièces (963 et 957 Hz, soit un écart de 0,6 %) est frappante compte tenu de la différence de tonalité, de tempo et de caractère. Les rapports R2/R1 (2,05 et 2,23) et R3/R1 (3,28 et 3,61) suggèrent en outre une organisation quasi harmonique de ces maxima.

Deux interprétations sont envisageables et l'analyse acoustique seule ne permet pas de trancher. Il peut s'agir d'un réglage de filtre récurrent, constituant une « voix » identifiable du duo. Il peut aussi s'agir d'un artefact de la méthode de Burg, qui tend à distribuer les résonances de manière régulière dans la bande analysée. L'écart-type élevé (280 à 500 Hz) invite à la prudence : ces valeurs décrivent une tendance centrale sur un signal fortement variable, non un réglage fixe.

### 3.4 Le spectre de modulation : verrouillage métrique des LFO

C'est le résultat le plus robuste de l'étude. L'analyse de Fourier de l'enveloppe d'énergie, conduite séparément sur quatre bandes, fait apparaître des pics de modulation dont les fréquences entretiennent des rapports entiers simples.

**Pics détectés (Hz)**

| Bande | *Ordre étant* | *Duderc'h* |
|---|---|---|
| Grave (20–120 Hz) | 0,52 · 3,13 | 3,00 · 1,50 |
| Bas-médium (120–800 Hz) | 6,27 · 3,13 | 6,00 · 2,25 |
| Médium (800–3000 Hz) | 6,27 · 1,57 | 6,00 · 3,00 |
| Aigu (3000–10000 Hz) | 1,57 · 6,27 | 6,00 |

Sur *Ordre étant*, la série 1,57 / 3,13 / 6,27 Hz présente des rapports de 1 : 2 : 4. Rapportée au tempo estimé de 94,0 BPM (noire = 1,567 Hz) :

| Pic | Rapport à la noire | Valeur métrique | Erreur |
|---|---|---|---|
| 0,52 Hz | 0,332 | blanche pointée | 0,3 % |
| 1,57 Hz | 1,002 | noire | 0,2 % |
| 3,13 Hz | 1,998 | croche | 0,1 % |
| 6,27 Hz | 4,002 | double-croche | 0,1 % |

Une correspondance à 0,1–0,3 % près sur quatre valeurs de subdivision distinctes ne peut relever de la coïncidence. **Les modulations d'amplitude sont verrouillées sur la grille métrique.**

Sur le plan technique, deux mécanismes peuvent produire ce résultat : une synchronisation des LFO par horloge MIDI émise par la station de bouclage, ou un réglage manuel à l'oreille. La précision observée est compatible avec les deux hypothèses, la synchronisation par horloge étant la plus économique.

Sur le plan musical, ce verrouillage a une conséquence directe : la modulation timbrale ne flotte pas au-dessus de la pulsation, elle la renforce. Le trémolo et les mouvements de filtre deviennent des agents rythmiques, participant à la fonction chorégraphique de la musique. C'est un point de convergence avec la fonction du couple traditionnel, dont l'ornementation et les battements d'accord soutiennent la danse.

### 3.5 Correction d'une erreur d'octave métrique

Sur *Duderc'h*, la même procédure produit un résultat initialement discordant. Rapportés au tempo de 120,2 BPM estimé par l'algorithme de suivi de battement, les pics à 1,50 / 3,00 / 6,00 Hz donnent des rapports de 0,749 / 1,498 / 2,995 — soit une erreur systématique de 49,8 % par rapport aux subdivisions binaires.

L'hypothèse d'un tempo de 90,0 BPM (noire = 1,50 Hz) résout exactement cette discordance :

| Pic | Rapport à la noire (90 BPM) | Valeur métrique |
|---|---|---|
| 1,50 Hz | 1,000 | noire |
| 3,00 Hz | 2,000 | croche |
| 6,00 Hz | 4,000 | double-croche |

L'estimation initiale résultait d'une **erreur d'octave métrique**, biais bien identifié des algorithmes d'extraction de tempo, qui confondent fréquemment un niveau métrique avec son double ou sa moitié. Ce biais est ici favorisé par la faible stabilité rythmique mesurée sur cette pièce : l'écart-type des intervalles entre battements y atteint 7,74 % contre 1,89 % sur *Ordre étant*.

Ce résultat a une portée méthodologique dépassant le corpus : **l'analyse du spectre de modulation constitue un test indépendant de validation du niveau métrique**, applicable à tout corpus où des modulations synchrones sont présentes. Pour l'étude des musiques à danser, où l'identification correcte du niveau métrique conditionne la caractérisation du répertoire, cette procédure de contrôle mérite d'être systématisée.

On notera que le tempo corrigé de 90 BPM situe cette scottish dans une fourchette lente, cohérente avec un traitement électronique privilégiant la texture sur la vélocité.

### 3.6 Ouverture progressive de filtre : une dramaturgie du timbre

L'évolution du centroïde spectral au cours du temps a été modélisée par régression linéaire, en excluant les quinze dernières secondes pour neutraliser les fondus de fin.

| | *Ordre étant* | *Duderc'h* |
|---|---|---|
| Pente du centroïde | **+5,17 Hz/s** | −0,33 Hz/s |
| R² | 0,298 | 0,001 |
| p | < 0,001 | 0,11 |
| Valeur initiale | 923 Hz | 1 494 Hz |
| Valeur finale | 2 380 Hz | 1 419 Hz |
| Pente du rolloff 85 % | +11,62 Hz/s | −0,88 Hz/s |

![Centroïde spectral au cours du temps et régression linéaire, pour les deux pièces (figure produite par `../scripts/analyse_osso.py --figures`).](figures/osso_centroide.png)

Sur *Ordre étant*, le centroïde spectral **augmente de façon monotone et statistiquement significative** sur les 282 secondes analysées, passant de 923 à 2 380 Hz — un facteur 2,6, soit approximativement une octave et demie. La pente du rolloff, plus de deux fois supérieure, indique que l'élargissement affecte davantage encore les composantes les plus aiguës du spectre.

Le R² de 0,298 mérite commentaire : il indique qu'environ 30 % de la variance du centroïde est expliquée par la tendance linéaire, le reste correspondant aux fluctuations locales liées au jeu. Sur un signal musical de cinq minutes, une tendance linéaire expliquant près d'un tiers de la variance constitue une structure forte.

Sur *Duderc'h*, aucune tendance n'est décelable : la pente est négligeable et non significative.

**Cette différence est le résultat le plus important pour l'analyse stylistique.** L'ouverture progressive de filtre — geste emblématique des musiques électroniques, où il assure la montée en tension — n'est pas une signature systématique du duo mais un **choix de forme appliqué à une pièce et non à l'autre**.

L'articulation avec la forme traditionnelle est ici remarquable. Le hanter-dro repose sur une structure cyclique : la répétition d'une phrase mélodique brève, sans développement thématique, sur une durée déterminée par les nécessités de la danse. Cette forme, du point de vue de l'écriture occidentale savante, est statique. L'ouverture continue du filtre **superpose à cette forme cyclique une trajectoire directionnelle**, sans altérer le matériau mélodique ni la métrique. La progression est entièrement portée par le timbre.

C'est, nous semble-t-il, le point de rencontre conceptuel le plus abouti entre les deux traditions convoquées : le procédé électronique ne remplace pas la forme traditionnelle, il lui ajoute une dimension d'évolution que la répétition seule n'assure pas, tout en préservant la fonction chorégraphique qui exige la stabilité du cycle.

### 3.7 Tonalité et modalité

L'estimation par corrélation aux profils de Krumhansl-Schmuckler donne :

| | Meilleure correspondance | r | Second candidat | r |
|---|---|---|---|
| *Ordre étant* | La mineur | 0,725 | La majeur | 0,693 |
| *Duderc'h* | Fa mineur | 0,834 | Fa majeur | 0,777 |

L'écart très faible entre les hypothèses majeure et mineure (0,032 et 0,057) est significatif en soi. Les profils de Krumhansl-Schmuckler ont été établis à partir du répertoire tonal occidental ; leur ambiguïté sur ce corpus suggère une organisation modale ne relevant ni du majeur ni du mineur.

Le profil chroma de *Ordre étant* apporte un élément de confirmation : après La (0,90), les degrés les plus saillants sont Si (0,42) et Sol♯ (0,41). La présence conjointe d'un Sol♯ marqué et d'une tonique La évoque une sensible ascendante, tandis que la faiblesse relative du Do (0,34) par rapport au Si laisse la tierce indéterminée. Cette configuration est compatible avec les organisations modales documentées dans le répertoire breton, où la distinction majeur/mineur n'est pas structurante.

Cette observation demanderait une vérification par analyse mélodique manuelle, que le caractère polyphonique du signal ne permet pas d'automatiser de façon fiable.

### 3.8 Dynamique

| | *Ordre étant* | *Duderc'h* |
|---|---|---|
| Facteur de crête | 10,8 dB | 13,2 dB |
| Étendue dynamique (p95−p10) | 10,5 dB | 7,9 dB |
| Intensité moyenne (Praat) | 82,3 dB | 80,6 dB |

Ces valeurs traduisent une compression marquée, cohérente avec la compression insérée sur chaque voie documentée par la fiche technique. Un facteur de crête de 10,8 dB est faible pour un signal acoustique mais habituel en production électronique. Cette réduction de la dynamique renforce la continuité sonore — propriété que le dispositif traditionnel obtenait par la réserve d'air du biniou, et que l'accordéon obtient par son soufflet.

---

## 4. Discussion

### 4.1 Trois niveaux de transposition

Les mesures permettent de distinguer trois régimes dans le rapport entre le dispositif électronique et son modèle traditionnel.

**Le maintien fonctionnel.** La répartition des rôles est conservée : une source grave continue et centrée, des sources médium mobiles et spatialisées. La continuité sonore, assurée dans le dispositif traditionnel par la réserve d'air, l'est ici par la compression et par le caractère continu des oscillateurs. Le facteur de crête réduit et la faible étendue dynamique sont les corrélats acoustiques de cette continuité.

**La traduction technique.** Certains traits traditionnels trouvent un équivalent électronique exact. Le battement produit par l'écart d'accord entre biniou et bombarde a pour équivalent le désaccord entre oscillateurs. Le doublage à l'octave devient une superposition de voix aux fréquences en rapport 2:1. La spatialisation stéréophonique remplace la séparation par le registre.

**L'apport idiomatique.** L'ouverture progressive de filtre n'a pas d'équivalent dans le dispositif traditionnel, où le timbre instrumental est fixe. C'est l'apport propre de l'électronique : une dimension d'évolution timbrale à l'échelle de la pièce entière, superposée à une forme cyclique qui, elle, reste inchangée.

### 4.2 Implications pour la pratique de l'accordéon en formation réduite

L'accordéon diatonique en duo — avec clarinette, violon ou tout instrument mélodique — se trouve dans une situation structurellement comparable à celle analysée ici : deux sources seulement doivent assurer simultanément la mélodie, l'harmonie, le bourdon éventuel et la conduite rythmique de la danse.

Trois enseignements se dégagent des mesures.

Le premier concerne la **synchronisation de la modulation**. Le verrouillage métrique observé (erreur < 0,3 %) suggère que le tremblement, le battement de basses ou toute modulation périodique gagne à être calé sur une subdivision de la pulsation plutôt que laissé libre. L'accordéoniste dispose d'un équivalent direct : le jeu de basses alternées et les effets de soufflet constituent des modulations d'amplitude dont la périodicité peut être maîtrisée.

Le deuxième concerne la **dramaturgie sur forme cyclique**. La démonstration que 30 % de la variance timbrale d'une pièce peut être expliquée par une tendance monotone montre qu'une progression est réalisable sans modifier le matériau mélodique. L'accordéoniste ne dispose pas de filtre, mais dispose de registres, de la pression du soufflet et de la densité d'accompagnement — paramètres qui, employés en trajectoire plutôt qu'en alternance, produiraient un effet structurellement analogue.

Le troisième concerne la **répartition spectrale**. La séparation nette entre un grave centré et un médium étalé indique une stratégie d'occupation de l'espace fréquentiel qui évite le masquage entre les sources. En duo accordéon-clarinette, la clarinette occupe précisément la bande médium identifiée ici comme la plus chargée (1–2 kHz, jusqu'à 25 % de l'énergie du canal side). L'accordéoniste a donc intérêt à privilégier les registres graves et l'assise harmonique, plutôt qu'à doubler la mélodie dans un registre déjà occupé.

### 4.3 Portée méthodologique

Deux procédures employées ici paraissent transposables à d'autres corpus de musique à danser.

L'analyse du **spectre de modulation par bande** permet de caractériser les traitements dynamiques indépendamment du contenu mélodique, et constitue un test de validation du niveau métrique là où les algorithmes standards échouent (cf. 3.5).

La **régression du centroïde spectral sur la durée** fournit un indicateur quantitatif de dramaturgie timbrale, applicable à toute musique de forme cyclique où l'analyse thématique classique est peu opérante. Cet indicateur pourrait être appliqué à des enregistrements de bal traditionnel pour évaluer si des trajectoires timbrales comparables s'y observent — question ouverte que ce travail ne permet pas de trancher.

---

## 5. Conclusion

L'analyse acoustique de deux pièces du duo OSSO établit trois résultats principaux. Premièrement, la stéréophonie encode la distribution fonctionnelle des rôles instrumentaux, l'extrême grave étant strictement monophonique (rapport mid/side de 9,2 sous 60 Hz) tandis que le médium est spatialisé. Deuxièmement, les modulations d'amplitude sont verrouillées sur la grille métrique avec une précision inférieure à 0,3 % sur quatre subdivisions distinctes, faisant de la modulation timbrale un agent rythmique au service de la fonction chorégraphique. Troisièmement, une ouverture progressive de filtre statistiquement significative (+5,17 Hz/s, R² = 0,298, p < 0,001) structure l'une des deux pièces sans être présente dans l'autre, ce qui la caractérise comme choix de forme plutôt que comme signature stylistique.

Ces résultats suggèrent que la transposition électronique du couple de sonneurs opère moins par substitution timbrale que par **redistribution des fonctions dans des dimensions nouvelles** — la spatialisation stéréophonique et la trajectoire timbrale — tout en préservant la structure cyclique et la fonction de danse qui définissent le répertoire.

La taille du corpus (n = 2) limite la portée de ces conclusions à des observations de cas. Une extension à un corpus plus large de formations électro-traditionnelles bretonnes permettrait d'établir si les procédés identifiés relèvent d'une pratique partagée ou d'un idiolecte.

---

## Annexe A — Reproductibilité

Environnement : Python 3, librosa 1.0.0, praat-parselmouth 0.4.7, scipy, numpy.

**Script complet** : [`../scripts/analyse_osso.py`](../scripts/analyse_osso.py) —
une fonction par section (`analyse_mid_side`, `analyse_timbre`,
`analyse_resonances`, `spectre_modulation`, `correction_metrique`,
`regression_centroide`, `estimation_tonalite`, `analyse_dynamique`).

```bash
cd research
pip install -e ".[musique]"                     # librosa, parselmouth, soundfile, matplotlib
python3 scripts/analyse_osso.py --data ~/audio/osso --figures
```

**Disponibilité des données.** Les deux enregistrements analysés **ne sont pas
versionnés dans ce dépôt** : ce sont des œuvres protégées, diffusées
commercialement. Aucun extrait sonore n'est reproduit ici — seuls des
descripteurs acoustiques dérivés sont publiés. Pour rejouer l'analyse, il faut
se procurer les fichiers légalement (achat sur la page Bandcamp du duo, ou
autorisation écrite des ayants droit pour un usage de recherche) et les placer
sous les noms `track1.mp3` (*Ordre étant*) et `track2.mp3` (*Duderc'h*) dans le
dossier passé à `--data`. En leur absence, le script s'arrête avec un message
explicite et un code de retour non nul.

Procédures principales :

```python
# Décomposition mid/side
y, sr = librosa.load(fichier, sr=44100, mono=False)
mid  = (y[0] + y[1]) / 2
side = (y[0] - y[1]) / 2

# Spectre de modulation par bande
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=256))
f = librosa.fft_frequencies(sr=sr, n_fft=2048)
env = S[(f >= lo) & (f < hi)].sum(axis=0)
env = env - env.mean()
spectre = np.abs(np.fft.rfft(env * np.hanning(len(env))))
freqs   = np.fft.rfftfreq(len(env), 1 / (sr / 256))

# Régression du centroïde (exclusion des 15 dernières secondes)
cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=2048)[0]
t = np.arange(len(cent)) * 2048 / sr
m = t < (t[-1] - 15)
pente, ordonnee, r, p, err = scipy.stats.linregress(t[m], cent[m])

# Mesures Praat
snd = parselmouth.Sound(fichier).resample(22050)
hnr = parselmouth.praat.call(snd, 'To Harmonicity (cc)', 0.01, 60, 0.1, 4.5)
fmt = parselmouth.praat.call(snd, 'To Formant (burg)', 0.02, 4, 5000, 0.025, 50)
```

## Annexe B — Tableau récapitulatif

| Descripteur | *Ordre étant* (hanter-dro) | *Duderc'h* (scottish) |
|---|---|---|
| Durée | 296,9 s | 240,4 s |
| Tempo (algorithme) | 94,0 BPM | 120,2 BPM *(erroné)* |
| Tempo (corrigé par modulation) | 94,0 BPM | **90,0 BPM** |
| Stabilité du battement (σ relatif) | 1,89 % | 7,74 % |
| Tonalité (K-S) | La, modal | Fa, modal |
| Énergie Mid / Side | 93,9 / 6,1 % | 94,5 / 5,5 % |
| Rapport mid/side sous 60 Hz | 9,2 | 3,3 |
| Harmonique / percussif | 98,1 / 1,9 % | 91,2 / 8,8 % |
| Platitude spectrale | 0,0033 | 0,0029 |
| HNR (Praat) | 4,77 dB | 2,19 dB |
| Rolloff 85 % | 3 194 Hz | 3 018 Hz |
| R1 (pic de résonance) | 963 Hz | 957 Hz |
| Modulations | 0,52 / 1,57 / 3,13 / 6,27 Hz | 1,50 / 3,00 / 6,00 Hz |
| Correspondance métrique | 0,1–0,3 % | 0,0 % (après correction) |
| Pente du centroïde | **+5,17 Hz/s** (p < 0,001) | −0,33 Hz/s (n.s.) |
| Facteur de crête | 10,8 dB | 13,2 dB |

## Références

Entrées BibTeX dans [`references.bib`](references.bib).

- **[Boersma 1993]** Boersma, P. *Accurate short-term analysis of the fundamental
  frequency and the harmonics-to-noise ratio of a sampled sound.* Proceedings of
  the Institute of Phonetic Sciences 17, 1993. — méthode du HNR.
- **[Boersma & Weenink]** Boersma, P. & Weenink, D. *Praat: doing phonetics by
  computer* (logiciel).
- **[Ellis 2007]** Ellis, D. P. W. *Beat tracking by dynamic programming.*
  Journal of New Music Research 36(1), 2007. — suivi de battement de librosa.
- **[Fitzgerald 2010]** Fitzgerald, D. *Harmonic/percussive separation using
  median filtering.* Proc. DAFx-10, 2010. — séparation HPSS.
- **[Jadoul *et al.* 2018]** Jadoul, Y., Thompson, B. & de Boer, B. *Introducing
  Parselmouth: A Python interface to Praat.* Journal of Phonetics 71, 2018.
- **[Krumhansl & Kessler 1982]** Krumhansl, C. L. & Kessler, E. J.
  *Tracing the dynamic changes in perceived tonal organization…*
  Psychological Review 89(4), 1982. — profils tonaux.
- **[Krumhansl 1990]** Krumhansl, C. L. *Cognitive Foundations of Musical Pitch.*
  Oxford University Press, 1990. — algorithme de Krumhansl-Schmuckler.
- **[McFee *et al.* 2015]** McFee, B. *et al.* *librosa: Audio and music signal
  analysis in Python.* Proc. 14th Python in Science Conference (SciPy), 2015.

---

*Analyse conduite sur les enregistrements diffusés publiquement par le duo. Les mesures présentées sont des descripteurs acoustiques dérivés ; aucun extrait sonore n'est reproduit. Une validation des attributions instrumentales auprès des musiciens serait souhaitable avant publication.*
