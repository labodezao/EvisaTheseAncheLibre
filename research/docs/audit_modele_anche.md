# Audit du modèle physique d'anche (`reed_model.py` + `modal.py`)

> Reproductible : `python3 scripts/diagnostic_reed_model.py`
> Garde-fous : `tests/test_reed_model_audit.py`

**Hypothèse de travail retenue : l'anche est alimentée en DÉBIT, pas en
pression.** C'est ta conception, et elle est juste : le soufflet impose une
vitesse volumique, la pression est ce qui en résulte. La preuve est dans le
jeu — à vitesse de soufflet constante, ouvrir un accord fait *chuter* la
pression ; une source de pression tiendrait la pression et doublerait le
débit. Tout ce qui suit part de là.

## Comment vérifier expérimentalement (tu as déjà le matériel)

Deux mesures, avec ton débitmètre et ton capteur de pression :

1. **Test du second jeu.** À commande de turbine fixe, mesurer (p, q) avec une
   anche ouverte, puis deux, puis trois. Source de débit → q total ≈ constant,
   p chute. Source de pression → p ≈ constante, q proportionnel au nombre
   d'anches. Décisif en dix minutes.

2. **Courbe caractéristique de la source.** Balayer la section d'ouverture
   (ton facteur `Section` du DOE est exactement ça) en relevant (p, q) à
   commande fixe, puis tracer p en fonction de q. La **pente** est
   l'impédance interne de la source : verticale = source de débit,
   horizontale = source de pression, oblique = réelle, et la pente donne
   directement l'impédance à mettre dans le modèle.

Le point 2 est le bon : il ne répond pas par oui/non mais par un **nombre**,
celui qu'il faut au modèle. Et `Mesures.py` sait déjà balayer `Section`.

---

## Ce qui est juste

### La base modale est exacte
Sur une poutre uniforme, `modal.assemble` retrouve la formule analytique
encastré-libre à **0,00 %** sur les trois premiers modes (134,11 / 840,46 /
2353,30 Hz). Le portage de `matkm`/`km` est fidèle. Figé par
`test_base_modale_retrouve_le_cantilever_analytique`.

### Les dimensions sont cohérentes
Vérification terme à terme : `γ` en m², `F = ΔP·γ` en N, `M` en kg,
`q_out` et `q_anche` en m³/s, `dV` en m³/s. Rien à redire.

### Le profil d'épaisseur n'est pas une coquille
`0,40 → 0,045 → 0,70 mm` (fin au milieu, épais au bout) surprend, mais donne
f₁ = 100,5 Hz ≈ **sol2 (98 Hz)**. C'est la conception classique d'une **anche
de basse lestée** : charnière mince au milieu, masse au bout pour descendre la
fréquence. Ça ressemble à une vraie mesure. *À confirmer au pied à coulisse* —
si le tronçon 2 valait 0,45 mm, on aurait 92,9 Hz, soit fa♯2, ce qui reste
plausible.

---

## Les défauts, par ordre de gravité

### 1. La loi de cavité est inversée — **cause racine**

```python
P = c.patm * (self.V0 / max(V, 1e-9)) ** c.gamma
```

`V` sert de variable d'état proportionnelle à la **masse d'air** (`dV = q_in −
q_out + q_anche`). Mais cette formule fait **chuter** la pression quand `V`
augmente. Autrement dit : **on injecte de l'air et la cavité se met en
dépression.**

Symptômes mesurés, qui s'expliquent tous par là :

| Observation | Valeur |
|---|---|
| Surpression de cavité | **toujours négative**, −8804 à −1326 Pa |
| Fente fermée | **99,2 % du temps** (l'anche est aspirée contre la plaque) |
| Fréquence dominante | **2,0 Hz** au lieu de 102 Hz |
| Volume de cavité | jusqu'à ×3,43 alors qu'elle est rigide |

L'anche est aspirée, se plaque, ne module plus rien : pas d'oscillation.

⚠️ **Inverser la formule ne suffit pas** : je l'ai testé, ça diverge
(28 GPa), parce que rien ne borne alors la pression par le haut.

### 2. Le schéma numérique ne peut pas intégrer la cavité

La formulation propre d'une cavité rigide prend la **pression** en variable
d'état : `dP/dt = (ρc²/V₀)·(q_in − q_out + q_anche)`. Mais
`ρc²/V₀ ≈ 1,8·10¹⁰ Pa/m³` : le système est **raide**. Un RK4 explicite à
44,1 kHz diverge (testé : 10¹⁵⁰ Pa).

Trois issues possibles : suréchantillonner (×8 à ×16), passer à un schéma
implicite ou semi-implicite, ou réduire la cavité en quasi-statique.

J'ai testé la réduction quasi-statique (`P = (ρ/2)·((q_in + q_anche)/(c_d·S))²`,
non raide, bornée) : elle **déborde aussi**, parce que le balayage de l'anche
`q_anche` devient dominant (voir point 5) et s'emballe quand la fente se
ferme. La quasi-statique tombe précisément là où la compliance ne peut plus
être négligée.

### 3. L'aire d'ouverture n'est bornée ni en bas ni en haut

```python
area = self.b * max(c.gap + y, 1e-6)
```

- **En bas** : le plancher `1e-6` empêche la racine carrée de diverger mais
  **masque la fermeture**. Le diagnostic montre une ouverture à **−100,6 mm** :
  l'anche a traversé sa plaque de 10 cm et le code continue comme si de rien
  n'était. Or c'est la fermeture qui **sature le cycle limite** et crée la
  richesse harmonique.
- **En haut** : rien. L'aire croît linéairement sans fin, alors qu'une fente
  réelle sature dès que la languette l'a quittée.

### 4. L'amortissement n'était pas physique — **corrigé**

```python
w = np.sqrt(np.clip(np.linalg.eigvals(self.Minv @ self.K).real, 0, None))
self.C = self.M @ np.diag(2 * zeta * w)
```

Deux problèmes :

- `M` porte **42,9 %** de couplage hors-diagonale (la base du cantilever
  uniforme n'est pas la base propre de l'anche multi-tronçon), donc
  `M @ diag(2ζω)` est **non symétrique**. Une matrice d'amortissement non
  symétrique **injecte** de l'énergie selon la direction du mouvement — ce
  n'est plus un amortissement.
- `np.linalg.eigvals` renvoie les valeurs propres dans un **ordre arbitraire**,
  et elles se rapportent aux *vecteurs propres*, pas aux coordonnées modales :
  l'amortissement du mode 1 était appliqué à une coordonnée qui mélange les
  modes.

**Corrigé** : on passe par les vecteurs propres M-orthonormés du problème
généralisé `K x = ω² M x`, puis `C = M Φ diag(2ζω) Φᵀ M`, symétrique par
construction. Quatre tests le figent (symétrie, semi-définie positive,
proportionnalité à ζ, tri des fréquences).

### 5. Le balayage de l'anche domine le débit d'entrée

`q_anche = γ·q̇` vaut environ **1,2·10⁻⁴ m³/s** pour une anche vibrant à
100 Hz avec 1 mm d'amplitude, contre `q_in ≈ 10⁻⁵ m³/s`. Le terme de
l'anche est **douze fois** celui de l'alimentation.

Ce n'est pas anormal en soi — c'est même le mécanisme de couplage — mais ça
veut dire que la stabilité du modèle est gouvernée par ce terme, pas par
l'alimentation. C'est lui qui fait diverger les reformulations naïves. Toute
correction doit être jugée sur ce terme-là.

### 6. Le jeu de 9 mm — et pourquoi le corriger ne suffit pas

`gap = 9e-3` contre 0,05 à 0,3 mm en réalité : facteur 30 à 180.

Mais le résultat est instructif : en passant le jeu à 0,05 / 0,15 / 0,50 mm,
**la course ne bouge pas** (2,92 / 3,08 / 4,61 mm). L'anche bat tellement plus
loin que le jeu que celui-ci ne joue **aucun rôle**. Le mécanisme
d'obturation, qui devrait être au cœur du fonctionnement, n'est jamais
sollicité.

### 7. L'asymétrie de l'ouverture fixe la hauteur de la note

Testé en marge : une ouverture symétrique `S = b·|y|` module la fente **deux
fois par période** et sort **470 Hz pour une anche à 220 Hz** — une octave
faux.

Une anche libre ne débite que **dans un sens** ; l'autre demi-course est
fermée par la soupape de cuir. C'est exactement pourquoi pousser et tirer
utilisent deux anches distinctes. L'asymétrie de `S(y)` n'est pas un
raffinement de second ordre : **elle fixe la hauteur**.

---

## Où ça en est

**Corrigé et livré** : l'amortissement (point 4), avec ses tests.

**Diagnostiqué, non corrigé** : les points 1, 2, 3, 5, 6, 7. J'ai testé trois
reformulations de la cavité — loi inversée, pression en variable d'état,
réduction quasi-statique — et **les trois échouent**, chacune d'une manière
différente et instructive. Je ne te livre pas un modèle qui a l'air de
marcher.

## L'ordre dans lequel je reprendrais

1. **Mesurer l'impédance de source** (§ « comment vérifier ») — ça donne un
   nombre, pas une hypothèse, et ça ferme le débat débit/pression.
2. **Reformuler la cavité** en pression d'état avec suréchantillonnage ×8 à
   ×16, aire bornée en bas (fermeture nette, sans plancher) et en haut
   (saturation de fente), ouverture **asymétrique**.
3. **Valider sur les cinq critères** avant de faire confiance au modèle :
   existence de `p_on` ; amplitude ∝ √(p − p_on) ; hystérésis `p_on > p_off` ;
   fréquence proche de la fréquence propre (pas de son double) ; course < 1 mm
   et surpression < 3 kPa. `seuil.py` et `bifurcation.py` mesurent déjà les
   trois premiers, au banc comme en simulation — c'est le pont avec toute la
   partie stochastique de la thèse.
4. **Recalage** seulement ensuite : `doe_analysis` (Plackett-Burman) pour
   savoir *quels* paramètres comptent, avant d'optimiser à l'aveugle dans dix
   dimensions. C'est le recalage que tu n'avais pas pu faire.

---

# Suite : le modèle reformulé et l'outil de seuil (`reed_oscillator.py`)

## Ce qui est livré et fonctionne

`banc_recherche/reed_oscillator.py` — `FreeReedModel`, reformulation complète :

- **pression en variable d'état** (la cavité rigide ne gonfle plus) ;
- **ouverture asymétrique** : seul le déplacement qui dégage la fente ouvre le
  passage, et la soupape bloque le débit inverse ;
- **aire bornée des deux côtés** : fermeture nette avec fuite résiduelle (toute
  plaque réelle en a une), saturation une fois la languette sortie ;
- **amortissement modal correct**, symétrique ;
- **intégration suréchantillonnée** (×8 par défaut).

Vérifications (9 tests dans `tests/test_reed_oscillator.py`) :

| Contrôle | Résultat |
|---|---|
| Conservation de la masse à l'équilibre | débit sortant = `q_in` à 10⁻⁶ près |
| L'équilibre est bien un point fixe | dérivée < 10⁻⁶ |
| Course du bout en simulation | **+0,649 mm** (sous le millimètre) |
| Surpression | 616 Pa |
| Ouverture | bornée entre fuite et saturation |
| Divergence numérique | aucune |

Le modèle est **bien posé et physique**. Il ne s'auto-entretient pas encore.

## L'outil qui fait gagner du temps : `growth_rate` / `hopf_threshold`

Plutôt que de simuler une demi-seconde et de regarder si ça décroît, on
linéarise autour de l'équilibre statique et on lit les valeurs propres. Le
taux de croissance maximal donne directement la réponse :

- négatif → l'équilibre est stable, l'anche ne démarre pas ;
- positif → il est instable, l'anche démarre ; la partie imaginaire donne la
  fréquence de démarrage.

`hopf_threshold` cherche le changement de signe par dichotomie et renvoie
`(q_on, p_on, f_on)` — **le seuil de Hopf prédit**, la grandeur même que
`seuil.py` et `bifurcation.py` mesurent au banc. Modèle et mesure parlent
enfin de la même chose.

**1 ms par évaluation, contre ~1 seconde de simulation.** C'est ce qui rend
possible de tester une variante de modèle en quelques secondes au lieu d'une
après-midi.

## Les résultats négatifs, et ce qu'ils éliminent

Tous obtenus avec l'outil ci-dessus, donc vérifiables en quelques secondes.

| Variante testée | Taux de croissance | Conclusion |
|---|---|---|
| Bernoulli quasi statique + compliance | −14 à −64 s⁻¹ | stable partout |
| + **inertance de fente** (0,5 / 1,2 / 3,0 mm) | −47,5 (vs −46,8) | **sans effet** |
| + force dépendante de la position, anche ouvrante | −33 à −2,6 s⁻¹ | stable |
| + force dépendante de la position, anche fermante | **+88 s⁻¹ à 30 Hz** | instable, mais **pas la note** |

Deux enseignements solides :

1. **Le couplage à l'écoulement ajoute de l'amortissement**, il n'en retire
   pas. À 5·10⁻⁵ m³/s, le taux vaut ≈ −40 s⁻¹ contre −2,6 s⁻¹ pour l'anche
   seule : l'écoulement dissipe **quinze fois** plus que l'anche. La boucle
   est à rétroaction négative — l'anche s'ouvre, le débit sort, la pression
   tombe, la force diminue, l'anche revient.

2. **L'inertance de fente n'est pas le déphasage manquant.** C'était
   l'hypothèse la plus naturelle ; elle est éliminée par la mesure.

Le seul cas instable trouvé sort à **30 Hz pour une anche à 102 Hz** : c'est
une instabilité lente de type claquement, pas l'auto-oscillation acoustique.
Je ne la présente pas comme un succès.

## Ce qu'il reste à trouver — et comment le chercher vite

Le mécanisme d'entretien d'une anche **libre** n'est pas dans les ingrédients
testés. Les pistes qui restent, par ordre de vraisemblance :

1. **La force de pression pendant la traversée de la fente.** La languette
   passe *à travers* la plaque ; la distribution de pression sur sa surface
   change de signe selon qu'elle est au-dessus, dans, ou sous la fente. C'est
   le point où les modèles de la littérature sur l'anche libre se séparent de
   ceux de l'anche battante.
2. **Le temps de transit de l'air** dans la fente, qui n'est pas l'inertance
   (déjà éliminée) mais un retard pur.
3. **Le couplage aux modes de la chambre**, si sa fréquence propre approche
   celle de l'anche.

La méthode, elle, est acquise : coder la variante, appeler `growth_rate` sur
une plage de débits, lire le signe. Chaque hypothèse se teste en une minute.
C'est précisément l'outil qui manquait pour faire le recalage.

---

# Percée : le modèle auto-oscille

## Ce qui bloquait, et que l'analyse de stabilité a révélé

En linéarisant, la condition d'entretien s'écrit

    ∂q_out/∂y  >  γ_m · (γ_air·P_atm/V₀) · ∂q_out/∂p

À gauche ce qui **entretient** — la modulation du débit par le mouvement de la
languette. À droite ce qui **dissipe** — la réaction du ressort d'air au
balayage de la languette.

D'où le piège, invisible en simulation : **si l'ouverture sature**, alors
`∂h/∂y = 0`, donc `∂q_out/∂y = 0`. Le terme d'entretien s'annule **quelle que
soit la pression**. Or c'était exactement le cas : le bout se stabilisait à
+0,649 mm pour une saturation à 0,4 mm. La languette était soufflée hors de sa
zone de travail, et ne modulait plus rien.

Le second levier est le **volume acoustique effectif** `V₀`. Le critère
approché donne `V₀ ≳ γ_m·γ_air·P_atm·h/(2p)`. Avec la seule chambre géométrique
(7,9 cm³) le ressort d'air est trop raide et rien ne démarre ; à 40 cm³ ça
démarre. (Le critère scalaire demande 78 cm³ là où le modèle démarre à 40 :
c'est un ordre de grandeur, pas une égalité — la fonction `growth_rate` fait
foi.)

Ce volume n'est pas une cote à mesurer : il inclut le canal du sommier et le
couplage au réservoir du soufflet. **C'est un paramètre à recaler sur ton
banc.**

## Ce que le modèle prédit maintenant

Valeurs par défaut (anche sol2 à 102,1 Hz, V₀ = 40 cm³, saturation 0,5 mm) :

| | q_in (m³/s) | Pression | Fréquence |
|---|---|---|---|
| **Seuil de démarrage** | 2,40·10⁻⁶ | **23,0 Pa** | 119,2 Hz |
| **Seuil d'étouffement** | 3,93·10⁻⁵ | **379,8 Pa** | 119,2 Hz |

Trois prédictions testables au banc :

1. **L'oscillation est bornée des deux côtés.** Trop peu de pression : rien.
   Trop de pression : la languette est soufflée hors de la fente, l'ouverture
   sature, et le son s'éteint. C'est l'étouffement que connaît tout
   accordéoniste — et le modèle le produit sans qu'on le lui ait demandé.
2. **La fréquence de jeu dépasse la fréquence propre** de ~17 % (119 Hz pour
   une anche à 102 Hz) : c'est le ressort d'air qui raidit le système. Le
   rapport dépend de `V₀` — donc **mesurer ce décalage, c'est mesurer `V₀`**.
3. **La fréquence monte avec la pression** (119 → 131 Hz sur la bande, avec
   une saturation plus large). Facile à vérifier avec ton accordeur.

## Ce qui reste à faire

- **L'amplitude ne sature pas proprement.** À 1,5× le seuil, la course vaut
  0,836 mm — une valeur d'accordéon. Mais à 2,5× elle atteint 2,5 mm et à 5×
  plus de 5 mm, en croissant encore. Il manque un mécanisme de limitation :
  butée mécanique, raidissement géométrique de la languette à grande
  amplitude, ou impédance finie de la source (ta turbine n'est pas une source
  de débit idéale — c'est l'impédance qu'il faut mesurer).
- **Le spectre est pauvre** : 2 harmoniques au-dessus de −30 dB. Un vrai son
  d'anche en a une dizaine. La richesse viendra de la fermeture franche, donc
  du point précédent.
- **Hopf supercritique ou sous-critique ?** Près du seuil, l'amplitude part
  de zéro continûment — ça ressemble à un supercritique. Or les anches sont
  réputées sous-critiques, avec hystérésis `p_on > p_off`. C'est précisément
  ce que `seuil.py` mesure : **la comparaison modèle/mesure sur l'hystérésis
  est le prochain test décisif**, et il porte au cœur de ta thèse.

## La méthode, maintenant acquise

`growth_rate` répond en 1 ms, `instability_band` en une seconde. Tester une
variante de modèle ne coûte plus une après-midi de simulations mais le temps
d'écrire la variante. C'est ce qui manquait pour recaler.

---

# Cycle limite stable : l'impédance de source

## Ce qui manquait

Le modèle démarrait mais l'amplitude ne se stabilisait pas : 0,84 mm à 1,5×
le seuil, 2,5 mm à 2,5×, 5 mm à 5×, en croissant encore. Cause identifiée :
une **source de débit idéale** impose `q_in` quoi qu'il arrive — y compris
quand la languette ferme la fente. La pression y fait alors un coup de bélier
sans limite (8550 Pa mesurés), qui relance l'anche de plus belle.

Or une turbine réelle, comme un soufflet réel, **débite moins quand la
pression monte** : `q = q₀ − p/R`. C'est cette pente qui borne l'amplitude.

`Source(impedance_pa_s_m3=2e8)` est désormais le défaut. `inf` redonne la
source idéale, pour comparaison.

## Le cycle limite converge

Course crête-crête, tranches de 0,25 s, à 2× le seuil :

| t (s) | 0,50–0,75 | 0,75–1,00 | 1,00–1,25 | 1,50–1,75 | 2,75–3,00 |
|---|---|---|---|---|---|
| course | 1,1047 mm | 1,1320 | 1,1358 | **1,1364** | **1,1364** |

**1,1364 mm, figé sur 1,5 s**, avec σ_p ≈ 132 Pa. C'est un vrai cycle limite,
et c'est une amplitude d'anche d'accordéon.

⚠️ La convergence demande **~1,5 s** : les simulations de 0,9 s concluaient à
tort que l'amplitude croissait sans fin. Simuler trop court fait dire
n'importe quoi à un système lent à s'établir.

## Correction : le spectre n'était pas pauvre, je le mesurais mal

J'avais annoncé « 2 harmoniques au-dessus de −30 dB », donc un timbre pauvre.
C'était faux, pour deux raisons :

1. **Mauvaise grandeur.** Un accordéon rayonne par le **débit modulé** à
   travers la fente, pas par la pression de chambre. En champ lointain le
   rayonnement suit `dq/dt`.
2. **Mauvais fondamental.** Je détectais `f₀` par `argmax`, qui attrape le
   partiel le plus **fort**. Or la dérivation accentue les aigus de
   6 dB/octave : le pic migre sur h4, et tous les « harmoniques » étaient
   comptés par rapport à la mauvaise fréquence.

En comptant les harmoniques du vrai f₀ (120 Hz) sur `dq/dt` : **12
harmoniques** au-dessus de −30 dB. Le modèle produit bien un timbre riche.

**À retenir pour la suite : la sortie sonore du modèle, c'est `dq/dt`**, pas
`pressure`. `OscillationResult` fournit `flow_out` pour cela.

## Effet de l'impédance de source sur les seuils

| Source | Seuil de démarrage | Seuil d'étouffement |
|---|---|---|
| idéale (`inf`) | 23,0 Pa | 379,8 Pa |
| `R = 2·10⁸` (défaut) | 25,8 Pa | 379,8 Pa |
| `R = 5·10⁷` | 35,9 Pa | 379,8 Pa |

Le seuil de démarrage **monte** quand la source est plus molle — elle aide
moins au démarrage. Le seuil d'étouffement, lui, ne bouge pas : il est fixé
par la géométrie de saturation, pas par la source. Cohérent.

`R` est la pente de la caractéristique (p, q) de ta turbine — celle que le
balayage du facteur `Section` de `Mesures.py` mesure directement. **C'est le
premier paramètre à recaler.**

---

# Hystérésis : la bifurcation est sous-critique

## Le résultat

En repartant d'un **cycle limite établi** et en baissant la consigne :

| q / q_on | Pression d'équilibre | Course | |
|---|---|---|---|
| 0,95 | — | 0,498 mm | oscille encore |
| 0,85 | — | 0,379 mm | oscille encore |
| 0,82 | 19,44 Pa | 0,292 mm | **oscille encore** |
| 0,79 | 18,40 Pa | 0,001 mm | s'éteint |
| 0,70 | 16,35 Pa | 0,000 | s'éteint |

- **p_on = 25,76 Pa** (démarrage)
- **p_off ≈ 19,44 Pa** (extinction)
- **hystérésis p_on / p_off ≈ 1,33**

L'oscillation **persiste en dessous du seuil de démarrage** : la bifurcation
est **sous-critique**. C'est le comportement des anches réelles, et c'est le
cœur de la thèse — `p_on > p_off`, ce que `seuil.py` mesure au banc par rampe
montante puis descendante. **Le modèle et la mesure sont désormais
comparables sur cette grandeur.**

`extinction_threshold()` rend la mesure reproductible, et un test la fige
(hors suite par défaut, ~40 s : `BANC_TESTS_LENTS=1`).

## Correction : j'avais d'abord conclu au supercritique, à tort

Deux erreurs successives, qu'il vaut la peine de consigner :

1. **Reconstruction d'état bancale.** Pour repartir d'un cycle établi,
   j'avais tenté de reconstruire l'état modal (N modes) à partir du seul
   déplacement du bout (un scalaire). C'est **sous-déterminé**, et ça donnait
   une extinction systématique — donc « supercritique ». `simulate()` renvoie
   maintenant `final_state`, et ne perturbe plus l'état quand on lui en
   fournit un : la reprise est exacte.

2. **La loi en racine m'a induit en erreur.** `A ∝ √(q − q_on)` est
   effectivement mesurée (rapports 1,35 / 1,29 / 1,35 / 1,45), et c'est la
   signature *attendue* d'un supercritique. Mais elle est **nécessaire, pas
   suffisante** : une bifurcation faiblement sous-critique présente la même
   loi au-dessus du seuil, avec en plus une petite zone d'hystérésis. Seul le
   test de persistance tranche.

À retenir : **pour distinguer super- de sous-critique, il faut redescendre**,
pas seulement monter. C'est exactement pourquoi `seuil.py` fait une rampe
dans les deux sens.

## Ce que ça donne à comparer au banc

Trois nombres, et une manière de les obtenir des deux côtés :

| Grandeur | Modèle | Au banc |
|---|---|---|
| Seuil de démarrage `p_on` | 25,8 Pa | `seuil.detect`, rampe montante |
| Seuil d'extinction `p_off` | 19,4 Pa | rampe descendante |
| Rapport d'hystérésis | 1,33 | le rapport des deux |

Si le rapport mesuré diffère nettement de 1,33, c'est le **volume acoustique
effectif** et l'**impédance de source** qu'il faut recaler en premier : ce
sont les deux paramètres dont dépend le plus la largeur de l'hystérésis.

---

# La languette ne comprime pas sa chambre

## Le symptôme, et pourquoi il était impossible

Le modèle faisait chanter une anche de **102,1 Hz** à **119,2 Hz**. Soit
**+267 cents** — une tierce mineure. Et ce décalage ne bougeait pas : de 1,3
à 8 fois le seuil, la note restait plantée à 118,8 Hz.

Ce n'était pas défendable. Tout le métier de l'accordeur repose sur le
contraire : on lime la languette, et la note suit. Une lame de 102 Hz sonne
102 Hz. Un modèle qui la fait sonner une tierce plus haut ne décrit pas une
anche libre.

## La cause : un terme de piston qui n'a pas lieu d'être

Le bilan de la chambre s'écrivait

    dp/dt = (γ·P/V₀) · (q_entrant − q_sortant − Γ·ẏ)

Le dernier terme, `Γ·ẏ`, est le **volume balayé par la languette**. Il est
juste pour une anche **battante** — une clarinette, un hautbois : la lame est
plaquée sur la table, elle *ferme* l'ouverture, c'est un vrai piston dans la
paroi de la cavité, et ce qu'elle balaie comprime bel et bien l'air.

Une anche **libre** n'est pas plaquée sur quoi que ce soit : elle est *dans*
sa fente, à quelques dizaines de microns de jeu. Quand elle s'écarte, ce
qu'elle libère d'un côté de la plaque est repris dans l'instant par la fente
elle-même — qui est exactement là où elle se trouve. Elle ne comprime rien.
Elle **module une ouverture**, et `opening()` en rendait déjà compte.

Le terme comptait donc le déplacement de la languette **deux fois**, et
ajoutait une raideur parasite `γ·P_atm·Γ²/V₀` en série avec celle de la lame.
D'où les 267 cents.

C'est, littéralement, la différence entre l'anche battante et l'anche libre —
et dans ce modèle elle ne se voyait nulle part ailleurs que dans ce terme.

## La correction

`Slot.sweep_coupling`, **0 par défaut** (anche libre), 1 pour une battante.
Un coefficient, une ligne dans `deriv`.

## Ce que ça change, mesuré

**La note redevient celle de la lame**, et l'écart résiduel se comporte comme
il doit : la raideur d'air ajoutée est à peu près fixe, celle de la languette
croît comme `f²`, donc l'écart s'efface vers l'aigu.

| languette | avant | après | écart après |
|---|---|---|---|
| 102,1 Hz | 119,2 Hz (+267 c) | **103,9 Hz** | **+30 cents** |
| 220 Hz | — | 221,2 Hz | +10 cents |
| 440 Hz | — | 440,5 Hz | +2 cents |
| 880 Hz | — | 880,1 Hz | 0 cent |

**La chambre réelle suffit.** Il fallait auparavant gonfler le volume à
40 cm³ — cinq fois la chambre géométrique — pour obtenir un démarrage. Ce
n'était pas un « volume acoustique effectif », c'était un cautère sur le
terme fantôme. Avec 7,9 cm³ (35 × 15 × 15 mm, une cote qu'on mesure au pied à
coulisse), le modèle démarre. Le défaut de `Chamber` est revenu à cette
valeur.

**La note baisse quand on pousse.** De 1,3× à 2× le seuil : **−15,7 cents**.
C'est le sens que connaît tout accordéoniste, et que l'ancien modèle prenait
à l'envers (+8 cents sur toute la plage). À vérifier au banc — c'est une
prédiction chiffrée et ton accordeur la lit au centième.

**Hors bande, l'écoulement lâche complètement.** Au-dessus de l'étouffement,
l'ouverture sature, `∂h/∂y = 0`, et comme il ne reste aucun autre chemin de
`ẏ` vers `p`, le taux de croissance tombe **exactement** sur `−ζω₁`. C'est
propre, et c'est vérifiable à la virgule.

## Deux tests figeaient le bug

Il faut le consigner, parce que la leçon vaut pour la suite.

1. `test_frequence_de_demarrage_proche_du_mode_de_l_anche` tolérait
   `1.0 < f_jeu/f_lame < 1.4` — jusqu'à **+580 cents**. Une borne assez large
   pour laisser passer une tierce mineure d'erreur. **Une borne large ne
   teste rien.** Elle est maintenant à ±50/+80 cents.

2. `test_hors_bande_l_ecoulement_dissipe_fortement` affirmait que
   l'écoulement dissipe « quinze fois plus que l'anche » (≈ −40 s⁻¹ contre
   −2,6). Ces 40 s⁻¹ étaient produits par le terme de balayage fantôme, pas
   par l'écoulement. Le test mesurait un bug et le protégeait.

3. `test_chambre_trop_petite_ne_demarre_pas` figeait le fait que la chambre
   réelle ne démarre pas — conséquence du bug, promue en propriété.

Trois garde-fous sur quinze protégeaient l'erreur qu'ils auraient dû
attraper. Un test qui fige un comportement sans le confronter à une grandeur
mesurable fige aussi bien un bug qu'une loi.

## Ce qui reste franchement faux

**Le seuil de démarrage.** Il vaut maintenant 1,80 Pa à 102 Hz et 1781 Pa à
880 Hz — trois décades sur l'étendue du clavier, là où un accordéon réel en
demande à peu près une (de l'ordre de 100 à 1000 Pa partout). Le grave part
beaucoup trop facilement, l'aigu beaucoup trop difficilement.

Ce n'est pas l'amortissement de la lame qui l'expliquera : le seuil varie
comme `ζ²`, il faudrait un `Q` de 12 pour remonter le grave à 180 Pa, alors
qu'une anche pincée sonne plusieurs secondes. Il manque donc un terme dans le
**moteur**, pas dans les pertes. Pistes, dans l'ordre :

1. **La force de pression ne s'applique pas sur toute la languette.** Le
   modèle applique `p·Γ` sur toute sa surface en permanence. La chute de
   pression se fait en réalité *à travers la fente* : une fois la languette
   dégagée, elle est dans le jet et ne voit plus `p`.
2. **Les pertes visqueuses dans le jeu de fente** (20 à 50 µm), que Bernoulli
   seul ignore : à petite ouverture le débit n'est pas en `h·√p` mais bien
   plus faible.
**L'amplitude n'est plus bornée du tout** — et c'est la contrepartie
honnête de la correction, qu'il faut dire sans l'enjoliver :

| q / q_on | 2 | 4 | 8 | 16 |
|---|---|---|---|---|
| course crête-crête | 2,15 mm | 9,5 mm | 21,2 mm | **47,4 mm** |
| note (vs 1,3×) | −15,7 c | −36,4 c | −37,8 c | −39,1 c |

47 mm de course pour une languette de 55 mm de long, c'est une absurdité
mécanique. Le terme de balayage fantôme, en plus de fausser la note, servait
de frein : il prélevait de l'énergie proportionnellement à la vitesse. En le
retirant, on découvre qu'**il n'y avait pas d'autre mécanisme de
limitation** — la saturation de cycle limite à 1,1364 mm consignée plus haut
était produite par le bug, pas par la physique.

La colonne de droite est en revanche un vrai gain : la note **baisse quand on
pousse**, ce que fait toute anche d'accordéon et que l'ancien modèle prenait
à l'envers (+8 cents sur toute la plage). −39 cents à pleine nuance, à
confronter au banc.

Le limiteur manquant est très probablement le point 1 ci-dessus, et les deux
défauts n'en font qu'un : le modèle applique `p·Γ` sur toute la languette
**quelle que soit sa position**. Une fois la languette dégagée de la fente,
elle est dans le jet et ne voit plus la chute de pression — la force
s'effondre et la ramène. Cette même dépendance en position expliquerait à la
fois le seuil trop bas dans le grave et l'amplitude non bornée.

⚠️ À vérifier : ces courses sont mesurées sur 1,2 s de simulation, et
l'établissement du cycle limite demande ~1,5 s (cf. plus haut). Elles
croissent encore peut-être. Le sens du résultat ne change pas.

C'est le prochain chantier, et il se teste avec le même outil :
`growth_rate`, une minute par hypothèse. À noter : la force dépendante de la
position avait déjà été essayée et écartée — mais **avec le terme fantôme
encore en place**, qui dominait tout. L'essai est à refaire.

---

# Deux anches, une note : chambres, table d'harmonie, clapet

`banc_recherche/coupled_reeds.py` — le réseau acoustique d'une note MM :
soufflet → anche → chambre → trou de la table d'harmonie → canal commun sous
le clapet → clapet → dehors (et l'inverse en tiré). Chaque élément est une
grandeur mesurable : un volume, une masse d'air `ρ·ℓ/S`, une perte
d'orifice. Le son sort par le clapet (monopôle, `ρ·dq/dt`), la puissance
rayonnée et le rendement se calculent sur le débit du clapet. Un mode par
anche, pour pouvoir simuler des secondes (un battement à 1 Hz en demande
plusieurs). Tests : `tests/test_coupled_reeds.py`.

## Ce que le réseau honnête a d'abord dit : rien ne démarre

Avec les vraies pertes des trous et du clapet, aucune anche ne s'entretient.
Balayé à 1000 Pa, poussé et tiré :

| mécanisme ajouté | croissance |
|---|---|
| aucun | −2,64 /s (l'amortissement de la lame seule) |
| inertie de l'air dans la fente | −2,64 /s |
| balayage de la languette, grand trou | −2,98 /s |
| balayage, petit trou (20 mm²) | −14,9 /s |

La théorie linéaire dit pourquoi. Une chambre n'entretient la languette que
si son impédance est dominée par la **compliance** à la fréquence de jeu
(pression en retard de 90° sur le débit → force en phase avec la vitesse).
Un vrai trou de table la **ventile** : Helmholtz chambre/trou ≈ 1,9 kHz, donc
impédance inertielle sur presque tout le clavier, et la chambre amortit.

C'est cohérent avec Ricot, Caussé et Misdariis (JASA 117, 2005) : une anche
d'accordéon démarre **même sans couplage acoustique**, par l'aérodynamique
de l'écoulement dans sa fente. Un modèle à pression uniforme sur la
languette ne contient pas ce mécanisme. C'est la vraie question ouverte, et
c'est là qu'une simulation d'écoulement (CFD) servirait — sur la fente,
pas sur l'instrument.

## Le démarrage calé, et où le mettre

Faute de mieux, on reprend le mécanisme du modèle à une anche : la
résistance effective de 5·10⁶ Pa·s/m³ (`Source`). Où la placer change tout :

| placement | 20 ¢ de désaccord (1,21 Hz entre lames) |
|---|---|
| partagée, au clapet | **verrouillées** à l'unisson — jusqu'à 80 ¢ (4,9 Hz) |
| propre à chaque chambre | battent à **1,209 Hz** |

Aucune musette réelle ne se verrouille à 80 ¢ : l'excitation d'une anche
lui est **propre**, et le canal commun ne les couple que faiblement. C'est
le placement par défaut.

## Ce que le modèle prédit, à vérifier au banc

- **Les voix se tirent près de l'unisson** : battement joué / écart des
  lames = −27 % à 1 ¢, −20 % à 2 ¢, −12 % à 3 ¢, rien à 5 ¢ (La grave de
  référence, 300 Pa, 4 s). Mesurable à l'accordeur : accorder une anche en
  bloquant l'autre, puis débloquer et relire le battement.
- **L'air ne double pas** : deux anches identiques consomment 1,56 fois ce
  que consomme une seule (10,8 contre 13,9 cm³/s chacune).
- **Deux anches en phase rayonnent mieux** : rendement 2,9·10⁻⁵ contre
  1,5·10⁻⁵ pour une seule.
- **Ressort d'air** : seule, l'anche joue +61 ¢ au-dessus de sa lame (le
  modèle à une anche donnait +49 ¢ au seuil).

⚠️ Valeurs par défaut du sommier = ordres de grandeur, à relever sur
l'instrument ; courses de 3–4 mm pour cette lame de grave très souple, et
démarrage limité à quelques centaines de pascals (le chantier des seuils,
plus haut, reste entier).

## Et Elmer ?

Pas pour remplacer ce réseau : pour en **calculer les paramètres** sur la
vraie géométrie. Une simulation acoustique (Helmholtz) de la chambre, du
trou et du canal donne leurs masses et compliances effectives, corrections
d'extrémité comprises, et la résistance de rayonnement du clapet. Le
mécanisme de démarrage, lui, relève de l'écoulement dans la fente :
Navier-Stokes instationnaire avec interaction fluide-structure — un chantier
de CFD, plus lourd, et le seul qui répondrait à la question ouverte
ci-dessus.

## Correction : la section qui se ferme — et l'audit qui va avec

Ce qui précède (« rien ne démarre », puis la résistance calée et son
placement) reposait sur une loi de passage **héritée du modèle à une
anche** : `FreeReedModel.opening()` fait **ouvrir** le passage par le souffle.

Si au contraire la languette, levée au repos du côté d'où vient l'air, est
poussée **dans** sa fente (passage qui se referme, puis se rouvre de
l'autre côté), la dérivation linéaire donne un mécanisme d'entretien propre
à chaque anche : la masse d'air du chemin change le ralentissement du débit
en surpression en phase avec la vitesse. Le modèle le confirme en retirant
un ingrédient à la fois ; plus aucune résistance n'est calée.

C'est une **hypothèse de géométrie à confirmer sur l'instrument**, et le
reste du modèle contient des valeurs devinées et des simplifications. Tout
est classé, élément par élément, avec les expériences qui peuvent le
contredire, dans **`docs/audit_deux_anches.md`**. Les publications citées
ont servi d'idée de départ, pas de preuve.

`FreeReedModel` garde l'ancienne loi : il nourrit le moteur temps réel et la
synthèse (`hybrid`, `live`, `embedded`). L'y corriger se fera avec des
mesures en main.
