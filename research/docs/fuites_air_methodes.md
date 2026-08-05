# Trouver les fuites d'air d'un accordéon — méthodes (du prouvé au révolutionnaire)

> Contrainte : **presque rien** (soufflet, carte son, un micro, un smartphone).
> Aucun détecteur ultrason du commerce (des centaines d'€), aucune caméra
> thermique. Idée centrale : **une fuite est un endroit où l'air s'échappe sans
> faire de son audible** — on va la *forcer à chanter*, puis l'entendre même
> noyée dans le bruit, et enfin la *rendre visible*.

Où fuit un accordéon : soupapes (peaux/clapets), plaques d'anches et cire,
joints du soufflet (coins, cadre), tampons du clavier, tiroirs de registre.

---

## 0. Le fond de physique
Un jet d'air à travers un petit orifice sous pression devient **turbulent** et
rayonne un **bruit large bande** (sifflement) qui monte haut en fréquence (jusque
dans l'ultrason). Deux leviers :
- **fréquentiel** : le sifflement de fuite est riche en aigus là où la voix de
  l'anche et le bruit de pièce sont pauvres → filtrer haut = isoler la fuite ;
- **temporel** : si on **module** la pression, l'intensité du sifflement suit la
  modulation → on peut extraire ce qui bouge à *notre* rythme et rejeter tout le
  reste.

---

## 1. ⭐ Méthode phare — **imagerie de fuite par détection synchrone (lock-in)**
*(le cœur révolutionnaire, cheap, et propre à ta thèse)*

**Principe.** On fait varier la pression du soufflet **sinusoïdalement** à une
fréquence connue `f_mod` (2–10 Hz — ton soufflet motorisé sait déjà faire des
courses contrôlées). Chaque fuite devient alors une **source acoustique dont
l'intensité clignote à `f_mod`**. On promène un micro bon marché près de la
surface ; pour chaque position on :
1. filtre la bande de sifflement (≈ 4–20 kHz) ;
2. prend l'**enveloppe** de ce sifflement ;
3. fait une **détection synchrone** (lock-in) de cette enveloppe à `f_mod`.

Le lock-in ne garde que ce qui bat exactement à `f_mod` et à la bonne phase : le
bruit de la pièce, la circulation, ta respiration — tout ce qui ne bat pas à
`f_mod` — est **rejeté**. On gagne des dizaines de dB de rapport signal/bruit.
On obtient une **carte de fuite** : là où le lock-in est fort = la fuite.

**Pourquoi c'est neuf.** Personne ne fait ça sur un accordéon. C'est le principe
de l'amplificateur à détection synchrone (le graal du signal faible en physique)
appliqué à l'acoustique de fuite, avec ton **soufflet comme modulateur** et ta
**DSP comme lock-in**. Coût : le soufflet que tu as + un micro + du code.

**Matériel** : soufflet motorisé (déjà là) ; un micro (même celui du téléphone,
mieux un petit micro-cravate ou MEMS à ~48–96 kHz) ; carte son.

**Code** : `banc_recherche/leak.py` → `lockin`, `acoustic_leak_strength`,
`leak_map`. **Poésie de thèse** : le lock-in *fait chanter la fuite silencieuse*
à ta fréquence — comme l'attention équanime (Vipassana) qui extrait un signal
ténu du fond d'agitation, en n'écoutant que ce qui bat au bon rythme.

---

## 2. ⭐ Localisation à **deux micros** (corrélation croisée, TDOA)
Le bruit de fuite arrive à deux micros avec un **décalage temporel** selon la
position de la fuite. La corrélation croisée donne ce délai → on triangule.
Deux micros + la géométrie suffisent ; c'est ce que l'industrie fait pour les
canalisations. Réutilise l'inter-spectre déjà écrit (`transfer`, `frf`).
**Code** : `leak.tdoa_delay`.

---

## 3. ⭐⭐ **Schlieren orienté fond (BOS)** — rendre le jet *visible* avec un
téléphone *(quasi gratuit, spectaculaire)*
L'air qui s'échappe a une densité (donc un indice optique) différente. Le
**Background-Oriented Schlieren** filme un **fond moucheté imprimé** à travers le
jet : le logiciel (flux optique) mesure les micro-déformations de l'image et
**révèle le jet invisible**. Encore plus net si tu souffles dans le soufflet un
air **tiède/humide** (ton haleine) ou riche en CO₂ : le contraste d'indice monte.
Matériel : un smartphone + une feuille de speckle imprimée + du code (OpenCV).
C'est une technique de labo d'aérodynamique, ramenée à ~0 €. **Effet « waouh »
publiable.** *(Scaffold : `leak_bos.py`, OpenCV optionnel.)*

---

## 4. Signature **globale** de fuite par FRF / facteur Q *(quantitatif)*
Une fuite amortit la cavité d'air de l'instrument. On envoie un **balayage sinus**
(ton `frf.py`) dans l'instrument scellé et on mesure le **facteur Q** (ring-down)
des résonances : plus ça fuit, plus Q chute (l'énergie s'échappe). En comparant à
une référence scellée, on **quantifie la fuite totale** et sa signature spectrale.
Ne localise pas, mais **mesure** — parfait pour un chapitre de thèse.
**Code** : `frf` + `stochastic`/ring-down (déjà là).

---

## 5. Traceur gazeux + capteur bon marché
Remplir le soufflet de **CO₂** (SodaStream, pastille effervescente, ou souffle) et
scanner la surface avec un petit **capteur CO₂/MQ** (~5–10 €) : la concentration
monte aux fuites. Chimique, robuste, cheap. Variante fumée (encens) + caméra
téléphone + flux optique : on voit où la fumée sort.

---

## 6. Signature **par anche** (gratuit, malin)
Une fuite près d'une anche vole une partie de son air → l'anche **démarre plus
tard, sonne moins fort, se désaccorde** d'une manière caractéristique. Ton
**accordeur** mesure déjà cents/niveau/`Tresp` par anche : une fuite locale
laisse une empreinte. Croisé avec un plan d'expériences (`doe_analysis`), on
remonte à la fuite sans micro de scan.

---

## Le combo que je recommande pour la thèse
1. **Lock-in** (§1) — la mesure phare, localisante, robuste, cheap, à toi.
2. **BOS** (§3) — la visualisation qui rend l'invisible visible (l'image forte).
3. **Q/FRF** (§4) — le chiffre global qui quantifie l'étanchéité.

Les trois racontent la même chose sous trois angles : rendre **audible**,
**visible**, **mesurable** ce qui, d'ordinaire, s'échappe sans laisser de trace.
C'est, mot pour mot, la démarche de ta thèse : donner forme à ce qui fuit en
silence.
