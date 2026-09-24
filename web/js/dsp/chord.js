// Accords en degrés : on dit « 1 3 5 » une fois, l'accordeur reconnaît
// lui-même la fondamentale de l'accord joué et mesure chaque note.
//
// Demande d'Ewen (24/09/2026) : 36 accords de basses à vérifier sur un
// chromatique — pas question de choisir les notes à la main pour chacun. Et
// sur les basses d'un chromatique, les notes d'un accord sont repliées dans
// une octave (renversements) : la quinte peut être sous la fondamentale, ou
// une octave au-dessus. On cherche donc chaque note là où elle EST.

// Degré → demi-tons au-dessus de la fondamentale.
const DEG = {
  1: 0, b2: 1, 2: 2, '#2': 3, b3: 3, 3: 4, 4: 5, '#4': 6, b5: 6, 5: 7, '#5': 8, b6: 8,
  6: 9, bb7: 9, b7: 10, 7: 11, 8: 12, b9: 13, 9: 14, '#9': 15, 11: 17, '#11': 18, b13: 20, 13: 21,
};
const NAME = { 0: '1', 1: '♭2', 2: '2', 3: '♭3', 4: '3', 5: '4', 6: '♭5', 7: '5', 8: '♯5', 9: '6',
  10: '♭7', 11: '7', 12: '8', 14: '9', 17: '11', 21: '13' };

// Accords usuels (basses standard d'un chromatique ou d'un piano à boutons).
// `suffix` : le nom court après la fondamentale (« Ré m », « La 7 »).
export const CHORD_TYPES = {
  quinte: { name: 'quinte', degrees: [0, 7], suffix: '5' },
  majeur: { name: 'majeur', degrees: [0, 4, 7], suffix: '' },
  mineur: { name: 'mineur', degrees: [0, 3, 7], suffix: 'm' },
  septieme: { name: 'septième', degrees: [0, 4, 10], suffix: '7' },
  diminue: { name: 'diminué', degrees: [0, 3, 9], suffix: 'dim' },
  sept5: { name: 'septième avec quinte', degrees: [0, 4, 7, 10], suffix: '7' },
};

// Type d'accord reconnu tout seul (comme l'accordeur de Dirk, qui affiche
// « Dm », « A », « Edim » sans qu'on lui dise quoi attendre) : les 36 accords
// d'un chromatique — majeurs, mineurs, septièmes — d'une seule traite.
//
// On essaie chaque type. Un accord ne compte que si TOUTES ses notes ont une
// vraie raie (pas seulement un harmonique : le partiel 7 de Do4 tombe à −31 ¢
// d'un Si♭ et ferait croire à « Do 7 ») ; parmi ceux-là, le plus riche en
// notes gagne (un accord majeur contient aussi une quinte), puis le plus
// fort. L'accord tenu est gardé tant qu'il reste valable et à 80 % du
// meilleur.
export function chordAuto(peaks, { a4 = 440, prev = null } = {}) {
  let best = null, keep = null;
  for (const [type, def] of Object.entries(CHORD_TYPES)) {
    const same = prev && prev.type === type;
    const ch = chordFromPeaks(peaks, def.degrees, { a4, prevRoot: same ? prev.rootPc : null,
      prevNotes: same ? prev.notes.map((n) => n.midi) : null });
    if (!ch || ch.harm) continue;
    // Notes de niveaux comparables (à 14 dB près) : les anches d'un accord
    // sonnent ensemble ; une raie bien plus faible qui passe (mesuré : un Fa5
    // fugace sur une quinte Do♯4 + Sol♯4) n'en fait pas un accord majeur.
    const amps = ch.notes.map((nt) => nt.amp * nt.amp);     // amp = √magnitude
    if (Math.min(...amps) < 0.2 * Math.max(...amps)) continue;
    const cand = { ...ch, type, n: def.degrees.length };
    if (same && ch.rootPc === prev.rootPc) keep = cand;
    if (!best || cand.n > best.n || (cand.n === best.n && cand.score > best.score)) best = cand;
  }
  if (keep && best && keep !== best && keep.n >= best.n && keep.score >= 0.8 * best.score) return keep;
  return best;
}

export function chordName(rootName, type) {
  const def = CHORD_TYPES[type];
  if (!def) return rootName;
  return def.suffix ? `${rootName}${def.suffix === 'm' || def.suffix === '7' ? '' : ' '}${def.suffix}` : rootName;
}

// « 1 3 5 », « 1 b3 5 », « 1 ♭3 6 », « 1-3-b7 » → [0, 4, 7] …
export function parseDegrees(text) {
  if (!text) return null;
  const toks = String(text).normalize('NFC').replace(/♭/g, 'b').replace(/♯/g, '#')
    .split(/[\s,;\-–/]+/).filter(Boolean);
  const out = [];
  for (const t of toks) {
    const k = t.toLowerCase();
    if (!(k in DEG)) return null;
    if (!out.includes(DEG[k])) out.push(DEG[k]);
  }
  if (!out.length) return null;
  if (!out.includes(0)) out.unshift(0);             // la fondamentale est toujours mesurée
  return out.sort((a, b) => a - b);
}

export function degreeLabel(semi) {
  return NAME[semi] ?? `+${semi}`;
}

export function degreesText(degrees) {
  return degrees.map(degreeLabel).join(' ');
}

// Reconnaît l'accord `degrees` dans les pics du spectre large bande.
//
// Pour chaque fondamentale possible (les 12 classes de notes), chaque degré
// doit trouver une raie forte (≥ −20 dB de la plus forte) de sa classe de
// note, à ±35 ¢ du tempérament égal : on prend la PLUS GRAVE, car les
// harmoniques d'une note sont toujours au-dessus d'elle (Do4 fait un Sol5 par
// son partiel 3, jamais un Sol4). Toutes les notes de l'accord doivent être
// là. Score : somme des amplitudes. `prevRoot` (classe de note) garde
// l'accord tenu tant qu'un concurrent ne le dépasse pas nettement.
//
// Retourne { rootPc, rootMidi, notes: [{ semi, midi }], score } ou null.
export function chordFromPeaks(peaks, degrees, { a4 = 440, prevRoot = null, prevNotes = null, midiMin = 28, midiMax = 96 } = {}) {
  if (!peaks?.length || !degrees?.length) return null;
  let maxMag = 0;
  for (const p of peaks) maxMag = Math.max(maxMag, p.mag);
  const strong = [];
  for (const p of peaks) {
    if (p.mag < maxMag / 10 || p.freq < 30 || p.freq > 3000) continue;
    const m = 69 + 12 * Math.log2(p.freq / a4);
    const r = Math.round(m);
    if (Math.abs(m - r) > 0.35 || r < midiMin || r > midiMax) continue;
    strong.push({ midi: r, pc: ((r % 12) + 12) % 12, amp: Math.sqrt(p.mag), freq: p.freq });
  }
  if (!strong.length) return null;
  // Une raie qui tombe sur un partiel (×2 … ×10) d'une raie forte plus grave
  // n'est sans doute qu'un harmonique. Mesuré sur une paire Ré4 + La4 : le
  // partiel 3 de La4 (Mi6, la raie la plus forte du son !) faisait reconnaître
  // « La4 + Mi6 ». Elle ne compte qu'à 30 %, et seulement si sa classe de note
  // n'a aucune raie plus franche.
  for (const s of strong) {
    s.harm = strong.some((q) => q.freq < s.freq * 0.95 && (() => {
      const k = Math.round(s.freq / q.freq);
      return k >= 2 && k <= 10 && Math.abs(1200 * Math.log2(s.freq / (k * q.freq))) < 25;
    })());
  }
  // Par classe de note : la raie la plus grave qui n'est pas un harmonique ;
  // à défaut, la plus grave tout court, pondérée à 30 %.
  const lowest = new Map();
  for (const s of strong) {
    const cur = lowest.get(s.pc);
    const better = !cur || (cur.harm && !s.harm) || (cur.harm === s.harm && s.midi < cur.midi);
    if (better) lowest.set(s.pc, { midi: s.midi, amp: s.harm ? 0.3 * s.amp : s.amp, harm: s.harm });
  }
  let best = null, prev = null;
  for (let r = 0; r < 12; r++) {
    const notes = [];
    let score = 0;
    let ok = true;
    let harm = false;
    for (const d of degrees) {
      const n = lowest.get((r + d) % 12);
      if (!n) { ok = false; break; }
      notes.push({ semi: d, midi: n.midi, amp: n.amp });
      score += n.amp;
      if (n.harm) harm = true;
    }
    if (!ok) continue;
    if (new Set(notes.map((n) => n.midi)).size < notes.length) continue;   // octave « 1 8 » : même raie
    const cand = { rootPc: r, rootMidi: notes[0].midi, notes, score, harm };
    if (r === prevRoot) prev = cand;
    if (!best || score > best.score) best = cand;
  }
  if (prev && best && prev !== best && prev.score >= 0.8 * best.score) return prev;
  // Un accord qui ne tient que par une raie « harmonique » ne remplace pas
  // l'accord tenu tant que celui-ci a encore une vraie raie : mesuré, une
  // anche du tiré se tait un instant et le partiel 3 de l'autre (La4 → Mi6)
  // faisait basculer Ré4 + La4 en « La4 + Mi6 ».
  if (best && prevRoot != null && best.rootPc !== prevRoot && best.harm) {
    const prevAlive = prevNotes?.some((m) => strong.some((s) => s.midi === m && !s.harm));
    if (prevAlive) return null;
  }
  return best;
}
