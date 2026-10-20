// Où en est la mesure d'une anche : attaque, en cours, résolue (v62, Ewen, 14/10/2026 : « au début ça
// fluctue, comme si la mesure était prise par les battements, et tout d'un coup, pof, ça se stabilise »).
//
// Deux causes distinctes, mesurées sur la prise H6 du 14/10/2026 (test/outils/phases.mjs, docs/PRISE-DE-SON.md) :
//  - la FENÊTRE d'analyse ne couvre pas encore assez de battements : deux anches qui battent à Ω Hz ne se séparent
//    qu'avec un son de plus de 2/Ω s (la lecture se pose en 1,1 fois 2/Ω en médiane : 1,4 à 6 s pour Ω de 0,5 à 1,5 Hz) ;
//  - l'ATTAQUE physique de l'anche : la hauteur suit la pression, elle monte puis retombe pendant 1 à 2,6 s (audit du
//    10/10/2026), même sans battement.
// Tant que ce n'est pas résolu, la courbe se trace en pointillé gris et aucun chiffre n'est dit juste : la mesure est
// « en cours », ou « attaque » (une information utile au luthier, pas un défaut à masquer).
//
// Pur, sans DOM : testé sous Node (test/phase.test.mjs).

export const ATTAQUE_S = 1.0;       // la première seconde de son d'une note : attaque
export const FACTEUR_OMEGA = 2.5;   // la fenêtre doit couvrir 2,5 / Ω secondes (la lecture se pose à 1,1 × 2/Ω = 2,2 / Ω)
export const OMEGA_MIN = 0.2;       // en dessous, pas de battement à résoudre
export const BESOIN_MAX_S = 6;      // on n'attend jamais plus de 6 s (la plus grande fenêtre du moteur est de 5,94 s)

// image du moteur -> { omega, voix: Map<id, { age, besoin, phase }> }. `phase` : 'attaque' | 'encours' | 'resolue'.
// `debutNote` : l'instant (s, horloge du moteur) de la première image de la note en cours ; l'âge du son est t.time - debutNote.
// (Le remplissage `fill` des groupes est celui de la plus grande fenêtre, 5,94 s : ce n'est pas l'âge de la note.)
export function phasesDe(t, debutNote = null) {
  const age = debutNote != null && Number.isFinite(t?.time) ? Math.max(0, t.time - debutNote) : 0;
  const out = new Map();
  let omega = 0;
  for (const g of t?.groups ?? []) {
    if (g.isHarmonic || g.isSub) continue;
    for (const v of g.voices ?? []) {
      if (!v.tracked || v.held) continue;
      omega = Math.max(omega, Math.abs(v.beatMeas ?? 0), Math.abs(v.beat ?? 0));
    }
  }
  const besoin = omega >= OMEGA_MIN ? Math.min(BESOIN_MAX_S, FACTEUR_OMEGA / omega) : 0;
  for (const g of t?.groups ?? []) {
    if (g.isHarmonic || g.isSub) continue;
    for (const v of g.voices ?? []) {
      if (!v.tracked) continue;
      // v64 : une seconde lecture certifiée (dsp/certificat.js) a déjà prouvé que les raies sont séparées : elle ne demande plus 2,5 / Ω
      const phase = age < ATTAQUE_S ? 'attaque' : age < besoin && !(v.cert?.ok && v.source === 'certificat') ? 'encours' : 'resolue';
      out.set(v.def.id, { age, besoin, phase });
    }
  }
  return { omega, voix: out };
}

// Les mots (français, anglais) d'une phase.
export function motPhase(phase, lang = 'fr') {
  const fr = lang !== 'en';
  if (phase === 'attaque') return fr ? 'attaque' : 'attack';
  if (phase === 'encours') return fr ? 'en cours' : 'settling';
  return '';
}
