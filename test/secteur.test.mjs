// Retirer le ronflement du secteur (dsp/secteur.js) sur des sons de synthèse : le ronflement part (30 dB
// et plus), un partiel à 1,5 Hz d'une harmonique n'est pas touché, et la mesure d'une note dont les
// partiels tombent près ou loin des harmoniques du secteur est la même qu'sans ronflement, à 0,05 ¢ près.
// Exécution : node test/secteur.test.mjs

import { RetireSecteur, affinerSecteur, partielProche } from '../web/js/dsp/secteur.js';
import { Engine } from '../web/js/dsp/engine.js';
// Anche suivie (finement) d'une image du moteur : son écart en ¢ à la liste (ce que fait ui/mesure.js dans PolyReed).
const anchesDuTick = (t) => (t.groups ?? []).filter((g) => !g.isHarmonic && !g.isSub).flatMap((g) => g.voices ?? []).map((v) => ({ fine: !!(v.tracked && !v.coarse && !v.held), cents: v.dTargetCents ?? null }));
import { ControlePrise } from '../web/js/dsp/prise.js';
import { alea, gauss, lin } from './synthese-prise.mjs';

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}

const SR = 48000;
void alea;

// Amplitude (crête, dBFS) d'une raie à f sur x (fenêtre de Hann).
function raie(x, f, sr = SR) {
  const N = x.length, w = 2 * Math.PI * f / sr, c = 2 * Math.cos(w);
  let s1 = 0, s2 = 0;
  for (let i = 0; i < N; i++) { const h = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N); const v = x[i] * h + c * s1 - s2; s2 = s1; s1 = v; }
  const re = s1 - s2 * Math.cos(w), im = s2 * Math.sin(w);
  return 20 * Math.log10(2 * Math.hypot(re, im) / N + 1e-12);
}

// Ronflement : harmoniques de f0 avec des amplitudes décroissantes (dBFS de crête pour la première).
function ronflement(n, f0, db1, sr = SR, harms = 8) {
  const x = new Float32Array(n);
  for (let h = 1; h <= harms; h++) {
    const a = lin(db1) / Math.sqrt(h), ph = 1.3 * h;
    for (let i = 0; i < n; i++) x[i] += a * Math.sin(2 * Math.PI * h * f0 * i / sr + ph);
  }
  return x;
}

function passer(x, rs, bloc = 512) {
  const y = new Float32Array(x.length);
  for (let o = 0; o + bloc <= x.length; o += bloc) y.set(rs.traiter(x.subarray(o, o + bloc)), o);
  return y;
}

console.log('Le ronflement part');
{
  const f0 = 50.04;                                   // le secteur n'est jamais pile à 50 Hz
  const n = SR * 12;
  const x = ronflement(n, f0, -60);
  for (let i = 0; i < n; i++) x[i] += lin(-80) * gauss();
  const fe = affinerSecteur(x.subarray(0, SR * 2), SR, 50);
  assert(Math.abs(fe - f0) <= 0.02, `fréquence du secteur estimée : ${fe} Hz (vrai ${f0})`);
  const rs = new RetireSecteur(SR);
  rs.regler(fe, 8);
  const y = passer(x, rs);
  const fin = (v) => v.subarray(n - SR * 2);
  for (const h of [1, 2, 3, 5]) {
    const avant = raie(fin(x), h * f0), apres = raie(fin(y), h * f0);
    assert(avant - apres >= 30, `harmonique ${h} (${(h * f0).toFixed(1)} Hz) : ${avant.toFixed(1)} -> ${apres.toFixed(1)} dBFS (${(avant - apres).toFixed(0)} dB de moins)`);
  }
  const x60 = ronflement(n, 59.97, -60);
  assert(Math.abs(affinerSecteur(x60.subarray(0, SR * 2), SR, 60) - 59.97) <= 0.02, 'secteur à 60 Hz : fréquence estimée à 0,02 Hz');
  assert(rs.frequences().length === 8 && partielProche(100.4, rs.frequences()) && !partielProche(101.5, rs.frequences()), 'les partiels à moins de 1 Hz d\'une harmonique sont dits proches');
}

console.log('Les anches ne sont pas abîmées');
{
  const f0 = 50.02, n = SR * 14;
  const x = new Float32Array(n);
  const tons = [[101.5, -40], [203.3, -45], [440, -35]];   // 1,5 Hz au-dessus de la 2e harmonique, loin des autres
  for (const [f, db] of tons) for (let i = 0; i < n; i++) x[i] += lin(db) * Math.sin(2 * Math.PI * f * i / SR + 0.4);
  const h = ronflement(n, f0, -55);
  const mix = x.map((v, i) => v + h[i]);
  const rs = new RetireSecteur(SR);
  rs.regler(affinerSecteur(mix.subarray(0, SR * 2), SR, 50), 8);
  const y = passer(mix, rs);
  const fin = (v) => v.subarray(n - SR * 2);
  for (const [f, db] of tons) {
    const a = raie(fin(y), f), ref = raie(fin(x), f);
    assert(Math.abs(a - ref) < 0.5, `partiel à ${f} Hz : ${ref.toFixed(2)} -> ${a.toFixed(2)} dBFS (écart ${(a - ref).toFixed(2)} dB)`);
  }
}

// Une note tenue (anche à 4 partiels) : sa hauteur lue par le moteur, en ¢ de la note la plus proche.
function hauteur(sig, sr = SR) {
  const e = new Engine(sr, { a4: 440, mode: 'auto', response: 'normal' });
  const c = [];
  for (let i = 0; i + 512 <= sig.length; i += 512) {
    const t = e.process(sig.subarray(i, i + 512));
    if (t && !t.quiet && i > sig.length * 0.6) { const a = anchesDuTick(t).find((v) => v.fine && v.cents != null); if (a) c.push(a.cents); }
  }
  c.sort((p, q) => p - q);
  return c.length >= 8 ? c[Math.floor(c.length / 2)] : null;
}
function note(f, cents, sec, db = -32) {
  const n = SR * sec, x = new Float32Array(n), fr = f * 2 ** (cents / 1200);
  for (let i = 0; i < n; i++) {
    let v = lin(-80) * gauss();
    for (let h = 1; h <= 5; h++) v += (lin(db) / h) * Math.sin(2 * Math.PI * fr * h * i / SR);
    x[i] = v;
  }
  return x;
}

console.log('Mesure : la même, avec ou sans ronflement, à 0,05 ¢ près (ronflement +36 dB au-dessus du plancher)');
{
  // plancher -80 dBFS, ronflement -44 dBFS : +36 dB
  const cas = [['La2 110 Hz (partiels à 110, 220, 330, 440, 550 : près de 100 et 150, 200, 300, 450, 550)', 110, 3.2],
    ['Mi2 82,4 Hz (partiel 2 à 164,8 près de 150, 3 à 247 près de 250)', 82.407, -4.1],
    ['La3 220 Hz (partiels 220, 440, 660 : loin des harmoniques de 50 Hz)', 220, 2.0],
    ['Do5 523 Hz (loin)', 523.25, -1.7]];
  for (const [nom, f, c] of cas) {
    const sec = 14, n = SR * sec;
    const propre = note(f, c, sec);
    const h = ronflement(n, 50.03, -44, SR, 12);
    const sale = propre.map((v, i) => v + h[i]);
    const rs = new RetireSecteur(SR);
    rs.regler(affinerSecteur(sale.subarray(0, SR * 2), SR, 50), 12);
    const net = passer(sale, rs);
    const a = hauteur(propre), b = hauteur(sale), d = hauteur(net);
    console.log(`    ${nom} : sans ronflement ${a?.toFixed(3)} ¢, avec ${b?.toFixed(3)} ¢, retiré ${d?.toFixed(3)} ¢`);
    assert(a != null && d != null && Math.abs(d - a) <= 0.05, `${nom.split(' (')[0]} : écart de la mesure après retrait ${(d - a).toFixed(3)} ¢ (avant retrait ${b == null ? 'illisible' : (b - a).toFixed(3)} ¢)`);
  }
}

console.log('Le contrôle de la prise : retiré, ce n\'est plus une alerte');
{
  const n = SR * 40;
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = lin(-80) * gauss();
  const h = ronflement(n, 50.0, -62);
  const sale = x.map((v, i) => v + h[i]);
  const c = new ControlePrise(SR);
  c.retireSecteur = true;
  const rs = new RetireSecteur(SR);
  let reglee = false;
  for (let o = 0, k = 0; o + 512 <= n; o += 512) {
    const blk = sale.subarray(o, o + 512);
    c.alimenter(blk);
    const pur = reglee ? rs.traiter(blk) : blk;
    c.alimenterNet(pur);
    if (++k % 8 === 0) {
      const e = c.etat();
      const dem = c.demandeSecteur();
      if (dem && !reglee) { rs.regler(dem.f0, dem.harmoniques); reglee = true; c.secteurActif(true); }
      void e;
    }
  }
  const e = c.etat();
  assert(reglee, 'le ronflement détecté déclenche le retrait');
  assert(!e.codes.includes('secteur') && !e.douteuse, `le ronflement retiré n'est plus une alerte (${JSON.stringify(e.codes)})`);
  assert(e.infos?.some((i) => i.code === 'secteurRetire' && i.detail.hz === 50), 'mais une information : « ronflement 50 Hz supprimé »');
  // trop fort pour être retiré : le résidu reste, l'alerte aussi
  const fort = new ControlePrise(SR);
  fort.retireSecteur = true;
  const dur = sale.map((v, i) => v + lin(-62) * 60 * 0 + (i % 997 === 0 ? 0 : 0));
  void dur;
  for (let o = 0, k = 0; o + 512 <= n; o += 512) {
    const blk = sale.subarray(o, o + 512);
    fort.alimenter(blk);
    fort.alimenterNet(blk);    // le retrait ne fait rien (annuleur arrêté)
    if (++k % 8 === 0) { fort.etat(); const d = fort.demandeSecteur(); if (d) fort.secteurActif(true); }
  }
  assert(fort.etat().codes.includes('secteur'), 'ronflement qui reste après retrait : l\'alerte reste');
}

console.log(failures === 0 ? '\nTous les tests du retrait du secteur passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
