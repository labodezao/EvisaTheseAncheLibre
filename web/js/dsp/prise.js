// Contrôle de la prise de son, en continu, dans le Worker (Ewen, 14/10/2026 :
// « un accordeur professionnel doit garantir que la prise de son est fiable, et
// le dire »). Il ne regarde que les échantillons reçus (et, si le navigateur les
// donne, les dates des blocs) : jamais la musique. Chaque détecteur cherche la
// SIGNATURE d'un défaut de la chaîne, pas un réglage propre à un micro.
//
// Pourquoi (J:\claude\tmp\accordeur_session_2026-10-14\diagnostic.md) : l'accordeur
// avait capté un micro USB générique au lieu du Zoom H6, avec l'effet vocal de
// Windows (suppression de bruit) : plages de zéros exacts dans les pauses (1629 de
// 1 ms et plus en 2 min, jusqu'à 23 ms), plancher de bruit à -88 dBFS contre -70
// à -84 pour le H6 (le bruit du soufflet), amplitudes relatives des partiels
// instables, ronflement du secteur à 50 Hz.
//
// Les alertes (codes) :
//   gate     suppresseur de bruit / porte : plages de zéros exacts de 1 à 250 ms, ou
//            plancher de bruit coupé net dans les pauses ;
//   pompage  traitement dynamique (compresseur, gain automatique) : la raie du secteur, qui
//            a une amplitude vraie constante, suit le niveau du son (gain qui baisse quand il monte).
//            Seulement quand le ronflement est là : sans lui, rien dans le signal ne sert de
//            référence (le fond de soufflet monte et descend tout seul : 12 à 23 dB dans les
//            prises du H6, mesuré), le contrôle ne dit alors rien du pompage ;
//   trous    blocs perdus ou doublés : la date du flux s'écarte du compte d'échantillons ;
//   ecretage échantillons collés au maximum ;
//   secteur  ronflement du secteur (raies à 50 ou 60 Hz et leurs harmoniques) ;
//   lent     fréquence d'échantillonnage de 8 à 16 kHz (téléphone, Bluetooth « mains libres »).
// Les seuils sont fixés sur des sons de synthèse (test/prise.test.mjs, banc) ; les
// prises réelles servent à valider, pas à régler (règle d'or de CLAUDE.md).
//
// Module pur, sans DOM : tourne dans le Worker (worker.js) et sous Node.

import { affinerSecteur } from './secteur.js';
import { HorlogeFlux } from './horloge-flux.js';

export const SEUILS = Object.freeze({
  chauffe_s: 1.0,           // rien n'est jugé pendant la première seconde (démarrage du flux)
  // gate : zéros exacts
  zeroMin_s: 0.001,         // plage de zéros d'au moins 1 ms ...
  zeroMax_s: 0.25,          // ... et d'au plus 250 ms (au-delà : micro coupé, pas une porte)
  gateFenetre_s: 30,
  gateEvents: 5,            // 5 plages en 30 s
  gateZeroPart: 0.6,        // ... dans un bloc de 100 ms dont les zéros ne font pas plus de 60 % (sinon : plancher sous la quantification, pas une porte)
  gateVoisinDb: -60,        // v69 (I4a) : ... et dont le bloc, le précédent ou le suivant dépasse ce niveau (dBFS, 100 ms) : une porte ferme sur un son ; un convertisseur de 16 bits dans une pièce calme (bruit sous 1 LSB) fait des plages de zéros partout (prise H6 en 16 bits : 65 s douteuses sur 211 avant, CERTIFICAT.md § 0C)
  // gate : plancher coupé net
  palierHaut: -80,          // dBFS : le niveau d'avant (une pause, entre -80 ...
  palierPause: -58,         // ... et -58 dBFS, depuis 3 blocs) ...
  palierBas: -84,           // ... et celui d'après
  palierSaut: 9,            // dB perdus en un seul bloc de 100 ms
  palierPlat: 2.5,          // dB : le plancher reste plat ensuite (3 blocs)
  palierEvents: 4,          // 4 coupures en 60 s
  palierFenetre_s: 60,
  // pompage : la raie du secteur, d'amplitude vraie constante, suit le niveau du son
  pompageEcart: 2,          // dB d'écart type de la raie d'une fenêtre à l'autre ...
  pompageCorr: -0.6,        // ... et corrélation avec le niveau de la fenêtre (le gain baisse quand le son monte)
  pompageMin: 8,            // fenêtres de ronflement qu'il faut pour juger
  // trous
  trouMs: 5,                // écart date / échantillons
  trouChauffe_s: 5,         // les 5 premières secondes : un saut de date est le démarrage du périphérique (v62, Ewen : 870 ms au lancement), pas une perte ; le compteur repart de la nouvelle date
  trouTenue_s: 15,
  trouAlerteMs: 400,        // Ewen, 19/10/2026 : un trou de moins de 0,4 s est seulement journalisé (CSV, JSON), sans alerte ni verdict bloqué ; seule la fenêtre qui le contient est écartée
  // v71 (F1, drapeau TROUS_COURTS, `cfg.trousCourts`) : un trou de quelques ms à 0,4 s ne fausse pas la mesure (session du 19/10 : erreur médiane 0,06 ¢ pour les images dont la
  // fenêtre contient un trou, 0,18 ¢ pour les autres). Il n'y a alors plus d'alerte « trous » ni de « prise douteuse » : seule l'IMAGE dont la fenêtre contient le trou n'a pas de verdict
  // (`ecartee`, pendant `trouGel_s`), sans rien afficher. Jusqu'à `trouCourt_ms` le trou est seulement journalisé (CSV, JSON) ; au-delà, un repère discret (`repere`, `trouRepere_s`).
  trousCourts: true,
  trouCourt_ms: 400,        // un trou de cette durée au plus est « court » : journalisé, rien à l'écran
  trouGel_s: 7,             // durée pendant laquelle la fenêtre de lecture contient le trou : la plus longue fenêtre du certificat (FEN_ENTIER_MAX_S 6,5 s) + 0,5 s. Plan d'expériences (3 plans, docs/PRISE-DE-SON.md) : après un trou, le moteur ne rend le même « sûr » que sans trou qu'au bout de 5,5 à 6,5 s ; 4,5 s laissait 15 à 27 images de « sûr » perdues sans raison visible
  trouRepere_s: 10,         // le repère discret d'un trou long reste affiché ce temps
  // écrêtage
  ecreteNiveau: 0.985,
  ecreteSuite: 3,           // 3 échantillons d'affilée au maximum
  ecreteEvents: 5,
  ecreteFenetre_s: 10,
  // secteur
  secteurFenetre_s: 2,
  secteurRatioDb: 15,       // la raie dépasse ses voisines de 15 dB ...
  secteurHarmDb: 8,         // ... et une de ses harmoniques de 8 dB
  secteurAbsDb: -85,        // dBFS (crête) : une raie plus faible n'est qu'un bruit de convertisseur
  secteurFenetres: 10,      // 10 fenêtres de 2 s gardées
  secteurMin: 6,
  secteurPart: 0.7,
  // échelle (v69, I4b) : la raie du secteur (50 ou 60 Hz, ±0,1 % en régime normal, médiane de ses fenêtres de 2 s sur 60 s) est une référence de fréquence EXTERNE à l'instrument.
  // Une prise rééchantillonnée ou transposée par un traitement audio (prise PC du 14/10 : +5 ¢) la déplace de la même échelle.
  echelleFenetre_s: 90,     // médiane des fréquences affinées du secteur sur les 90 dernières secondes ...
  echelleMin: 25,           // ... au moins 25 fenêtres de 2 s où la raie est présente (50 s de ronflement) : sinon rien n'est dit
  echelleAlerte: 0.002,     // |f / f_nominale − 1| > 2 ‰ (3,5 ¢) : alerte `echelle`, prise douteuse
  echelleAvert: 0.001,      // entre 1 et 2 ‰ : avertissement sans refus
  // lent
  srLent: 16000,
  // durée de maintien d'une alerte après la dernière preuve
  tenue_s: 30,
});

// Les alertes qui rendent une mesure douteuse (toutes ; le ronflement seulement
// quand il est détecté, c'est-à-dire fort : ratio et niveau ci-dessus).
export const CODES = Object.freeze(['gate', 'pompage', 'trous', 'ecretage', 'secteur', 'echelle', 'lent', 'bluetooth']);

const BLOC_S = 0.1;   // niveau par blocs de 100 ms

export class ControlePrise {
  constructor(sr, seuils = {}) {
    this.sr = sr;
    this.s = { ...SEUILS, ...seuils };
    this.n = 0;                 // échantillons reçus (hors pause du contrôle)
    this.muet = false;
    // zéros exacts
    this.zeros = 0;
    this.evGate = [];           // temps (s) des plages de zéros
    this.zerosVus = 0;          // pour le rapport : toutes les plages
    this.pend = [];             // plages de zéros finies dans le bloc de 100 ms en cours
    this.attente = [];          // v69 : plages du bloc précédent, jugées quand on connaît le niveau du bloc suivant (gateVoisinDb)
    this.lvAvant = -200; this.lvPrec = -200;
    this.bz = 0;                // zéros dans ce bloc
    this.zeroMax = 0;           // la plus longue vue (s)
    // niveau par blocs
    this.bn = 0; this.bsom = 0; this.B = Math.max(1, Math.round(sr * BLOC_S));
    this.niv = [];              // derniers niveaux (dBFS), 8 blocs
    this.evPalier = [];
    // écrêtage
    this.suiteCrete = 0; this.enCrete = false; this.evEcrete = [];
    // trous
    this.ts0 = null; this.cum = 0; this.rRef = 0; this.candidat = null; this.demarrageMs = null; this.trous = []; this.dernierTrou = -1e9; this.dernierTrouLong = -1e9; this.ecarteJusqua = -1e9;
    this.tsDernier = null; this.cumDernier = 0;
    this.horloge = new HorlogeFlux(sr);   // lot F2 (c) : dérive de l'horloge du micro, hors trous
    // secteur
    this.tamponS = new Float32Array(Math.round(sr * this.s.secteurFenetre_s));
    this.remplis = 0;
    this.fenetresS = [];        // 1 par fenêtre : { hit, ratio, abs, base }
    this.dernierSecteur = null;
    this.hann = null;
    // états, épisodes
    this.actifs = new Map();    // code -> { depuis, dernier, n, detail }
    this.episodes = [];         // { code, debut_s, fin_s, n, detail }
    // retrait du ronflement (v62, dsp/secteur.js) : le contrôle regarde le signal BRUT (alimenter) et le signal retiré (alimenterNet)
    this.retireSecteur = true;      // réglage : retirer le ronflement quand il est détecté
    this.secteurOn = false;         // l'annuleur travaille (le Worker l'a réglé)
    this.tActif = 0;
    this.tamponN = new Float32Array(this.tamponS.length);
    this.remplisN = 0;
    this.fenetresN = [];
    this.secteurF0 = null; this.secteurH = 0; this.secteurNouveau = false;
    this.evHz = [];             // v69 : [temps, f affinée / f nominale] de chaque fenêtre de ronflement (échelle de la prise)
    this.infos = [];
    this.externes = new Map();  // défauts connus de la page, pas du signal : un micro Bluetooth (prise-micro.js)
    this.dernierEtat = null;
  }

  // La page sait quelque chose du micro que le signal ne dit pas (son nom : « Hands-Free »).
  declarer(code, detail = {}) { this.externes.set(code, detail); }
  retirer(code) { this.externes.delete(code); }

  get temps() { return this.n / this.sr; }

  // Mesure coupée (annonce vocale, son de référence : le flux donne des zéros
  // voulus) : rien n'est jugé, les suites de zéros et de niveaux repartent.
  suspendre(oui) {
    this.muet = !!oui;
    this.zeros = 0; this.suiteCrete = 0; this.niv.length = 0; this.pend.length = 0; this.attente.length = 0; this.lvAvant = this.lvPrec = -200; this.bz = 0;
    this.bn = 0; this.bsom = 0;
    this.remplis = 0;
    this.ts0 = null; this.candidat = null;   // la date du flux repart : la coupure n est pas un trou
    this.horloge.coupure();
  }

  // Un bloc d'échantillons (la suite exacte du flux, sans trou).
  alimenter(x) {
    if (this.muet) { this.n += x.length; return; }   // le temps avance (même horloge que le moteur), rien n'est jugé
    const s = this.s, sr = this.sr, B = this.B;
    const zMin = Math.round(s.zeroMin_s * sr), zMax = Math.round(s.zeroMax_s * sr);
    const lim = s.ecreteNiveau;
    for (let i = 0; i < x.length; i++) {
      const v = x[i];
      const a = v < 0 ? -v : v;
      this.n++;
      // zéros exacts
      if (v === 0) { this.zeros++; this.bz++; }
      else {
        if (this.zeros >= zMin && this.zeros <= zMax && this.temps > s.chauffe_s) {
          this.pend.push(this.temps, this.zeros / sr);
        }
        this.zeros = 0;
      }
      // écrêtage
      if (a >= lim) {
        if (++this.suiteCrete === s.ecreteSuite && this.temps > s.chauffe_s) this.evEcrete.push(this.temps);
      } else this.suiteCrete = 0;
      // niveau par blocs
      this.bsom += v * v;
      if (++this.bn === B) {
        const lvl = 10 * Math.log10(this.bsom / B + 1e-20);
        this.niveau(lvl);
        // Les plages de zéros d'un bloc comptent si les zéros n'en sont pas la plus grande partie (sinon le plancher est sous la quantification,
        // pas une porte) ET si un son l'entoure (le bloc d'avant, le sien ou le suivant dépasse gateVoisinDb : v69, I4a).
        if (this.attente.length && Math.max(this.lvAvant, this.lvPrec, lvl) > s.gateVoisinDb) {
          for (let k = 0; k < this.attente.length; k += 2) {
            this.evGate.push(this.attente[k]);
            this.zerosVus++;
            if (this.attente[k + 1] > this.zeroMax) this.zeroMax = this.attente[k + 1];
          }
        }
        this.attente.length = 0;
        if (this.pend.length && this.bz / B < s.gateZeroPart) for (const v of this.pend) this.attente.push(v);
        this.lvAvant = this.lvPrec; this.lvPrec = lvl;
        this.pend.length = 0; this.bz = 0;
        this.bn = 0; this.bsom = 0;
      }
      // tampon du secteur
      if (this.remplis < this.tamponS.length) this.tamponS[this.remplis++] = v;
    }
    if (this.remplis === this.tamponS.length) {
      this.jugerSecteur();
      this.remplis = 0;
    }
  }

  // Niveau d'un bloc de 100 ms : coupure nette du plancher.
  niveau(db) {
    const s = this.s, t = this.temps;
    const L = this.niv;
    L.push(db);
    if (L.length > 8) L.shift();
    if (t <= s.chauffe_s) return;
    // plancher coupé net : un saut vers le bas de 9 dB et plus d'un bloc à l'autre, de
    // -78 dBFS ou plus haut à -84 ou plus bas, puis 3 blocs plats
    const m = L.length;
    if (m >= 8) {
      const av = L[m - 5], ap = L[m - 4];
      // le plancher d'avant est celui d'une pause (le bruit du soufflet, -80 à -58 dBFS) depuis 3 blocs : la fin
      // d'une note qui tombe au bruit de fond n'est pas une coupure
      const pause = [L[m - 7], L[m - 6], av].every((v) => v >= s.palierHaut && v <= s.palierPause);
      if (pause && ap <= s.palierBas && av - ap >= s.palierSaut) {
        const plat = [L[m - 3], L[m - 2], L[m - 1]].every((v) => Math.abs(v - ap) <= s.palierPlat);
        if (plat) this.evPalier.push(t - 0.4);
      }
    }
  }

  // Les dates du flux (microsecondes) face au compte d'échantillons.
  // `ts` : AudioData.timestamp, `n` : numberOfFrames.
  // `retardMs` : le temps que le Worker lui-même vient de mettre à traiter un bloc (s'il est du même ordre que le
  // saut, c'est le calcul qui n'a pas suivi, pas le micro : cause « retard »).
  bloc(ts, n, retardMs = 0) {
    if (this.muet || !Number.isFinite(ts)) return;
    this.horloge.bloc(ts, this.ts0 === null ? 0 : this.cum, n);
    if (this.ts0 === null) {
      this.ts0 = ts; this.cum = 0; this.rRef = 0; this.tsDernier = ts; this.cumDernier = 0;
    } else {
      const r = (ts - this.ts0) / 1e6 - this.cum / this.sr;
      const ecart = r - this.rRef;
      const ms = ecart * 1000;
      // Un vrai trou décale TOUTES les dates suivantes (un palier) ; une date qui tremble (gigue de la
      // capture) ne dépasse le seuil que sur un bloc. Le trou n'est donc retenu qu'au bloc suivant.
      const c = this.candidat;
      if (c && Math.abs(ms) > 0.6 * this.s.trouMs && Math.sign(ms) === Math.sign(c.ms)) {
        const trou = { t_s: c.t, ms: Math.round(c.ms * 10) / 10, cause: Math.abs(c.ms) <= 1.5 * (c.retard || 0) + 20 ? 'retard' : 'flux' };
        if (this.s.trousCourts) {
          trou.court = Math.abs(c.ms) <= this.s.trouCourt_ms;      // v71 (F1) : journalisé dans tous les cas, affiché seulement au-delà de trouCourt_ms
          if (!trou.court) this.dernierTrouLong = this.temps;
          this.ecarteJusqua = Math.max(this.ecarteJusqua, this.temps + this.s.trouGel_s);
        }
        this.trous.push(trou);
        if (this.trous.length > 500) this.trous.shift();
        if (Math.abs(c.ms) > this.s.trouAlerteMs) this.dernierTrou = this.temps;   // l'alerte (prise douteuse) : seulement au-delà de trouAlerteMs
        this.rRef = r;
        this.candidat = null;
      } else {
        this.candidat = null;
        if (Math.abs(ms) > this.s.trouMs && this.temps <= this.s.trouChauffe_s) {
          // Démarrage : la date du flux se cale. On repart de cette date, sans compter de trou.
          this.demarrageMs = Math.round(ms);
          this.rRef = r;
        } else if (Math.abs(ms) > this.s.trouMs) this.candidat = { ms, t: this.temps, retard: retardMs };
        else this.rRef += 0.02 * ecart;   // l'horloge du micro dérive lentement (100 à 150 ppm) : on la suit
      }
      this.tsDernier = ts; this.cumDernier = this.cum;
    }
    this.cum += n;
  }

  // Dérive de l'horloge du micro face à celle du navigateur (ppm), sur toute la prise.
  deriveHorloge() {
    return this.horloge.lire().ppm;
  }

  // Le signal APRÈS le retrait du ronflement : sert à dire si le ronflement est parti.
  alimenterNet(x) {
    if (this.muet || !this.secteurOn) return;
    for (let i = 0; i < x.length; i++) {
      this.tamponN[this.remplisN++] = x[i];
      if (this.remplisN === this.tamponN.length) { this.jugerSecteur(this.tamponN, this.fenetresN, false); this.remplisN = 0; }
    }
  }

  // Le Worker doit-il (re)régler l'annuleur ? Deux fenêtres de ronflement de suite le déclenchent ; chaque nouvelle
  // fenêtre rend la fréquence affinée du secteur et les harmoniques à retirer (une seule fois par fenêtre).
  demandeSecteur() {
    if (!this.retireSecteur || !this.secteurNouveau) return null;
    const f = this.fenetresS;
    if (f.length < 2 || !f[f.length - 1].hit || !f[f.length - 2].hit || !this.secteurF0) return null;
    this.secteurNouveau = false;
    return { f0: this.secteurF0, harmoniques: this.secteurH };
  }

  // L'annuleur travaille (true) ou s'est arrêté.
  secteurActif(on) {
    if (on && !this.secteurOn) { this.tActif = this.temps; this.fenetresN = []; this.remplisN = 0; }
    this.secteurOn = !!on;
    if (!on) this.infos = [];
  }

  // Ronflement du secteur : raies à 50 (ou 60) Hz et à leurs harmoniques 2 et 3,
  // face à leurs voisines à ±4 et ±6 Hz, sur une fenêtre de 2 s (case de 0,5 Hz).
  jugerSecteur(tampon = this.tamponS, liste = this.fenetresS, brut = true) {
    const s = this.s, sr = this.sr, N = tampon.length;
    if (!this.hann) {
      this.hann = new Float32Array(N);
      for (let i = 0; i < N; i++) this.hann[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N);
    }
    if (this.temps <= s.chauffe_s) return;
    const x = tampon, h = this.hann;
    const puissance = (f) => {
      if (f >= sr / 2 - 10) return 0;
      const w = 2 * Math.PI * f / sr, c = 2 * Math.cos(w);
      let s1 = 0, s2 = 0;
      for (let i = 0; i < N; i++) { const v = x[i] * h[i] + c * s1 - s2; s2 = s1; s1 = v; }
      const re = s1 - s2 * Math.cos(w), im = s2 * Math.sin(w);
      return (re * re + im * im) * 4 / (N * N);   // amplitude de crête au carré (fenêtre de Hann : somme N/2)
    };
    const db = (p) => 10 * Math.log10(p + 1e-20);
    let meilleur = null;
    for (const base of [50, 60]) {
      const r = [];
      for (let k = 1; k <= 3; k++) {
        const f = base * k;
        const p = puissance(f);
        const v = (puissance(f - 6) + puissance(f - 4) + puissance(f + 4) + puissance(f + 6)) / 4;
        r.push({ f, ratio: db(p) - db(v), abs: db(p) });   // abs : crête en dBFS (dB de l'amplitude au carré)
      }
      const [a, b, c] = r;
      const hit = a.ratio >= s.secteurRatioDb && a.abs >= s.secteurAbsDb && Math.max(b.ratio, c.ratio) >= s.secteurHarmDb;
      const cand = { hit, base, ratio: a.ratio, abs: a.abs, harm: Math.max(b.ratio, c.ratio) };
      if (!meilleur || (hit && !meilleur.hit) || (hit === meilleur.hit && cand.ratio > meilleur.ratio)) meilleur = cand;
    }
    let somme = 0;
    for (let i = 0; i < N; i++) somme += x[i] * x[i];
    meilleur.niveau = db(somme / N);
    meilleur.t = this.temps;
    if (brut) this.dernierSecteur = meilleur;
    liste.push(meilleur);
    if (liste.length > s.secteurFenetres) liste.shift();
    if (brut && meilleur.hit) {
      // v69 (I4b) : la fréquence réelle du secteur, fenêtre par fenêtre, sert aussi de référence d'échelle (alerte `echelle`), que le ronflement soit retiré ou non
      const fa = affinerSecteur(x, sr, meilleur.base);
      this.baseSecteur = meilleur.base;
      this.evHz.push(this.temps, fa / meilleur.base);
      while (this.evHz.length && this.evHz[0] < this.temps - s.echelleFenetre_s) this.evHz.splice(0, 2);
    }
    if (brut && meilleur.hit && this.retireSecteur) {
      // Fréquence réelle du secteur (à 0,01 Hz) et harmoniques qui dépassent leurs voisines de 8 dB : celles-là sont retirées.
      const f0 = affinerSecteur(x, sr, meilleur.base);
      this.secteurF0 = this.secteurF0 && Math.abs(this.secteurF0 - f0) < 0.15 ? Math.round((0.5 * this.secteurF0 + 0.5 * f0) * 100) / 100 : f0;
      let hmax = 1;
      for (let k = 2; k <= 16 && k * this.secteurF0 < Math.min(1500, sr / 2 - 20); k++) {
        const f = k * this.secteurF0;
        const p = puissance(f);
        const v = (puissance(f - 6) + puissance(f - 4) + puissance(f + 4) + puissance(f + 6)) / 4;
        if (db(p) - db(v) >= 8 && db(p) / 2 >= -110) hmax = k;
      }
      this.secteurH = hmax;
      this.secteurNouveau = true;
    }
  }

  // ---- État ----
  // Preuve la plus récente et nombre de preuves dans la fenêtre, par code.
  preuves() {
    const s = this.s, t = this.temps;
    const dans = (ev, fen) => { while (ev.length && ev[0] < t - fen) ev.shift(); return ev; };
    const out = {};
    const gate = dans(this.evGate, s.gateFenetre_s);
    const palier = dans(this.evPalier, s.palierFenetre_s);
    const zerosOk = gate.length >= s.gateEvents;
    if (zerosOk || palier.length >= s.palierEvents) {
      const ev = zerosOk ? gate : palier;
      out.gate = { premiere: ev[0], derniere: ev[ev.length - 1], n: gate.length + palier.length,
        detail: { zeros: gate.length, coupures: palier.length, plusLongue_ms: Math.round(this.zeroMax * 10000) / 10 } };
    }
    if (!s.trousCourts && this.trous.length && t - this.dernierTrou <= s.trouTenue_s) {
      out.trous = { premiere: this.dernierTrou, derniere: this.dernierTrou, n: this.trous.length,
        detail: { dernier_ms: this.trous[this.trous.length - 1].ms, dernier_t_s: Math.round(this.trous[this.trous.length - 1].t_s * 10) / 10,
          cause: this.trous[this.trous.length - 1].cause, total: this.trous.length } };
    }
    const crete = dans(this.evEcrete, s.ecreteFenetre_s);
    if (crete.length >= s.ecreteEvents) out.ecretage = { premiere: crete[0], derniere: crete[crete.length - 1], n: crete.length, detail: {} };
    if (this.fenetresS.length >= s.secteurMin) {
      const hits = this.fenetresS.filter((f) => f.hit);
      if (hits.length / this.fenetresS.length >= s.secteurPart) {
        const d = hits[hits.length - 1];
        out.secteur = { premiere: hits[0].t, derniere: d.t, n: hits.length,
          detail: { hz: d.base, ratio_db: Math.round(d.ratio * 10) / 10, crete_dbfs: Math.round(d.abs * 10) / 10 } };
      }
    }
    if (out.secteur) {
      const h = this.fenetresS.filter((f) => f.hit);
      if (h.length >= s.pompageMin) {
        const a = h.map((f) => f.abs), l = h.map((f) => f.niveau);
        const m = (v) => v.reduce((x, y) => x + y, 0) / v.length;
        const ma = m(a), ml = m(l);
        let saa = 0, sll = 0, sal = 0;
        for (let i = 0; i < a.length; i++) { saa += (a[i] - ma) ** 2; sll += (l[i] - ml) ** 2; sal += (a[i] - ma) * (l[i] - ml); }
        const ecart = Math.sqrt(saa / a.length), corr = saa > 0 && sll > 0 ? sal / Math.sqrt(saa * sll) : 0;
        if (ecart >= s.pompageEcart && corr <= s.pompageCorr) {
          out.pompage = { premiere: h[0].t, derniere: h[h.length - 1].t, n: h.length,
            detail: { ecart_db: Math.round(ecart * 10) / 10, correlation: Math.round(corr * 100) / 100 } };
        }
      }
    }
    // v69 (I4b) : l'échelle de la prise, d'après la fréquence moyenne du secteur
    this.echelle = null;
    {
      const n = this.evHz.length / 2;
      if (n >= s.echelleMin) {
        const v = []; for (let i = 1; i < this.evHz.length; i += 2) v.push(this.evHz[i]);
        v.sort((p, q) => p - q);
        const e = v[v.length >> 1], ecart = e - 1, cents = 1200 * Math.log2(e);      // la médiane : une fenêtre où une note accroche la recherche (49,80 Hz au lieu de 50,15) ne compte pas
        this.echelle = { e, cents, n };
        if (Math.abs(ecart) > s.echelleAlerte) out.echelle = { premiere: this.evHz[0], derniere: this.evHz[this.evHz.length - 2], n, detail: { cents: Math.round(cents * 10) / 10, hz: Math.round(e * (this.baseSecteur ?? 50) * 100) / 100, ecart_pour_mille: Math.round(ecart * 10000) / 10 } };
      }
    }
    for (const [code, detail] of this.externes) out[code] = { premiere: 0, derniere: t, n: 1, detail };
    // Ronflement retiré : ce n'est plus une alerte mais une information, tant que ce qui reste est faible.
    this.infos = [];
    if (this.echelle && !out.echelle && Math.abs(this.echelle.e - 1) > s.echelleAvert) this.infos.push({ code: 'echelleAvert', detail: { cents: Math.round(this.echelle.cents * 10) / 10 } });
    if (out.secteur && this.secteurOn) {
      const nets = this.fenetresN.filter((f) => f.t > this.tActif + 8);
      const dernier = this.fenetresN[this.fenetresN.length - 1];
      const encore = nets.length >= 4 && nets.filter((f) => f.hit).length / nets.length >= s.secteurPart;
      const info = { hz: out.secteur.detail.hz, avant_db: out.secteur.detail.ratio_db, apres_db: dernier ? Math.round(dernier.ratio * 10) / 10 : null, f0: this.secteurF0, harmoniques: this.secteurH };
      if (encore) out.secteur.detail.trop_fort = true;
      else { this.infos = [{ code: 'secteurRetire', detail: info }]; delete out.secteur; }
    }
    if (this.sr <= s.srLent && this.n > 0) out.lent = { premiere: 0, derniere: t, n: 1, detail: { sr: this.sr } };
    return out;
  }

  // { douteuse, codes, alertes: [{ code, depuis_s, n, detail }] }. L'alerte reste
  // `tenue_s` après sa dernière preuve (SEUILS.tenue_s), sauf les trous (15 s).
  etat() {
    const t = this.temps, s = this.s;
    const p = this.preuves();
    for (const [code, e] of Object.entries(p)) {
      const a = this.actifs.get(code);
      if (a) { a.dernier = e.derniere; a.n = e.n; a.detail = e.detail; a.vue = t; }
      else {
        this.actifs.set(code, { depuis: e.premiere, dernier: e.derniere, n: e.n, detail: e.detail, vue: t });
        this.episodes.push({ code, debut_s: e.premiere, fin_s: null, n: e.n, detail: e.detail });
      }
    }
    for (const [code, a] of [...this.actifs]) {
      if (!p[code] && t - a.vue > (code === 'trous' ? 0 : s.tenue_s)) {
        this.actifs.delete(code);
        for (let i = this.episodes.length - 1; i >= 0; i--) {
          if (this.episodes[i].code === code && this.episodes[i].fin_s === null) {
            this.episodes[i].fin_s = a.vue; this.episodes[i].n = a.n; this.episodes[i].detail = a.detail;
            break;
          }
        }
      }
    }
    for (const ep of this.episodes) {
      const a = this.actifs.get(ep.code);
      if (a && ep.fin_s === null) { ep.n = a.n; ep.detail = a.detail; }
    }
    const alertes = [...this.actifs].map(([code, a]) => ({ code, depuis_s: a.depuis, n: a.n, detail: a.detail }));
    const out = { douteuse: alertes.length > 0, codes: alertes.map((a) => a.code), alertes, infos: this.infos, t };
    if (s.trousCourts) {
      // v71 (F1) : l'image dont la fenêtre contient un trou n'a pas de verdict (sans « prise douteuse ») ; un trou long laisse un repère discret ; `trou` : la colonne du CSV.
      out.ecartee = t <= this.ecarteJusqua;
      out.repere = t - this.dernierTrouLong <= s.trouRepere_s;
      out.trou = out.repere ? 'long' : out.ecartee ? 'court' : '';
    }
    return out;
  }

  // Les épisodes pour le JSON de la session. `t0` : l'instant de la session dans
  // le temps du contrôle (s) ; les temps rendus sont ceux de la session.
  episodesSession(t0 = 0) {
    this.etat();
    return this.episodes.map((e) => ({
      code: e.code, debut_s: Math.max(0, Math.round((e.debut_s - t0) * 100) / 100),
      fin_s: e.fin_s == null ? null : Math.round((e.fin_s - t0) * 100) / 100, n: e.n, detail: e.detail,
    }));
  }

  // Les trous datés, pour le JSON.
  trousSession(t0 = 0) {
    return this.trous.map((x) => ({ t_s: Math.round((x.t_s - t0) * 1000) / 1000, ms: x.ms, ...(x.court !== undefined ? { court: x.court } : {}) }));
  }

  // Résumé chiffré de la prise (JSON de la session, tests).
  resume() {
    return {
      duree_s: Math.round(this.temps * 10) / 10,
      plages_de_zeros: this.zerosVus, plus_longue_plage_ms: Math.round(this.zeroMax * 10000) / 10,
      coupures_de_plancher: this.evPalier.length,
      derive_horloge_ppm: this.deriveHorloge(), derive_horloge_brute_ppm: this.horloge.lire().brut, saut_au_demarrage_ms: this.demarrageMs ?? null,
    };
  }
}
