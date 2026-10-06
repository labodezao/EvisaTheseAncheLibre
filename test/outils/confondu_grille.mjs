// Grilles de synthèse du 16'+8' (docs/POLYPHONIE-ESSAIS.md, § 4.3), sur le
// moteur actuel :
//
//   node test/outils/confondu_grille.mjs separation [notes]   (défaut 39,41,46,52)
//   node test/outils/confondu_grille.mjs derive [notes]       (défaut 38,46)
//   node test/outils/confondu_grille.mjs stable [notes]       (défaut 39,46)
//
// separation : 8' de ±0,3 à +7 ¢ de l'octave, −10 à +13 dB, deux timbres du
//   16', 5 s ; erreur des lectures que le moteur dit séparées (merged faux),
//   selon le temps écoulé depuis la séparation.
// derive : le 16' et le 8' dérivent l'un par rapport à l'autre (δ qui bouge,
//   passe par zéro), 8' de −10 à +16 dB, 3,5 s ; stable : sans dérive
//   différentielle, 4 s. Pour les deux : part des images confondues dont la
//   vérité est dans la marge, par rapport d'amplitude et par méthode.
// Vérité : la hauteur moyenne du 8' sur la partie de la fenêtre que lit le
// moteur (synthese-anches.mjs, vraie). Une image où la note lue n'est pas
// celle du 8' (16' trop faible, note lue une octave plus haut) est écartée.
import { anches, timbre, hasard, rejoue, voix, vraie, at } from '../synthese-anches.mjs';

const cents = (f, r) => 1200 * Math.log2(f / r);
const [quoi = 'separation', notesTxt] = process.argv.slice(2);
const defaut = { separation: '39,41,46,52', derive: '38,46', stable: '39,46' }[quoi];
const notes = (notesTxt ?? defaut).split(',').map(Number);
const q = (xs, p) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : NaN; };
const f2 = (x) => (Number.isFinite(x) ? x.toFixed(2) : '—');

if (quoi === 'separation') {
  const tranches = [['1re image', (d) => d === 0], ['0 à 0,4 s', (d) => d > 0 && d <= 0.4], ['0,4 à 1 s', (d) => d > 0.4 && d <= 1], ['après 1 s', (d) => d > 1]];
  const e = tranches.map(() => []);
  for (const m of notes) for (const d of [0.3, -0.3, 1, -1, 3, -3, 7]) for (const db of [-10, -4, 0, 6, 13]) for (const p of [-3.5, -1.5]) {
    const liste = [{ f: at(m, 7), a: 1, H: timbre(20, hasard(1 + m), p), vib: 0.2, derive: 0.1 }, { f: at(m + 12, 7 + d), a: 10 ** (db / 20), vib: 0.2, derive: 0.1 }];
    const x = anches(liste, 5, { graine: 1 + m + db });
    let depuis = null, avant = true;
    for (const im of rejoue({ mode: 'register', register: 'LM' }, x)) {
      const v = voix(im, '8');
      if (im.m !== m + 12 || !v?.tracked) continue;
      if (!v.merged && avant) depuis = im.t;
      avant = v.merged;
      if (v.merged) continue;
      const g = im.r.groups.find((gg) => gg.voices.includes(v));
      const err = Math.abs(cents(v.fMeas, vraie(x, liste, 1, im.t, g.W / g.srd)));
      const i = tranches.findIndex(([, t]) => t(im.t - depuis));
      if (i >= 0) e[i].push(err);
    }
  }
  console.log('Lectures séparées du 8\' : erreur (¢), médiane / 95e centile / max, images à plus de 1 ¢');
  tranches.forEach(([nom], i) => console.log(`  ${nom.padEnd(10)} n=${String(e[i].length).padStart(5)}  ${f2(q(e[i], 0.5))} / ${f2(q(e[i], 0.95))} / ${f2(Math.max(...e[i]))}  ${e[i].filter((x) => x > 1).length}`));
} else {
  const cas = quoi === 'derive'
    ? [[0.6, 0.5, 0], [-0.6, -0.5, 0], [1, 0.8, 0], [0.5, 0, -0.4], [-1, 0.3, 0.3], [0.3, 0.2, 0]]
    : [[0.3, 0.1, 0.1], [-0.3, 0.1, 0.1], [1, 0.1, 0.1], [-1, 0.1, 0.1], [3, 0.1, 0.1]];
  const parDb = new Map();
  for (const m of notes) for (const [d, d16, d8] of cas) for (const db of [-10, -4, 0, 6, 10, 13, 16]) for (const p of [-3.5, -1.5]) {
    const liste = [{ f: at(m, 7), a: 1, H: timbre(20, hasard(1 + m), p), vib: 0.2, derive: d16 }, { f: at(m + 12, 7 + d), a: 10 ** (db / 20), vib: 0.2, derive: d8 }];
    const x = anches(liste, quoi === 'derive' ? 3.5 : 4, { graine: 1 + m + db });
    for (const im of rejoue({ mode: 'register', register: 'LM' }, x)) {
      const v = voix(im, '8');
      if (im.m !== m + 12 || !v?.confondu || v.fEstimee == null) continue;
      const g = im.r.groups.find((gg) => gg.voices.includes(v));
      const err = Math.abs(cents(v.fEstimee, vraie(x, liste, 1, im.t, g.W / g.srd)));
      if (!parDb.has(db)) parDb.set(db, []);
      parDb.get(db).push({ err, marge: v.margeCents, me: v.methode });
    }
  }
  const ligne = (nom, L) => {
    const met = ['octave', 'battement', 'raie'].map((k) => `${k} ${L.filter((r) => r.me === k).length}`).join(', ');
    console.log(`  ${nom.padEnd(8)} n=${String(L.length).padStart(5)}  dans la marge ${(100 * L.filter((r) => r.err <= r.marge).length / Math.max(1, L.length)).toFixed(1).padStart(5)} %  erreur méd ${f2(q(L.map((r) => r.err), 0.5))} p95 ${f2(q(L.map((r) => r.err), 0.95))}  marge méd ${f2(q(L.map((r) => r.marge), 0.5))}  (${met})`);
  };
  console.log(`8' confondu (${quoi}) : par rapport 8'/16'`);
  for (const [db, L] of [...parDb].sort((a, b) => a[0] - b[0])) ligne(`${db > 0 ? '+' : ''}${db} dB`, L);
  const tout = [...parDb.values()].flat();
  ligne('tout', tout);
  ligne('raie', tout.filter((r) => r.me === 'raie'));
}
