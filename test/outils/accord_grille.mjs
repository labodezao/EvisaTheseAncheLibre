// Accord en 16'+8' (moteur v54, docs/POLYPHONIE-ESSAIS.md § 4.6) : quatre accords
// de synthèse (Sol+Ré et Ré+La d'un diato, Do majeur et Ré mineur d'un
// Stradella), chaque note en 16'+8', une anche à +6 ¢ à chaque essai, réponses
// Normal et Rapide. Sur les images après 3 s : lectures dans leur marge (la
// vérité sur la fenêtre lue), désaccordée désignée (|écart| − marge > 1 ¢),
// autres justes (|écart| + marge ≤ 1 ¢), et les pires lectures hors marge.
//
//   node test/outils/accord_grille.mjs
import { anches, rejoue, at, vraie } from '../synthese-anches.mjs';

const LM = [{ oct: 0, pied: "16'" }, { oct: 1, pied: "8'" }];
const quinte = { mode: 'chord', chordType: 'quinte', chordDegrees: [0, 7], chordVoices: LM };
const CAS = {
  'diato Sol+Ré': { notes: [55, 62], cfg: quinte },
  'diato Ré+La': { notes: [62, 57], cfg: quinte },
  'Stradella Do': { notes: [60, 52, 55], cfg: { mode: 'chord', chordType: 'majeur', chordDegrees: [0, 4, 7], chordVoices: LM } },
  'Stradella Rém': { notes: [62, 53, 57], cfg: { mode: 'chord', chordType: 'mineur', chordDegrees: [0, 3, 7], chordVoices: LM } },
};
let tot = 0, dedans = 0, juste = 0, njuste = 0, desi = 0, ndesi = 0, absent = 0, desiAutre = 0;
const pires = [];
for (const [nom, { notes, cfg }] of Object.entries(CAS)) for (const response of ['normal', 'fast']) {
  const reeds = notes.flatMap((m) => [m, m + 12]);
  for (let j = 0; j < reeds.length; j++) {
    const liste = reeds.map((m, i) => ({ f: at(m, i === j ? 6 : 0), a: i % 2 ? 0.7 : 1, vib: 0.1 }));
    const x = anches(liste, 5, { graine: 63 + j });
    for (const im of rejoue({ ...cfg, response }, x).filter((q) => q.t > 3)) {
      reeds.forEach((m, i) => {
        const v = im.vs.find((q) => q.midi === m);
        if (!v?.tracked) { absent++; return; }
        const g = im.r.groups.find((gg) => gg.voices.includes(v));
        const c = v.confondu && v.fEstimee != null ? v.centsEstimesCible : v.dTargetCents;
        const mg = v.confondu && v.margeCents != null ? v.margeCents : 0;
        const vr = 1200 * Math.log2(vraie(x, liste, i, im.t, g.W / g.srd) / v.target);
        tot++;
        if (Math.abs(c - vr) <= Math.max(0.15, mg)) dedans++;
        else pires.push(`${nom} ${response} essai ${j} ${v.def.id} ${im.t.toFixed(2)} s : ${c.toFixed(2)} ±${mg.toFixed(2)} pour ${vr.toFixed(2)} ${v.methode ?? ''}`);
        if (i === j) { ndesi++; if (Math.abs(c) - mg > 1) desi++; } else { njuste++; if (Math.abs(c) + mg <= 1) juste++; if (Math.abs(c) - mg > 1) desiAutre++; }
      });
    }
  }
}
console.log(`dans la marge ${dedans}/${tot} ; désaccordée désignée ${desi}/${ndesi} ; autres justes ${juste}/${njuste}, désignées à tort ${desiAutre} ; absentes ${absent}`);
console.log(pires.slice(0, 15).join('\n'));
