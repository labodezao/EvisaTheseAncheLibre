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
