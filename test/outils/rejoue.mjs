// Rejoue un enregistrement (WAV d'un ZIP de session) dans le moteur, hors
// navigateur, et résume ce qu'affiche la courbe : par note et par anche,
// médiane, étendue, sauts > 1 ¢, trous, valeurs > 40 ¢.
//
//   node test/outils/rejoue.mjs session.wav '{"mode":"register","register":"LM"}' [t0 t1] [--images]
//
// Modes utiles : {"mode":"auto"}, {"mode":"reeds","reedOctaves":[0]},
// {"mode":"register","register":"LM"|"MM"}, {"mode":"chord","chordType":"quinte","chordDegrees":[0,7]}.
// --images : une ligne par image (hauteur, drapeaux M = confondue avec
// l'octave, h = maintenue, r = estimation rapide).
// ENG=chemin/vers/engine.js pour comparer une autre version du moteur.
import { lireWav } from './wav.mjs';
const { Engine } = await import(process.env.ENG ?? new URL('../../web/js/dsp/engine.js', import.meta.url).href);
const { noteLabel } = await import(new URL('../../web/js/music.js', import.meta.url).href);
const args = process.argv.slice(2).filter((a) => a !== '--images');
const images = process.argv.includes('--images');
const [wav, cfgTxt = '{"mode":"auto"}', t0s = '0', t1s = '1e9'] = args;
const { x, sr } = lireWav(wav);
const t0 = +t0s, t1 = +t1s;
const e = new Engine(sr, JSON.parse(cfgTxt));
const segs = [];
let cur = null, grosses = 0, total = 0;
for (let i = 0; i + 512 <= x.length; i += 512) {
  const T = (i + 512) / sr;
  if (T > t1) break;
  const r = e.process(x.subarray(i, i + 512));
  if (!r || T < t0) continue;
  const vs = r.groups.filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices);
  if (images) {
    console.log(T.toFixed(2), r.playedMidi != null ? noteLabel(r.playedMidi).full : '—', r.quiet ? 'silence' : '',
      vs.map((v) => `${v.def.label ?? v.def.id}=${v.tracked ? v.dCents.toFixed(2) + (v.merged ? 'M' : '') + (v.held ? 'h' : '') + (v.coarse ? 'r' : '') : '—'}`).join('  '));
  }
  if (r.quiet || r.playedMidi == null) { cur = null; continue; }
  if (!cur || cur.midi !== r.playedMidi) { cur = { t: T, midi: r.playedMidi, v: {} }; segs.push(cur); }
  for (const v of vs) {
    const k = v.def.label ?? v.def.id;
    (cur.v[k] ??= []).push(v.tracked ? v.dCents : null);
    if (v.tracked) { total++; if (Math.abs(v.dCents) > 40) grosses++; }
  }
}
for (const s of segs) {
  const n = Object.values(s.v)[0]?.length ?? 0;
  if (n < 12) continue;
  const parts = Object.entries(s.v).map(([k, a]) => {
    const vals = a.filter((c) => c != null);
    if (!vals.length) return `${k}: —`;
    const q = [...vals].sort((p, r) => p - r);
    let j = 0;
    for (let i = 1; i < a.length; i++) if (a[i] != null && a[i - 1] != null && Math.abs(a[i] - a[i - 1]) > 1) j++;
    return `${k}: méd ${q[q.length >> 1].toFixed(1)} [${q[Math.floor(q.length * 0.1)].toFixed(1)}, ${q[Math.floor(q.length * 0.9)].toFixed(1)}] sauts ${j}, trous ${a.length - vals.length}/${a.length}`;
  });
  console.log(`${s.t.toFixed(1).padStart(7)} s  ${noteLabel(s.midi).full.padEnd(5)} ${parts.join(' | ')}`);
}
console.log(`valeurs au-delà de 40 ¢ : ${grosses} / ${total}`);
