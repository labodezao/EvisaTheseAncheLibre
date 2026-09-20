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
