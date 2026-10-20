// Worker de lecture du micro (lot F2, drapeau LECTURE_DECOUPLEE de lecture.js).
//
// Il ne fait QUE vider le flux du micro (MediaStreamTrackProcessor.readable) : jamais de calcul ici, donc la file du
// processeur ne déborde pas quand le moteur est occupé. Chaque trame est copiée (premier canal, Float32) et passée au
// Worker du moteur par un MessagePort, avec sa date et sa fréquence ; la file du port n'est pas bornée.
import { copierPlan } from './lecture.js';

async function lire(readable, port) {
  const lecteur = readable.getReader();
  for (;;) {
    const { value: ad, done } = await lecteur.read();
    if (done) break;
    try {
      const plan = new Float32Array(ad.numberOfFrames);
      copierPlan(ad, plan);
      port.postMessage({ t: Date.now(), ts: ad.timestamp, sr: ad.sampleRate, format: ad.format, canaux: ad.numberOfChannels, pcm: plan }, [plan.buffer]);
    } finally {
      ad.close();
    }
  }
  port.postMessage({ fin: true });
}

self.onmessage = (e) => {
  const d = e.data;
  if (d?.type === 'lire') lire(d.readable, d.port).catch((err) => d.port.postMessage({ erreur: String(err?.message ?? err) }));
};
