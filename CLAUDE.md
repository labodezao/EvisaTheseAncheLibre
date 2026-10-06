# EvisaTheseAncheLibre — mémoire du projet

## Ce que c'est
Deux modules autour de la **physique de l'anche libre** (accordéon) :
- `web/` + `firmware/` — **accordeur** web (précision < 0,1 cent, polyphonique) et
  **banc d'accordage** ESP32-S3 (soufflet motorisé, électro-aimants, capteurs).
- `research/` — banc de **recherche** Python (`banc_recherche`, GUI PyQt6 + CLI) :
  acquisition, analyse Praat, impédance, DOE type Minitab, bifurcations et
  **physique stochastique des oscillateurs non linéaires** (Kramers-Moyal,
  potentiel, Stuart-Landau, résonance cohérente, Kramers), modes propres
  (`modal`), FRF swept-sine (`frf`), espace des phases (`phase_space`), modèle
  non linéaire anche-cavité (`reed_model`).

## La personne (important, à honorer)
Ewen — **auto-entrepreneur seul, à la dèche**. Contrainte forte : **pas de
matériel coûteux** (surtout **pas de vibromètre laser**). Tout doit marcher avec
presque rien : carte son, un micro, un petit **accéléromètre piézo** (quelques
euros). Le profil « laser » est OPTIONNEL — proposer des alternatives bon marché
(comparateur, capteur analogique, photo/OpenCV). Ne jamais pousser vers de
l'achat cher.

## La vision de la thèse / du livre (le pourquoi de tout)
Écrire la thèse **à la manière de Roger Penrose** (*À la découverte des lois de
l'univers*) : la science au **niveau de l'expérience humaine**, un « savoir
chaud », pas des équations froides. **Tresser trois fils** :
1. **le dehors** — physique de l'anche : bifurcation (Hopf), hystérésis,
   transitoire, résonance, bruit, espace des phases ;
2. **le dedans** — observation des sensations (**Vipassana**) : *anicca*
   (impermanence), *sankhara* (conditionnements), *kalāpa* (au plus fin, comme
   les quarks/atomes de Penrose), équanimité, *sacca* (vérité) ;
3. **le vivant** — l'histoire de vie d'Ewen, l'organique, les transitions.
Idée centrale : **« la nature ne ment pas »** — l'honnêteté de l'expérience
scientifique = l'honnêteté radicale avec la sensation. Faire le pont
intérieur ↔ extérieur.

Ponts déjà justes (les réutiliser) : hystérésis `p_on>p_off` ↔ sankhara ;
échappement de Kramers ↔ sortir d'un état bistable ; transitoire d'attaque ↔
naissance/impermanence ; espace des phases ↔ observer une sensation sans juger ;
DOE/ANOVA ↔ laisser la mesure contredire l'hypothèse.

## Où en est l'écriture
- `research/docs/livre_au_seuil_de_lanche.md` — squelette de livre tressé
  (7 parties), encarts « ⟢ ton expérience » à laisser vides (à Ewen).
- `research/docs/design_theory.lyx` / `design_practical.lyx` — manuscrits LyX
  (gabarit *Legrand Orange Book*) ; à faire évoluer dans cette vision.
- `design_practical.lyx` (anglais) et `design_practical_fr.lyx` sont GÉNÉRÉS : ne pas les
  éditer à la main. Sources : `research/docs/design_practical/NN_piece_{en,fr}.md` (une pièce
  de l'accordéon par partie : théorie, analyse, outils, réparation), puis
  `python research/scripts/design_practical_lyx.py`. Chiffres : `research/scripts/outils_atelier.py`
  (testé) ; figures : `figures_pratique.py`, `figures_mecanique.py`.

## Ton
Chaleureux, humain, honnête. Relier la physique au vivant. Respecter la
dimension personnelle et spirituelle sans la survoler. La passion pour l'anche
n'a de sens que reliée à ce qui se passe dans le cadre du corps.

## Pratique dev
- Développer sur `claude/accordion-tuner-app-jvjgnv`, PR en **draft**.
- Tests `research` pensés **numpy seul** (deps lourdes importées paresseusement).
- Sources d'origine (Drive) versées dans `research/scripts/legacy/` (+ `models/`),
  avec les fileId pour re-télécharger à la demande.
- **TUTT et les perces d'Ewen sont versionnés** (décision d'Ewen, 2026-09-21 :
  « oui tout dans le dépôt, tout est coauteurs mets tout »). Sources Fortran de
  TUTT 4.1 dans `research/scripts/legacy/tutt/` (œuvre de B.B. « Ninob » —
  `CREDITS.md` du dossier crédite explicitement) ; perces réelles d'Ewen
  (bombarde, clarinette folk) dans `research/scripts/legacy/perces/`. Le reste
  de sa bibliothèque Drive (saxophones, hautbois, cuivres, cromornes…) n'est
  pas encore rapatrié — à faire à la demande, même convention.

## Éléments finis, banque d'anches, reedgui (2026-10-03)
- `research/fem/README.md` : la marche en 5 étapes, de la mesure de l'anche au recalage.
  Elmer 26.2 (la 9.0 est désinstallée), trouvé par `research/fem/elmer_outils.py`
  (variable `ELMER_DOSSIER` ; ne pas se fier à `ELMER_HOME` système ni au PATH).
- Une seule source de vérité pour une anche : la banque CSV d'Ewen
  (`research/fem/anche/banque_anches.csv`) -> yaml produit -> `banc_recherche/languette.py`
  (Euler-Bernoulli exact, Rayleigh-Ritz, pont vers `coupled_reeds`) -> Elmer, recalage, reedgui.
- `research/reedgui/` : l'outil d'Ewen (2020) réécrit, seule version vivante.
- Leçon : Rayleigh-Ritz sur 2 modes de poutre uniforme (km.py) surestime de 51 % une anche
  grattée à masse au bout ; référence = Euler-Bernoulli exact (matrices de transfert), Elmer à 0,4 %.
- Recalage expérimental (2026-10-04) : `research/docs/protocole_recalage_experimental.md` (anche
  seule pincée, sur sa chambre, soufflerie par escalier noté à la main) ; outils `pince_modes.py`,
  `fem/comparer_pince.py`, `fem/souffle.py`. Thèse : `design_theory.lyx` (chapitre Static and
  modal analysis, en anglais). design_practical = comment concevoir un accordéon, PAS la thèse
  (correction d'Ewen, 04/10). Partage (Ewen, 05/10) : design_theory = la théorie vraiment
  acoustique (anche, sommier, couplages) ; design_practical = la théorie de la fabrication,
  appliquée à la conception d'instrument et au métier de réparateur, organisée PIÈCE PAR PIÈCE
  de l'accordéon (étude théorique -> analyse -> outils d'aide à la conception / réparation).
  Ex. : la mécanique main gauche, les fuites vont dans practical. Sa table des matières actuelle
  (copie de design_theory) ne compte pas : on peut la réécrire. Compilation : biblatex (structure.tex du gabarit Legrand) ->
  `\addbibresource{references.bib}`, `\printbibliography` en ERT, biber, `bibliography.bib` vide ;
  pas de grec ni de symbole Unicode en texte (formule). Les sons d'Ewen arrivent dans `J:\multimedia à tier\INBOX` : les lire, ne
  jamais les déplacer. Le .lyx est en CRLF dans le dépôt : garder CRLF (sinon tout le fichier change).

## Accordeur web (`web/`) — état et leçons (v41, 2026-10-06)
Déployé sur GitHub Pages depuis `main` (https://labodezao.github.io/EvisaTheseAncheLibre/).

**Le moteur se développe dans PolyReed** (dépôt privé d'Ewen,
`J:\claude\depots\polyreed`) **et se reporte ici après chaque changement.**
Repris de PolyReed v41 le 06/10/2026 et publié en licence MIT par son auteur
(Ewen : « Oui, je publie tout »). Ce qui se reporte : `web/js/dsp/*`,
`web/js/music.js`, la page de recherche (`ancien.html` de PolyReed devient
`web/index.html` ici, avec `app.js`, `report.js`, `bench.js`, `seuils.js`,
`zip.js`, `capture-worklet.js`, `theme-init.js`, `css/style.css`), les tests du
moteur (`dsp.test.mjs`, `synthese-anches.mjs`, `polyphonie.test.mjs`,
`seuils.test.mjs`), les outils de `test/outils/` et `docs/POLYPHONIE-ESSAIS.md`.
Ce qui ne vient jamais ici : la licence, la vente, l'interface v2 (`web/js/ui/`),
Electron et Android de PolyReed, ses documents commerciaux, le nom et les visuels
de la marque. Ici, l'application garde le nom « Accordeur Anche Libre » ; `APP_VERSION`
est écrite dans `app.js` (PolyReed la lit dans `ui/version.js`) ; `SHELL` de
`web/sw.js` est la liste de la thèse. Après un report :
`grep -ri "polyreed\|licence\|stripe\|paddle" web test docs` ne doit rien
trouver (hors README et ce fichier).
Références d'Ewen : **Peterson** (strobe) et **Dirk's Accordion Tuner** (qu'il utilise).
Ewen parle français, souvent en dictée vocale ; il teste en jouant sur SON
accordéon et envoie des ZIP de session (WAV + CSV + JSON, bouton Exporter ;
trop lourds → il les pousse dans `test/`). Toujours lui répondre en français.

**Règle d'or d'Ewen : « ça doit marcher pour tous les accordéons »** — jamais
de réglage sur ses fichiers ; chaque correction part d'un mécanisme physique
et se vérifie sur un test synthétique (`test/dsp.test.mjs`) qui échoue avant.
Ce qui est réel ne se lisse pas (attaque, pression du soufflet, poussé ≠ tiré :
ses anches diffèrent de 15–25 ¢ entre poussé et tiré) ; ce qui est artefact se
corrige à la source.

### Chaîne de mesure (fichiers clés)
- `web/js/dsp/worker.js` : capture micro **directe** (MediaStreamTrackProcessor,
  à l'horloge du micro) — le rééchantillonneur de Chrome faisait des marches de
  ±6 ¢. Web Audio en repli (Firefox/Safari rééchantillonnent encore).
- `web/js/dsp/coarse.js` : spectre large bande → note (et accords, `chord.js`).
- `web/js/dsp/zoom.js` : traqueur par partiel (hétérodyne, décimation 512 en
  CIC : 32 puis **2×16**, l'ordre 2 évite qu'une raie forte hors bande — le 16'
  — se replie en fantôme dans la bande du 8').
- `web/js/dsp/engine.js` : l'API (`Engine`, `ENGINE_VERSION`), `configure`,
  `process`, `tick` ; ses autres méthodes vivent dans 6 modules posés sur
  `Engine.prototype` : `battement.js` (battement, bat/min), `appariement.js`
  (voix↔raies, `assignOrdered`, amas `clusterRefine`), `anches-mp.js` (**Matrix
  Pencil**, `subspace.js`, anches d'un même ton en 0,5 s), `stabilite.js`
  (médiane, maintien, marches, inversion du soufflet sans silence
  `watchReversal`), `plan.js` (anches attendues, partiel de mesure, collisions),
  `confondu.js` (anche confondue avec l'octave : estimation et marge).
- `web/js/app.js` : UI (strobe par anche, courbe avec échelle Auto stable ou
  **Relatif**, barre Mode, vumètre + seuil auto, alertes, sélecteur de notes).
- Versions : `ENGINE_VERSION`, `APP_VERSION` (`app.js`), `data-version` de
  `index.html` et cache `aal-shell-vNN` de `sw.js` doivent être identiques
  (test 27) — les monter ensemble à chaque report, à la valeur de PolyReed,
  sinon le service worker garde l'ancien. Un nouveau fichier de `web/` entre
  dans `SHELL` (`web/sw.js`), sinon le hors-ligne casse.

### Mécanismes appris (à ne pas réintroduire)
Chacun a un test dans `test/dsp.test.mjs` ; essais réels et chiffres : `docs/POLYPHONIE-ESSAIS.md`.
Liste tenue dans PolyReed, recopiée à chaque report.

- Partiels pairs d'une anche qui a une voisine à l'octave au-dessus : partagés. Le 16' se mesure
  sur un partiel impair (`avoidEven`) ; en Automatique, une note grave (k ≥ 2) aussi, et ses
  partiels pairs n'entrent dans la fusion que s'ils concordent à 0,5 ¢ (sinon : alerte) (test 50).
- Collisions de partiels : testées sur toutes les fréquences jusqu'au partiel étudié, pas
  seulement les 16 premières. Quand TOUS les partiels d'une anche tombent sur ceux d'une autre (le
  8' d'un 16'+8', `octaveClash`), le choix se fait sur les fréquences MESURÉES : `octaveFuse` lit
  le 8' sur ses partiels séparés de la raie connue du 16' (tests 45, 46). Aucun partiel fixé
  d'avance : sur une basse réelle, le rapport 16'/8' saute de ±20 dB d'un partiel au suivant.
- L'amas de phase (`clusterRefine`, ±5 Hz) s'arrête à mi-chemin des raies CONNUES des autres
  anches, sinon il avale la plus forte et la pente de phase la lit.
- Filtres anti-fantôme bornés par la résolution de la fenêtre (`OCTAVE_SEP_BINS` = 2 cases de
  1/T), jamais par une constante en cents (8 ¢ effaçait un 4' réel, test 47).
- Auto-anches : une anche ajoutée à la main n'est déclarée que sur preuve ; une raie revendiquée
  par une autre anche ne prouve rien et n'entre pas dans l'appariement. Anches limitées à ±35 ¢
  dans la bande. Le plancher (−25 dB) compare des anches (leur partiel le plus fort), pas des
  partiels (test 48). Une anche seule dans son groupe est lue sur ses partiels fondus (test 49).
- Garde d'octave d'un registre : à sens unique. Une anche lâchée ne fait jamais apparaître une
  fondamentale plus grave ; une note proposée plus bas dont les partiels impairs ont une énergie
  à elle est acceptée (le 8' qui parle avant le 16', test 44).
- Une limite physique n'est pas un défaut : deux raies δ Hz l'une de l'autre ne se séparent
  qu'avec une fenêtre de plus de 2/(k δ) s. Avant, la valeur est « confondue » (M), d'erreur
  bornée par l'écart réel ; un test le vérifie au lieu d'exiger l'impossible.
- Note imposée (cible, verrou) : le moteur ne la cherche plus, il mesure ce qui tombe dans la
  bande de son partiel. Elle n'est lue que si son partiel le plus grave mesurable (premier
  au-dessus de 150 Hz) est dans le spectre large bande (`silentLock`, plan.js) : sinon le partiel 5
  d'un La4 joué se lisait en Do#5 à 550 Hz (5/4), validé en mésotonique (test 51).
- Anche confondue : sa justesse quand même, avec sa marge (`dsp/confondu.js`, tests 52 à 55 et
  57, UI 18). Par l'octave : 2 f16 ± 1/T (jamais la raie commune comme centre : sa phase déborde
  de [2 f16, f8]). Par le battement : chaque partiel k du 8', démodulé par la phase du 16'
  (× 2k/m), est un cercle parcouru à k δ autour de la raie du 16' ; le sens de rotation donne le
  signe, sur toute la note (≤ 8 s). Marge = √(A² + B² + S²) et 0,1 ¢ du 16' ; B compte l'écart
  entre la note entière et ses DEUX moitiés (un δ qui bouge, qui passe par zéro sous le soufflet,
  sort l'ajustement de la note de l'intervalle des moitiés : 85 % de vérités dans la marge, test
  57). Par la raie commune, quand le 8' y domine (P08) : biais borné par min(|δ| ρ/(1−ρ),
  3 asin ρ/(2π k L)), ρ lu sur le CERCLE des points (centre = 16', rayon = 8'), jamais par
  l'ajustement à δ constant (qui le sous-estime quand δ bouge) ; il faut deux partiels au moins,
  forts, et l'intersection de leurs intervalles. `merged`, `fMeas`, `dCents` ne changent pas ; tout
  est dans des champs à part (`confondu`, `fEstimee`, `centsEstimes`, `centsEstimesCible`,
  `margeCents`, `methode` octave | battement | raie, `signeConnu`). Interface : le chiffre est
  l'estimation, plus fin, en pointillé, « ±0,14 ¢ · par le battement » ; jamais « juste » si la
  marge déborde ; validée seulement si |estimation| + marge < tolérance ; le carnet et le CSV
  gardent la marge.
- Séparation du 8' (test 56) : une raie à 2 cases de celle du 16' n'est pas le 16', mais rien ne
  dit qu'elle est le 8' (repli de la décimation à −30 dB, lecture de la raie commune poussée seule
  au-delà du seuil) : 8 à 26 ¢ d'erreur, parfois toute la note. Elle n'est retenue que si un AUTRE
  partiel du 8' distinct de la raie du 16' dit la même hauteur, à leurs biais près (1/(2kT) séparé,
  1/(kT) sinon). La tenue d'1 s (l'anche reste dite confondue tant que la mesure séparée sort de la
  marge) n'est plus qu'un garde-fou : reste un biais de 1 à 3 ¢ sur la toute première image quand
  la fenêtre est courte.
- Estimation rapide : à plus d'un demi-ton de la note, elle lit déjà la note suivante ; pas de
  repli sur elle. Secteur (50 Hz et sous-multiples) : jamais pris pour une anche ni une vérité.
- Le ronflement 50 Hz du micro USB d'Ewen (−88 dBFS) est là depuis toujours ;
  ne pas l'accuser à tort.

### Outils (`test/outils/`, voir `LISEZMOI.md`)
`csv_resume.py` (ce qui a été affiché), `rejoue.mjs` (rejouer un WAV dans le
moteur, `ENG=` pour comparer deux versions), `bande.py` (vérité terrain par
raie), `esprit.py` (séparer 2–3 anches), `banc_musette.mjs`. Tests :
`npm test` (57 scénarios du moteur au 06/10/2026 et les seuils, doivent tous
passer) ; `npm run test:poly` : défauts polyphoniques reproduits en synthèse,
au même état que dans PolyReed (ceux qui restent échouent exprès). Outils ajoutés
le 06/10 : `images.mjs`, `verite_poly.py`, `compare_poly.py`, `resume_poly.py`,
`avant_apres_poly.py`, `confondu_poly.py`, `confondu_grille.mjs`,
`boucles_dirks.py` (voir `test/outils/LISEZMOI.md`).

### Ouvert / idées
- 16'+8' : un 8' à quelques cents de l'octave n'est séparable qu'après ~2 s
  (limite physique, 2/(k δ) s) ; avant, il est « confondu » et sa justesse est
  estimée avec sa marge (`confondu.js`).
- Option d'affichage proposée à Ewen (pas faite) : estomper les attaques et
  fins de souffle (vrais mouvements de hauteur) pour lire les paliers.
- Détection d'inversion : deux inversions à < 1,5 s → la 2e n'est pas vue.
- Accords mineurs / septièmes / diminués : vérifiés seulement en synthèse
  (Ewen devait envoyer des ZIP) ; vibrato (bat/min) idem.
- Idée de Dirk non faite : erreur par rapport au diapason droit vs liste de
  battements. Calibration longue façon Dirk (horloge carte son) : non faite.
- `test/session-2026-09-25-23-58-20.zip` (59 Mo) est dans `main` (fusion
  classique) : session quintes + octaves main gauche, utile en référence.
