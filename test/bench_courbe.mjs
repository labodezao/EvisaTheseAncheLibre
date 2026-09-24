// La courbe de justesse est-elle propre ? On compare, image par image, ce
// que l'accordeur affiche à ce que l'anche fait vraiment (hauteur connue du
// signal de synthèse, soufflet compris) :
//   - « bruit »  : écart RMS affiché − vrai, après la convergence (¢) ;
//   - « dents »  : plus grand saut image à image NON expliqué par le vrai
//                  mouvement de l'anche (¢) — une dent de scie, un décrochage.
// Le « bruit » contient aussi un écart lisse et inoffensif : la mesure est
// une moyenne pondérée sur ~2,7 s, la référence une moyenne uniforme — sous
// un soufflet qui ondule, les deux diffèrent de quelques centièmes, sans à-coup.
//   node test/bench_courbe.mjs
import { Engine } from '../web/js/dsp/engine.js';

const SR = 48000;
let seed = 99;
const rnd = () => { seed = (1103515245 * seed + 12345) & 0x7fffffff; return seed / 0x40000000 - 1; };
// Spectre mesuré sur le Mi4 Gaillard (dB) : fondamentale, H2 très faible, puis riche.
const SPECTRE_DB = [-1, -19, 0, -1.4, 0, -0.8, -2.5, -6, -9.5, -13.5, -7.8, -5.4, -15, -9.8];
const SPECTRE = SPECTRE_DB.map((d) => 10 ** (d / 20));

// Soufflet : la pression ondule (fréquence fw, ±wobC cents) et l'amplitude
// suit (±amDb). Chaque anche a sa propre sensibilité (la plus aiguë bouge un
// peu plus), comme de vraies anches.
function scene(reeds, seconds, { wobC = 0.3, fw = 0.7, amDb = 3, noise = 3e-4 } = {}) {
  const n = Math.floor(SR * seconds);
  const out = new Float32Array(n);
  const truth = reeds.map(() => new Float64Array(n));
  reeds.forEach(({ f, a = 1, sens = 1 }, r) => {
    const ph = SPECTRE.map(() => (rnd() + 1) * Math.PI);
    let phase = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const s = Math.sin(2 * Math.PI * fw * t);
      const fi = f * 2 ** ((wobC * sens * s) / 1200);
      truth[r][i] = fi;
      phase += (2 * Math.PI * fi) / SR;
      const env = Math.min(1, t / 0.3) * 10 ** ((amDb * s) / 20);
      let y = 0;
      for (let h = 0; h < SPECTRE.length; h++) {
        if (f * (h + 1) > SR * 0.45) break;
        y += SPECTRE[h] * Math.sin((h + 1) * phase + ph[h]);
      }
      out[i] += 0.05 * a * env * y;
    }
  });
  for (let i = 0; i < n; i++) out[i] += noise * rnd();
  return { out, truth };
}

const cents = (f, r) => 1200 * Math.log2(f / r);

function banc(nom, cfg, reeds, opt) {
  const seconds = 12;
  const { out, truth } = scene(reeds, seconds, opt);
  const e = new Engine(SR, cfg);
  const series = reeds.map(() => []);
  for (let i = 0; i + 512 <= out.length; i += 512) {
    const r = e.process(out.subarray(i, i + 512));
    if (!r) continue;
    const t = (i + 512) / SR;
    if (t < 3.5) continue;                                   // après convergence
    const g = r.groups.find((gg) => !gg.isHarmonic && !gg.isSub);
    if (!g) continue;
    // Chaque anche vraie ↔ la voix affichée la plus proche de sa hauteur.
    reeds.forEach((_, k) => {
      const vrai = truth[k][i + 511];
      let best = null;
      for (const v of g.voices) if (v.tracked && (!best || Math.abs(v.fMeas - vrai) < Math.abs(best.fMeas - vrai))) best = v;
      // Référence : la hauteur vraie MOYENNÉE sur la fenêtre d'analyse (la
      // mesure est une moyenne glissante : on ne lui reproche pas son retard).
      const w = Math.min(i + 512, Math.round((g.W / g.srd) * SR));
      let s = 0;
      for (let j = i + 512 - w; j < i + 512; j += 64) s += truth[k][j];
      const moy = s / Math.ceil(w / 64);
      series[k].push(best ? cents(best.fMeas, moy) : NaN);
    });
  }
  const cells = series.map((s) => {
    const ok = s.filter(Number.isFinite);
    const rms = Math.sqrt(ok.reduce((a, x) => a + x * x, 0) / Math.max(1, ok.length));
    let dent = 0;
    for (let i = 1; i < s.length; i++) if (Number.isFinite(s[i]) && Number.isFinite(s[i - 1])) dent = Math.max(dent, Math.abs(s[i] - s[i - 1]));
    const trous = s.length - ok.length;
    return `bruit ${rms.toFixed(3)}¢ dents ${dent.toFixed(3)}¢${trous ? ` ${trous} trous` : ''}`.padEnd(34);
  });
  console.log(`${nom.padEnd(38)} ${cells.join(' ')}`);
  if (process.env.SERIE && nom.includes(process.env.SERIE)) {
    for (let i = 0; i < series[0].length; i += 2) console.log('   ', series.map((s) => s[i]?.toFixed(3)).join('  '));
  }
  return series;
}

const la = 440, mi = 329.63, re = 146.83;
for (const [lbl, opt] of [['soufflet calme ±0,3¢', { wobC: 0.3, fw: 0.7, amDb: 3 }],
  ['soufflet vivant ±1¢, 1,5 Hz', { wobC: 1, fw: 1.5, amDb: 6 }]]) {
  console.log(`\n=== ${lbl} ===`);
  banc('M  auto, La4', { mode: 'auto' }, [{ f: la }], opt);
  banc('M  auto, Ré3', { mode: 'auto' }, [{ f: re }], opt);
  banc('MM registre, Mi4 +1,5 Hz', { mode: 'register', register: 'MM' }, [{ f: mi }, { f: mi + 1.5, a: 0.9, sens: 1.3 }], opt);
  banc('MM registre, Ré3 +0,8 Hz', { mode: 'register', register: 'MM' }, [{ f: re }, { f: re + 0.8, a: 0.9, sens: 1.3 }], opt);
  banc('MMM registre, La4 ±1,6 Hz', { mode: 'register', register: 'MMM' },
    [{ f: la - 1.6, sens: 0.8 }, { f: la }, { f: la + 1.6, a: 0.9, sens: 1.3 }], opt);
}
