# Fréquences des deux anches : justesse et cohérence avec le battement (v57, v58)

Demande d'Ewen (11/10/2026, après la v56) : « il faut vérifier qu'on a bien une mesure précise des fréquences des 2 anches
et que ça colle dans le cas général ». Ce que « ça colle » veut dire : f(8'+) − f(8') doit valoir le battement de
l'enveloppe du volume (celui qu'on entend, stable à 0,01-0,05 Hz depuis la v56), et la hauteur de CHAQUE anche doit être
juste et ne pas sauter. La v58 (audit couplage du 11/10/2026) corrige la définition de « juste » et le banc, puis ajoute le
peigne rigide pour les anches qui se tirent.

## Ce que vaut « la fréquence de chaque anche » quand elles se tirent (v58)

Deux anches libres couplées par la chambre sont deux oscillateurs auto-entretenus faiblement couplés (Adler 1946 ; Pikovsky,
Rosenblum, Kurths 2001 ; sur des tuyaux d'orgue : Abel, Bergweiler, Gerhard-Multhaupt 2006, JASA 119, 2467). Hors accrochage,
la phase relative tourne de façon non uniforme (dψ/dt = 2πΔ0 − K sin ψ) : chaque anche subit une modulation de phase au
rythme du battement observé Ω = √(Δ0² − κ²). Conséquences : le battement observé est plus lent que l'écart des anches seules ;
la fréquence moyenne de chaque anche est tirée vers l'autre de (Δ0 − Ω)/2 ≈ β²Ω/… ; f2 − f1 (moyennes) = Ω exactement.

- **La bonne définition** : la fréquence MOYENNE de chaque anche en place sur un nombre ENTIER de périodes de battement
  (`fenetreEntiere`, `vraieEntiere` de `synthese-anches.mjs`). Sur une période entière la modulation de phase s'annule. C'est ce
  que le luthier accorde. La fréquence « anche seule » n'est pas observable dans le son couplé sans modèle ; le tirage
  (β²Ω, 0,2 à 0,4 ¢ pour β = 0,2) ne s'affiche pas.
- **Les niveaux du banc de la v57 étaient irréalistes** : en régime d'Adler β ≈ κ/(2Ω) ; β = 0,5 à 1,2 rad au fondamental impose
  des anches accrochées (plus de battement). Réaliste : β ≤ 0,3 rad (raie latérale ≤ −16 dB), AM ≤ 15 %. Les anciens cas sont
  gardés, étiquetés « extrême », hors tolérance. Les 1 à 4 ¢ résiduels de la v57 venaient surtout de ces niveaux
  (extrêmes) ; en régime d'Adler, d'une vérité ambiguë (voir le tableau plus bas).

## Le banc

`node test/bench_frequences.mjs [--nom=<filtre>] [--json --out=<fichier>]` (297 cas, 9 s de synthèse chacun, ~1,2 s par cas).
Notes de Do2 à Do7, battements de 0,2 à 8 Hz (au plus 12 ¢ d'écart pour être un unisson d'accordéon), 2 anches (MM) et 3 anches
(MMM, −Δ / 0 / +Δ ; asymétrique Δ− = 0,7 Δ+), rapports d'amplitude de 3 à 12 dB, partiels réalistes, anches qui se tirent :
**réaliste** (β 0,1 à 0,3 rad, AM 5 à 15 %, 54 cas), **Adler** (κ/Δ0 = 0,3, 0,6, 0,9), **extrême** (β 0,5 à 1,2, AM 30 %),
dérive de pression de 1 ¢/s, vibrato de soufflet lent, secousse à 1,2 Hz, bruit à 20 dB, raie étrangère près de l'unisson,
Do6 sous 0,5 Hz avec vibrato. Pour chaque cas, après deux périodes de battement + 1 s (au moins 4,5 s) : erreur de CHAQUE anche
(¢) contre la vérité entière (et contre celle de la v57, colonne à part : 15 à 85 % de la fenêtre), erreur du battement,
cohérence (|f2 − f1 − battement affiché|, Hz), temps de stabilisation, permutation, part des images lues par le peigne.
`test/frequences.test.mjs` en garde une cinquantaine (F 1 à F 11, T1 à T7 de l'audit).

## Le peigne rigide (v58, `dsp/peigne.js`)

Deux anches qui se tirent donnent un PEIGNE de raies à k f1 + m Δ (Δ = f2 − f1, m de −2 à k+2 ; porteuses en m = 0 et m = k).
La contrainte que l'ajustement de la v57 n'avait pas : **toutes les raies sont à des positions liées**. Deux paramètres non
linéaires seulement (F = k f1, Δ), les amplitudes complexes (linéaires) sont éliminées par moindres carrés (variable projection,
Golub et Pereyra 2003) ; Gauss-Newton avec la dérivée projetée de Kaufman sur la bande de base complexe du traqueur (2 à 4,5 s,
un nombre ENTIER de périodes de battement, au moins 2). Mesuré : 1 à 2 ms par ajustement, un ajustement toutes les 40 ms.

- **Quelle raie est l'anche** : les porteuses sont les deux raies voisines de k pas dont le plus petit module est le plus grand
  (une raie latérale est à −16 dB au plus quand β ≤ 0,3). Si l'anche faible vaut une raie latérale de la forte, les lectures
  d'avant tranchent seulement si elles désignent la MÊME étiquette ; sinon l'étiquette est ambiguë et le peigne refusé.
  Contrôle de la physique : deux partiels (2 puis 1, sinon 3) disent le même f1(k)/k à 0,3 ¢ + 3 σ, le même Δ à 5 %, et Δ colle à
  l'enveloppe du volume à 10 % + 0,02 Hz.
- **Quand il est choisi** : résidu r = ‖y − Vc‖²/‖y‖² < 0,05 (−13 dB) ET (raies latérales à −12 dB ou plus AU PARTIEL MESURÉ par
  le moteur — déduites de celles lues en bas par la loi de Bessel, l'indice de phase étant proportionnel au rang — OU la paire
  lue ne colle pas à Δ). Un amas net (latérales plus basses, paire cohérente) garde sa lecture : 0,03 ¢ depuis la v56. Une raie
  étrangère (1,7 / 2,7 / 3,4 Δ) n'est pas sur le peigne : r monte, refus, lecture inchangée (T5). Trois ajustements d'affilée
  pour entrer, 0,5 s de tenue pour sortir.
- **Sortie** : `fMeas` de chaque anche, `source = 'peigne'`, `sigmaCents` (borne de Rife et Boorstyn, prudente : le résidu inclut
  le défaut de modèle), `peigne` { r, laterales (dB), k, T, delta }. Colonnes `source`, `sigma_cents`, `peigne_*` du CSV de la
  carte « unisson et replis » de la section recherche.

## Ce qu'on peut dire, et quand (cas 3 et 4 ; `etatPaire`)

La limite est la durée, pas l'algorithme : deux raies d'écart Δ demandent T ≳ 1/Δ ; le vibrato commun du soufflet (±2 ¢ =
±1,2 Hz à Do6) noie un écart de 0,5 Hz dans toute lecture de raies. Atteignable : le **centre** de l'amas (immunisé par la
cohérence des deux anches) et le **battement** par l'enveloppe (0,03 Hz). Chaque anche d'un unisson porte `etatAnche` :

| état | quand | ce que l'interface dit |
|---|---|---|
| `sur` | le peigne a la main avec σ ≤ 0,3 ¢, ou l'amas colle à un battement connu, et la note a duré T_besoin | le chiffre, sans marge |
| `en cours` | avant T_besoin = max(1 s, 1,2/Δ) (2/Δ sous 0,8 Hz), ou paire qui ne colle pas, ou σ > 0,3 ¢ | « ±Δ/2 ¢ · en cours · encore n s » |
| `centre` | Δ < 1/T de la fenêtre (Do6-Do7 sous 0,35 Hz) : le peigne ne tient pas non plus | le milieu des deux (moyenné sur des périodes entières), chaque anche « ±Δ/2 » |

Le chiffre porte sa marge comme une anche confondue avec l'octave (`mesure.js`, `texteMarge`) : la validation automatique attend
|écart| + marge < tolérance, jamais de vert « juste » trompeur.

## Résultats (erreur p95 par anche, en ¢, vérité entière ; v57 → v58)

| famille | cas | pire v57 → v58 | médiane v57 → v58 | cas > 0,3 ¢ v57 → v58 |
|---|---|---|---|---|
| deux anches nettes, rapports 3-12 dB, bruit 20 dB, MMM nettes | 82 | 0,38 → 0,38 (Do7 sous 1 Hz) | 0,05 → 0,05 | 1 → 1 |
| couplage RÉALISTE (β ≤ 0,3, AM ≤ 15 %) | 54 | 0,71 → 0,13 | 0,10 → 0,04 | 8 → 0 |
| Adler, κ/Δ0 = 0,3 / 0,6 / 0,9 | 18 | 3,12 → 3,12 (κ/Δ0 = 0,9, Ω < 0,4 Hz) | 0,20 → 0,09 | 7 → 6 |
| Do6 sous 0,5 Hz avec vibrato de 2 ¢ | 2 | 0,90 → 0,41 | 0,90 → 0,41 | 2 → 2 |
| MMM couplé réaliste et asymétrique, Δ ≤ 12 ¢ (pas de peigne à trois anches) | 15 | 0,74 → 0,74 | 0,12 → 0,12 | 6 → 6 |
| idem, Δ > 12 ¢ (3 Hz à Do3) | 6 | 35,3 → 35,3 | 0,16 → 0,16 | 2 → 2 |
| raie étrangère + couplage réaliste | 18 | 12,7 → 12,7 | 0,16 → 0,16 | 7 → 7 |
| raie étrangère, deux anches nettes (T5) | 18 | 4,54 → 4,54 (Do6 à 0,8 Hz) | 0,05 → 0,05 | 3 → 3 |
| couplage EXTRÊME (β 0,5-1,2, AM 30 %), hors tolérance | 24 | 29,6 → 29,6 | 0,69 → 0,69 | 15 → 15 |

Contre la vérité de la v57 (15 à 85 % de la fenêtre, sans la phase modulée), les mêmes cas donnent le même ordre de grandeur en
couplage réaliste (0,72 → 0,14) ; en régime d'Adler la vérité de la v57 est ambiguë (8,7 ¢ contre 3,1 ¢ avec la vérité entière,
le tirage de chaque anche n'y est pas) : c'est là que le désaccord de définition pesait.

La dérive de pression de 1 ¢/s, le vibrato de 3 ¢ et la secousse du soufflet (1,0 à 4,2 ¢ contre la vérité entière, qui finit à t)
ne bougent pas : c'est le retard de toute lecture sur un mouvement réel, pas un défaut de couplage (contre la vérité de la v57 :
0,1 à 2,4 ¢, comme avant). Charge : +0,1 ms par bloc de 10,7 ms en moyenne (+10 %), +0,5 ms au p95 (mesuré, rejeu de synthèse).

### La session d'Ewen du 11/10/2026 (rejeu du WAV, 17 notes tenues avec battement mesurable, MM)

| | v56 | v57 | v58 |
|---|---|---|---|
| images où f(8'+) − f(8') s'écarte de plus de 0,15 Hz du battement de l'enveloppe | 41,5 % | 4,7 % | 4,7 % |
| images où le CHIFFRE du battement s'écarte de plus de 0,15 Hz de l'enveloppe | 20,4 % | 3,4 % | 3,4 % |
| écart type des cents du 8'+ (moyenne pondérée des notes) | 1,34 ¢ | 1,02 ¢ | 1,01 ¢ |
| images lues par le peigne | | | 12 % |

La session n'a presque pas d'anches qui se tirent à β > 0,1 : le peigne ne la change pas, et c'est voulu (pas de réglage sur ce
seul fichier). Reste hors tolérance : Do#4 (109 s, battement de 0,14 Hz : l'enveloppe ne voit pas deux périodes en 8 s). Les
écarts types de 3 à 4,5 ¢ de Ré4, Si4 et Sol#5 sont des mouvements réels du soufflet (les deux anches bougent ensemble).

## Ce qui a été corrigé en v57 (cohérence, inchangé)

`dsp/battement.js`, `cohererPaire` : la paire lue doit coller au battement de l'enveloppe. Une paire cohérente n'est
jamais touchée. Quand elle ne l'est plus (le moteur a pris la raie de rang n±1 du peigne), la dernière paire cohérente de
la note (au plus 1,5 s, retrouvée dans l'historique des 3 s : l'enveloppe n'est lue qu'après 2,5 s de note) dit laquelle des
deux anches a gardé sa raie ; l'autre est replacée à un battement d'elle. Les deux près de leur dernière valeur : l'écart
est rétabli au prorata de ce dont chacune a bougé. Aucune ne suit : la dernière paire est tenue. Sans référence, rien.
`pairRepaired` / colonne `paire_reparee` des CSV de session. En v58, le peigne passe avant ; cette correction reste pour tout
ce que le peigne refuse.

## Essayé et écarté

- Ajustement d'un peigne à positions LIBRES (noyau exact de Hann, porteuses libres, raies d'intermodulation pénalisées) : 25-60 ms
  par image, mal conditionné. Remplacé par le peigne rigide de la v58 (2 paramètres).
- Pente de phase de l'amas ENTIER (les deux anches et leur peigne) avec l'écart de l'enveloppe, centre de masse du spectre
  quand les deux anches ont la même force : la phase d'une somme suit l'anche forte quelle que soit la modulation ; +0,3 à 2 ¢ sur
  deux anches nettes dont une raie étrangère fuit dans le masque (Sol#4 de la session à 418 Hz). Écarté.
- Ancrer sur la raie la plus forte ; choisir la paire de raies d'écart égal au battement : pas mieux que le moteur.
- v58 : moyenne de l'amas sur des périodes entières pour toutes les paires (la demande de l'audit). Sur le banc elle ajoute le
  retard de la fenêtre de l'amas (la dérive de 1 ¢/s passait de 1,0 à 1,5 ¢) sans ôter de modulation de phase (le tirage
  réaliste est déjà dans la pente de phase). Gardée seulement dans l'état « centre ». Le peigne, lui, fait cette moyenne par sa
  construction.
- v58 : peigne sur un seul partiel : l'étiquette des porteuses est ambiguë (une anche faible vaut une raie latérale de la forte
  à k ≥ 3) ; deux partiels qui s'accordent la lèvent.

## Ce qui reste hors tolérance

- Anches qui se tirent à β > 0,3 rad ou AM > 15 % (les anciens cas, étiquetés « extrême » au banc) : des anches presque accrochées,
  l'étiquette des porteuses y est ambiguë. À fixer par la mesure réelle de l'audit (note MM tenue 10 s, puis 8'+ bouché, puis 8'
  bouché : tirage = écart « seul » − Ω observé, à comparer à β²Ω ; si moins de 0,1 ¢, la moyenne en place est la réponse).
- Trois anches qui se tirent (MMM : peigne à trois anches f0, Δ−, Δ+ non fait) : 0,5 à 0,7 ¢ au pire en couplage réaliste.
- Une raie étrangère à 1,7 à 3,4 Δ dans la bande d'anches qui se tirent (6 à 13 ¢ au pire) : elle est à moins de 0,4 Δ d'une raie du
  peigne, donc dans la résolution de la fenêtre ; le peigne est refusé (variante de l'audit « raies libres » non faite).
- Battement sous 0,35 Hz (Do6-Do7) : le centre, chaque anche à ± Δ/2 ; les 2 à 4 premières secondes d'une note : « en cours ».
