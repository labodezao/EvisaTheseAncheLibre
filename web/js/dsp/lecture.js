// Lecture du micro : file des trames, trames perdues, simulation (lot F2, 19/10/2026).
//
// Cause visée. Le micro est lu par MediaStreamTrackProcessor. Son `readable`
// était transféré au MÊME Worker que le moteur : quand un calcul dure (p99
// 38,7 ms le 19/10, ajustements du certificat), le Worker ne lit plus le flux ;
// la file du processeur est BORNÉE (maxBufferSize) et, pleine, le navigateur
// jette les trames les plus anciennes. L'horloge du flux saute alors d'autant :
// c'est le « trou » de prise (cause « retard »). Correction (drapeau
// LECTURE_DECOUPLEE) : un Worker léger (lecture-worker.js) ne fait que vider le
// flux et passer les blocs au moteur par un MessagePort, dont la file n'est pas
// bornée ; la file du processeur est en plus agrandie (TRAMES_TAMPON).
//
// Ce module est pur (aucun Worker, aucun DOM) : la logique de file est donc
// testable sous Node (test/lecture-flux.test.mjs).

// Drapeau : lecture du micro découplée du calcul (allumé le 19/10 : 0 trame perdue sur 30 s dans Chrome contre 346 sans). Éteint = lecture dans le Worker du moteur (v70).
export const LECTURE_DECOUPLEE = true;

// Trames de 10 ms gardées par le navigateur avant de jeter les plus anciennes : environ 2 s.
export const TRAMES_TAMPON = 200;

// File par défaut du navigateur, SUPPOSÉE (Chrome ne documente pas la valeur ; à mesurer dans le navigateur) : quelques trames de 10 ms.
// Le 19/10, des trous de 30 à 100 ms sont apparus pour un Worker bloqué de 7 à 53 ms seulement : la file est donc petite.
export const TRAMES_TAMPON_DEFAUT = 2;

const CHAUFFE_S = 5;   // les premières secondes : un saut de date est le démarrage du périphérique, pas une perte (prise.js : trouChauffe_s)

// Retard toléré par le moteur sur la lecture découplée. Les blocs en attente (file du MessagePort, non bornée) retardent ce que
// l'écran montre ; le moteur ne rattrape pas un retard durable (machine plus lente que le temps réel, ou calcul qui n'en finit
// pas) : au-delà de RETARD_MAX_MS il écarte les blocs les plus anciens, d'un coup, jusqu'à ne plus avoir que RETARD_REPRISE_MS
// de retard. Ces blocs écartés sont comptés comme des trames perdues (CompteurTrames voit le saut de date) : rien n'est caché.
export const RETARD_MAX_MS = 1000;
export const RETARD_REPRISE_MS = 250;

export class Retard {
  constructor(max = RETARD_MAX_MS, reprise = RETARD_REPRISE_MS) { this.max = max; this.reprise = reprise; this.rattrape = false; }
  // `lagMs` : l'âge du bloc quand le moteur le prend. Vrai : le traiter. Un âge inconnu (NaN) se traite.
  garder(lagMs) {
    if (!Number.isFinite(lagMs)) return true;
    if (this.rattrape) { if (lagMs <= this.reprise) this.rattrape = false; }
    else if (lagMs > this.max) this.rattrape = true;
    return !this.rattrape;
  }
}

// Options de `new MediaStreamTrackProcessor(...)` : la file agrandie quand le drapeau est allumé.
export function optionsProcesseur(piste, decouplee = LECTURE_DECOUPLEE) {
  return decouplee ? { track: piste, maxBufferSize: TRAMES_TAMPON } : { track: piste };
}

// Une trame (AudioData) copiée dans `plan` (Float32Array de numberOfFrames), premier canal. Float32 ou Int16.
export function copierPlan(ad, plan) {
  const n = ad.numberOfFrames;
  if (/^f32/.test(ad.format)) {
    ad.copyTo(plan, { planeIndex: 0, format: 'f32-planar' });
    return plan;
  }
  const planaire = ad.format.endsWith('planar');
  const pas = planaire ? 1 : ad.numberOfChannels;
  const tmp = new Int16Array(n * pas);
  ad.copyTo(tmp, { planeIndex: 0 });
  for (let i = 0; i < n; i++) plan[i] = tmp[i * pas] / 32768;
  return plan;
}

// Compte les trames perdues d'après les dates du flux (microsecondes) face au nombre d'échantillons reçus.
// Une perte décale TOUTES les dates suivantes d'un palier (une date qui tremble ne le fait pas) : elle n'est retenue
// qu'au bloc suivant. L'horloge du micro dérive lentement (100 à 150 ppm) : la référence la suit.
export class CompteurTrames {
  constructor(sr, chauffeS = CHAUFFE_S) {
    this.sr = sr;
    this.chauffeS = chauffeS;
    this.perdues = 0;        // trames de la taille d'un bloc, perdues depuis le début
    this.ms = 0;             // durée perdue (ms)
    this.evenements = [];    // [{ t_s, ms, trames }] (les 500 derniers)
    this.n = 0;              // échantillons reçus
    this.ts0 = null; this.rRef = 0; this.candidat = null;
    this.demarrageMs = null;   // saut de date au démarrage du périphérique (les CHAUFFE_S premières secondes) : un calage, pas une perte
  }

  // `ts` : AudioData.timestamp (µs), `n` : numberOfFrames.
  bloc(ts, n) {
    if (!Number.isFinite(ts)) { this.n += n; return; }
    const duree = n / this.sr;
    if (this.ts0 === null) { this.ts0 = ts; this.rRef = 0; this.n = 0; }
    const r = (ts - this.ts0) / 1e6 - this.n / this.sr;
    const ecart = r - this.rRef;
    const c = this.candidat;
    if (c && ecart > 0.5 * c.ecart) {
      // Confirmé par le bloc suivant : le palier tient.
      if (c.t <= this.chauffeS) {
        this.demarrageMs = Math.round(c.ecart * 1000);   // le périphérique démarre : la date se cale (comme prise.js, trouChauffe_s)
      } else {
        const trames = Math.max(1, Math.round(c.ecart / duree));
        this.perdues += trames; this.ms += c.ecart * 1000;
        this.evenements.push({ t_s: Math.round(c.t * 1000) / 1000, ms: Math.round(c.ecart * 10000) / 10, trames });
        if (this.evenements.length > 500) this.evenements.shift();
      }
      this.rRef = r;
      this.candidat = null;
    } else {
      this.candidat = null;
      if (ecart > 0.5 * duree) this.candidat = { ecart, t: this.n / this.sr };
      else this.rRef += 0.02 * ecart;
    }
    this.n += n;
  }

  resume() {
    return { trames_perdues: this.perdues, trames_perdues_ms: Math.round(this.ms * 10) / 10 };
  }
}

// Simulation de la file de lecture (banc, sans navigateur). Une trame de `trameMs` arrive toutes les `trameMs`.
//   decouplee false : le Worker du moteur lit lui-même dans la file du navigateur (bornée à `tampon`, les plus anciennes jetées).
//   decouplee true  : un lecteur léger vide la file à l'arrivée de chaque trame et la passe au moteur (file non bornée, retard borné par Retard).
// Le moteur met `coutMs` par trame, et `calculMs` de plus toutes les `periodeS` secondes (un calcul qui dure).
// Rend { trames, livrees, perdues, retardMaxMs, fileMax, perduesVues } ; `perduesVues` est ce que CompteurTrames compte
// sur les dates des trames livrées (doit égaler `perdues`).
export function simulerLecture({
  dureeS = 60, trameMs = 10, tampon = TRAMES_TAMPON_DEFAUT, decouplee = false,
  coutMs = 0.2, calculMs = 0, periodeS = 1, sr = 48000,
} = {}) {
  const total = Math.floor(dureeS * 1000 / trameMs);
  const nEch = Math.round(sr * trameMs / 1000);
  const parPeriode = Math.max(1, Math.round(periodeS * 1000 / trameMs));
  const retard = new Retard();
  const compteur = new CompteurTrames(sr, 0);   // le banc n'a pas de démarrage de périphérique
  const file = [];                  // indices de trames en attente
  let prochaine = 0;                // prochaine trame à arriver
  let perdues = 0, livrees = 0, retardMax = 0, fileMax = 0;
  let c = 0;                        // l'instant (ms) où le moteur est libre
  const arriveeAvant = (t) => {
    while (prochaine < total && prochaine * trameMs <= t) {
      file.push(prochaine++);
      if (!decouplee) {
        // File du navigateur bornée : au-delà de `tampon`, la plus ancienne est jetée.
        while (file.length > tampon) { file.shift(); perdues++; }
      }
      if (file.length > fileMax) fileMax = file.length;
    }
  };
  while (livrees + perdues < total) {
    arriveeAvant(c);
    if (!file.length) { c = prochaine * trameMs; continue; }
    const k = file.shift();
    if (decouplee && !retard.garder(Math.max(c, k * trameMs) - k * trameMs)) { perdues++; continue; }
    // Date de la trame k pour le compteur : horloge du flux (les trames jetées laissent un trou).
    compteur.bloc(k * trameMs * 1000 + 1e6, nEch);
    const cout = coutMs + (k % parPeriode === 0 && k > 0 ? calculMs : 0);
    c = Math.max(c, k * trameMs) + cout;
    retardMax = Math.max(retardMax, c - k * trameMs);
    livrees++;
  }
  // Une dernière trame livrée confirme un éventuel palier en attente : le banc finit par un bloc de plus (sans effet sur les comptes).
  return { trames: total, livrees, perdues, retardMaxMs: Math.round(retardMax * 10) / 10, fileMax, perduesVues: compteur.perdues };
}
