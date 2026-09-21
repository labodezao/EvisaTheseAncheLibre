# Vers un modèle jouable — ce qui manque pour atteindre le niveau SWAM

> Diagnostic reproductible : `python3 scripts/diagnostic_reed_model.py`

## Le constat, d'abord

J'ai voulu brancher l'extraction de paramètres (`sample_extract.py`) sur le
modèle physique du dépôt (`reed_model.py`) pour fermer la boucle. Le modèle ne
le permet pas encore. Les chiffres, sur les paramètres par défaut :

| Grandeur | Simulé | Réel (accordéon) |
|---|---|---|
| Surpression de cavité | −82 205 à +1 455 Pa | ±500 à 3 000 Pa |
| Course du bout d'anche | **109,6 mm** crête-crête | 0,05 à 1,5 mm |
| Ouverture `gap + y` | **−100,6 mm** | 0 à 0,5 mm |
| Volume de cavité | 0,99 à **3,43 × V₀** | rigide, ≈ 1 |
| Écart-type de pression, 0,05 → 0,45 s | 8324 → 1834 → **497 Pa** | stable |

Deux conclusions :

1. **Le régime est physiquement impossible.** Une ouverture de −100 mm veut
   dire que la languette a traversé sa plaque de 10 cm. Le `max(gap + y, 1e-6)`
   du code empêche la racine carrée de diverger, mais il **masque** la
   traversée au lieu de modéliser le contact.
2. **Le modèle n'auto-oscille pas.** L'amplitude est divisée par 17 en
   0,4 s. Ce qu'on entend est un transitoire qui s'éteint, pas une note. Et
   l'amplitude **décroît** quand le débit d'entrée augmente — l'inverse d'une
   bifurcation de Hopf, où l'amplitude croît comme √(p − p_seuil).

Ce n'est pas un bug d'implémentation : le portage du MATLAB est probablement
fidèle. C'est le **modèle** qui ne décrit pas encore l'instrument.

## Pourquoi c'est bloquant pour la synthèse

La chaîne actuelle de `synth_export` est **ouverte** : source → filtre. Un
instrument réel est une **boucle fermée** : la pression de cavité réagit sur
l'anche, qui module l'ouverture, qui change le débit, qui change la pression.
C'est cette boucle qui fait qu'en soufflant plus fort le spectre s'enrichit
tout seul, sans qu'on ait à fondre entre des couches d'échantillons.

C'est exactement ce qui sépare un sampleur d'un SWAM. Et c'est exactement ce
que `reed_model.py` cherche à faire — d'où l'enjeu de le corriger.

## Les cinq corrections, par ordre d'impact

### 1. Les paramètres sont hors échelle
`gap = 9 mm`. Une anche d'accordéon a un jeu de l'ordre de **0,05 à 0,3 mm**.
Facteur 30 à 180. À 9 mm de jeu, la languette n'obture jamais la fente : il
n'y a plus de modulation de débit, donc plus de mécanisme d'entretien.

### 2. La cavité ne peut pas gonfler
Le code prend le **volume** comme variable d'état (`dV = q_in − q_out + q_reed`)
puis en déduit la pression par la loi adiabatique. Mais une cavité rigide a un
volume **fixe** : ce qui varie, c'est la **masse d'air**. La bonne formulation
est une compliance acoustique, pression en variable d'état :

```
dp/dt = (ρc²/V₀) · (u_entrant − u_sortant)
```

Avec la formulation actuelle, le volume triple — impossible pour une boîte en
bois.

### 3. On joue en pression, pas en débit
`q_in` est un débit constant imposé. On ne joue pas un accordéon en imposant un
débit : on impose une **pression de soufflet**, et le débit est ce qui en
résulte. C'est aussi la variable que tu mesures au banc, et celle que le
contrôleur continu pilotera en jeu. Imposer le débit revient à brancher le
modèle à l'envers.

### 4. Il manque le contact — et il doit être asymétrique
C'est la non-linéarité qui **fixe l'amplitude** du cycle limite et qui crée la
richesse harmonique. Sans elle, rien ne sature, donc pas de cycle limite.

Mais attention au piège, que j'ai vérifié expérimentalement : une ouverture
symétrique `S = b·|y|` module la fente **deux fois par période**, et le modèle
sort une fréquence de **470 Hz pour une anche à 220 Hz**. La note est fausse
d'une octave.

L'anche d'accordéon est une **anche libre** : la languette traverse la fente,
et elle ne débite que dans **un seul sens** — l'autre demi-course est fermée
par la soupape de cuir. C'est précisément pourquoi pousser et tirer utilisent
deux anches distinctes. L'asymétrie de `S(y)` n'est pas un raffinement :
**elle fixe la hauteur de la note.**

### 5. Il manque le déphasage qui permet l'entretien
Un ressort-masse attaqué par un Bernoulli quasi statique ne s'entretient pas :
force et vitesse sont en quadrature, le travail net sur un cycle est nul. Il
faut un retard de phase, apporté par l'**inertance de l'air dans la fente**
(Bernoulli instationnaire, `L·du/dt = Δp − pertes`, avec `L = ρ·l_fente/S`)
et/ou par la compliance de cavité.

## Le critère de validation — non négociable

Un modèle corrigé doit passer ces cinq tests avant qu'on lui fasse confiance :

1. **Seuil de Hopf** : il existe `p_on` en dessous duquel rien ne démarre.
2. **Loi d'amplitude** : au-dessus du seuil, amplitude ∝ √(p − p_on).
3. **Hystérésis** : `p_on > p_off` (sous-critique, typique des anches) — que
   `bifurcation.py` et `seuil.py` savent déjà mesurer, au banc comme en
   simulation. C'est le pont avec toute la partie stochastique de la thèse.
4. **Fréquence** : proche de la fréquence propre de la languette, **pas** de
   son double.
5. **Plages physiques** : course < 1 mm, surpression < 3 kPa, ouverture ≥ 0.

Le script `diagnostic_reed_model.py` teste 1, 2, 4 et 5 ; il renvoie un code
de sortie non nul tant que ça ne passe pas. Il sert donc de **test de
non-régression** : le jour où le modèle est corrigé, il passe au vert.

## La route jusqu'au niveau SWAM

### Étape 1 — Un modèle qui oscille (bloquante)
Les cinq corrections ci-dessus. **Non franchie à ce jour** : mes propres
tentatives de correction rapide (pilotage en pression + contact) échouent
aussi — soit l'anche se plaque et reste fermée, soit l'oscillation décroît.
C'est le sujet de ta thèse, pas une correction de quelques lignes.

### Étape 2 — Identification inverse
Une fois le modèle oscillant, on renverse la démarche : au lieu d'extraire des
descripteurs d'un son, on cherche **les paramètres physiques tels que le
modèle simulé produise le son mesuré**.

- Fonction de coût : distance log-spectrale (`synth_export.spectral_distance_db`,
  déjà là) + écart sur `p_on` + écart sur le temps d'attaque.
- Optimiseur sans dérivée (le RK4 n'est pas différentiable) : Nelder-Mead.
- **Et surtout** : `doe_analysis` sert ici à plein régime. Un plan de
  Plackett-Burman sur les paramètres du modèle dit lesquels comptent avant
  d'optimiser — au lieu d'optimiser à l'aveugle dans 10 dimensions.

### Étape 3 — La carte d'expression (le cœur du SWAM)
C'est là que se joue la qualité perçue, plus que dans la précision spectrale.
Il faut une **matrice** de mesures : plusieurs notes × plusieurs nuances
(pp → ff) × poussé/tiré. On en tire la trajectoire des paramètres en fonction
de la pression de soufflet. Le modèle interpole alors **physiquement** au lieu
de fondre entre des couches.

L'outil d'extraction sert déjà à ça : `brightness_slope_hz_per_db` est
exactement cette loi de commande.

### Étape 4 — Les transitions
Ce que les sampleurs ratent le plus : le legato, la réarticulation. Avec un
modèle, la transition est gratuite — on ne réinitialise pas, on laisse la
boucle tourner et on change la géométrie. C'est le seul point où un modèle
physique gagne sans effort.

### Étape 5 — Le micro-vivant
Deux notes ne sont jamais identiques. Instabilité près du seuil, jitter,
souffle. `stochastic.py` (Kramers, résonance cohérente) traite déjà cette
physique-là : elle n'est pas un défaut à gommer, c'est ce qui fait vivant.

## Est-ce que ça tient sur un STM32 ?

Ordre de grandeur, pour une voix : anche à 1–2 modes + débit de fente +
compliance de cavité ≈ 15 variables d'état, RK4 = 4 évaluations par
échantillon, soit ~50 à 100 opérations flottantes par échantillon. À 48 kHz :
**2,4 à 5 MFLOPS par voix**.

Un STM32H7 à 480 MHz avec FPU simple précision fait de l'ordre de
400–500 MFLOPS utiles. Même en divisant par 5 pour rester prudent, une
dizaine de voix polyphoniques est plausible. **Le modèle physique n'est pas
le problème côté calcul** — le problème est qu'il soit juste.

## Ce que cette session a établi, et ce qu'elle n'a pas fait

**Établi** (reproductible) : le modèle actuel n'auto-oscille pas et tourne
hors des plages physiques ; le diagnostic est scriptée ; les cinq causes sont
identifiées et argumentées ; l'asymétrie de l'ouverture est vérifiée comme
déterminante pour la hauteur (470 Hz au lieu de 220).

**Non fait** : je n'ai **pas** produit de modèle d'anche libre auto-oscillant
validé. Mes essais rapides échouent, et je préfère te le dire que de te
livrer quelque chose qui a l'air de marcher. Le premier jalon reste l'étape 1.
