// Calcul du certificat hors du moteur (v66, audit Fable final F4 : « le Worker est à 49 %, le certificat prend 80 % du tick, l'écran montre 93 à 100 % du temps la lecture brute »).
//
// Le moteur (engine.js) garde toute la logique du certificat (critères, C9, sentinelle, battement) ; seul l'AJUSTEMENT, le calcul lourd (350 ms à froid pour deux anches,
// 1 s pour trois), part dans un Worker dédié (cert-worker.js). Trois exécutants offrent la même interface :
//   soumettre(travail, tNow)   : met le travail dans la file ; un travail de même note et de même genre (principal | sentinelle) qui attend encore est REMPLACÉ (la file saute les demandes périmées) ;
//   recuperer(cle, tNow)       : les résultats finis de la note `cle` (liste de { id, cle, nls, ms } ou { id, cle, erreur }).
// - FileCalcul : la file et la boucle de calcul, sans Worker (testée sous Node) ; cert-worker.js la pilote dans le navigateur ;
// - ExecutantSimule : le même calcul sur une HORLOGE VIRTUELLE (celle du son), pour rejouer une prise « comme dans l'application » sans attendre le temps réel : un travail dure
//   (coût en unités × `msParUnite` × `facteurCpu`) ms de calcul sur un cœur à lui, et ne revient qu'après (bancs d'usage réel, temps de pose, perf ×4) ;
// - le moteur sans exécutant (cfg.certificat sans Worker) calcule en ligne par tranches (certificat.js, repli et bancs déterministes).
import { executerTravail } from './certificat.js';

// Exécute un travail jusqu'au bout, rend { nls, ms, cout } (cout : unités de coût, comme COUT_PAR_IMAGE).
export function calculerTravail(spec) {
  const t0 = typeof performance !== 'undefined' ? performance.now() : 0;
  const g = executerTravail(spec);
  let r, cout = 0;
  while (!(r = g.next()).done) cout += typeof r.value === 'number' ? r.value : 0.5;
  return { nls: r.value, ms: typeof performance !== 'undefined' ? performance.now() - t0 : 0, cout };
}

// La file : une demande par (note, genre) en attente, les sentinelles d'abord (courtes, elles décident de l'invalidation d'un certificat), puis les travaux principaux dans l'ordre d'arrivée.
export class FileCalcul {
  constructor() { this.attente = []; this.cours = null; }
  ajouter(travail) {
    const genre = !!travail.sentinelle;
    this.attente = this.attente.filter((t) => !(t.cle === travail.cle && !!t.sentinelle === genre));
    this.attente.push(travail);
  }
  oublier(cle) { this.attente = this.attente.filter((t) => t.cle !== cle); }
  // Le prochain travail à lancer (le retire de la file) ou null.
  suivant() {
    const i = this.attente.findIndex((t) => t.sentinelle);
    const k = i >= 0 ? i : 0;
    return this.attente.length ? this.attente.splice(k, 1)[0] : null;
  }
  get taille() { return this.attente.length; }
}

// Exécutant simulé sur l'horloge du son. Un seul cœur de calcul (comme le Worker dédié), sentinelles prioritaires.
//   msParUnite : durée d'une unité de coût sur la machine mesurée (0,26 ms sur le PC de l'audit, banc etalon_cout) ; facteurCpu : machine plus lente (4 : un portable).
export class ExecutantSimule {
  constructor({ msParUnite = 0.26, facteurCpu = 1 } = {}) {
    this.msParUnite = msParUnite; this.facteurCpu = facteurCpu;
    this.file = new FileCalcul(); this.libreA = { principal: 0, sentinelle: 0 }; this.finis = [];
    this.stats = { travaux: 0, msTotal: 0, retardMax: 0, sentinelles: 0 };
  }
  soumettre(travail, tNow) {
    this.file.ajouter({ ...travail, tSoumis: tNow });
    this.avancer(tNow);
  }
  // Fait tourner la file jusqu'à l'instant tNow (horloge du son) : tout travail qui démarre avant tNow est calculé (en vrai, tout de suite) et daté de sa fin virtuelle.
  // Deux voies : les sentinelles (courtes) ne font pas la queue derrière un ajustement principal, comme dans le Worker qui les intercale.
  avancer(tNow) {
    for (let encore = true; encore; ) {
      encore = false;
      for (const voie of ['sentinelle', 'principal']) {
        const cand = this.file.attente.filter((q) => !!q.sentinelle === (voie === 'sentinelle')).sort((a, b) => a.tSoumis - b.tSoumis)[0];
        if (!cand) continue;
        const debut = Math.max(this.libreA[voie], cand.tSoumis);
        if (debut > tNow) continue;
        this.file.attente.splice(this.file.attente.indexOf(cand), 1);
        const { nls, cout } = calculerTravail(cand);
        const duree = cout * this.msParUnite * this.facteurCpu / 1000;
        this.libreA[voie] = debut + duree;
        this.stats.travaux++; if (voie === 'sentinelle') this.stats.sentinelles++;
        this.stats.msTotal += duree * 1000; this.stats.retardMax = Math.max(this.stats.retardMax, this.libreA[voie] - cand.tSoumis);
        this.finis.push({ id: cand.id, cle: cand.cle, nls, ms: duree * 1000, tFin: this.libreA[voie] });
        encore = true;
      }
    }
  }
  recuperer(cle, tNow) {
    this.avancer(tNow);
    const prets = [], reste = [];
    for (const r of this.finis) (r.cle === cle && r.tFin <= tNow ? prets : reste).push(r);
    this.finis = reste;
    return prets;
  }
}

// L'exécutant du navigateur : un Worker dédié (cert-worker.js). `mort` : le Worker n'a pas pu démarrer ou a planté ; le moteur reprend alors le calcul en ligne.
export class ExecutantWorker {
  constructor() {
    this.finis = []; this.mort = false;
    this.w = new Worker(new URL('./cert-worker.js', import.meta.url), { type: 'module' });
    this.w.onmessage = (e) => { if (e.data?.type === 'resultat') this.finis.push(e.data); };
    this.w.onerror = () => { this.mort = true; };
  }
  soumettre(travail) { try { this.w.postMessage({ type: 'travail', travail }, [travail.x.buffer]); } catch { this.mort = true; } }
  oublier(cle) { try { this.w.postMessage({ type: 'oublier', cle }); } catch { /* sans effet */ } }
  recuperer(cle) {
    const prets = [], reste = [];
    for (const r of this.finis) (r.cle === cle ? prets : reste).push(r);
    this.finis = reste;
    return prets;
  }
  arreter() { try { this.w.terminate(); } catch { /* sans effet */ } }
}
