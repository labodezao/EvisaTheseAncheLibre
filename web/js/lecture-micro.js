// Côté page : branche le micro sur le moteur (lot F2). Pur côté DOM : utilisé par ui/audio.js et app.js.
//
// Drapeau LECTURE_DECOUPLEE éteint : le `readable` du processeur va au Worker du moteur (v70).
// Allumé : il va à un Worker léger (dsp/lecture-worker.js) qui le vide sans calcul et passe les blocs au moteur par un
// MessagePort ; la file du processeur est agrandie (TRAMES_TAMPON, environ 2 s).
// Rend { lecteur } (le Worker léger à arrêter avec le reste, ou null).
import { optionsProcesseur } from './dsp/lecture.js';

export function brancherMicro(piste, workerMoteur, decouplee) {
  const proc = new MediaStreamTrackProcessor(optionsProcesseur(piste, decouplee));
  if (!decouplee) {
    workerMoteur.postMessage({ type: 'stream', readable: proc.readable }, [proc.readable]);
    return { lecteur: null, processeur: proc };
  }
  const lecteur = new Worker(new URL('./dsp/lecture-worker.js', import.meta.url), { type: 'module' });
  const canal = new MessageChannel();
  workerMoteur.postMessage({ type: 'lecture', port: canal.port1 }, [canal.port1]);
  lecteur.postMessage({ type: 'lire', readable: proc.readable, port: canal.port2 }, [proc.readable, canal.port2]);
  return { lecteur, processeur: proc };
}
