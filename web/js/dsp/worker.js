// Worker DSP : reçoit l'audio du AudioWorklet via un MessagePort dédié
// (sans passer par le thread principal) et renvoie les analyses au thread
// principal pour l'affichage.

import { Engine } from './engine.js';

let engine = null;

self.onmessage = (e) => {
  const d = e.data;
  if (d.type === 'init') {
    engine = new Engine(d.sampleRate, d.cfg || {});
    if (d.port) {
      d.port.onmessage = (ev) => {
        if (!engine) return;
        const t0 = performance.now();
        const result = engine.process(ev.data);
        if (result) {
          // Charge DSP : temps de calcul rapporté à la période d'analyse.
          result.dspMs = performance.now() - t0;
          // Les spectres sont transférés (zéro copie) plutôt que clonés.
          const transfer = [];
          if (result.coarseSpectrum) transfer.push(result.coarseSpectrum.buffer);
          for (const g of result.groups) if (g.spectrum) transfer.push(g.spectrum.buffer);
          self.postMessage(result, transfer);
        }
      };
    }
  } else if (d.type === 'config' && engine) {
    engine.configure(d.cfg);
  }
};
