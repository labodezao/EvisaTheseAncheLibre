// Rejoue un passage d'un WAV dans le moteur et écrit chaque image en JSON
// (une ligne par image) : note, et pour chaque anche affichée son octave,
// sa hauteur, ses drapeaux, la fenêtre du traqueur, et pour une anche
// confondue avec l'octave son estimation (fe, ce, mg, me, sg). Sert à comparer le moteur
// à une vérité terrain calculée hors moteur (verite_poly.py) SUR LA MÊME
// FENÊTRE de son.
//
//   node test/outils/images.mjs son.wav '<réglages JSON>' t0 t1 [bruit_dB] [graine]
//
// bruit_dB : ajoute un bruit blanc gaussien à ce rapport signal sur bruit,
// calculé sur le passage (t0, t1). Lecture seule du WAV.
import { lireWav } from './wav.mjs';
const { Engine } = await import(process.env.ENG ?? new URL('../../web/js/dsp/engine.js', import.meta.url).href);
const [wav, cfgTxt = '{"mode":"auto"}', t0s = '0', t1s = '1e9', snrS = '', graineS = '1'] = process.argv.slice(2);
const { x: brut, sr } = lireWav(wav);
const t0 = Math.max(0, +t0s), t1 = Math.min(brut.length / sr, +t1s);
const x = brut.slice(Math.floor(t0 * sr), Math.floor(t1 * sr));
if (snrS !== '') {
  let p = 0;
  for (const v of x) p += v * v;
  p /= x.length;
  const s = Math.sqrt(p / 10 ** (+snrS / 10));
  let g = +graineS || 1;
  const rnd = () => { g = (g * 16807) % 2147483647; return g / 2147483647; };
  for (let i = 0; i < x.length; i += 2) {
    const r = Math.sqrt(-2 * Math.log(rnd() + 1e-300)), th = 2 * Math.PI * rnd();
    x[i] += s * r * Math.cos(th);
    if (i + 1 < x.length) x[i + 1] += s * r * Math.sin(th);
  }
}
const e = new Engine(sr, JSON.parse(cfgTxt));
const out = [];
for (let i = 0; i + 512 <= x.length; i += 512) {
  const r = e.process(x.subarray(i, i + 512));
  if (!r) continue;
  const T = t0 + (i + 512) / sr;
  const vs = [];
  for (const g of r.groups) {
    if (g.isHarmonic || g.isSub) continue;
    for (const v of g.voices) {
      vs.push({
        id: v.def.id, lab: v.def.label ?? v.def.id, midi: v.midi, nom: +v.nominal.toFixed(5),
        f: v.tracked ? +v.fMeas.toFixed(6) : null, c: v.tracked ? +v.dCents.toFixed(4) : null,
        M: !!v.merged, h: !!v.held, r: !!v.coarse, mp: !!v.mp, st: !!v.step, ab: !!v.absent,
        k: g.kTrack, W: g.W, srd: +g.srd.toFixed(5),
        // Anche confondue avec l'octave (confondu.js) : estimation et marge.
        ...(v.confondu ? { cf: 1, fe: v.fEstimee != null ? +v.fEstimee.toFixed(6) : null,
          ce: v.centsEstimes != null ? +v.centsEstimes.toFixed(4) : null,
          mg: v.margeCents != null ? +v.margeCents.toFixed(4) : null, me: v.methode, sg: v.signeConnu ? 1 : 0 } : {}),
      });
    }
  }
  const sub = r.groups.find((g) => g.subspace)?.subspace?.map((c) => +c.cents.toFixed(3)) ?? null;
  out.push(JSON.stringify({
    t: +T.toFixed(4), q: r.quiet ? 1 : 0, m: r.playedMidi, lv: +(20 * Math.log10(r.level + 1e-12)).toFixed(1),
    v: vs, u: r.unison?.reeds?.map((c) => +c.toFixed(3)) ?? (r.unison ? [r.unison.cents] : null), sub,
    pd: r.partialsDisagree ? +r.partialsDisagree.cents.toFixed(2) : null,
  }));
}
console.log(out.join('\n'));
