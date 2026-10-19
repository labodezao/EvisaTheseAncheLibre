// Protocole d'accordage guidé : une disposition de clavier donne la SUITE
// ATTENDUE des notes (rangée, bouton, sens) ; le rapport avance tout seul dans
// cette suite à mesure qu'Ewen joue, range chaque mesure à sa case, signale
// une note inattendue sans casser la suite et permet de refaire une case.
// Module pur (Node et navigateur), testé par test/accordage.test.mjs.
//
// Ordre (Ewen, 19/10/2026) : toute la première rangée en TIRÉ, puis la
// deuxième (puis la troisième), chaque fois du grave vers l'aigu, bouton par
// bouton ; puis les mêmes rangées en POUSSÉ. Au chromatique, la note d'un
// bouton est la même tirée et poussée, mais ce sont deux anches : le
// protocole passe quand même deux fois (une fois par sens).

import { PLANS_CLAVIER } from './plans-clavier.js';

export const SENS = Object.freeze({ T: 'tiré', P: 'poussé' });

// ---- Dispositions -----------------------------------------------------------------
// Diatonique : les 42 présets de l'outil « Plan de claviers » du site des
// stages (plans-clavier.js, source dans son en-tête). Un bouton = [poussé, tiré].
// Chromatique : aucun préset dans l'outil. Disposition STANDARD, à confirmer
// par Ewen : trois rangées, des boutons espacés d'une tierce mineure (3 demi-tons)
// le long d'une rangée ; d'une rangée à la suivante, un demi-ton de plus
// (système C) ou de moins (système B, image miroir). Le premier bouton et le
// nombre de boutons par rangée sont des paramètres.
export const CHROMATIQUE_DEFAUT = Object.freeze({ premier: 52, boutons: 12 }); // Mi3, 12 par rangée : À CONFIRMER

export function planChromatique(systeme = 'C', { premier = CHROMATIQUE_DEFAUT.premier, boutons = CHROMATIQUE_DEFAUT.boutons, rangs = 3 } = {}) {
  const signe = systeme === 'B' ? -1 : 1;
  return {
    nom: `Chromatique système ${systeme} — ${rangs} rangs`,
    categorie: 'Chromatique',
    chromatique: true,
    rangs: Array.from({ length: rangs }, (_, r) => ({
      nom: `Rangée ${r + 1}`,
      touches: Array.from({ length: boutons }, (_, k) => {
        const n = premier + signe * r + 3 * k;
        return [n, n];
      }),
    })),
  };
}

export function dispositions() {
  const out = [];
  for (const [id, p] of Object.entries(PLANS_CLAVIER)) {
    out.push({ id, nom: p.nom, groupe: p.categorie ?? 'Diatonique', plan: p, source: 'stages-lutherie, outils/clavier-accordeon/presets' });
  }
  for (const s of ['C', 'B']) {
    out.push({ id: `chromatique-${s}`, nom: `Chromatique système ${s} (3 rangs)`, groupe: 'Chromatique', plan: planChromatique(s), source: 'disposition standard, à confirmer par Ewen', aConfirmer: true });
  }
  return out;
}

export function dispositionDe(id, params = {}) {
  if (/^chromatique-[BC]$/.test(id)) {
    const plan = planChromatique(id.slice(-1), params);
    return { id, nom: plan.nom, groupe: 'Chromatique', plan, aConfirmer: true };
  }
  const p = PLANS_CLAVIER[id];
  return p ? { id, nom: p.nom, groupe: p.categorie ?? 'Diatonique', plan: p } : null;
}

// ---- La suite attendue -----------------------------------------------------------
// Une case : { id, rang, bouton, sens, midi, nomRang } (rang et bouton à partir de 0
// en interne ; `id` et l'affichage comptent à partir de 1). `inverser` : la
// rangée listée en dernier dans le préset est jouée en premier.
export function suiteAttendue(plan, { inverser = false, sens = ['T', 'P'] } = {}) {
  const ordre = plan.rangs.map((_, i) => i);
  if (inverser) ordre.reverse();
  const out = [];
  for (const s of sens) {
    for (const r of ordre) {
      plan.rangs[r].touches.forEach((t, b) => {
        const midi = s === 'P' ? t[0] : t[1];
        if (midi == null) return;
        out.push({ id: `${s}-r${r + 1}-b${b + 1}`, rang: r + 1, bouton: b + 1, sens: s, midi, nomRang: plan.rangs[r].nom });
      });
    }
  }
  return out;
}

// ---- Le remplissage automatique -------------------------------------------------
export class Protocole {
  constructor(plan, options = {}) {
    this.plan = plan;
    this.options = options;
    this.suite = suiteAttendue(plan, options);
    this.faits = new Map(); // id de case -> { ts }
    this.index = 0;         // position de la dernière case remplie + 1
    this.alertes = [];      // journal des signalements (texte)
  }

  get termine() { return this.suite.every((c) => this.faits.has(c.id)); }
  get nbFaits() { return this.faits.size; }

  // La case attendue : la première non remplie à partir de `index`, sinon la
  // première non remplie de toute la suite (cases sautées).
  courante() {
    const ap = this.suite.findIndex((c, i) => i >= this.index && !this.faits.has(c.id));
    if (ap >= 0) return this.suite[ap];
    return this.suite.find((c) => !this.faits.has(c.id)) ?? null;
  }

  _alerte(type, texte) {
    this.alertes.push({ type, texte });
    if (this.alertes.length > 50) this.alertes.shift();
    return texte;
  }

  // Une mesure stable : { midi (note jouée), sens ('T' | 'P') }.
  // Rend { type, cas?, alerte? } : 'ok' (case attendue), 'saut' (une case plus
  // loin : celles entre les deux restent à faire), 'sens' (bonne note, mauvais
  // sens : rien n'est rangé), 'deja' (case déjà faite : rien n'est écrasé),
  // 'inattendue' (note absente de la suite), 'termine'.
  entrer({ midi, sens }) {
    const attendue = this.courante();
    if (!attendue) return { type: 'termine' };
    const nom = (c) => `${c.nomRang} bouton ${c.bouton}, ${SENS[c.sens]}`;
    if (attendue.midi === midi && attendue.sens === sens) {
      return this._remplir(attendue, 'ok');
    }
    const pos = (c) => this.suite.indexOf(c);
    const dansSuite = this.suite.filter((c) => c.midi === midi);
    // Le sens détecté ne change jamais l'étape : s'il diffère du sens attendu, on
    // alerte « sens inversé » et rien n'est rangé (sauf si Ewen avance l'étape).
    if (sens && sens !== attendue.sens) {
      if (!dansSuite.length) return { type: 'inattendue', alerte: this._alerte('inattendue', `note inattendue (MIDI ${midi}, ${SENS[sens] ?? sens}) ; attendu : ${nom(attendue)}`) };
      return { type: 'sens', cas: dansSuite.find((c) => c.sens === attendue.sens && !this.faits.has(c.id)) ?? dansSuite[0],
        alerte: this._alerte('sens', `sens inversé : entendue en ${SENS[sens]}, attendu en ${SENS[attendue.sens]} (${nom(attendue)})`) };
    }
    // La case est cherchée dans la rangée et le sens de l'étape en cours, jamais ailleurs.
    const rangee = this.suite.filter((c) => c.rang === attendue.rang && c.sens === attendue.sens && c.midi === midi);
    const libres = rangee.filter((c) => !this.faits.has(c.id));
    if (libres.length) {
      const ap = pos(attendue);
      const dist = (c) => { const d = pos(c) - ap; return d < 0 ? 1e6 - d : d; };
      const cible = libres.slice().sort((x, y) => dist(x) - dist(y))[0];
      const sautees = this.suite.slice(Math.min(ap, pos(cible)), pos(cible)).filter((c) => !this.faits.has(c.id));
      const r = this._remplir(cible, 'saut');
      r.sautees = sautees;
      r.alerte = this._alerte('saut', sautees.length
        ? `bouton sauté : ${sautees.slice(0, 3).map(nom).join(' ; ')}${sautees.length > 3 ? ' …' : ''} ; mesure rangée à ${nom(cible)}`
        : `mesure rangée à ${nom(cible)} (hors de l'ordre attendu)`);
      return r;
    }
    if (rangee.length) {
      return { type: 'deja', cas: rangee[0], alerte: this._alerte('deja', `${nom(rangee[0])} est déjà mesuré : cliquez sur la case pour la refaire`) };
    }
    // Une case restée vide PLUS HAUT dans la suite (bouton passé sans être mesuré), même sens :
    // on la remplit (rattrapage), sans changer l'étape en cours (Ewen, 19/10/2026 : Sol#5 de
    // la rangée La refusé une fois l'étape passée à la rangée Ré).
    const ap0 = pos(attendue);
    const derriere = dansSuite.filter((c) => c.sens === attendue.sens && !this.faits.has(c.id) && pos(c) < ap0);
    if (derriere.length) {
      const cible = derriere[derriere.length - 1];
      this.faits.set(cible.id, { ts: Date.now() });
      return { type: 'rattrapage', cas: cible, suivante: this.courante(),
        alerte: this._alerte('rattrapage', `case passée sans mesure, remplie maintenant : ${nom(cible)}`) };
    }
    const ailleurs = dansSuite.filter((c) => c.sens === attendue.sens);
    if (ailleurs.length) {
      return { type: 'inattendue', alerte: this._alerte('inattendue', `note inattendue pour cette étape (MIDI ${midi}) : elle existe ailleurs (${nom(ailleurs[0])}) mais n'est pas rangée ; attendu : ${nom(attendue)}`) };
    }
    if (dansSuite.length) {
      return { type: 'sens', cas: dansSuite[0], alerte: this._alerte('sens', `sens inversé : cette note est dans la suite en ${SENS[dansSuite[0].sens]}, entendue en ${SENS[sens] ?? sens} (attendu : ${nom(attendue)})`) };
    }
    return { type: 'inattendue', alerte: this._alerte('inattendue', `note inattendue (MIDI ${midi}, ${SENS[sens] ?? sens}) ; attendu : ${nom(attendue)}`) };
  }

  // Un clic sur un bouton du plan en fait l'étape en cours ; une case déjà mesurée est à refaire
  // (la prochaine mesure la remplace).
  viser(id) {
    const i = this.suite.findIndex((c) => c.id === id);
    if (i < 0) return null;
    this.faits.delete(id);
    this.index = i;
    return this.suite[i];
  }

  _remplir(cas, type) {
    this.faits.set(cas.id, { ts: Date.now() });
    this.index = this.suite.indexOf(cas) + 1;
    return { type, cas, suivante: this.courante() };
  }

  // Relit les cases déjà mesurées dans le rapport (ids de cases) : au chargement,
  // et après une correction du rapport (bascule tiré / poussé, réaffectation).
  restaurer(ids) {
    this.faits.clear();
    let max = -1;
    for (const id of ids) {
      const i = this.suite.findIndex((c) => c.id === id);
      if (i >= 0) { this.faits.set(id, { ts: 0 }); max = Math.max(max, i); }
    }
    this.index = 0; // la première case encore à faire (une case sautée ou corrigée revient)
  }

  // Refaire une case : elle redevient la case attendue.
  refaire(id) {
    const i = this.suite.findIndex((c) => c.id === id);
    if (i < 0) return null;
    this.faits.delete(id);
    this.index = i;
    return this.suite[i];
  }
}
