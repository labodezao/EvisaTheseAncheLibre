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
- Trouvailles de l'accordeur (19/10/2026, six audits du 15 au 19/10) : `design_theory.lyx` et `design_theory_fr.lyx`, section « Reading coupled reeds » du chapitre Reed coupling (physique de la paire : peigne de Bessel, quadrature, moyenne sur des battements entiers, trois anches) et section « How sure is a reading » de « Ways and measuring protocols » (Cramér-Rao, règle des trois, chaîne de mesure qui fabrique de la physique, banc circulaire) ; miroir dans `these_parties_2_a_5_fr.md`. Détail et notes de savoir : coffre, Projets actifs/Accordeur d'accordéon/Savoir/.
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

## Accordeur web (`web/`) — état et leçons (v58, 2026-10-12)
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
v42 (10/10/2026) : session de recherche longue (Ewen, 07/10 : « 60 min au lieu de 10, pour
suivre tout l'accordage »). Durée max 10 / 30 / 60 / 120 min (60 par défaut) ; le Worker rend un
morceau toutes les 10 s (son Int16 et lignes du CSV), `web/js/session-stockage.js` l'écrit dans
l'OPFS (sinon IndexedDB), l'export assemble le ZIP sans tout charger (`zipPlan` de `zip.js`), une
session coupée se récupère ; un WAV rejoué est lu par morceaux (`?vitesse=` pour aller plus vite).
Formats communs : `web/js/session-format.js`. Test : `test/session-longue.test.mjs`.
v45 (10/10/2026) : audit de répétabilité au soufflet (docs/POLYPHONIE-ESSAIS.md § 4.4). Le moteur
suit le sens du soufflet (`tick.sens`, `tick.soufflet` : part du sens tiré / poussé de la page, bascule à
chaque creux franc ou silence de moins de 1,5 s ; colonnes `sens`, `sens_source`, `inversions` de la
session) et donne les battements d'intervalles (`tick.intervalles` : quinte 3:2, quarte, tierces, octave,
douzième, double octave ; b = m f_b − n f_h mesuré et voulu selon le tempérament, enveloppe). La page les
montre (`qSens`, `qIntervals`). Essayé et retiré : lire la pente de phase sur tout le son reçu (pire sur
le réel). Ewen (10/10) : quintes à l'égal par défaut ; la session du 25/09 ne dit rien du sens.
v52 (11/10/2026) : moteur repris de PolyReed v52 (audit d'usage pro n° 1, 6, 11 ; docs/POLYPHONIE-ESSAIS.md
§ 4.5 de PolyReed). Raies repliées par le filtre de décimation écartées (`zoom.js`, `repli`, `groupe.replis`) ;
note imposée lue seulement si son partiel grave est un pic (`partielEnPic`) ; note entendue à côté du verrou
(`tick.noteEntendue`) ; unisson d'un registre (`dsp/proches.js`) : anche seule donnée à la voix visée
(`cfg.voix`), marge « anches proches » quand une voix manque ou que deux raies sont séparées de justesse ;
octave exacte « immobile » (l'octave ne bat pas, marge 0,5/(k_max T), `confondu.js`). La page montre les
méthodes nouvelles dans la ligne de l'anche confondue. Tests 60 à 62 de `test/dsp.test.mjs`.
v54 (11/10/2026) : moteur repris de PolyReed v54 (POLYPHONIE-ESSAIS § 4.6). Mode accord : chaque anche de
chaque note (`cfg.chordVoices` ; la page : « Anches par note », une, 16'+8', 16'+8'+4', fondamentale-quinte-
octave d'un diato), avec les règles d'un registre 16'+8' (partiel impair, `octaveFuse`, estimation et marge,
l'octave qui ne bat pas) ; raies des autres notes lues sur leur mesure de l'image ; raie d'une autre note
dans la bande d'un partiel (`v.etrangeres`, le 8' de la quinte à la douzième du 16' de la fondamentale) hors
du battement ; note lue une octave trop haut quand le 16' a un fondamental faible (`abaisserOctaves`).
Test 63 de `test/dsp.test.mjs`, `test/outils/accord_grille.mjs`.
v55 (11/10/2026) : moteur repris de PolyReed v55 (POLYPHONIE-ESSAIS § 4.7). Registre 16'+8'+4' : le 8' du
milieu lu comme le 8' d'un 16'+8' (`octaveClash`) ; le 4' estimé sur le 16' (`rapport` 4, le 8' entre les deux :
marge qui couvre sa place, battement seulement où il est fixe) ; raies de l'image pour le 4' ; octave qui ne
bat pas jugée partiel par partiel. Anche d'un MMM qui ne sonne pas : « — », sa voisine garde sa marge. Tests
64 et 65 de `test/dsp.test.mjs`.
v60 (13/10/2026) : moteur repris de PolyReed v60 : verrou de phase par anche en OPTION EXPÉRIMENTALE (case « Verrou de phase (expérimental) » du panneau de réglages, éteinte par défaut ; éteinte, rien ne change : v58), lu sur une note tenue 3 s au moins dans un second Worker (`dsp/lecteur-note.js`, `verrou-worker.js`, `verrou-note.js`, `verrou.js`), battements forts jusqu'à 40 Hz et A6 lus sur les raies ou refusés ; ses tests et bancs sont dans PolyReed (`test/verrou*.test.mjs`, `bench_reel.mjs`, `bench_plage.mjs`), l'interface est celle de cette page (`web/js/app.js`, `ui/verrou-affichage.js`).
v62 (14/10/2026) : repris de PolyReed v62 : ronflement du secteur retiré (`dsp/secteur.js`), blocs perdus confirmés hors démarrage, verrou refusé à plus de 20 ¢ du moteur (les phases attaque / en cours et la courbe sont dans la nouvelle interface de PolyReed).
v61 (14/10/2026) : prise de son contrôlée, reprise de PolyReed v61 (`docs/PRISE-DE-SON.md`) : le Worker contrôle les échantillons (`dsp/prise.js` : suppresseur de bruit, gain automatique, blocs perdus, écrêtage, ronflement du secteur, 8-16 kHz), la barre du micro dit le micro, sa fréquence réelle et ses canaux et permet de le choisir (`prise-micro.js`), une mesure prise pendant un défaut est « prise douteuse » ; le JSON de la session porte le micro, les épisodes de défaut et le début exact de la capture. Tests : `test/prise.test.mjs`.
v58 (12/10/2026) : moteur repris de PolyReed v58 (PR 67 à 69, `docs/FREQUENCES-ANCHES.md`) : battement par
l'enveloppe (v56), paire cohérente (v57), peigne rigide `dsp/peigne.js` et états sûr / en cours / au centre (v58) ;
colonnes de session `battement_hz`, `battement_brut_hz`, `battement_source`, `paire_reparee` ; l'état et sa marge
sont lus dans `app.js` (`estimationConfondue`). Tests `battement` et `frequences`. Détail : bloc « Battement affiché » plus bas.
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

Battement affiché (v56, session d'Ewen du 11/10/2026, test/battement.test.mjs) :

- Le chiffre du battement d'un unisson n'est plus la différence brute des deux fréquences (`beatMeas` = f(8'+) − f(8'))
  : deux anches voisines se tirent et font un PEIGNE de raies à ±Δ ; la différence valait Δ, 2Δ ou 3 Hz pour 0,8 Hz
  vrai. `dsp/battement.js`, `fuserBattement` : l'enveloppe du volume (`measureBeat`, stable à 0,01-0,05 Hz) fait
  foi quand elle est sûre (deux anches, partiels d'accord, au moins 0,3 Hz) ; « modulation » ou pas sûre, elle ne
  tranche que si l'écart mesuré s'en écarte de plus de 40 % ; sinon médiane de l'écart sur 1 s. `beatBrut` garde
  l'écart brut, `beatSource` (enveloppe | ecart) dit d'où vient le chiffre, les CSV les exposent. Ne pas
  remettre `beatMeas` brut dans l'interface.

Hauteurs des deux anches cohérentes avec le battement (v57, `docs/FREQUENCES-ANCHES.md`, banc `test/bench_frequences.mjs`,
`test/frequences.test.mjs`) :

- f(8'+) − f(8') doit valoir le battement de l'enveloppe. `cohererPaire` (battement.js) ne touche JAMAIS une paire
  cohérente (±10 %) ; une paire incohérente (raie de rang n±1 du peigne prise pour l'anche : Fa#4 de la session, +12 ¢ pendant
  1,8 s) est ramenée à la dernière paire cohérente de la note (≤ 1,5 s, retrouvée dans l'historique de 3 s : l'enveloppe ne
  vient qu'après 2,5 s de note) : l'anche qui la suit reste, l'autre est à un battement d'elle ; sans référence, rien. Le
  contrôle est sur les voix FINALES (après `stabilize`), pas sur les raies.
- Essayé et écarté (détail dans le doc) : pente de phase de l'amas entier + centre de masse avec l'écart de l'enveloppe
  (mieux sur anches qui se tirent fort, mais +0,3 à 2 ¢ sur deux anches nettes quand une raie étrangère fuit dans le masque) ;
  ancrage sur la raie la plus forte ; moyenne de l'amas sur des périodes entières hors de l'état « centre » (retard : dérive
  1 ¢/s de 1,0 à 1,5 ¢). Ne pas les refaire sans le banc. L'ajustement de peigne à positions LIBRES (v57) est remplacé par
  le peigne RIGIDE (v58, ci-dessous).
- Hors tolérance, connu : anches qui se tirent à β > 0,3 rad ou AM > 15 % (des anches accrochées, pas un unisson : le banc
  les garde étiquetées « extrêmes »), trois anches qui se tirent (MMM : pas de peigne à trois anches), une raie étrangère qui
  tombe dans la bande d'anches qui se tirent, battement sous 0,35 Hz (Do6-Do7 : le centre, pas l'anche).

Anches qui se tirent : peigne rigide et ce qu'on peut dire (v58, audit couplage du 11/10/2026, `dsp/peigne.js`) :

- Vérité du banc : la fréquence MOYENNE de chaque anche en place sur un nombre ENTIER de périodes de battement
  (`fenetreEntiere`, `vraieEntiere` de synthese-anches.mjs ; la modulation de phase s'y annule). Couplage réaliste : β ≤ 0,3 rad
  au fondamental, AM ≤ 15 % (en régime d'Adler β ≈ κ/(2Ω) : β = 0,5 à 1,2 impose des anches accrochées). Les anciens cas sont
  « extrême » et hors tolérance. Les 1 à 4 ¢ de la v57 étaient en bonne part ce désaccord de définition.
- `ajusterPeigne` : toutes les raies sont à k f1 + m Δ (m de −2 à k+2) ; deux paramètres non linéaires (F, Δ) par Gauss-Newton
  (Kaufman) sur la bande de base du traqueur, amplitudes linéaires éliminées (variable projection). Deux partiels (2 puis 1, sinon
  3) : f1(k)/k à 0,3 ¢ près, Δ à 5 %, et Δ à 10 % + 0,02 Hz de l'enveloppe. Les porteuses sont les deux raies voisines de k pas dont
  le PLUS PETIT module est le plus grand ; si l'anche faible vaut une raie latérale de la forte (amplitudes ambiguës), les lectures
  d'avant tranchent seulement si elles désignent la même étiquette. Fenêtre = au moins 2 périodes (raies séparées) et 1,5 s, en
  nombre entier de périodes. Pris si r < 0,05 ET (raies latérales ≥ −12 dB au partiel mesuré, déduites de celles de k = 1-2 par
  la loi de Bessel, OU paire qui ne colle pas à Δ) ; trois ajustements d'affilée pour entrer, 0,5 s de tenue pour sortir.
  `source = 'peigne'`, `sigmaCents`. Une raie étrangère fait monter r : refus, le moteur d'avant lit (anches nettes à 0,05 ¢).
- `etatPaire` : `etatAnche` 'sur' | 'en cours' | 'centre' et `margeAnche` (¢) par anche d'un unisson, que l'interface lit comme la
  marge d'une anche confondue (ici `app.js`, `estimationConfondue` : « ±3,100 ¢ · en cours · encore 2 s »). Jamais « sûr » avant
  T_besoin = max(1 s, 1,2/Δ) (2/Δ sous 0,8 Hz), sans battement connu et paire qui colle, ni avec σ > 0,3 ¢. Sous la résolution de
  la fenêtre (Δ < 1/T, Do6-Do7 sous 0,35 Hz) : 'centre', le milieu des deux anches moyenné sur des périodes entières, chacune
  à ± Δ/2 (Δ par l'enveloppe, 0,03 Hz). La validation attend |écart| + marge < tolérance.
- Banc : `node test/bench_frequences.mjs` (297 cas) ; tests F 1 à F 11 de `test/frequences.test.mjs` (le F 12, de l'interface, reste dans PolyReed) (T1 à T7 de l'audit).

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
- v63 (16/10/2026) : certificat des lectures « sûr » reporté du produit (moteur : engine, plan, battement, certificat, nls-bessel ; docs/CERTIFICAT.md). Le refus s'affiche comme une anche « en cours » avec marge.
- v64 (16/10/2026) : le certificat devient la lecture affichée, super musette à trois anches (`nls-trio.js`), horloge du micro exigée (`cfg.horlogeIncertPpm`, absente ici : jamais refusée pour cela), domaine jusqu'à 60 Hz, battement affiché stable avec son incertitude (`beatCert`), un silence efface les certificats. Moteur reporté de PolyReed ; chiffres : docs/CERTIFICAT.md. Fiche de survol de la courbe d'accordage corrigée (fond noir fixe sous un texte sombre en thème clair : « carré noir » d'Ewen, 16/10/2026).
- v66 (16/10/2026, report du moteur de PolyReed v66, audit Fable final) : un « sûr » est invalidé dès que la note le quitte (sentinelle + lecture contredisante), le calcul du certificat tourne dans un Worker dédié (`dsp/cert-calcul.js`, `cert-worker.js`), la hauteur « sûre » exige 0,8 Hz de battement (raison `lent`), super musette `ident3` / `absente`. L'interface de l'ancienne page n'a PAS l'écran sobre ni la courbe du battement de PolyReed (ils vivent dans `web/js/ui/` de PolyReed, qui ne part jamais ici). Détail et chiffres : `docs/CERTIFICAT.md` § 0.
- v67 (18/10/2026, report du moteur de PolyReed v67, audit Fable n° 3) : modèle d'anches « struct » corrigé d'après les prises réelles du Zoom H6 (`dsp/nls-bessel.js` : AM par partiel, bornes `RK_MAX`, `MK_MAX`), lecture des battements lents sur un nombre entier de battements (`dsp/certificat.js`), incertitude de pression (`incertitudePression`). Gain mesuré sur H6 réel : 6 -> 16 notes posées sur 27, sans faux ; synthèse large 407 -> 470 posées, 2 -> 1 faux à 0,53 ¢. Limites : 6 faux de 0,51 à 0,72 ¢ sur synthèse, téléphone trop lent. Pas reporté : l'affichage de la pression (`ui/composants/chiffre.js`, absent ici), `test/modele-struct.test.mjs` et les bancs `test/outils/pose/` (restent dans PolyReed). Détail : `docs/CERTIFICAT.md` § 0A.
- v68 (18/10/2026, report du moteur de PolyReed v68, audit Fable n° 4) : retard après un saut mesuré et sentinelle prioritaire/moins chère (`dsp/certificat.js`), graves exigeant 3 partiels (`KU_SUR_MIN_GRAVE`), garde de cohérence des étiquettes (`ETIQ_COH_C` : une mauvaise étiquette à -21,5 ¢ était posée « sûre » dans un réglage essayé), calcul léger mesuré sur machine lente (`MS_LENT`, `msFroid`), simulateur du Worker à un cœur (`dsp/cert-calcul.js`), battement doublé corrigé (`dsp/nls-bessel.js` rival Ω/2, `llrOmega2` ; `dsp/battement.js` passe l'enveloppe au certificat) : le test F10 est remis à sa force et passe sous Node 22 ET Node 24. 0 « sûr » faux sur toutes les passes, 11 % de notes posées en moins en synthèse (le prix des graves). Pas reporté : bancs `test/outils/pose/`, tests du certificat, interface de PolyReed. Détail : `docs/CERTIFICAT.md` § 0B.
- v69 (19/10/2026, report du moteur de PolyReed v69, audit Fable n° 5) : 2 départs et 1 ajustement de front pour toutes les machines (`NDEPARTS` 2, `JOBS_MAX` 1 ; PB12 : +24 notes sur 300 en synthèse h6, 0 faux sur 3 600 notes de confirmation), graves jusqu'à 120 Hz (`F0_GRAVE_HZ`), gardes mortes retirées de `dsp/certificat.js`, comparaison d'étiquettes (`kcMax`, `kcPropre`, éteintes) et `kMin` de la sentinelle (réfuté) dans `dsp/nls-bessel.js`, contrôle de prise : fausse alarme 16 bits corrigée et alerte `echelle` par le secteur (`dsp/prise.js`), vitesse de calcul dans le JSON de la session. Pas reporté : bancs `test/outils/pose/`, interface de PolyReed. Détail et tableau de bord : `docs/CERTIFICAT.md` § 0C.
- v70 (19/10/2026, report du moteur de PolyReed v70, audit Fable n° 6) : `LIBRE_DOUBLON` (`dsp/certificat.js`, `dsp/nls-bessel.js` : une raie étrangère ajustée en doublon d'une anche n'est pas adoptée ; ferme le dernier « sûr » faux, 0 faux sur 3 600 notes), diagnostic du résidu des partiels 3-4 ; détail `docs/CERTIFICAT.md` § 0D.
