// Banc synthétique (aucun enregistrement) : deux anches d'un même ton, avec
// les écarts relevés sur une banque de notes musette (Fa3 +2,1/+21,7 ¢ …) et
// un soufflet qui ondule (±0,4 ¢ à 0,9 Hz). Pour chaque mode : à partir de
// quand les deux anches sont justes (à 1 ¢), et combien du temps ensuite.
//
//   node test/outils/banc_musette.mjs
//   ENG=autre/engine.js node test/outils/banc_musette.mjs   (comparer deux versions)
const { Engine } = await import(process.env.ENG ?? new URL('../../web/js/dsp/engine.js', import.meta.url).href);
const { midiToFreq } = await import(new URL('../../web/js/music.js', import.meta.url).href);
const SR = 48000;
const at = (m, ct) => midiToFreq(m) * 2 ** (ct / 1200);
function musette(reeds, seconds, mod = 0.4) {
  const n = SR * seconds, x = new Float32Array(n);
  for (const { f, a = 1 } of reeds) {
    const H = [1, 0.8, 0.5, 0.4, 0.25, 0.15];
    let ph = Math.random() * 6;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      ph += (2 * Math.PI * f * 2 ** ((mod * Math.sin(2 * Math.PI * 0.9 * t)) / 1200)) / SR;
      for (let h = 0; h < H.length; h++) x[i] += Math.min(1, t / 0.05) * 0.08 * a * H[h] * Math.sin((h + 1) * ph + h);
    }
  }
  for (let i = 0; i < n; i++) x[i] += 3e-4 * (Math.random() * 2 - 1);
  return x;
}
const cas = [[53, 2.1, 21.7], [60, -3.6, 20.7], [62, -3.8, 17.2], [68, -1.5, 16.6], [83, 1.0, 11.9], [69, -2, 2]];
const modes = [{ mode: 'reeds', reedOctaves: [0] }, { mode: 'register', register: 'MM' }, { mode: 'auto' }];
for (const [m, c1, c2] of cas) {
  const x = musette([{ f: at(m, c1) }, { f: at(m, c2), a: 0.85 }], 4);
  for (const cfg of modes) {
    const e = new Engine(SR, cfg);
    let premier = null, bons = 0, tot = 0, alerte = null;
    for (let i = 0; i + 512 <= x.length; i += 512) {
      const r = e.process(x.subarray(i, i + 512));
      if (!r) continue;
      const T = (i + 512) / SR;
      if (r.unison?.reeds && !alerte) alerte = `${T.toFixed(2)} s (${r.unison.reeds.map((c) => c.toFixed(1)).join(' / ')} ¢)`;
      const cs = r.groups.filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices)
        .filter((v) => v.tracked).map((v) => v.dCents).sort((a, b) => a - b);
      const ok = cs.length === 2 && Math.abs(cs[0] - c1) < 1 && Math.abs(cs[1] - c2) < 1;
      if (T > 1) { tot++; if (ok) bons++; }
      if (ok && premier == null) premier = T;
    }
    const nom = cfg.mode + (cfg.register ?? '');
    console.log(`midi ${m} (${c1} / ${c2} ¢) ${nom.padEnd(10)} deux anches justes dès ${premier?.toFixed(2) ?? '—'} s, ${(100 * bons / tot).toFixed(0)} % après 1 s${alerte ? `, alerte trémolo ${alerte}` : ''}`);
  }
}
