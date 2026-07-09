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
        const result = engine.process(ev.data);
        if (result) self.postMessage(result);
      };
    }
  } else if (d.type === 'config' && engine) {
    engine.configure(d.cfg);
  }
};
