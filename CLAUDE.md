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
  (correction d'Ewen, 04/10). Compilation : biblatex (structure.tex du gabarit Legrand) ->
  `\addbibresource{references.bib}`, `\printbibliography` en ERT, biber, `bibliography.bib` vide ;
  pas de grec ni de symbole Unicode en texte (formule). Les sons d'Ewen arrivent dans `J:\multimedia à tier\INBOX` : les lire, ne
  jamais les déplacer. Le .lyx est en CRLF dans le dépôt : garder CRLF (sinon tout le fichier change).

## Accordeur web (`web/`) — état et leçons (v27, 2026-09-26)
Déployé sur GitHub Pages depuis `main` (https://labodezao.github.io/EvisaTheseAncheLibre/).
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
- `web/js/dsp/engine.js` : groupes d'anches, choix du partiel de mesure,
  appariement voix↔raies (`assignOrdered`, mesure d'amas `clusterRefine`),
  stabilisation (médiane 3, maintien 1 s), détection de marche, **Matrix
  Pencil** (`subspace.js`, `mpReeds`) pour séparer les anches d'un même ton en
  0,5 s, détection d'inversion du soufflet sans silence (`watchReversal` : creux
  net et isolé), battement (bat/min).
- `web/js/app.js` : UI (strobe par anche, courbe avec échelle Auto stable ou
  **Relatif**, barre Mode, vumètre + seuil auto, alertes, sélecteur de notes).
- Versions : `ENGINE_VERSION`, `APP_VERSION`, `data-version` de `index.html` et
  cache `aal-shell-vNN` de `sw.js` doivent être identiques (test 27) — les
  monter ensemble à chaque changement, sinon le service worker garde l'ancien.

### Mécanismes appris (à ne pas réintroduire)
- Partiels qui se superposent : une anche à l'octave d'une autre (16'+8', et
  les basses de la main gauche qui ont des anches à l'octave) a tous ses
  partiels sur des partiels PAIRS de l'anche grave → mesurer l'anche grave sur
  un partiel **impair** ; ne jamais afficher la raie commune comme la hauteur
  d'une anche qui vient d'avoir la sienne (c'est un mélange).
- Contrôle des collisions sur TOUS les partiels jusqu'à la fréquence étudiée
  (quinte à la douzième : Fa4 ×6 = La♯2 ×18).
- Auto-anches : toutes les anches admises (±35 ¢) doivent tenir dans la bande
  du partiel choisi ; cases rangées par ordre (une anche seule = 8').
- Une valeur d'estimation rapide à plus d'un demi-ton lit la note suivante.
- Le ronflement 50 Hz du micro USB d'Ewen (−88 dBFS) est là depuis toujours ;
  ne pas l'accuser à tort.

### Outils (`test/outils/`, voir `LISEZMOI.md`)
`csv_resume.py` (ce qui a été affiché), `rejoue.mjs` (rejouer un WAV dans le
moteur, `ENG=` pour comparer deux versions), `bande.py` (vérité terrain par
raie), `esprit.py` (séparer 2–3 anches), `banc_musette.mjs`. Tests :
`node test/dsp.test.mjs` (43 tests, doivent tous passer).

### Ouvert / idées
- 16'+8' : un 8' à quelques cents de l'octave n'est séparable qu'après ~2 s.
- Option d'affichage proposée à Ewen (pas faite) : estomper les attaques et
  fins de souffle (vrais mouvements de hauteur) pour lire les paliers.
- Détection d'inversion : deux inversions à < 1,5 s → la 2e n'est pas vue.
- Accords mineurs / septièmes / diminués : vérifiés seulement en synthèse
  (Ewen devait envoyer des ZIP) ; vibrato (bat/min) idem.
- Idée de Dirk non faite : erreur par rapport au diapason droit vs liste de
  battements. Calibration longue façon Dirk (horloge carte son) : non faite.
- `test/session-2026-09-25-23-58-20.zip` (59 Mo) est dans `main` (fusion
  classique) : session quintes + octaves main gauche, utile en référence.
