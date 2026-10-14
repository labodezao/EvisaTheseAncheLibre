// Worker du verrou de phase expérimental (v59) : lit une note enregistrée par `lecteur-note.js` avec `lireNote` (verrou-note.js), hors du
// Worker de mesure et de l'interface (7 s de calcul pour une note de 9 s : voir docs/FREQUENCES-ANCHES.md). Un travail à la fois.
import { lireNote } from './verrou-note.js';
import { resumeLecture } from './lecteur-note.js';

self.onmessage = (e) => {
  const { x, sr, fc, moteur, midi, t } = e.data;
  const t0 = performance.now();
  let lecture;
  try {
    const l = lireNote(x, sr, 0, x.length, fc, { moteur });
    lecture = resumeLecture(l, { midi, t, ms: performance.now() - t0, moteur });
    if (l.plage) lecture.plageS = (l.plage.i1 - l.plage.i0) / sr;
  } catch (err) {
    lecture = { sure: false, raison: 'erreur', erreur: String(err?.message ?? err), midi, t, ms: performance.now() - t0 };
  }
  self.postMessage(lecture);
};
