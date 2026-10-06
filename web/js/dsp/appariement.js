// Appariement des raies mesurées aux anches attendues : affinage de la
// hauteur par la phase de l'amas de raies (clusterRefine), appariement
// dans l'ordre des fréquences (assignOrdered), méthodes matchVoices et
// fillVoice. Sorti d'engine.js (v28) sans rien changer : les méthodes sont
// posées sur Engine.prototype par engine.js (Object.assign), `this` reste
// le moteur.

import { FFT } from './fft.js';
import { centsBetween } from '../music.js';

// Hauteur moyenne d'une anche = pente de la PHASE de son amas de raies.
//
// Le soufflet module la pression, donc la hauteur : chaque partiel d'une
// anche devient un amas — la porteuse et des raies latérales à ±f_soufflet,
// d'autant plus fortes que le partiel est haut (indice de modulation ∝ k).
// Mesuré (test/bench_courbe.mjs, MMM, soufflet ±1 ¢ à 1,5 Hz, suivi sur H5) :
// la raie latérale n'est qu'à −4 dB de la porteuse, et le traqueur sautait
// de l'une à l'autre d'une image à l'autre — +1,2 ¢, 0, +1,2 ¢… : des dents
// de scie sur la courbe, sur un son parfaitement régulier.
//
// On ne choisit donc plus UNE raie : on garde tout l'amas de l'anche (jusqu'à
// mi-chemin de ses voisines, au plus CLUSTER_HZ dans le domaine du partiel),
// on revient dans le temps par FFT inverse, et la pente de la phase déroulée
// donne la fréquence MOYENNE DANS LE TEMPS de l'anche sur la fenêtre. Un
// barycentre de puissance a été essayé et écarté : quand on pousse plus fort,
// l'anche est à la fois plus forte et plus haute, et un barycentre de
// puissance penche vers les instants forts (+0,1 ¢ biais, soufflet calme ;
// +0,56 ¢, soufflet vivant). La phase, elle, ne pèse pas le son.
const CLUSTER_HZ = 5;
// Les bornes d'amas sont prises à mi-chemin des positions ATTENDUES des
// anches voisines (`expectedMt` : leur mesure précédente, sinon leur cible),
// pas des raies choisies : une raie choisie peut être une raie latérale, et
// des bornes qui sautent avec elle refont des dents de scie.
//
// `foreign` : fréquences (Hz) des raies CONNUES d'autres anches (le partiel
// 2k du 16' dans la bande du partiel k du 8'). L'amas s'arrête aussi à
// mi-chemin de chacune : sinon il les avalait (l'amas fait ±5 Hz, l'écart
// réel n'est que de k δ) et la pente de phase lisait la raie la plus forte
// des deux, celle du 16' sur une basse au timbre riche.
export function clusterRefine(chosen, az, calib, div, expectedMt = null, foreign = null) {
  const { W, srd, fc, re, im } = az;
  if (!re || W < 64) return;                      // fenêtre trop courte : on garde la raie
  const binHz = srd / W;
  const foreignOff = foreign ? foreign.map((f) => f / calib - fc).filter((o) => Math.abs(o) < srd / 2) : [];
  const offOf = (b) => (b <= W / 2 ? b : b - W) * binHz;
  const toOff = (f) => (f * div) / calib - fc;    // fondamentale → décalage dans la bande
  // Centre de l'amas : la mémoire de l'anche (sa hauteur à l'image
  // précédente) si la raie choisie en est proche — c'est peut-être une raie
  // latérale, l'amas se centre alors sur la porteuse. Sinon, la raie
  // elle-même : quand la « mémoire » n'est que la CIBLE du registre et que
  // l'anche en est loin (musette à +17 ¢ pour une cible à +7 ¢), l'amas
  // centré sur la cible excluait l'anche, la mesure d'amas échouait, l'anche
  // n'avait jamais de mémoire — et une raie latérale de sa voisine, plus
  // proche de la cible, finissait par lui être attribuée (−2,8 ¢ au lieu de
  // +17,2 ¢ après 3 s de note). Mais seulement si la raie est bien à l'écart
  // des raies des autres voix : une voix sans anche (registre 8'+8' quand une
  // seule anche sonne) prend une raie latérale de sa voisine, et l'amas centré
  // sur elle couperait en deux celui de la vraie anche.
  const centre = (i) => {
    const m = expectedMt?.[i] != null ? toOff(expectedMt[i]) : null;
    if (m == null || Math.abs(m - chosen[i].off) < CLUSTER_HZ / 2) return m ?? chosen[i].off;
    const alone = chosen.every((c, j) => j === i || !c || Math.abs(c.off - chosen[i].off) >= CLUSTER_HZ);
    return alone ? chosen[i].off : m;
  };
  const idx = chosen.map((c, i) => (c ? i : -1)).filter((i) => i >= 0)
    .sort((a, b) => centre(a) - centre(b));
  const fft = FFT.get(W);
  const zr = new Float64Array(W), zi = new Float64Array(W);
  idx.forEach((i, r) => {
    const c = chosen[i];
    if (c.off == null || c.cluster) return;
    const m = centre(i);
    let lo = Math.max(m - CLUSTER_HZ, r > 0 ? (centre(idx[r - 1]) + m) / 2 : -Infinity);
    let hi = Math.min(m + CLUSTER_HZ, r < idx.length - 1 ? (centre(idx[r + 1]) + m) / 2 : Infinity);
    for (const fo of foreignOff) {
      if (Math.abs(fo - c.off) < 2 * binHz) continue;   // la raie choisie est celle-là (confondue)
      if (fo > c.off) hi = Math.min(hi, (fo + c.off) / 2); else lo = Math.max(lo, (fo + c.off) / 2);
    }
    // La raie choisie doit être dans l'amas, avec son lobe principal.
    if (c.off - lo < 2 * binHz || hi - c.off < 2 * binHz || hi - lo < 6 * binHz) return;
    const half = Math.max(c.off - lo, hi - c.off);
    // Masque : l'amas seul (spectre conjugué → FFT directe = FFT inverse conjuguée).
    zr.fill(0); zi.fill(0);
    const b0 = Math.floor(lo / binHz), b1 = Math.ceil(hi / binHz);
    for (let bb = b0; bb <= b1; bb++) {
      const b = ((bb % W) + W) % W;
      const f = offOf(b);
      if (f < lo || f > hi) continue;
      zr[b] = re[b]; zi[b] = -im[b];
    }
    fft.transform(zr, zi);                        // z[n] = conj(résultat)/W — le signe se règle ci-dessous
    // Démodulation par la raie choisie : la phase résiduelle tourne lentement,
    // le déroulement est sans ambiguïté.
    const w0 = (2 * Math.PI * c.off) / srd;
    const n0 = Math.floor(W * 0.15), n1 = Math.ceil(W * 0.85);
    let last = null, acc = 0;
    let sw = 0, sn = 0, sp = 0, snn = 0, snp = 0;
    for (let n = n0; n < n1; n++) {
      const pr = zr[n], pi = -zi[n];              // z = conj(FFT(conj X)) (à 1/W près)
      const cr = Math.cos(w0 * n), ci = -Math.sin(w0 * n);
      const dr = pr * cr - pi * ci, di = pr * ci + pi * cr;
      let ph = Math.atan2(di, dr);
      if (last != null) {
        let d = ph - last;
        d -= 2 * Math.PI * Math.round(d / (2 * Math.PI));
        acc += d;
      }
      last = ph;
      // Pente par moindres carrés NON pondérés : ni par l'amplitude du son
      // (biais vers les instants forts), ni par la fenêtre de Hann (mesuré :
      // ±0,044 ¢ d'écart lisse sous un soufflet qui ondule, contre ±0,019 ¢
      // sans pondération — la pente non pondérée est plus proche de la
      // moyenne uniforme de la hauteur sur la fenêtre).
      const w = 1;
      sw += w; sn += w * n; sp += w * acc; snn += w * n * n; snp += w * n * acc;
    }
    const den = sw * snn - sn * sn;
    if (!(den > 0)) return;
    const slope = (sw * snp - sn * sp) / den;     // rad / échantillon décimé
    const off = c.off + (slope * srd) / (2 * Math.PI);
    if (!Number.isFinite(off) || Math.abs(off - c.off) > half) return;
    c.off = off;
    c.freq = ((fc + off) * calib) / div;
    c.cluster = true;
  });
}

// Écart minimal, en cases de la fenêtre courante (1 case = 1/T), entre la
// raie du 8' et celle, connue, du 16' sur un même partiel (cf. octaveFuse).
// À 2 cases, le lobe principal de Hann (±2 cases) fait deux pics distincts,
// et la fenêtre contient au moins deux périodes du battement des deux
// raies : la pente de phase de l'amas, coupé à mi-chemin de la raie du 16',
// converge vers la raie la plus forte, avec un biais borné par
// asin(B/A) / (π k T). Si c'est le 16' qui domine, la valeur retombe sur sa
// raie, à moins de 2 cases : elle est écartée. Mesuré sur synthèse (16'
// au timbre riche ou pauvre, 8' de −10 à −2 dB) : 4 cases laissaient
// confondu tout le long un 8' à 1,7 ¢ de l'octave, que 2 cases mesurent à
// 0,05 ¢ dès que la fenêtre atteint 2,7 s.
export const OCTAVE_SEP_BINS = 2;

// Tolérance (Hz) sous laquelle une raie est celle, revendiquée, d'une autre
// anche : 0,6 case de la fenêtre courante (au moins 0,08 Hz).
export function tolClaimHz(srd, W) { return Math.max(0.08, (0.6 * srd) / W); }

// Appariement voix ↔ composantes préservant l'ordre fréquentiel (alignement
// de séquences par programmation dynamique). Une voix peut rester non
// appariée (coût = tolHz) ; une composante revendiquée par une harmonique
// grave coûte presque autant que l'abandon, elle n'est donc retenue que si
// aucune composante libre ne convient.
export function assignOrdered(voices, comps, tolHz) {
  const nV = voices.length;
  const nC = comps.length;
  const skip = tolHz;
  const claimPenalty = tolHz * 0.9;
  const INF = 1e15;
  const cost = (i, j) => {
    const d = Math.abs(comps[j].freq - (voices[i].mt ?? voices[i].target));
    if (d >= tolHz) return INF;
    return d + (comps[j].claimed ? claimPenalty : 0);
  };
  const dp = [];
  const bt = [];
  for (let i = 0; i <= nV; i++) {
    dp.push(new Float64Array(nC + 1));
    bt.push(new Uint8Array(nC + 1));
  }
  for (let i = 1; i <= nV; i++) { dp[i][0] = i * skip; bt[i][0] = 2; }
  for (let i = 1; i <= nV; i++) {
    for (let j = 1; j <= nC; j++) {
      let best = dp[i][j - 1], which = 1;            // composante ignorée
      const s = dp[i - 1][j] + skip;                 // voix non appariée
      if (s < best) { best = s; which = 2; }
      const m = dp[i - 1][j - 1] + cost(i - 1, j - 1); // appariement
      if (m < best) { best = m; which = 3; }
      dp[i][j] = best; bt[i][j] = which;
    }
  }
  const out = new Array(nV).fill(null);
  let i = nV, j = nC;
  while (i > 0) {
    const w = j > 0 ? bt[i][j] : 2;
    if (w === 1) j--;
    else if (w === 2) i--;
    else { out[i - 1] = comps[j - 1]; i--; j--; }
  }
  return out;
}

// Méthodes d'Engine (cf. engine.js, Object.assign).
export const methodesAppariement = {
  // Associe les composantes mesurées aux voix attendues du groupe.
  // `claimed` : fréquences absolues (Hz) déjà expliquées comme harmoniques
  // de voix plus graves — elles ne sont utilisées qu'en dernier recours.
  matchVoices(group, az, calib, claimed = [], anchor = null, cont = null) {
    const expected = group.voices
      .map((v) => ({ ...v }))
      .sort((a, b) => a.target - b.target);
    const k = group.kTrack ?? 1;
    // Groupes de base : fréquences ramenées à la fondamentale (mesure sur le
    // partiel k). Groupes harmoniques : on reste dans le domaine du partiel,
    // sa fréquence réelle est la grandeur d'intérêt (inharmonicité).
    const div = group.isHarmonic ? 1 : k;
    // Ancrage harmonique : quand la fondamentale mesurée est connue, on
    // cherche le partiel autour de k·f0 (mt), pas autour du nominal — et dans
    // une fenêtre resserrée (±40 ¢) qui laisse passer l'inharmonicité réelle
    // mais interdit de sauter sur une raie parasite au voisinage du nominal.
    const useAnchor = anchor != null && group.isHarmonic && !group.isSub;
    for (const v of expected) v.mt = v.target;
    // Continuité par anche : chaque voix cherche d'abord là où SON anche était
    // à l'image précédente (mesure d'amas, donc sa hauteur moyenne), pas près
    // de la cible. Sinon, une raie latérale de soufflet qui tombe plus près
    // de la cible que l'anche elle-même lui était appariée. Garde-fou : la
    // mémoire n'est reprise que si elle reste dans la tolérance de la cible.
    if (!group.isHarmonic && this.prevF) {
      const tolMem = Math.max(2.5, group.center * 0.05);
      for (const v of expected) {
        const p = this.prevF.get(`${group.key}:${v.def.id}`);
        if (p != null && Math.abs(p - v.target) < tolMem) v.mt = p;
      }
    }
    if (useAnchor) {
      // Ancre par anche (Map id → fréquence du partiel) ou ancre unique.
      if (anchor instanceof Map) {
        for (const v of expected) if (anchor.has(v.def.id)) v.mt = anchor.get(v.def.id);
      } else {
        expected[0].mt = anchor;
      }
    }
    const anchorRef = anchor instanceof Map ? group.center * k : anchor;
    // Tolérance : ±85 cents en général ; ±40 cents pour un partiel ancré ;
    // ±20 cents pour les bandes sous-harmoniques (un doublement de période
    // est verrouillé sur la fondamentale — un pic éloigné est du bruit).
    const tolHz = group.isSub
      ? Math.max(1.5, group.fc * 0.012)
      : useAnchor
        ? Math.max(2.5, anchorRef * 0.023)
        : Math.max(2.5, (group.center * (group.isHarmonic ? k : 1)) * 0.05);
    let comps = az
      ? az.components.map((cp) => ({ ...cp, freq: (cp.freq * calib) / div }))
      : [];
    comps = comps.filter((cp) =>
      expected.some((v) => Math.abs(cp.freq - v.mt) < tolHz));
    // Plancher relatif : un pic à plus de 30 dB sous le plus fort du groupe
    // est une fuite spectrale ou du bruit, pas une anche — les anches d'un
    // même ton jouent à quelques dB les unes des autres. (Les bandes
    // sous-harmoniques, volontairement faibles, ne sont pas concernées.)
    if (!group.isSub && comps.length > 1) {
      let mMax = 0;
      for (const cp of comps) mMax = Math.max(mMax, cp.mag);
      // Auto-anches : le nombre d'anches n'est pas connu, chaque raie peut
      // devenir une « anche » — on n'y admet que des raies franches (−12 dB),
      // sinon les bandes latérales du soufflet prennent les emplacements.
      comps = comps.filter((cp) => cp.mag >= mMax / (this.cfg.mode === 'reeds' && !group.isHarmonic ? 4 : 31.6));
      // Auto-anches : les raies à moins de 0,4 Hz (ramenées à la fondamentale)
      // sont UNE anche et ses bandes latérales de soufflet (mesuré : ±0,15 Hz
      // autour de chaque anche d'un trémolo La♯3) ; deux anches d'un trémolo
      // sont toujours plus écartées. On ne garde que la plus forte.
      if (this.cfg.mode === 'reeds' && !group.isHarmonic) {
        const kept = [];
        for (const cp of [...comps].sort((a, b) => b.mag - a.mag)) {
          if (!kept.some((q) => Math.abs(q.freq - cp.freq) < 0.4)) kept.push(cp);
        }
        comps = kept.sort((a, b) => a.freq - b.freq);
      }
    }
    const tolClaim = az ? tolClaimHz(az.srd, az.W) : 0.08;
    for (const cp of comps) {
      // Un groupe harmonique mesure par définition une fréquence déjà
      // « revendiquée » par sa fondamentale : pas d'exclusion ici.
      const abs = cp.freq * (div === 1 ? 1 : k);
      // Exception : les partiels d'une anche à l'octave d'une plus grave (le
      // 8' d'un 16'+8', cf. plan.js octaveClash). Leur bande contient aussi
      // le partiel 2k du 16' ; on reçoit alors les seules raies revendiquées
      // par les AUTRES anches, et la raie du 16' y est reconnue comme telle.
      cp.claimed = group.isHarmonic && !group.octaveClash
        ? false
        // Au-delà de 1,5 kHz, les partiels élevés (×9, ×18…) d'une anche
        // grave s'écartent de m×f de quelques hertz (soufflet, raideur) : on
        // les reconnaît à 2,6 ¢ près. Mesuré (session d'Ewen, quinte
        // La♯2 + Fa4, Fa4 suivi sur son partiel 6) : le partiel 18 de La♯2,
        // 2,6 Hz à côté de m×f, n'était pas reconnu comme tel et le « 5 »
        // basculait toutes les demi-secondes de +7 ¢ à +14 ¢.
        : claimed.some((f) => Math.abs(abs - f) < Math.max(tolClaim, f >= 1500 ? f * 0.0015 : 0));
    }
    // Anche accordée à l'octave juste : sa fondamentale tombe DANS le partiel
    // pair de l'anche grave, déjà revendiqué. Une raie libre bien plus faible
    // à côté (bande latérale, bruit de soufflet, boucle d'un sample) n'est pas
    // une anche : mesuré sur un bandonéon La3+La4, le 8' s'y accrochait et
    // affichait −7,4 ¢ au lieu de l'octave juste. On écarte donc les raies
    // libres à plus de 12 dB sous la raie revendiquée ; la voix prend alors
    // la raie commune, marquée `merged` (« confondue avec l'octave »).
    let mClaimed = 0;
    for (const cp of comps) if (cp.claimed) mClaimed = Math.max(mClaimed, cp.mag);
    if (mClaimed > 0) comps = comps.filter((cp) => cp.claimed || cp.mag >= mClaimed / 4);
    // Auto-anches, octave ajoutée (16', 4', 2') : une raie revendiquée par
    // une autre anche ne prouve rien (cf. engine.js, l'anche n'est déclarée
    // que sur preuve) ; elle n'entre donc pas dans l'appariement. Avant, elle
    // prenait la case la plus proche de la note (le partiel 8 de La#2, 7 dB
    // plus fort que le 4', dans la case 4'), la vraie raie était poussée dans
    // une case voisine, et les deux s'effaçaient tour à tour.
    const octaveAjoutee = this.cfg.mode === 'reeds' && !group.isHarmonic && (group.voices[0].def.oct ?? 0) !== 0;
    if (octaveAjoutee) comps = comps.filter((cp) => !cp.claimed);

    // Verrou de continuité (voix unique, mode auto sur un ton battu) : on
    // n'accepte QUE la composante proche (±3 ¢) de la dernière mesure fine —
    // rester sur la même anche. Si aucune (creux de battement où l'anche suivie
    // s'efface, remplacée par des raies parasites), on ne suit pas cette trame
    // → le maintien reprend la dernière valeur. Sans ça, la fondamentale
    // sautait sur l'autre anche à chaque battement.
    if (cont != null && expected.length === 1) {
      const tolC = Math.max(0.03, cont * (Math.pow(2, 3 / 1200) - 1));
      let best = null, bestD = Infinity;
      for (const cp of comps) {
        const dd = Math.abs(cp.freq - cont);
        if (dd < tolC && dd < bestD) { bestD = dd; best = cp; }
      }
      if (best && az) clusterRefine([best], az, calib, div);
      this.fillVoice(expected[0], best, az?.W);
      expected[0].beatMeas = 0;
      return expected;
    }

    const chosen = assignOrdered(expected, comps, tolHz);
    const tNow = this.samplesTotal / this.sr;
    // Anche à l'octave juste d'une autre (registre 16'+8') : sa raie EST le
    // partiel pair de l'anche grave. Le coût de la raie « revendiquée » la
    // réservait aux anches à moins de ~9 ¢ de leur cible ; plus loin, la voix
    // restait vide (« — ») — ou, avant la décimation d'ordre 2, prenait une
    // raie fantôme. Une voix sans raie prend donc la raie commune la plus
    // proche, dans la tolérance, marquée « confondue avec l'octave ».
    if (!group.isHarmonic && !group.isSub) {
      for (let i = 0; i < expected.length; i++) {
        if (chosen[i]) continue;
        const ref = expected[i].mt ?? expected[i].target;
        let best = null;
        for (const cp of comps) {
          if (!cp.claimed || chosen.includes(cp) || Math.abs(cp.freq - ref) >= tolHz) continue;
          if (!best || Math.abs(cp.freq - ref) < Math.abs(best.freq - ref)) best = cp;
        }
        if (best) chosen[i] = best;
      }
    }
    // Une anche qui avait SA raie il y a moins d'une seconde et qui ne trouve
    // plus que la raie commune avec l'octave : cette raie est le mélange des
    // deux anches (la FFT ne les sépare plus à cette image), pas sa hauteur.
    // On ne l'affiche pas — la dernière mesure est tenue (cf. stabilize).
    // Mesuré (session d'Ewen, 16'+8' main gauche, Ré♯4) : le 8' basculait
    // d'une image à l'autre entre +1 ¢ (sa raie) et +9 à +18 ¢ (celle du 16').
    if (!group.isHarmonic && !group.isSub && this.ownT) {
      for (let i = 0; i < expected.length; i++) {
        const key = `${group.key}:${expected[i].def.id}`;
        if (chosen[i]?.claimed && tNow - (this.ownT.get(key) ?? -1e9) < 1) chosen[i] = null;
        else if (chosen[i] && !chosen[i].claimed) this.ownT.set(key, tNow);
      }
    }
    // L'amas s'arrête aux raies connues des autres anches (cf. clusterRefine)
    // là où elles tombent dans la bande : 8' d'un 16'+8', octave ajoutée
    // d'Auto-anches.
    if (az && !group.isSub) clusterRefine(chosen, az, calib, div, expected.map((v) => v.mt), group.octaveClash || octaveAjoutee ? claimed : null);
    for (let i = 0; i < expected.length; i++) {
      this.fillVoice(expected[i], chosen[i], az?.W);
      expected[i].merged = !!chosen[i]?.claimed;
      if (!group.isHarmonic && this.prevF) {
        const key = `${group.key}:${expected[i].def.id}`;
        if (chosen[i]?.cluster) this.prevF.set(key, expected[i].fMeas);
        else if (!chosen[i]) this.prevF.delete(key);
      }
    }

    // Battements mesurés par rapport à la voix de référence du groupe.
    const base = expected.find((v) => v.def.beatSign === 0) ?? expected[0];
    for (const v of expected) {
      v.beatMeas = (v.fMeas != null && base?.fMeas != null && v !== base)
        ? v.fMeas - base.fMeas
        : (v === base ? 0 : null);
    }
    return expected;
  },

  // Anche à l'octave d'une plus grave (le 8' d'un 16'+8', plan.js
  // octaveClash). Son partiel k tombe sur le partiel 2k du 16' : les deux
  // raies ne sont écartées que de k δ, δ = f8 − 2 f16 (0,16 Hz pour un 8' à
  // 1,7 ¢ de l'octave en Mi2). Sur la fondamentale seule, la fenêtre voyait
  // leur somme (session d'Ewen : 8' lu à 0,4 à 3 ¢ de sa hauteur). Or le
  // 16' est mesuré à part, sur un partiel impair : la position de sa raie
  // dans chaque bande du 8' est CONNUE (raies revendiquées). Les traqueurs
  // du stroboscope suivent déjà le 8' sur ses partiels 2 à 8.
  //  1) Partiels où la raie du 8' est à OCTAVE_SEP_BINS cases au moins de
  //     celle du 16' : fondus avec le poids (A k)², la variance d'une mesure
  //     sur le partiel k (cf. la fusion du mode Automatique).
  //  2) Aucun : la fenêtre est trop courte pour séparer les deux anches (une
  //     basse de 3 s à 1,7 ¢ de l'octave). Sur chaque partiel, la pente de
  //     phase penche alors vers la raie la plus forte des deux, avec un biais
  //     d'environ δ ρ / (1 ± ρ), ρ = A16 / A8 sur ce partiel : il ne
  //     décroît PAS avec k. On fond donc la base et les partiels dont la
  //     raie se distingue de celle du 16' (tolérance des raies revendiquées,
  //     tolClaimHz), avec le poids A² : plus la raie du 8' est forte, plus il
  //     y domine. La valeur est marquée « confondue avec l'octave ».
  // Le timbre décide tout seul : sur une basse réelle (ESPRIT, passages P03,
  // P04, P09), le partiel 2k du 16' est tantôt 28 dB sous le partiel k du
  // 8', tantôt 8 dB au-dessus, d'un partiel au suivant.
  octaveFuse(groups, claimed, claimedBy) {
    // Une raie qui sert à mesurer une anche doit pouvoir être cette anche : à
    // plus de 30 dB sous la voix la plus forte de la note, c'est le reste
    // d'une autre (même règle que les voix du registre, engine.js).
    let aMax = 0;
    for (const g of groups) if (!g.isHarmonic && !g.isSub) for (const v of g.voices) if (v.tracked) aMax = Math.max(aMax, v.amp);
    const floor = aMax * Math.pow(10, -30 / 20);
    for (const g of groups) {
      if (!g.octaveClash || g.isHarmonic || g.isSub || g.voices.length !== 1) continue;
      const v = g.voices[0];
      if (!v.tracked) continue;
      const others = claimed.filter((_, i) => claimedBy[i] !== g.center);
      const k0 = g.kTrack || 1;
      const cands = [{ k: k0, f: v.fMeas * k0, amp: v.amp, W: g.W, srd: g.srd, merged: v.merged, base: true }];
      for (const p of groups) {
        const pv = p.voices[0];
        if (p.isPartial && p.baseKey === g.key && pv?.tracked) {
          cands.push({ k: p.kTrack, f: pv.fMeas, amp: pv.amp, W: p.W, srd: p.srd, merged: pv.merged });
        }
      }
      // Écart (Hz) de la raie à la plus proche raie connue du 16'.
      const gap = (cd) => others.reduce((m, f) => Math.min(m, Math.abs(f - cd.f)), Infinity);
      const fuse = (ok, weight) => {
        let num = 0, den = 0;
        const use = [];
        const ks = [];   // partiels fondus (diagnostic : partielsMesure)
        for (const cd of cands) {
          if (!(cd.W > 0) || cd.amp < floor || !ok(cd)) continue;
          const w = weight(cd);
          num += w * (cd.f / cd.k);
          den += w;
          use.push([cd.f / cd.k, w]);
          ks.push(cd.k);
        }
        if (!(den > 0)) return null;
        const f = num / den;
        let sd = 0;
        for (const [x, w] of use) sd += w * centsBetween(x, f) ** 2;
        return { f, sd: Math.sqrt(sd / den), n: use.length, parts: use.map(([x, w], i) => ({ k: ks[i], f: x, poids: w })) };
      };
      // Une raie à OCTAVE_SEP_BINS cases de celle du 16' n'est pas le 16' ;
      // rien ne dit encore qu'elle est le 8'. Mesuré (synthèse, et P09) : une
      // raie parasite (repli de la décimation, −30 dB) ou une lecture de la
      // raie commune poussée au-delà du seuil par le battement (sur un seul
      // partiel, quand la vraie raie n'en est qu'à une case) passait pour le
      // 8' séparé : 8 à 26 ¢ d'erreur, parfois toute la note. Une anche est
      // périodique : une raie séparée n'est retenue que si un AUTRE partiel du
      // 8', distinct de la raie du 16' (un témoin), dit la même hauteur à
      // leurs biais près (Hz, à la fondamentale) : 1/(2 k T) pour une raie
      // séparée (pente de phase à 2 cases d'une raie plus forte, au pire
      // asin(1)/(π k T)), une case 1/(k T) pour un témoin pas encore séparé.
      // Sinon l'anche reste confondue, avec son estimation (confondu.js).
      const sep = (cd) => !cd.merged && gap(cd) >= (OCTAVE_SEP_BINS * cd.srd) / cd.W;
      const temoin = (cd) => cd.W > 0 && cd.amp >= floor && !cd.merged && gap(cd) >= tolClaimHz(cd.srd, cd.W);
      const biais = (cd) => ((sep(cd) ? 0.5 : 1) * cd.srd) / (cd.W * cd.k);
      const confirme = (cd) => cands.some((w) => w !== cd && temoin(w) && Math.abs(w.f / w.k - cd.f / cd.k) <= biais(cd) + biais(w));
      let r = fuse((cd) => sep(cd) && confirme(cd), (cd) => (cd.amp * cd.k) ** 2);
      v.merged = r == null;
      // Diagnostic (section recherche de L'anche, cartes « séparation » et
      // « partiels de mesure ») : chaque lecture, son écart en cases à la raie
      // du 16', et qui la confirme. Rien ici ne change la mesure.
      v.detailSeparation = {
        separee: r != null,
        lectures: cands.map((cd) => ({
          k: cd.k, f: cd.f / cd.k, amp: cd.amp, base: !!cd.base,
          cases: cd.W > 0 && Number.isFinite(gap(cd)) ? (gap(cd) * cd.W) / cd.srd : null,
          separee: cd.W > 0 && sep(cd), temoin: temoin(cd),
          temoins: cd.W > 0 && sep(cd)
            ? cands.filter((w) => w !== cd && temoin(w) && Math.abs(w.f / w.k - cd.f / cd.k) <= biais(cd) + biais(w)).map((w) => w.k)
            : [],
          sousPlancher: cd.amp < floor,
        })),
      };
      let role = 'separee';
      if (r == null) {
        role = 'confondue';
        r = fuse((cd) => cd.base || (!cd.merged && gap(cd) >= tolClaimHz(cd.srd, cd.W)), (cd) => cd.amp ** 2);
        // La raie commune (l'octave mesurée du 16'), au plus près de la base.
        const fb = v.fMeas * k0;
        const common = others.reduce((b, x) => (b == null || Math.abs(x - fb) < Math.abs(b - fb) ? x : b), null);
        // Une anche est périodique : ses partiels disent la même hauteur. Une
        // lecture seule ne se contrôle pas ; et si plusieurs se dispersent
        // plus qu'elles ne s'écartent de la raie commune, elles ne
        // distinguent pas le 8' de l'octave du 16'. Dans les deux cas on
        // montre la raie commune (erreur bornée par l'écart réel à l'octave).
        if (common != null && (!r || r.n < 2 || Math.abs(centsBetween(r.f, common / k0)) <= r.sd)) {
          r = { f: common / k0 };
          role = 'commune';
        }
      }
      v.partielsMesure = r?.parts ? r.parts.map((p) => ({ ...p, role })) : r ? [{ k: k0, f: r.f, poids: 1, role }] : null;
      // Lectures brutes de chaque partiel, de cette image (cf. confondu.js,
      // estimeRaie).
      v.lecturesOctave = { n: this.samplesTotal, liste: cands.filter((cd) => cd.amp >= floor).map(({ k, f, amp, W, srd }) => ({ k, f, amp, W, srd })) };
      if (r == null) continue;
      const f = r.f;
      v.fMeas = f;
      v.dCents = centsBetween(f, v.nominal);
      v.dHz = f - v.nominal;
      v.dTargetCents = centsBetween(f, v.target);
    }
  },

  // Auto-anches, une seule anche dans le groupe : rien à séparer. Le partiel
  // de mesure du groupe a été choisi pour SÉPARER des anches supposées
  // (unisonHarmonic : le plus haut qui les écarte), sans regarder sa force ;
  // une raie faible voisine le fait dévier (session d'Ewen, Ré#4 seul :
  // partiel 3 à −17 dB lu −0,09 ¢, les autres +0,13 à +0,19 ¢ ; Auto-anches
  // affichait −0,25 ¢). Une anche seule est périodique : on la lit comme en
  // Automatique, en fondant son partiel de mesure et ceux du stroboscope,
  // poids (A k)² (variance d'une mesure sur le partiel k), avec la même porte
  // progressive autour de leur médiane (pleine à 0,5 ¢, nulle à 1,5 ¢). Un
  // partiel qui tombe sur la raie d'une autre anche (à moins de
  // OCTAVE_SEP_BINS cases) n'en est pas.
  fuseSingleReed(g, groups, claimed, claimedBy) {
    const on = g.voices.filter((v) => v.tracked);
    if (on.length !== 1 || on[0].held || on[0].merged) return;
    const v = on[0];
    const others = claimed.filter((_, i) => claimedBy[i] !== g.center);
    const libre = (fBand, srd, W) => !others.some((f) => Math.abs(f - fBand) < (OCTAVE_SEP_BINS * srd) / Math.max(1, W));
    const k0 = g.kTrack || 1;
    const cands = [];
    if (libre(v.fMeas * k0, g.srd, g.W)) cands.push({ x: v.fMeas, w: (v.amp * k0) ** 2, k: k0 });
    for (const p of groups) {
      if (!p.isPartial || p.baseKey !== g.key) continue;
      let best = null;
      for (const pv of p.voices) {
        if (!pv.tracked || pv.merged || !libre(pv.fMeas, p.srd, p.W)) continue;
        const x = pv.fMeas / p.kTrack;
        if (!best || Math.abs(x - v.fMeas) < Math.abs(best.x - v.fMeas)) best = { x, w: (pv.amp * p.kTrack) ** 2, k: p.kTrack };
      }
      if (best) cands.push(best);
    }
    if (cands.length < 2) return;
    // Médiane pondérée : la référence de la porte.
    const tri = [...cands].sort((a, b) => a.x - b.x);
    let tot = 0;
    for (const c of tri) tot += c.w;
    let acc = 0, ref = tri[tri.length - 1].x;
    for (const c of tri) { acc += c.w; if (acc >= tot / 2) { ref = c.x; break; } }
    let num = 0, den = 0, n = 0;
    const parts = [];   // diagnostic : partielsMesure
    for (const c of cands) {
      const dev = Math.abs(centsBetween(c.x, ref));
      if (dev >= 1.5) { parts.push({ k: c.k, f: c.x, poids: 0, role: 'ecarte' }); continue; }
      const w = (dev <= 0.5 ? 1 : 1.5 - dev) * c.w;
      num += w * c.x; den += w; n++;
      parts.push({ k: c.k, f: c.x, poids: w, role: 'fondu' });
    }
    if (!(den > 0) || n < 2) return;
    v.partielsMesure = parts;
    v.fMeas = num / den;
    v.dCents = centsBetween(v.fMeas, v.nominal);
    v.dHz = v.fMeas - v.nominal;
    v.dTargetCents = centsBetween(v.fMeas, v.target);
    v.fusedN = n;
  },

  fillVoice(v, comp, w) {
    if (comp) {
      v.fMeas = comp.freq;
      // Amplitude ramenée à l'échelle du signal (pic Hann complexe ≈ A·W/2).
      v.amp = comp.mag / ((w || 2) / 2);
      v.dCents = centsBetween(comp.freq, v.nominal);
      v.dHz = comp.freq - v.nominal;
      v.dTargetCents = centsBetween(comp.freq, v.target);
      v.tracked = true;
    } else {
      v.fMeas = null; v.amp = 0; v.dCents = null; v.dHz = null;
      v.dTargetCents = null; v.tracked = false;
    }
  },
};
