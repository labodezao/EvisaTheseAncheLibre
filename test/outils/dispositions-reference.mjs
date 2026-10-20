// Référence des dispositions de clavier diatonique (main droite) et vérifications.
// Même fichier dans stages-lutherie (outils/clavier-accordeon/) et dans l'accordeur de la thèse
// (test/outils/) : le modifier aux deux endroits.
//
// Une disposition : { nom, rangs: [{ nom: "Rangée Sol (extérieure)", touches: [[poussé, tiré], ...] }] },
// notes en MIDI (La4 = 69), null = case absente. Le nom d'un rang donne sa tonalité.
//
// La RÉFÉRENCE est le Sol/Do 21 boutons (GC21, plan de Bernard Loffet, diato.free.fr, repris le 10/10/2026) :
// le rang Sol a 11 boutons et le rang Do 10. Un autre ton se déduit par transposition de chaque rang
// (bouton par bouton, poussé et tiré), l'octave étant celle de l'instrument mais la MÊME pour tout le rang.
// Cause du bogue de La/Ré (20/10/2026) : les présets étaient « transposés » à la main de l'ancien GC21,
// qui avait 4 boutons faux (b1, b1', b6' tiré, b10' tiré) ; l'erreur d'octave se retrouvait au bouton 6 et 10.

export const REF_GC21 = Object.freeze({
  sol: Object.freeze([[51, 49], [50, 54], [55, 57], [59, 60], [62, 64], [67, 66], [71, 69], [74, 72], [79, 76], [83, 78], [86, 81]]),
  do: Object.freeze([[56, 58], [55, 59], [60, 62], [64, 65], [67, 69], [72, 71], [76, 74], [79, 77], [84, 81], [88, 83]]),
});

// Présets dont on ne tranche pas la vraie note (instruments réels de facteurs, plans « Alts ») : seulement
// signalés par la vérification physique, jamais corrigés. Voir la question « Accordeur : dispositions ».
export const DOUTEUX = Object.freeze({
  SolDo_Darwin: 'Darwin 33/24 : rang Do identique à l\'ancien Do fautif (Si♭, Mi et Fa# dans un rang de Do)',
  SolDo_Lamarck: 'Lamarck 33/24 : rangs Fa et Do aux sauts de plus de 5 demi-tons',
  SolDo_Corgeron: 'Corgeron 33/8 : rang « Sol » poussé/tiré échangés par rapport à Heim 18b',
  SolDo_Heim: 'Heim 33/12 : rang « Sol » échangé et rang « Do » qui répète le Sol',
  SolDo_Heim12b: 'Heim 12 basses : mêmes réserves que Heim',
  SolDo_MilleretPignol12b: 'Milleret Pignol 12 basses : mêmes réserves que Heim',
  SolDo_Heim18b: 'Heim 18 basses : repris du plan Loffet 3R33-18B',
  SolDoAlts_Bottasso: 'rang Alts : altérations de l\'instrument',
  SolDoAlts_Gaillard: 'rang Alts : altérations de l\'instrument',
  SolDoAlts_JPL: 'rang Alts : altérations de l\'instrument',
  SolDoAlts_LTL: 'rang Alts : altérations de l\'instrument',
  SolDoAlts_milleretPignol18b: 'octaves incohérentes (Si4 après Sol3 puis Ré4) : saisie à reprendre sur l\'instrument',
  DG21: 'Ré/Sol « gamme en 4 » (plan Loffet DG_2r8b) : autre système que GC21',
});

// Plans repris de Loffet dont le bouton 1 (altération) n'est pas celui du GC21 transposé (systèmes irlandais,
// Fa/Sib) : le bouton 1 n'est pas comparé à la référence.
export const BOUTON1_PROPRE = Object.freeze(['BC21', 'CSharpD21', 'FBb21', 'ADb21', 'DbEb21', 'EbF21', 'FGb21', 'GAb21']);

const NOMS = ['Do', 'Do#', 'Ré', 'Ré#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'];
export const nomNote = (m) => (m == null ? '-' : NOMS[((m % 12) + 12) % 12] + (Math.floor(m / 12) - 1));
const CL = { do: 0, re: 2, 'ré': 2, mi: 4, fa: 5, sol: 7, la: 9, si: 11 };

export function toniqueDuRang(nom) {
  const m = /Rang[ée]e\s+(do|ré|re|mi|fa|sol|la|si)\s*(#|b|♭)?(?![a-zé])/i.exec(String(nom ?? ''));
  if (!m) return null;
  return (CL[m[1].toLowerCase()] + (m[2] === '#' ? 1 : m[2] ? -1 : 0) + 12) % 12;
}
export function typeErreur(d) {
  if (d % 12 === 0) return 'octave';
  if (Math.abs(d) === 1) return 'demi-ton';
  if (Math.abs(d) === 2) return 'ton';
  return 'autre';
}
const MAJ = [0, 2, 4, 5, 7, 9, 11];
export const dansGamme = (m, t) => MAJ.includes((((m - t) % 12) + 12) % 12);

// Attendu d'un rang de 2 rangs (21 boutons) : GC21 transposé. Le décalage est congru à (tonique - tonique de
// référence) modulo 12 ; on prend celui qui colle le mieux au rang (une octave d'ensemble n'est pas une erreur).
export function attenduDeuxRangs(rang) {
  const t = toniqueDuRang(rang.nom);
  const n = rang.touches.length;
  const base = n === 11 ? REF_GC21.sol : n === 10 ? REF_GC21.do : null;
  if (base == null || t == null) return null;
  const k = (((t - (n === 11 ? 7 : 0)) % 12) + 12) % 12;
  let best = null;
  for (const s of [k - 24, k - 12, k, k + 12, k + 24]) {
    let tot = 0;
    for (let i = 0; i < n; i++) for (const j of [0, 1]) {
      const v = rang.touches[i]?.[j];
      if (v != null) tot += Math.abs(v - (base[i][j] + s));
    }
    if (best === null || tot < best.tot) best = { s, tot };
  }
  return { attendu: base.map(([p, q]) => [p + best.s, q + best.s]), decalage: best.s };
}

// Rang diatonique des plans à trois rangs : le bouton 1 pousse la tonique et tire le 2e degré (Sol3/La3 du GC21) ;
// poussé = accord parfait (degrés 1 3 5), tiré = degrés 2 4 6 7.
const P_DEG = [0, 4, 7];
const T_DEG = [2, 5, 9, 11];
const gen = (deg, t, idx, base) => base + t + deg[idx % deg.length] + 12 * Math.floor(idx / deg.length);
export function attenduEngendre(rang) {
  const t = toniqueDuRang(rang.nom);
  if (t == null) return null;
  const n = rang.touches.length;
  const cote = [[], []];
  for (const [j, deg] of [[0, P_DEG], [1, T_DEG]]) {
    let best = null;
    for (let oct = 12; oct <= 84; oct += 12) {
      const seq = []; let ok = 0; let dist = 0;
      for (let i = 0; i < n; i++) {
        const v = gen(deg, t, i, oct);
        seq.push(v);
        const r = rang.touches[i][j];
        if (r != null) { if ((r - v) % 12 === 0) ok++; dist += Math.abs(r - v); }
      }
      if (best === null || ok > best.ok || (ok === best.ok && dist < best.dist)) best = { ok, dist, seq };
    }
    cote[j] = best.seq;
  }
  return { attendu: cote[0].map((p, i) => [p, cote[1][i]]) };
}

// Contrôles physiques d'un rang, à partir du bouton `debut` (2 : le bouton 1 est une altération).
export function controlesPhysiques(rang, { debut = 1, gamme = true } = {}) {
  const res = [];
  const t = toniqueDuRang(rang.nom);
  for (const [j, sens] of [[0, 'poussé'], [1, 'tiré']]) {
    const s = rang.touches.map((b) => b[j]);
    for (let i = debut + 1; i < s.length; i++) {
      if (s[i] == null || s[i - 1] == null) continue;
      const d = s[i] - s[i - 1];
      if (d < 0) res.push({ sens, bouton: i + 1, type: 'décroît', detail: `${nomNote(s[i - 1])} -> ${nomNote(s[i])}` });
      else if (d === 0) res.push({ sens, bouton: i + 1, type: 'répété', detail: nomNote(s[i]) });
      else if (d > 5) res.push({ sens, bouton: i + 1, type: 'saut > 5 demi-tons', detail: `${nomNote(s[i - 1])} -> ${nomNote(s[i])} (${d})` });
    }
    if (gamme && t != null) s.forEach((m, i) => { if (i >= debut && m != null && !dansGamme(m, t)) res.push({ sens, bouton: i + 1, type: 'hors gamme', detail: nomNote(m) }); });
  }
  rang.touches.forEach((b, i) => {
    if (i >= debut && b[0] != null && b[1] != null && Math.abs(b[0] - b[1]) > 7) res.push({ sens: 'p/t', bouton: i + 1, type: 'poussé/tiré > 7 demi-tons', detail: `${nomNote(b[0])}/${nomNote(b[1])}` });
  });
  return res;
}

export function comparer(rang, attendu, debut = 0) {
  const errs = [];
  rang.touches.forEach((b, i) => {
    if (i < debut) return;
    for (const [j, sens] of [[0, 'poussé'], [1, 'tiré']]) {
      const exp = attendu[i]?.[j];
      if (b[j] == null || exp == null || b[j] === exp) continue;
      const d = b[j] - exp;
      errs.push({ sens, bouton: i + 1, calcule: nomNote(b[j]), attendu: nomNote(exp), type: typeErreur(d), diff: d });
    }
  });
  return errs;
}

// Vérifie un ensemble de plans { id: { nom, rangs } }. Retourne les écarts à la référence, les contrôles
// physiques en défaut, les plans vérifiés et les plans laissés (DOUTEUX).
export function verifierPlans(plans) {
  const res = { verifies: [], douteux: [], ecarts: [], physiques: [] };
  for (const [id, plan] of Object.entries(plans)) {
    if (DOUTEUX[id]) { res.douteux.push(id); continue; }
    const nb = plan.rangs.length;
    if (nb !== 2 && nb !== 3) continue;
    res.verifies.push(id);
    const debut = BOUTON1_PROPRE.includes(id) ? 1 : 0;
    for (const rang of plan.rangs) {
      const a = nb === 2 ? attenduDeuxRangs(rang) : attenduEngendre(rang);
      if (a) for (const e of comparer(rang, a.attendu, debut)) res.ecarts.push({ id, rang: rang.nom.trim(), ...e });
      for (const p of controlesPhysiques(rang, { debut: nb === 2 ? 1 : 0 })) res.physiques.push({ id, rang: rang.nom.trim(), ...p });
    }
  }
  return res;
}
