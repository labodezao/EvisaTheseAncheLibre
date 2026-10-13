// Verrou de phase (expérimental, v59) : ce que la page montre d'une lecture de note (dsp/lecteur-note.js, resumeLecture). Pur.
// Une lecture sûre donne les deux fréquences et le battement ; Δ non résolu, seulement le centre ± Δ/2 ; sinon la raison, jamais un chiffre.
import { t } from './langue.js';
import { formatHz } from './format.js';

const RAISONS = {
  plage: 'verrou raison plage', courte: 'verrou raison courte', instable: 'verrou raison instable', battement: 'verrou raison battement',
  raies: 'verrou raison raies', etiquette: 'verrou raison etiquette', dispersion: 'verrou raison dispersion', ecart: 'verrou raison dispersion',
  lecture: 'verrou raison lecture', bruit: 'verrou raison bruit', ambigu: 'verrou raison battement', erreur: 'verrou raison erreur',
};

// lecture : le dernier message du Worker (ou null) ; allume : réglage verrouPhase. { etat: 'cache' | 'calcul' | 'sur' | 'nonresolu' | 'refus', texte }
export function afficherVerrou(lecture, allume) {
  if (!allume) return { etat: 'cache', texte: '' };
  const titre = t('verrou phase court');
  if (!lecture) return { etat: 'attente', texte: `${titre} : ${t('verrou attente')}` };
  if (lecture.calcul) return { etat: 'calcul', texte: `${titre} : ${t('verrou calcul')}` };
  if (lecture.sure && lecture.f) {
    const [a, b] = lecture.f;
    return { etat: 'sur', texte: t('verrou sur', { titre, a: formatHz(a, 3), b: formatHz(b, 3), o: formatHz(b - a, 2) }) };
  }
  if (lecture.raison === 'non-resolu' && lecture.centre != null) {
    return { etat: 'nonresolu', texte: t('verrou non resolu', { titre, c: formatHz(lecture.centre, 3), d: formatHz(lecture.demi ?? 0, 2) }) };
  }
  return { etat: 'refus', texte: t('verrou refus', { titre, raison: t(RAISONS[lecture.raison] ?? 'verrou raison lecture') }) };
}
