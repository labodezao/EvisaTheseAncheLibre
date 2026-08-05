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
