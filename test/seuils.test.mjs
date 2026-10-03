// Tests des seuils d'auto-entretien et du débit de fuite (web/js/seuils.js).
// Exécution : node test/seuils.test.mjs
import {
  rampThresholds, splitCycles, analyseRun, debounce, powerLaw,
  equivalentHoleMm, leakFlow,
} from '../web/js/seuils.js';

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}
const near = (a, b, tol) => Math.abs(a - b) <= tol;

// Une rampe 0 → pMax → 0 lue à 20 Hz (cadence de la télémétrie), et une
// « anche » à hystérésis : démarre à pOn, se plaque à pChoke, repart à
// pUnchoke en descente, s'éteint à pOff. Niveau et clarté comme l'accordeur
// les donne : souffle = clarté basse, note = clarté haute.
function synth({ pOn = 150, pOff = 110, pChoke = 700, pUnchoke = 620, pMax = 800, rate = 20, hz = 20, t0 = 0, glitch = false } = {}) {
  const T = 2 * pMax / rate, rows = [];
  let on = false, choked = false;
  for (let i = 0; i <= T * hz; i++) {
    const t = i / hz, rising = t < T / 2;
    const p = rising ? rate * t : pMax - rate * (t - T / 2);
    if (rising) {
      if (!on && !choked && p >= pOn && p < pChoke) on = true;
      if (on && p >= pChoke) { on = false; choked = true; }
    } else {
      if (choked && p <= pUnchoke) { choked = false; on = true; }
      if (on && p <= pOff) on = false;
    }
    let sounding = on;
    if (glitch && i === Math.round(((pOn + pChoke) / 2) / rate * hz)) sounding = false; // un raté d'une trame
    rows.push({
      t: t0 + t, p, q: 0.9 * Math.sqrt(Math.max(p, 1)),
      level: sounding ? -20 : -50 + 10 * p / pMax,      // le souffle monte avec p
      clarity: sounding ? 0.97 : 0.3,
    });
  }
  return rows;
}

console.log('Seuils d\'auto-entretien');
{
  const rows = synth();
  const a = analyseRun(rows);
  const c = a.cycles[0];
  assert(a.cycles.length === 1, `un cycle trouvé (${a.cycles.length})`);
  assert(near(c.p_on, 150, 5), `démarrage ≈ 150 Pa (${c.p_on.toFixed(1)})`);
  assert(near(c.p_choke, 700, 5), `plaquage ≈ 700 Pa (${c.p_choke.toFixed(1)})`);
  assert(near(c.p_unchoke, 620, 5), `reprise ≈ 620 Pa (${c.p_unchoke.toFixed(1)})`);
  assert(near(c.p_off, 110, 5), `extinction ≈ 110 Pa (${c.p_off.toFixed(1)})`);
  assert(c.hysteresis > 0 && c.choke_reached, 'hystérésis positive, plaquage atteint');
  assert(near(c.usable_range, 550, 10), `plage utile ≈ 550 Pa (${c.usable_range.toFixed(0)})`);
  assert(near(a.flow.n, 0.5, 0.02), `débit en p^0,5 (n = ${a.flow.n.toFixed(3)})`);
}
{
  // Le souffle seul (clarté basse) ne doit jamais compter comme une note,
  // même s'il devient fort.
  const rows = synth().map((r) => ({ ...r, level: -10, clarity: 0.4 }));
  const a = analyseRun(rows);
  assert(!a.osc.some(Boolean), 'souffle fort mais apériodique : jamais « sonne »');
}
{
  // Un raté d'une seule trame en plein jeu n'est pas un plaquage.
  const a = analyseRun(synth({ glitch: true }));
  assert(near(a.cycles[0].p_choke, 700, 5), `raté isolé ignoré (plaquage lu à ${a.cycles[0].p_choke.toFixed(0)} Pa)`);
}
{
  // Trois cycles répétés : moyenne et écart-type.
  const r1 = synth(), r2 = synth({ pOn: 160, t0: 81 }), r3 = synth({ pOn: 140, t0: 162 });
  const a = analyseRun([...r1, ...r2, ...r3]);
  assert(a.cycles.length === 3, `trois cycles (${a.cycles.length})`);
  assert(near(a.mean.p_on, 150, 5) && a.std.p_on > 5, `p_on moyen ${a.mean.p_on.toFixed(1)} ± ${a.std.p_on.toFixed(1)} Pa`);
}
{
  // Retard capteur : 0,5 s à 20 Pa/s cache 2 × 10 Pa d'hystérésis ; lagS le corrige.
  const rows = synth({ pOn: 150, pOff: 150, pChoke: 1e9, pUnchoke: 1e9, pMax: 400 });
  const lag = 0.5, t = rows.map((r) => r.t);
  const late = rows.map((r) => ({ ...r, p: Math.max(0, r.t < 20 ? 20 * (r.t - lag) : 400 - 20 * (r.t - lag - 20)) }));
  const osc = late.map((r) => r.clarity > 0.8);
  const brut = rampThresholds(t, late.map((r) => r.p), osc);
  const corr = rampThresholds(t, late.map((r) => r.p), osc, { lagS: lag });
  assert(brut.hysteresis < -15, `capteur en retard : hystérésis lue ${brut.hysteresis.toFixed(1)} Pa (fausse)`);
  assert(Math.abs(corr.hysteresis) < 5, `corrigée : ${corr.hysteresis.toFixed(1)} Pa`);
}
{
  const d = debounce([false, true, false, false, false], [0, 0.05, 0.1, 0.15, 0.2], 0.1);
  assert(!d[1], 'anti-rebond : un état d\'une trame est ignoré');
  assert(splitCycles([0, 1, 2, 3]).length === 0, 'pas de cycle sans amplitude');
}

console.log('Fuites');
{
  const law = powerLaw([100, 200, 400, 800], [1, 2, 4, 8]);
  assert(near(law.n, 1, 1e-9), 'loi de puissance : n = 1 (fuite visqueuse)');
  const d = equivalentHoleMm(0.8222, 500);
  assert(near(d, 1.0, 0.01), `0,82 L/min sous 500 Pa = trou de 1 mm (${d.toFixed(3)})`);
  // Chute de pression d'un volume de 2 L qui fuit comme un trou de 0,3 mm.
  const V = 2e-3, rows = [];
  let p = 800;
  const k = 0.6 * Math.PI * (0.3e-3) ** 2 / 4 * Math.sqrt(2 / 1.2);   // q = k √p (m³/s)
  for (let i = 0; i <= 4000; i++) {
    rows.push([i * 10, p]);                                           // t en ms
    p -= 101325 / V * k * Math.sqrt(Math.max(p, 0)) * 0.01;
  }
  const lf = leakFlow(rows, 2, 500);
  assert(near(lf.n, 0.5, 0.03), `type de fuite : orifice (n = ${lf.n.toFixed(3)})`);
  assert(near(lf.holeMm, 0.3, 0.01), `trou équivalent retrouvé : ${lf.holeMm.toFixed(3)} mm`);
}

console.log(failures === 0 ? '\nTous les tests de seuils passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
