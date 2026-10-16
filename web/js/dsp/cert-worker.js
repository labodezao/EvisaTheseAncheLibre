// Worker du certificat (v66, F4) : reçoit les ajustements du moteur (cert-calcul.js, FileCalcul), les calcule par tranches de ~10 ms (entre deux tranches il lit les messages : une
// demande plus récente remplace celle qui attend, une sentinelle passe devant un ajustement principal) et rend le résultat sans le modèle.
import { FileCalcul, calculerTravail } from './cert-calcul.js';
import { executerTravail } from './certificat.js';

const file = new FileCalcul();
let pompe = false;
const mc = new MessageChannel();
const rendre = () => new Promise((ok) => { mc.port1.onmessage = ok; mc.port2.postMessage(0); });

self.onmessage = (e) => {
  const m = e.data;
  if (m.type === 'travail') { file.ajouter(m.travail); pomper(); } else if (m.type === 'oublier') file.oublier(m.cle);
};

async function pomper() {
  if (pompe) return;
  pompe = true;
  try {
    for (let t = file.suivant(); t; t = file.suivant()) {
      const t0 = performance.now();
      const g = executerTravail(t);
      let r, tranche = performance.now();
      try {
        while (!(r = g.next()).done) {
          if (performance.now() - tranche > 10) { await rendre(); tranche = performance.now(); if (!t.sentinelle && file.attente.some((q) => q.sentinelle)) { const s = file.attente.findIndex((q) => q.sentinelle); const q = file.attente.splice(s, 1)[0]; const rs = calculerTravail(q); self.postMessage({ type: 'resultat', id: q.id, cle: q.cle, nls: rs.nls, ms: rs.ms }); tranche = performance.now(); } }
        }
        self.postMessage({ type: 'resultat', id: t.id, cle: t.cle, nls: r.value, ms: performance.now() - t0 });
      } catch (err) {
        self.postMessage({ type: 'resultat', id: t.id, cle: t.cle, erreur: String(err?.message ?? err) });
      }
      await rendre();
    }
  } finally { pompe = false; }
}
