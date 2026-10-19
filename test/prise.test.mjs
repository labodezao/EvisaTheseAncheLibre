// Contrôle de la prise de son (dsp/prise.js) sur des sons de SYNTHÈSE : les
// seuils sont fixés ici, avec un défaut fabriqué à la fois (porte à zéros,
// plancher coupé, gain automatique, ronflement, écrêtage, blocs perdus, 8 kHz)
// et une prise propre qui ne doit déclencher AUCUNE alerte. Les prises réelles
// (PC sans traitement contre H6) ne servent qu'à valider :
// test/outils/prise_sessions.mjs.
// Exécution : node test/prise.test.mjs

import { ControlePrise, SEUILS } from '../web/js/dsp/prise.js';
import { alea, gauss, lin, accordeon, passer } from './synthese-prise.mjs';

let failures = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ✓ ${msg}`);
  else { failures++; console.error(`  ✗ ÉCHEC : ${msg}`); }
}

const SR = 48000;

console.log('Prise propre : aucune alerte');
{
  const x = accordeon(90, SR);
  const { e, c } = passer(x, SR);
  assert(e.codes.length === 0, `90 s de soufflet, de notes et de pauses : ${JSON.stringify(e.codes)}`);
  assert(c.episodesSession().length === 0, 'aucun épisode enregistré');
  // même chose à 44,1 kHz (le H6)
  const y = accordeon(60, 44100);
  assert(passer(y, 44100).e.codes.length === 0, '44,1 kHz : aucune alerte');
  // bruit de fond plus bas, d\'une interface soignée (-82 dBFS)
  const z = accordeon(60, SR, { bruitDb: -82 });
  assert(passer(z, SR).e.codes.length === 0, 'plancher à -82 dBFS (interface silencieuse) : aucune alerte');
  // un micro très calme : tout le signal sous 1 LSB, mais ce n'est pas une porte
  const q = accordeon(40, SR, { bruitDb: -100 });
  assert(passer(q, SR).e.codes.includes('gate') === false, 'plancher sous la quantification (-100 dBFS) : pas une porte');
  // une note grave à 49 Hz avec ses harmoniques n'est pas du secteur
  const g = new Float32Array(SR * 40);
  for (let i = 0; i < g.length; i++) g[i] = Math.round((lin(-30) * (Math.sin(2 * Math.PI * 49 * i / SR) + 0.6 * Math.sin(2 * Math.PI * 98 * i / SR) + 0.4 * Math.sin(2 * Math.PI * 147 * i / SR))) * 32768) / 32768;
  assert(!passer(g, SR).e.codes.includes('secteur'), 'une note de 49 Hz (98, 147 Hz) n\'est pas le secteur');
  // une basse à 100 Hz tenue
  const b = new Float32Array(SR * 40);
  for (let i = 0; i < b.length; i++) b[i] = lin(-30) * (Math.sin(2 * Math.PI * 100.4 * i / SR) + 0.5 * Math.sin(2 * Math.PI * 200.8 * i / SR));
  assert(!passer(b, SR).e.codes.includes('secteur'), 'une basse à 100,4 Hz n\'est pas le secteur');
}

console.log('Porte (suppresseur de bruit) : zéros exacts');
{
  const x = accordeon(60, SR, { porte: 'zeros' });
  const { e, c } = passer(x, SR);
  assert(e.codes.includes('gate'), `porte à zéros : alerte « gate » (${JSON.stringify(e.codes)})`);
  const ep = c.episodesSession().find((p) => p.code === 'gate');
  assert(ep && ep.debut_s < 15, `datée tôt (${ep?.debut_s} s)`);
  assert(e.douteuse, 'la prise est douteuse');
  // 5 plages en 30 s au moins sont nécessaires : 4 plages isolées ne suffisent pas
  const y = accordeon(20, SR);
  for (const t0 of [3, 6, 9, 12]) for (let i = 0; i < 100; i++) y[Math.round(t0 * SR) + i] = 0;
  assert(!passer(y, SR).e.codes.includes('gate'), '4 plages de zéros en 20 s : pas d\'alerte (seuil 5)');
}

console.log('Porte : plancher coupé net, sans zéros');
{
  const x = accordeon(80, SR, { porte: 'plancher' });
  const { e } = passer(x, SR);
  assert(e.codes.includes('gate'), `plancher coupé net de 16 dB : alerte « gate » (${JSON.stringify(e.codes)})`);
}

console.log('Micro coupé : des zéros voulus ne sont pas une porte');
{
  const x = accordeon(40, SR);
  const c = new ControlePrise(SR);
  passer(x, SR, { c });
  c.suspendre(true);
  passer(new Float32Array(SR * 20), SR, { c });
  c.suspendre(false);
  assert(!c.etat().codes.includes('gate'), '20 s de zéros pendant la coupure de la mesure : rien');
  // un micro mort : une seule très longue plage, pas une porte
  const d = new ControlePrise(SR);
  passer(new Float32Array(SR * 20), SR, { c: d });
  assert(!d.etat().codes.includes('gate'), 'silence numérique continu : pas une porte (plage de plus de 250 ms)');
}

console.log('Ronflement du secteur');
{
  const x = accordeon(60, SR, { hum: -76 });
  const { e, c } = passer(x, SR);
  assert(e.codes.includes('secteur'), `50 Hz à -76 dBFS : alerte « secteur » (${JSON.stringify(e.codes)})`);
  const a = e.alertes.find((p) => p.code === 'secteur');
  assert(a?.detail.hz === 50, 'la raie est reconnue à 50 Hz');
  assert(!e.codes.includes('pompage'), 'ronflement constant : pas de pompage');
  const y = accordeon(60, SR, { hum: -76, humHz: 60 });
  assert(passer(y, SR).e.alertes.find((p) => p.code === 'secteur')?.detail.hz === 60, '60 Hz reconnu (États-Unis)');
  const z = accordeon(60, SR, { hum: -100 });
  assert(!passer(z, SR).e.codes.includes('secteur'), 'raie à -100 dBFS : bruit de convertisseur, pas d\'alerte');
  assert(c.episodesSession().some((p) => p.code === 'secteur'), 'épisode enregistré');
}

console.log('Traitement dynamique (gain automatique)');
{
  const x = accordeon(90, SR, { hum: -70, agc: 0.4 });
  const { e } = passer(x, SR);
  assert(e.codes.includes('pompage'), `gain automatique : la raie du secteur suit le niveau (${JSON.stringify(e.alertes.map((a) => [a.code, a.detail]))})`);
  const y = accordeon(90, SR, { hum: -70, agc: 0 });
  assert(!passer(y, SR).e.codes.includes('pompage'), 'sans gain automatique : pas de pompage');
}

console.log('Écrêtage');
{
  const x = accordeon(30, SR, { ampli: 1 });
  const fort = accordeon(30, SR, { niveaux: [-32, -42, -36, -46], ampli: 40 });
  assert(!passer(x, SR).e.codes.includes('ecretage'), 'niveaux normaux : pas d\'écrêtage');
  assert(passer(fort, SR).e.codes.includes('ecretage'), 'signal poussé à fond : « ecretage »');
}

console.log('Blocs perdus (dates du flux)');
{
  const sr = 48000, n = 480;
  const flux = (trouMs = 0, dérive = 125e-6, gigue = 0.0003, secondes = 24) => {
    const c = new ControlePrise(sr);
    let cum = 0, t0 = 1e6, saut = 0;
    const blocs = Math.floor(secondes * sr / n);
    for (let b = 0; b < blocs; b++) {
      if (trouMs && b === Math.floor(blocs / 2)) saut += trouMs * 1000;
      const ts = t0 + cum / sr * 1e6 * (1 + dérive) + saut + gigue * 1000 * (alea() - 0.5) * 2;
      c.bloc(ts, n);
      c.alimenter(new Float32Array(n).map(() => lin(-70) * gauss()));
      cum += n;
      if (b % 20 === 0) c.etat();
    }
    return c;
  };
  const propre = flux();
  assert(propre.trous.length === 0, `dérive de 125 ppm et gigue de 0,3 ms : aucun trou (${propre.trous.length})`);
  assert(!propre.etat().codes.includes('trous'), 'aucune alerte');
  const d = propre.deriveHorloge();
  assert(d > 110 && d < 140, `dérive de l'horloge lue : ${d} ppm (125 attendus)`);
  const perdu = flux(40);
  const e = perdu.etat();
  assert(perdu.trous.length === 1 && Math.abs(perdu.trous[0].ms - 40) < 2, `40 ms perdus : un trou de ${perdu.trous[0]?.ms} ms à ${perdu.trous[0]?.t_s?.toFixed(1)} s`);
  assert(e.codes.includes('trous'), 'alerte « trous »');
  // une date qui tremble d'un bloc (gigue de la capture) n'est pas un trou : un vrai trou décale tout ce qui suit
  const trembleur = new ControlePrise(sr);
  { let cum = 0; for (let b = 0; b < 2000; b++) { const gigue = b % 97 === 50 ? 9000 : b % 131 === 70 ? -9000 : 0; trembleur.bloc(1e6 + cum / sr * 1e6 + gigue, n); trembleur.alimenter(new Float32Array(n).map(() => lin(-70) * gauss())); cum += n; } }
  assert(trembleur.trous.length === 0, `dates qui sautent de 9 ms sur un seul bloc : aucun trou (${trembleur.trous.length})`);
  // Démarrage du périphérique : la date saute de 870 ms à 2 s de la prise (Ewen, v61 réel) : pas une perte
  const demarrage = new ControlePrise(sr);
  { let cum = 0, saut = 0; for (let b = 0; b < 3000; b++) { if (b === 200) saut = 870000; demarrage.bloc(1e6 + cum / sr * 1e6 + saut, n); demarrage.alimenter(new Float32Array(n).map(() => lin(-70) * gauss())); cum += n; if (b % 20 === 0) demarrage.etat(); } }
  assert(demarrage.trous.length === 0 && !demarrage.etat().codes.includes('trous'), 'saut de 870 ms au démarrage : aucun trou, aucune alerte');
  assert(demarrage.resume().saut_au_demarrage_ms === 870, 'le saut est gardé dans le résumé, pas dans les alertes');
  { let cum = 0, saut = 870000; const c = demarrage; c.alimenter(new Float32Array(0)); void cum; void saut; }
  // la vraie détection reste : même saut après le démarrage, avec son instant et sa cause
  const apres = new ControlePrise(sr);
  { let cum = 0, saut = 0; for (let b = 0; b < 1300; b++) { if (b === 1000) saut = 870000; apres.bloc(1e6 + cum / sr * 1e6 + saut, n, 3); apres.alimenter(new Float32Array(n).map(() => lin(-70) * gauss())); cum += n; if (b % 20 === 0) apres.etat(); } }
  const tr = apres.etat().alertes.find((x) => x.code === 'trous');
  assert(tr && Math.abs(tr.detail.dernier_t_s - 10) < 0.2 && tr.detail.cause === 'flux', `saut de 870 ms à 10 s : alerte avec l'instant (${tr?.detail.dernier_t_s} s) et la cause « flux »`);
  const lent = new ControlePrise(sr);
  { let cum = 0, saut = 0; for (let b = 0; b < 1300; b++) { if (b === 1000) saut = 300000; lent.bloc(1e6 + cum / sr * 1e6 + saut, n, 280); lent.alimenter(new Float32Array(n).map(() => lin(-70) * gauss())); cum += n; if (b % 20 === 0) lent.etat(); } }
  assert(lent.trous[0]?.cause === 'retard', 'saut du même ordre que le temps de calcul du Worker : cause « retard »');
  const petit = flux(4);
  assert(petit.trous.length === 0, '4 ms d\'écart : sous le seuil de 5 ms');
  const double = flux(-30);
  assert(double.trous.length === 1 && double.trous[0].ms < -25, `30 ms en double : trou de ${double.trous[0]?.ms} ms`);
}

console.log('Fréquence d\'échantillonnage trop basse');
{
  for (const sr of [8000, 16000]) {
    const { e } = passer(accordeon(10, sr), sr, { blocs: 256 });
    assert(e.codes.includes('lent'), `${sr} Hz : alerte « lent »`);
  }
  assert(!passer(accordeon(10, 44100), 44100).e.codes.includes('lent'), '44,1 kHz : rien');
}

console.log('Épisodes et fin d\'alerte');
{
  // une porte pendant 40 s, puis une prise propre : l'alerte tombe 30 s après sa dernière preuve
  const mauvais = accordeon(40, SR, { porte: 'zeros' });
  const bon = accordeon(60, SR);
  const c = new ControlePrise(SR);
  passer(mauvais, SR, { c });
  assert(c.etat().codes.includes('gate'), 'alerte pendant la porte');
  passer(bon, SR, { c });
  assert(!c.etat().codes.includes('gate'), 'alerte levée après 60 s propres');
  const ep = c.episodesSession().find((p) => p.code === 'gate');
  assert(ep && ep.fin_s > 35 && ep.fin_s < 80, `épisode refermé (${ep?.debut_s} à ${ep?.fin_s} s)`);
  assert(SEUILS.tenue_s === 30, 'tenue de 30 s');
}

console.log('v69 (I4a) : un convertisseur de 16 bits dans une pièce calme n\'est pas une porte, une porte réelle en est une');
{
  // bruit de fond passe-bas (300 Hz) quantifié sur 16 bits : des suites de petites valeurs, donc des plages de zéros exacts entre et sous les notes
  // (avant la v69 : la prise H6 réécrite en 16 bits donnait 65 s douteuses sur 211, `gate`)
  for (const bruitDb of [-80, -85, -90, -92]) {
    const calme = passer(accordeon(70, 44100, { bruitDb, bruitFc: 300 }), 44100).e;
    assert(!calme.codes.includes('gate'), `16 bits, plancher à ${bruitDb} dBFS, pas de porte : pas d'alerte (${calme.codes.join('+') || 'aucune'})`);
  }
  for (const bruitDb of [-80, -85, -90]) {
    const porte = passer(accordeon(70, 44100, { bruitDb, bruitFc: 300, coupure: -45 }), 44100).e;
    assert(porte.codes.includes('gate'), `16 bits, plancher à ${bruitDb} dBFS, porte réelle à -45 dBFS : alerte « gate »`);
  }
  assert(SEUILS.gateVoisinDb === -60, 'gateVoisinDb : -60 dBFS (plan 2^3, CERTIFICAT.md § 0C)');
}

console.log('v69 (I4b) : l\'échelle de la prise, par la fréquence du secteur');
{
  const SR2 = 44100, cents = (c) => 50 * 2 ** (c / 1200);
  const lire = (c, hum, sec, bruitDb = -74) => { const r = passer(accordeon(sec, SR2, { hum, bruitDb, humHz: cents(c) }), SR2); return { e: r.e, c: r.c, infos: r.c.etat().infos.map((i) => i.code) }; };
  for (const hum of [-60, -78]) {
    const bruitDb = hum === -78 ? -95 : -74;
    assert(!lire(0, hum, 75, bruitDb).e.codes.includes('echelle'), `ronflement ${hum} dBFS, sans décalage, 75 s : pas d'alerte d'échelle`);
    const a5 = lire(5, hum, 75, bruitDb);
    assert(a5.e.codes.includes('echelle'), `ronflement ${hum} dBFS, prise transposée de +5 ¢, 75 s : alerte « echelle » (${a5.c.echelle?.cents.toFixed(2)} ¢)`);
    assert(Math.abs(a5.c.echelle.cents - 5) < 0.3, `l'échelle est mesurée à 0,3 ¢ près (${a5.c.echelle?.cents.toFixed(2)})`);
    assert(!lire(5, hum, 30, bruitDb).e.codes.includes('echelle'), `${hum} dBFS, +5 ¢ mais 30 s seulement : pas encore dit (il faut 50 s de ronflement)`);
    assert(!lire(5, null, 75).e.codes.includes('echelle'), 'sans ronflement : rien à dire, pas d\'alerte');
  }
  assert(!lire(2, -60, 75).e.codes.includes('echelle') && lire(2, -60, 75).infos.includes('echelleAvert'), '+2 ¢ : avertissement sans refus');
  for (const f of [49.96, 50.04]) {
    const r = passer(accordeon(75, SR2, { hum: -60, humHz: f }), SR2);
    assert(!r.e.codes.includes('echelle'), `réseau à ${f} Hz (±0,08 %, régime normal) : pas d'alerte`);
  }
  assert(passer(accordeon(75, SR2, { hum: -60, humHz: 50.2 }), SR2).e.codes.includes('echelle'), 'réseau à 50,2 Hz (incident, 4 ‰) : alerte, la prise est douteuse');
}

console.log(failures === 0 ? '\nTous les tests de prise passent.' : `\n${failures} échec(s).`);
process.exit(failures === 0 ? 0 : 1);
