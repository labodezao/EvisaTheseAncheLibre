# Expériences à mener — liste de travail

> Chaque entrée dit **ce qu'on mesure**, **avec quoi**, **ce que ça débloque**,
> et **le chiffre du modèle à confronter**. Les prédictions viennent de
> `reed_oscillator.py` sur l'anche de référence (sol2, premier mode 102,1 Hz),
> détaillées dans `audit_modele_anche.md`.
>
> Matériel supposé : turbine + débitmètre + capteur de pression, carte son et
> micro, accordeur du dépôt. Rien de coûteux.

---

## Priorité 1 — les deux paramètres dont tout dépend

Sans ces deux nombres, le modèle reste paramétré au jugé. Avec eux, tout le
reste devient une comparaison honnête.

### ☐ E1. Caractéristique pression–débit de la source
**Mesure** : à commande de turbine fixe, balayer la section d'ouverture et
relever les couples (p, q). Tracer p en fonction de q.
**Avec** : `Mesures.py` sait déjà balayer le facteur `Section` ; débitmètre +
capteur de pression.
**Ce que ça donne** : la **pente** est l'impédance interne `R` de la source.
C'est le paramètre `Source.impedance_pa_s_m3`, qui **borne l'amplitude** du
cycle limite. Valeur provisoire dans le modèle : 2·10⁸ Pa·s/m³.
**Débloque** : l'amplitude prédite, donc toute comparaison de niveau sonore.

### ☐ E2. Volume acoustique effectif, par le décalage de fréquence
**Mesure** : fréquence propre de la languette **libre** (pincée, hors
instrument, au micro) puis fréquence de **jeu** de la même anche montée.
**Avec** : accordeur du dépôt ; `frf.py` pour la languette libre.
**Ce que ça donne** : le rapport des deux fréquences dépend du volume
acoustique effectif `V₀` — le ressort d'air raidit le système. Le modèle
prédit **+16 %** (118 Hz de jeu pour 102,1 Hz propres) avec V₀ = 40 cm³.
**Débloque** : `Chamber.volume_m3`, dont dépend le seuil de démarrage **et**
la largeur de l'hystérésis. C'est une cote *acoustique*, pas géométrique :
elle inclut le canal du sommier et le couplage au réservoir.

---

## Priorité 2 — valider ou casser le modèle

### ☐ E3. Hystérésis p_on / p_off
**Mesure** : rampe de pression **montante** jusqu'au démarrage, puis
**descendante** jusqu'à l'extinction. Relever les deux seuils.
**Avec** : `seuil.py` (`seuil.detect`), `ramp.py` pour répéter.
**Prédiction du modèle** : p_on = 25,8 Pa, p_off = 19,4 Pa, **rapport 1,33**.
**Ce que ça teste** : le caractère **sous-critique** de la bifurcation, cœur
de la thèse. Si le rapport mesuré s'écarte nettement de 1,33, ce sont E1 et
E2 qu'il faut recaler d'abord.
**Important** : faire la rampe **dans les deux sens**. Monter seul ne permet
pas de distinguer sous- de supercritique — j'ai fait l'erreur.

### ☐ E4. Seuil d'étouffement
**Mesure** : monter la pression bien au-delà du seuil de jeu, jusqu'à ce que
l'anche **cesse** de sonner. Relever la pression.
**Prédiction** : **379,8 Pa**.
**Ce que ça teste** : le mécanisme de saturation d'ouverture (la languette
soufflée hors de la fente ne module plus rien). C'est une prédiction que le
modèle produit sans qu'on la lui ait demandée — donc un bon test.

### ☐ E5. Loi d'amplitude au-dessus du seuil
**Mesure** : amplitude du son (ou excursion du bout) à plusieurs pressions
au-dessus du seuil. Tracer l'amplitude en fonction de √(p − p_on).
**Prédiction** : droite (loi en racine), **0,96 mm crête-crête à 1,5× le
seuil**.
**Ce que ça teste** : la forme normale de Hopf. Croisé avec E3, ça distingue
proprement super- de sous-critique.

### ☐ E6. Excursion réelle du bout d'anche
**Mesure** : amplitude crête-crête de la languette en jeu.
**Avec** : stroboscope multi-harmonique de l'accordeur + caméra, ou
comparateur. Pas de vibromètre nécessaire.
**Prédiction** : ~1 mm à 1,5–2× le seuil.
**Ce que ça teste** : que le modèle travaille dans la bonne plage physique —
la première version en prédisait 109 mm.

---

## Priorité 3 — la géométrie d'entrée du modèle

### ☐ E7. Profil d'épaisseur de l'anche de référence
**Mesure** : épaisseur au pied à coulisse ou au micromètre, sur les trois
tronçons.
**Pourquoi** : `SECTIONS_DEFAULT` porte 0,40 / **0,045** / 0,70 mm. Ce profil
mince-au-milieu / épais-au-bout est celui d'une **anche de basse lestée** et
donne 100,5 Hz ≈ sol2, donc il est probablement juste — mais 0,045 mm est
assez surprenant pour mériter une vérification. Si c'était 0,45, on aurait
92,9 Hz (fa♯2).
**Débloque** : la confiance dans toute la base modale.

### ☐ E8. Fréquences propres de la languette libre
**Mesure** : FRF de la languette seule (excitation EM ou pichenette), relever
les 2–3 premiers modes.
**Avec** : `frf.py`, `modal.natural_frequencies`.
**Prédiction** : 102,1 et 652,0 Hz (rapport 6,39).
**Ce que ça teste** : `modal.py`, déjà validé à 0,00 % contre la solution
analytique sur poutre uniforme — reste à confronter au réel multi-tronçon.

### ☐ E9. Amortissement ζ de la languette
**Mesure** : décroissance libre après excitation (ring-down), en extraire le
facteur Q.
**Avec** : `ringdown.py`.
**Valeur provisoire** : ζ = 0,004 (Q ≈ 125).
**Débloque** : le seuil de démarrage dépend directement de ζ.

---

## Priorité 4 — la source / filtre et la synthèse

### ☐ E10. Jeu de notes pour séparer source et résonateur
**Mesure** : enregistrer **une dizaine de notes** réparties sur la tessiture,
même instrument, même prise de son, micro proche et sec.
**Avec** : `sample_extract.extract_multi`.
**Pourquoi une dizaine** : mesuré, pas supposé — en dessous de 6 notes la
résonance est mal localisée, au-delà de 12 le gain devient marginal. Sur une
note unique le problème est **sous-déterminé** : l'enveloppe passe par les
sommets des partiels et contient source et filtre confondus.
**Débloque** : le résonateur (biquads) et la pente de source, donc l'export
vers STM32 / wavetable.

### ☐ E11. Matrice notes × nuances
**Mesure** : les mêmes notes, à 3 nuances au moins (pp, mf, ff), poussé et
tiré.
**Débloque** : la **loi de commande** brillance ↔ niveau, celle qui rend un
modèle physique jouable en continu au lieu de fondre entre des couches
d'échantillons. C'est ce qui sépare un sampleur d'un instrument.

### ☐ E12. Spectre réel contre spectre du modèle
**Mesure** : spectre d'une anche isolée en régime établi, micro proche.
**Prédiction** : 6 à 12 harmoniques au-dessus de −30 dB sur `dq/dt`.
**Attention** : comparer la **bonne grandeur**. Une anche libre rayonne par
le **débit modulé**, et en champ lointain par sa dérivée — pas par la
pression de chambre. `OscillationResult.radiated` donne `dq/dt`.

---

## Priorité 5 — la question ouverte

### ☐ E13. Anche seule contre anche + chambre
**Mesure** : seuil de démarrage d'une anche montée sur des chambres de
volumes différents (caler des volumes connus derrière la plaque).
**Ce que ça teste** : la prédiction la plus forte et la plus falsifiable du
modèle — **sous un certain volume, l'anche ne démarre pas du tout**, parce
que le ressort d'air est trop raide et que le balayage de la languette écrase
la modulation de pression. Le modèle situe cette limite vers 12 cm³.
**Si ça ne se vérifie pas**, c'est la formulation du couplage qu'il faut
reprendre, pas les paramètres.

---

## Ordre conseillé

E1 et E2 d'abord — tout le reste s'appuie dessus. Puis E3 (l'hystérésis, le
cœur de la thèse) et E4 (l'étouffement, la prédiction gratuite). E7 à E9
peuvent se faire en parallèle, ce sont des mesures de paillasse. E10–E12
forment un bloc à part, celui de la synthèse. E13 en dernier, mais c'est
celle qui peut tout remettre en cause : à garder en tête.

Le principe qui vaut pour toutes : **une expérience utile est une expérience
dont le résultat serait différent si l'hypothèse était fausse.** Trois fois
au cours de ce travail, une mesure a contredit un raisonnement qui semblait
solide.

---

## Priorité 6 — la famille élargie (modèle hybride)

Ajoutées avec `hybrid.py` / `identify.py` / `embedded.py`. Voir
`modele_hybride_generalise.md`. Elles remplacent des paramètres **supposés**
par des paramètres **mesurés** — c'est toute leur raison d'être.

### ☐ E14. Impédance d'entrée d'une perce réelle
**Mesure** : impédance d'entrée d'un chalumeau, d'un corps de clarinette ou
d'une perce de bombarde, à la méthode deux micros.
**Avec** : `transfer.py`, déjà dans le dépôt.
**Ce que ça donne** : `z_peak`, les facteurs Q et les fréquences de mode —
c'est-à-dire **tout le résonateur**, mesuré au lieu de supposé.
**Pourquoi c'est la plus rentable des six** : `z_peak` décide si
l'instrument parle. En dessous de `|∂q/∂Δp| > 1/z_peak`, rien ne s'entretient.
Actuellement il vaut `20 × ρc/S`, un ordre de grandeur pris dans la
littérature.

### ☐ E15. Matrice force × position d'archet (vielle à roue)
**Mesure** : balayer la pression du chien et la position du point de contact,
relever le régime obtenu (Helmholtz franc / raucous / sifflement).
**Avec** : une roue, un dynamomètre de cuisine, un micro.
**Prédiction** : zone de Helmholtz stable sous ~0,3 N avec les paramètres
actuels ; au-delà de 0,5 N le modèle devient **chaotique** (deux simulations
à 10⁻⁷ près divergent complètement). C'est le diagramme de Schelleng.
**Ce que ça teste** : la borne haute de force, que le modèle produit sans
qu'on la lui ait demandée.

### ☐ E16. Rapport cyclique et équilibre pair/impair
**Mesure** : sur une anche double ou simple, faire varier la pression de
souffle et relever à la fois le spectre et (si possible) la fraction de temps
où l'anche est fermée.
**Prédiction** : l'écart impairs/pairs fait des allers-retours avec la
pression (mesuré sur le modèle : 17 → 5 → 27 → 6 dB), et suit le rapport
cyclique. Une anche fermée près de la moitié du temps éteint ses harmoniques
paires **même sur une perce conique**.
**Ce que ça teste** : que la pression de souffle ne change pas seulement la
nuance mais la **nature** du timbre. Si ça se vérifie, c'est un résultat
musical autant que physique.

### ☐ E17. Profilage réel sur carte
**Mesure** : compiler `hybrid_voice.c` sur la cible, chronométrer `hv_render`
sur un bloc de 64 échantillons, compter les voix tenues sans décrochage.
**Prédiction** : 32 MFLOP/s par voix, soit ~5 voix sur un STM32F4 à 168 MHz
et ~15 sur un H7 à 480 MHz.
**Attention** : l'estimation compte les flops et ignore les accès mémoire et
la boucle — elle est donc **optimiste de 20 à 40 %**. C'est une prédiction à
corriger, pas une promesse.

### ☐ E18. La loi d'échelle d'un jeu d'anches libres
**Mesure** : sur une plaque d'anches d'accordéon de récupération — un jeu
entier, si possible du grave à l'aigu — relever pour chaque languette sa
longueur, sa largeur, son épaisseur et sa note. Un pied à coulisse suffit ;
pour l'épaisseur, une cale d'épaisseur ou un palmer d'occasion. La note se
lit à l'accordeur du dépôt, sans démonter quoi que ce soit.
**Prédiction du modèle** : similitude géométrique — les trois dimensions en
`1/f`, donc `m ∝ 1/f³`. En tracer le log : trois droites de pente −1.
**Ce que ça teste, et pourquoi ça compte** : c'est la loi qui décide si une
note parle. À cotes fixes, l'amplitude qu'une pression donnée obtient décroît
en `1/ω²` — au-dessus de 185 Hz la languette du la grave ne module plus rien
et l'anche devient **muette**, ce qui s'est vu tout de suite en jouant au
clavier. Si les vraies anches suivent une autre pente (les facteurs changent
souvent d'épaisseur par registre, en marches plutôt qu'en pente continue),
c'est le modèle qu'il faut corriger, pas la mesure.
**Bonus, si une cellule de sommier est accessible** : son volume, à la
seringue d'eau. Le modèle veut `V ∝ 1/f³` — et ce n'est pas un choix : c'est
ce qui sort de la condition « le couplage anche↔chambre garde la même force
d'une note à l'autre ». Une mesure qui contredirait ce `−3` contredirait le
couplage lui-même.
**Coût** : zéro, si la plaque d'anches vient d'un accordéon hors service.
