# Outils de mesure par chapitre (d'après `design_theory.lyx`)

Cartographie de la table des matières du manuscrit **Conceptual accordion
design : Theory** → grandeur à mesurer, instrument, outil logiciel, et **statut**
vis-à-vis des deux modules du dépôt.

**Légende de statut**
- ✅ **couvert** par un module existant (`web/` accordeur, `research/`, `firmware/`)
- 🟡 **partiel** : la brique existe, il manque un capteur ou un traitement
- ➕ **à ajouter** : nouvel outil proposé (voir §« Nouveaux outils » en bas)

Principe directeur : **réutiliser le matériel déjà là** (table X à pas-à-pas,
excitation EM Behringer/OUTTA, capteurs P/Q, stroboscope multi-harmonique,
estimateur Matrix Pencil) avant d'acheter.

---

## Partie I — Reeds (anches)

### Static and modal analysis

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Forme statique de l'anche (courbure au repos) | Capteur laser de déplacement monté sur la table X (balayage) ; à défaut microscope numérique + détection de contour | OpenCV (edge), scan piloté par le firmware | ➕ (réutilise la table X) |
| Fréquences propres f₁…fₙ | **Excitation EM** (sweep) + micro ou pickup optique | `excitation.response` (sweep → résonances) | ✅ |
| Déformées modales (mode shapes) | Stroboscope + caméra, ou vibromètre laser (LDV) si dispo | strobe multi-harmonique (accordeur) + imagerie | 🟡 (strobe ✅, imagerie ➕) |
| Inharmonicité (rapports des partiels) | Micro de mesure | analyse harmonique de l'accordeur (FFT + peak-matching) | ✅ |
| Anches iso-fréquence (comparaison f₀) | Micro | mode polyphonique / registre de l'accordeur | ✅ |
| Amortissement / facteur Q | Décroissance après excitation EM (ring-down) | **Matrix Pencil** (`web/js/dsp/subspace.js`) estime déjà les pôles = amortissement | 🟡 (estimateur ✅, séquence « step + décroissance » ➕) |

### Material of reeds

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Masse volumique ρ | Balance de précision + pied à coulisse / microscope | tableur | ➕ (manuel) |
| Module d'Young E | Jig cantilever : lamelle bridée, excitée EM → f₁ → E (Euler-Bernoulli) | résonance (`excitation`) + calcul E | ➕ (réutilise EM + `CLAMP`) |
| Amortissement matériau | Ring-down cantilever | Matrix Pencil | 🟡 |

### The reed socket / physical model / FEM (FSI)

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Jeu anche/plaque, étanchéité socle | Jauge d'épaisseur, mesure optique | — | ➕ |
| Validation modèle physique / FEM couplé fluide-structure | (données ci-dessus : f₀, déformées, amortissement, forme statique) | **CalculiX / Elmer / SfePy** (FSI open source) pour le modèle ; les mesures servent de validation | ➕ (chaîne FEM) |

## Self-sustained conditions

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Énergie stockée / dissipation (Q) | Ring-down EM | Matrix Pencil | 🟡 |
| Couplage multi-anches (battements, accrochage de modes) | Micro | mode **polyphonique** de l'accordeur (2–4 anches, battements) | ✅ |
| Saturation harmonique (amplitude des partiels vs pression) | Banc : rampe de pression + micro | DOE (`doe`) + FFT | ✅ |
| Hystérésis vs auto-entretien (p_on / p_off) | Banc : rampe montée/descente | `seuil.detect` (porté de `mes_seuil_autoentretien`) | ✅ |

## Temporal and frequency of free reed

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Décalage de fréquence f₀(pression) | Banc DOE + micro | `plan_exp.csv` (Freq0) + zoom accordeur | ✅ |
| Temps de réponse (Tresp) | Micro | `analysis.praat_calcs` (Tresp) | ✅ |
| Intensité | Micro **calibré** (SPL) | intensité Praat | 🟡 (calibration ➕) |
| Hystérésis | Rampe de pression | `seuil` | ✅ |

---

## Partie II — Reed blocks coupling

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Ouverture de section, pression & débit → **impédance** | BMP280 (P) + SFM3000 (Q) sur le banc | `impedance.compute` (P/Q, P·Q) | ✅ |
| **Impédance acoustique** de cavité / problème inverse | **Méthode à 2 microphones** (tube type Kundt) avec l'EM comme source | `excitation` (sweep + inter-spectre) → matrice de transfert | ➕ (2 micros dans la Behringer) |
| Rayonnement acoustique | Sonde d'intensité (2 micros) | inter-spectre | ➕ |
| Géométrie du reed block / « bend » | DOE section×clapet | `doe` / `plan_exp` | ✅ |
| Dissipation en cavité | Ring-down cavité | Matrix Pencil | 🟡 |

---

## Partie III — Mechanics and valves

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Transmittance acoustique des clapets | Rig **2 micros** (matrice de transfert, perte par transmission TL) | `excitation` + calcul TL | ➕ |
| Influence du matériau d'étanchéité | Idem (TL) + essai de fuite | 2 micros + test de fuite | ➕ |
| Dynamique du clavier (force/course) | **Cellule de charge (HX711)** + position (encodeur AS5600 / capteur linéaire) | firmware (nouvelle voie) + log | ➕ |
| Détection de fuites (annexe) | **Essai de décroissance de pression** (fermer vanne, mesurer chute P) ou détecteur ultrason | BMP280 + commande firmware `LEAKTEST` | ➕ (logiciel sur matériel existant) |

---

## Partie V — Other parts (bellows, timbral)

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Soufflet (pression, débit, uniformité) | Soufflet motorisé + BMP280 + SFM3000 | firmware + télémétrie | ✅ |
| Grille / caisse de résonance (modes) | Marteau d'impact + accéléromètre/micro → FRF | inter-spectre (`excitation`) | ➕ (marteau + accéléro) |
| Clapets et sourdines (perte par transmission) | Rig 2 micros | matrice de transfert | ➕ |

---

## Partie VI — Measuring and quantify

| Grandeur | Instrument | Outil logiciel | Statut |
|---|---|---|---|
| Enregistrement micro | Micro de mesure + interface **Behringer 24 bits** | `audio` (sounddevice) | ✅ |
| Enregistrement accéléromètre | Accéléromètre piézo léger sur la plaque (3ᵉ voie Behringer) | `audio` (multi-voies) — les campagnes HDF5 ont déjà `Mesures_Accelerations` | 🟡 (voie ➕) |
| Accordéon instrumenté « in-vivo » | Micro-capteurs de pression en cavité + position soufflet + micro, log **ESP32** sans fil | firmware + télémétrie | ➕ (variante embarquée) |
| Table d'expérience « in-vitro » | **Ce projet** (banc + GUI) | `research/` + `firmware/` | ✅ |

---

## Nouveaux outils proposés (priorisés)

Du plus rentable (réutilise l'existant) au plus lourd :

1. **Rig à 2 microphones + EM** → impédance acoustique de cavité et perte par
   transmission des clapets/sourdines. La Behringer offre **1 entrée stéréo +
   1 mono = 3 voies** ; `excitation.py` calcule déjà l'inter-spectre. Ajout :
   deux micros de mesure + le calcul de matrice de transfert. **Fort levier
   scientifique, faible coût.** (chapitres : impédance & problème inverse,
   clapets, grille/caisse)
2. **Amortissement / Q par ring-down EM** → excite, coupe, laisse décroître ;
   `subspace.js` (Matrix Pencil) rend déjà les pôles = fréquence + amortissement.
   Ajout : une séquence « step puis silence » côté banc + un petit traitement.
   (self-sustained, dissipation, matériau)
3. **Essai de fuite par décroissance de pression** → commande firmware
   `LEAKTEST` : fermer la vanne, mesurer la chute BMP280 → conductance de fuite.
   **100 % logiciel sur le matériel actuel.** (annexe fuites, étanchéité)
4. **Capteur laser de déplacement sur la table X** → forme statique de l'anche
   et amplitude de vibration, sans contact (réutilise le pas-à-pas). Réf abordables :
   optoNCDT ILD1220 / Panasonic HG-C / Keyence IL. (forme statique, déformées)
5. **Jig cantilever pour E** → lamelle bridée (`CLAMP`), excitée EM, f₁ → module
   d'Young. Réutilise EM + bridage. (matériau)
6. **Voie accéléromètre** (piézo léger) dans la 3ᵉ entrée Behringer → on
   réactive le `Mesures_Accelerations` déjà présent dans les campagnes HDF5.
7. **Dynamique de clavier** : cellule de charge **HX711** + encodeur **AS5600**
   → courbe force/course d'une touche (nouvelle voie firmware). (clavier)
8. **Imagerie stroboscopique des déformées** : le stroboscope multi-harmonique
   de l'accordeur + une caméra → visualisation des modes et du « bend ».
9. **Chaîne FEM/FSI open source** (**CalculiX**, **Elmer**, ou **SfePy**) pour
   les chapitres « physical model » / « finite element FSI » ; les mesures
   ci-dessus servent de **validation**.
10. **Métrologie de base** : balance de précision + pied à coulisse/microscope
    (ρ, dimensions) — manuel, indispensable au calage des modèles.

### Ce qui est déjà couvert (rappel)

f₀ et inharmonicité, mode polyphonique/battements, f₀(pression), Tresp,
seuil d'auto-entretien (hystérésis), impédance P/Q et P·Q, DOE
Section×Pression×Clapet, soufflet motorisé instrumenté, enregistrement
Behringer + analyse Praat, stroboscope multi-harmonique.

> Résumé : **le cœur « pression → son » est couvert** par tes deux modules. Les
> ajouts à plus fort levier concernent l'**acoustique** (rig 2 micros) et la
> **mécanique/matériau** (ring-down Q, laser de forme, jig E, clavier).
