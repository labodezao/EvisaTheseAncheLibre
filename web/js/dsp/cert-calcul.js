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

// Exécutant simulé sur l'horloge du son. UN SEUL cœur de calcul, comme le Worker dédié (cert-worker.js : un fil, des tranches de 10 ms), les sentinelles passent devant un ajustement principal
// et le PRÉEMPTENT (le temps d'une sentinelle est pris sur le cœur : l'ajustement principal en cours finit plus tard). v68 (audit n° 4, H2) : jusqu'à la v67 deux voies tournaient en parallèle
// (une pour les sentinelles, une pour les ajustements : deux cœurs), ce qui cachait le coût des sentinelles ; `voies: 2` rend l'ancien comportement (comparaison avec les chiffres des audits 3 et 4).
//   msParUnite : durée d'une unité de coût sur la machine mesurée (0,26 ms sur le PC de l'audit, banc etalon_cout) ; facteurCpu : machine plus lente (4 : un portable).
export class ExecutantSimule {
  constructor({ msParUnite = 0.26, facteurCpu = 1, voies = 1 } = {}) {
    this.msParUnite = msParUnite; this.facteurCpu = facteurCpu; this.voies = voies;
    this.file = new FileCalcul(); this.libreA = { principal: 0, sentinelle: 0 }; this.finis = [];
    this.stats = { travaux: 0, msTotal: 0, retardMax: 0, sentinelles: 0, msSentinelles: 0 };
    this.t = 0; this.actifs = [];        // un cœur : { id, cle, nls, duree, reste, sentinelle, tSoumis, commence }
  }
  soumettre(travail, tNow) {
    if (this.voies === 2) { this.file.ajouter({ ...travail, tSoumis: tNow }); this.avancer(tNow); return; }
    this.avancer(tNow);
    const genre = !!travail.sentinelle;
    // comme FileCalcul : une demande de même note et de même genre qui n'a pas commencé est remplacée
    this.actifs = this.actifs.filter((q) => !(q.cle === travail.cle && q.sentinelle === genre && !q.commence));
    const { nls, cout } = calculerTravail(travail);
    const duree = cout * this.msParUnite * this.facteurCpu / 1000;
    this.actifs.push({ id: travail.id, cle: travail.cle, nls, duree, reste: duree, sentinelle: genre, tSoumis: tNow, commence: false });
  }
  // Fait tourner le cœur jusqu'à l'instant tNow (horloge du son). Priorité aux sentinelles (la plus ancienne d'abord), puis aux ajustements dans l'ordre d'arrivée.
  avancer(tNow) {
    if (this.voies === 2) return this.avancer2(tNow);
    let t = this.t;
    while (t < tNow - 1e-12) {
      const prets = this.actifs.filter((q) => q.tSoumis <= t + 1e-12);
      if (!prets.length) { t = Math.min(tNow, ...this.actifs.map((q) => q.tSoumis)); continue; }
      const cour = prets.filter((q) => q.sentinelle).sort((a, b) => a.tSoumis - b.tSoumis)[0] ?? prets.sort((a, b) => a.tSoumis - b.tSoumis)[0];
      cour.commence = true;
      const dt = Math.min(cour.reste, tNow - t);
      cour.reste -= dt; t += dt;
      if (cour.reste <= 1e-12) {
        this.actifs.splice(this.actifs.indexOf(cour), 1);
        this.stats.travaux++; this.stats.msTotal += cour.duree * 1000; this.stats.retardMax = Math.max(this.stats.retardMax, t - cour.tSoumis);
        if (cour.sentinelle) { this.stats.sentinelles++; this.stats.msSentinelles += cour.duree * 1000; }
        this.finis.push({ id: cour.id, cle: cour.cle, nls: cour.nls, ms: cour.duree * 1000, tFin: t });
      }
    }
    this.t = Math.max(this.t, tNow);
  }
  // Ancien comportement (v66, v67) : deux voies indépendantes, sentinelles et ajustements ne se gênent pas.
  avancer2(tNow) {
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
        this.stats.travaux++; if (voie === 'sentinelle') { this.stats.sentinelles++; this.stats.msSentinelles += duree * 1000; }
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
