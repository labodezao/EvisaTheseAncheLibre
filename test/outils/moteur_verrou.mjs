// Moteur (plateau) contre verrou de phase, note par note, sur une prise (H6 ou PC) : la question d'Ewen (14/10/2026) « le verrou
// est-il plus précis ? ». Le moteur v62 lit chaque anche ; le plateau est la médiane de ses 40 dernières % d'images fines de la
// note. Le verrou (dsp/verrou-note.js) lit la note entière. Écart en ¢ entre les deux, par anche.
//   node test/outils/moteur_verrou.mjs <wav> <canal> <json de session (reglages_moteur)> [--mettre-secteur]
import fs from 'node:fs';
import { lireWav } from './wav.mjs';
import { Engine } from '../../web/js/dsp/engine.js';
import { LecteurNote } from '../../web/js/dsp/lecteur-note.js';
import { lireNote } from '../../web/js/dsp/verrou-note.js';
import { RetireSecteur, affinerSecteur } from '../../web/js/dsp/secteur.js';

const [chemin, canal, jsonp] = process.argv.slice(2);
const secteur = process.argv.includes('--secteur');
const j = JSON.parse(fs.readFileSync(jsonp, 'utf8'));
const cfg = { ...j.reglages_moteur }; delete cfg.lockNote;
const { x, sr } = lireWav(chemin, Number(canal ?? 0));
const med = (a) => { const s = [...a].sort((p, q) => p - q); return s.length ? s[s.length >> 1] : NaN; };
const cents = (a, b) => 1200 * Math.log2(a / b);
const e = new Engine(sr, cfg);
const notes = [];
const lecteur = new LecteurNote(sr, (n) => notes.push(n));
let rs = null;
if (secteur) { rs = new RetireSecteur(sr); rs.regler(affinerSecteur(x.subarray(0, sr * 2), sr, 50), 8); }
for (let i = 0; i + 512 <= x.length; i += 512) {
  const brut = x.subarray(i, i + 512);
  const bloc = rs ? rs.traiter(brut) : brut;
  const t = e.process(bloc);
  lecteur.alimenter(bloc, t ?? null);
}
console.log(`${chemin} canal ${canal}${secteur ? ' (secteur retiré)' : ''} : ${notes.length} notes lues`);
for (const n of notes) {
  const tard = n.moteur.filter((q) => q[0] > n.moteur[n.moteur.length - 1][0] * 0.6);
  const m8 = med(tard.map((q) => q[1])), mp = med(tard.map((q) => q[2]));
  let l; try { l = lireNote(n.x, sr, 0, n.x.length, n.fc, { moteur: n.moteur }); } catch (err) { l = { sure: false, raison: String(err.message) }; }
  const ecarts = l.sure && l.f ? [cents(l.f[0], m8), cents(l.f[1], mp)] : null;
  console.log(`midi ${n.midi} t=${n.t.toFixed(1)}s ${(n.x.length / sr).toFixed(1)}s moteur ${m8.toFixed(3)}/${mp.toFixed(3)} Hz verrou ${l.sure ? `${l.f[0].toFixed(3)}/${l.f[1].toFixed(3)} Hz (sûr), écart moteur-verrou ${ecarts.map((c) => c.toFixed(2)).join(' / ')} ¢` : `refus : ${l.raison}${l.centre ? ` centre ${l.centre.toFixed(3)} ± ${(l.demi ?? 0).toFixed(2)}` : ''}`}`);
}
