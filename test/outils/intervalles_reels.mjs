// Battements d'intervalles du moteur sur un passage réel (audit du 10/10/2026, docs/POLYPHONIE-ESSAIS.md
// § 4.4) : pour chaque intervalle de la note (tick.intervalles), le battement mesuré m f_b − n f_h, le
// voulu (cibles : tempérament, La, décalages) et l'enveloppe du partiel commun, médianes des 0,6 s finales.
//
//   node test/outils/intervalles_reels.mjs son.wav '{"mode":"register","register":"Q"}' t0 t1 [t0 t1 ...]
//
// Le moteur démarre 1,5 s avant t0 (le temps de reconnaître l'accord). ENG=chemin/vers/engine.js pour une
// autre version du moteur.
import { lireWav } from './wav.mjs';
const { Engine } = await import(process.env.ENG ?? new URL('../../web/js/dsp/engine.js', import.meta.url).href);
const [wav, cfgTxt = '{"mode":"register","register":"Q"}', ...bornes] = process.argv.slice(2);
const { x, sr } = lireWav(wav);
const med = (a) => { const s = [...a].sort((p, q) => p - q); return s.length ? s[s.length >> 1] : null; };
const f = (v, d = 3) => (v == null ? '—' : v.toFixed(d));
for (let b = 0; b + 1 < bornes.length; b += 2) {
  const t0 = +bornes[b], t1 = +bornes[b + 1];
  const e = new Engine(sr, JSON.parse(cfgTxt));
  const parNom = new Map();
  for (let i = Math.floor(Math.max(0, t0 - 1.5) * sr); i + 512 <= Math.floor(t1 * sr); i += 512) {
    const r = e.process(x.subarray(i, i + 512));
    const T = (i + 512) / sr;
    if (!r || T < t1 - 0.6) continue;
    for (const q of r.intervalles ?? []) {
      const k = `${q.nom} ${q.bas}-${q.haut}`;
      if (!parNom.has(k)) parNom.set(k, { q, mes: [], env: [] });
      const s = parNom.get(k);
      if (q.mesure != null) s.mes.push(q.mesure);
      if (q.enveloppe?.sure) s.env.push(q.enveloppe.hz);
      s.q = q;
    }
  }
  console.log(`${t0.toFixed(2)} à ${t1.toFixed(2)} s`);
  if (!parNom.size) console.log('  aucun intervalle');
  for (const [k, s] of parNom) {
    console.log(`  ${k.padEnd(22)} f ${f(s.q.fBas, 4)} / ${f(s.q.fHaut, 4)} Hz · mesuré ${f(med(s.mes))} Hz · voulu ${f(s.q.voulu)} Hz · enveloppe ${f(med(s.env))} Hz`);
  }
}
