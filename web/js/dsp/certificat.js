// Certificat d'une lecture « sûre » (v63, audit Fable du 15/10/2026, R6, R8, R10, R11, R13, R14 ; docs/AUDIT-FABLE-ACCORDEUR.md).
//
// Un accordeur professionnel ne dit « sûr » que s'il peut le prouver. La v62 disait « sûr » à partir de la seule cohérence de sa propre
// lecture (la paire colle au battement, la note a duré assez) : 61 premières lectures « sûr » fausses de plus de 0,5 ¢ sur 134 notes posées
// du plan réaliste de l'audit, 100 % de fausses à 8 Hz et 12 ¢ (une anche hors de la bande du traqueur : la faible est lue pour la forte,
// une raie du peigne pour l'autre), 30 à 50 % de fausses au grave quand les anches se tirent (modulation de phase non modélisée).
//
// Ici une SECONDE LECTURE, indépendante : le son brut des dernières secondes (anneau du moteur) est ajusté par le modèle de deux anches à
// peigne de Bessel (nls-bessel.js), SANS regarder le traqueur (le moteur ne sert que de départ parmi d'autres), et la lecture n'est « sûre »
// que si TOUS les critères tiennent (audit § 3) :
//   C1 prise saine : ni plage de zéros ni trou dans la fenêtre lue (R11) — le reste de la prise (suppresseur, secteur…) est jugé par prise.js ;
//   C2 peigne sain (R10) : le son est celui de deux anches seules (résidu relatif du modèle, plancher entre les raies, partiels assez nets) ;
//      refuse l'intermodulation d'un micro traité, une raie étrangère forte, deux anches trop écartées ;
//   C3 résolution : K·Ω·T ≥ 1,5 (les raies des deux anches sont séparées au partiel le plus haut utilisé) ;
//   C4 étiquette : rapport de vraisemblance ≥ 25 entre la meilleure hypothèse et l'autre (l'anche faible n'est pas une raie latérale) ;
//   C6 stabilité : dérive ≤ 0,5 ¢/s et agitation ≤ 0,3 ¢ (une fenêtre qui contient la fin d'une attaque est refusée) ;
//   C8 accord : la lecture du moteur et la seconde lecture s'accordent à 0,3 ¢ près.
// Sinon l'écran dit pourquoi (R14) : la lecture reste affichée, « en cours », avec une marge de 1,5 ¢ qui interdit « juste » et la validation.
//
// Le calcul est réparti sur les images du moteur (générateur : `CERT.PAS_PAR_IMAGE` itérations par image de 85 ms).
import { lireBesselGen, NLS_LLR_SUR } from './nls-bessel.js';

export const CERT = {
  AGE_MIN_S: 1.3,            // la note doit durer au moins ça avant le premier contrôle
  DEBUT_S: 0.35,             // l'établissement de la note (premières 350 ms) n'est jamais dans la fenêtre
  FEN_MAX_S: 3,              // fenêtre lue au plus
  FEN_MIN_S: 0.9,
  REESSAI_S: 0.5,            // nouvelle tentative quand 0,5 s de son de plus est arrivé
  ESSAIS_MAX: 10,
  PAS_PAR_IMAGE: 20,         // itérations de Levenberg-Marquardt par image (bancs et tests : calcul déterministe)
  MS_PAR_IMAGE: null,        // si donné (l'application : 15 ms), c'est le temps qui borne le travail de chaque image, pas le nombre de pas
  ACCORD_C: 0.3,             // C8
  CONFIRME_C: 0.25,          // C9 : deux ajustements successifs (fenêtres décalées d'au moins 0,5 s) d'accord à ce point près
  LLR_MIN: NLS_LLR_SUR,      // C4
  KOT_MIN: 1.5,              // C3
  R_MAX: 0.05,               // C2 : résidu relatif du modèle (juste sans raie étrangère : 0,01 ; avec : jusqu'à 0,08 ; deux anches manquées : 0,085 et plus)
  PLANCHER_MAX_DB: -28,      // C2 : plancher hors modèle, partiels 1 et 2
  BETA_MAX: 0.45,            // C2 : indice de modulation de phase (au-delà : anches presque accrochées)
  DERIVE_MAX: 0.5,           // C6 : ¢/s
  AGIT_MAX: 2.5,             // C6 : ¢ (garde-fou seulement : sur les prises réelles le warp suit aussi la modulation au rythme du battement, 0,5 à 1,6 ¢)
  ZERO_MAX_S: 0.0004,        // C1 : plage de zéros exacts de plus de 0,4 ms
  MARGE_REFUS_C: 1.5,        // marge posée sur une lecture non certifiée
  TENUE_C: 0.25,              // le certificat tient tant que le moteur reste à ce point de lui
  OMEGA_MIN: 0.2,            // Hz : en dessous, pas de battement à lire
  OMEGA_MAX: 25,             // Hz : au-delà, hors domaine (anches « presque deux notes »)
};

// Raisons de refus : clés de langue (ui/langues) et ordre de gravité (la plus parlante d'abord).
export const RAISONS = ['trois', 'trous', 'peigne', 'resolution', 'etiquette', 'stabilite', 'accord', 'verification', 'domaine'];

// Jugement d'une seconde lecture. nls : sortie de lireBessel ; moteur : { f: [f8, f8+] } (Hz, calibrés) ; calib : facteur d'horloge.
// Rend { ok, raisons: [...] , detail }.
export function juger(nls, moteur, { calib = 1, zeros = false } = {}) {
  const raisons = [];
  const detail = {};
  if (zeros) raisons.push('trous');
  if (!nls || !nls.ok) { raisons.push('domaine'); return { ok: false, raisons, detail }; }
  const f = nls.f.map((v) => v * calib);
  const cents = (a, b) => 1200 * Math.log2(a / b);
  detail.accord = Math.max(Math.abs(cents(moteur.f[0], f[0])), Math.abs(cents(moteur.f[1], f[1])));
  detail.kot = nls.K * nls.Om * nls.T;
  detail.plancher = Math.max(...nls.plancherDb.slice(0, 2).map((v) => (v == null || Number.isNaN(v) ? 999 : v)));
  if (nls.Om < CERT.OMEGA_MIN || nls.Om > CERT.OMEGA_MAX) raisons.push('domaine');
  if (!(nls.r <= CERT.R_MAX) || !(detail.plancher <= CERT.PLANCHER_MAX_DB) || Math.max(...nls.b.map(Math.abs)) > CERT.BETA_MAX) raisons.push('peigne');
  if (!(detail.kot >= CERT.KOT_MIN)) raisons.push('resolution');
  if (!(nls.llr >= CERT.LLR_MIN)) raisons.push('etiquette');
  if (!(Math.abs(nls.derive) <= CERT.DERIVE_MAX) || !(nls.agit <= CERT.AGIT_MAX)) raisons.push('stabilite');
  if (!(detail.accord <= CERT.ACCORD_C)) raisons.push('accord');
  return { ok: raisons.length === 0, raisons, detail };
}

// Plus longue plage de zéros exacts (en secondes) dans x[i0, i1), et la fin de la dernière plage trop longue (indice, ou -1).
export function plagesDeZeros(x, i0, i1, sr) {
  const seuil = Math.max(8, Math.round(CERT.ZERO_MAX_S * sr));
  let run = 0, finDerniere = -1;
  for (let i = i0; i < i1; i++) {
    if (x[i] === 0) run++;
    else { if (run >= seuil) finDerniere = i; run = 0; }
  }
  if (run >= seuil) finDerniere = i1;
  return finDerniere;
}

// Méthodes d'Engine (engine.js, Object.assign).
export const methodesCertificat = {
  // Anneau du son brut (8 s), alimenté par process().
  initAnneau() {
    this.anneau = new Float32Array(Math.round(8 * this.sr));
    this.certEtat = new Map();
  },
  alimenterAnneau(chunk) {
    if (!this.anneau) return;
    const L = this.anneau.length, n = chunk.length, p = this.samplesTotal - n;     // samplesTotal est déjà incrémenté
    const a = ((p % L) + L) % L;
    if (a + n <= L) this.anneau.set(chunk, a);
    else { const k = L - a; this.anneau.set(chunk.subarray(0, k), a); this.anneau.set(chunk.subarray(k), 0); }
  },
  // Copie contiguë de [i0, i1) (indices absolus en échantillons), ou null si trop ancien.
  extraireAnneau(i0, i1) {
    const L = this.anneau.length;
    if (i1 > this.samplesTotal || i0 < this.samplesTotal - L || i1 <= i0) return null;
    const out = new Float32Array(i1 - i0);
    for (let i = i0, o = 0; i < i1; ) {
      const a = ((i % L) + L) % L, k = Math.min(L - a, i1 - i);
      out.set(this.anneau.subarray(a, a + k), o); o += k; i += k;
    }
    return out;
  },

  // Appelée par fuserBattement après etatPaire pour le groupe à deux anches. Pose `refus` / `cert` sur les deux voix et, si la lecture
  // n'est pas certifiée, ramène `etatAnche` à « en cours » avec une marge.
  certifierPaire(g, tNow) {
    const opts = { ...CERT, ...(this.cfg.certificat ?? {}) };
    if (this.cfg.certificat?.actif === false) return;
    const cle = `${g.key}:${g.center}`;
    const c = this.cohEtat?.get(cle);
    const [v0, v1] = [...g.voices].sort((a, b) => a.target - b.target);
    const ok = (v) => v?.tracked && !v.held && !v.coarse && !v.merged && Number.isFinite(v.fMeas);
    if (!this.anneau) this.initAnneau();
    for (const v of [v0, v1]) if (v) { v.refus = null; v.cert = null; }
    if (!c || !ok(v0) || !ok(v1)) { this.certEtat.delete(cle); return; }
    let st = this.certEtat.get(cle);
    if (!st || st.t0 !== c.t0) { st = { t0: c.t0, job: null, cert: null, essais: 0, tFenFin: -1e9, vu: tNow }; this.certEtat.set(cle, st); }
    st.vu = tNow;
    const calib = 1 + (this.cfg.calibrationPpm || 0) * 1e-6;
    const age = tNow - c.t0;
    const pasI = opts.PAS_PAR_IMAGE ?? CERT.PAS_PAR_IMAGE;

    // 1. un calcul en cours : on lui donne ses pas de cette image
    if (st.job) {
      let fini = false;
      const tDebut = opts.MS_PAR_IMAGE ? performance.now() : 0;
      for (let i = 0; !fini && (opts.MS_PAR_IMAGE ? i === 0 || performance.now() - tDebut < opts.MS_PAR_IMAGE : i < pasI); i++) {
        let r;
        try { r = st.job.gen.next(); } catch (e) { st.job = null; st.cert = { ok: false, raisons: ['domaine'], t: tNow, erreur: String(e?.message ?? e) }; break; }
        if (r.done) {
          fini = true;
          const v = juger(r.value, { f: [st.job.f8, st.job.f8p] }, { calib, zeros: false });
          const f = r.value.ok ? r.value.f.map((x) => x * calib) : null;
          // C9 répétabilité : deux fenêtres différentes, deux ajustements indépendants, d'accord à CONFIRME_C près (un hasard de fenêtre ne passe pas deux fois)
          if (v.ok && !(st.prev?.f && Math.max(...f.map((x, j) => Math.abs(1200 * Math.log2(x / st.prev.f[j])))) <= opts.CONFIRME_C)) { v.ok = false; v.raisons = ['verification']; }
          st.prev = v.ok || (f && v.raisons.every((q) => q === 'verification')) ? { f, t: tNow } : null;
          st.cert = { ...v, t: tNow, tMilieu: st.job.tMilieu, nls: resumeNls(r.value), f };
          st.job = null; st.essais++;
        }
      }
    }

    // 2. démarrage d'un calcul
    const tPeut = tNow - st.tFenFin >= opts.REESSAI_S;
    const certTient = st.cert?.ok && this.certAccord(st.cert, v0, v1, tNow, opts);
    if (!st.job && !certTient && age >= opts.AGE_MIN_S && tPeut && st.essais < opts.ESSAIS_MAX) {
      const iFin = this.samplesTotal;
      const fen0 = Math.min(opts.FEN_MAX_S, age - opts.DEBUT_S, this.anneau.length / this.sr - 0.1);
      let x = this.extraireAnneau(iFin - Math.round(fen0 * this.sr), iFin);
      if (x) {
        // R11 : une fenêtre qui contient une plage de zéros (porte du micro) ou un trou est exclue ; on ne lit que ce qui la suit
        const zFin = plagesDeZeros(x, 0, x.length, this.sr);
        let zeros = false;
        if (zFin >= 0) { x = x.subarray(zFin); zeros = true; }
        const fen = x.length / this.sr;
        st.tFenFin = tNow;
        if (fen >= opts.FEN_MIN_S) {
          st.job = { gen: lireBesselGen(x, 0, x.length, this.sr, g.center, { prior: [v0.fMeas / calib, v1.fMeas / calib] }), f8: v0.fMeas, f8p: v1.fMeas, tMilieu: tNow - fen / 2, zeros };
        } else st.cert = { ok: false, raisons: zeros ? ['trous'] : ['verification'], t: tNow };
      }
    }

    // 3. verdict affiché
    const certOk = st.cert?.ok && this.certAccord(st.cert, v0, v1, tNow, opts);
    const raisons = certOk ? [] : st.cert && !st.cert.ok ? st.cert.raisons : ['verification'];
    for (const v of [v0, v1]) { v.cert = st.cert ? { ok: !!st.cert.ok, llr: st.cert.nls?.llr ?? null, r: st.cert.nls?.r ?? null, derive: st.cert.nls?.derive ?? null } : null; }
    if (certOk) return;
    // pas certifiée : si la v62 la disait « sûre » (ou ne disait rien), elle devient « en cours » avec une marge qui interdit « juste »
    const etat = v0.etatAnche;
    if (etat === 'sur' || etat == null || v0.margeAnche === 0) {
      const motif = RAISONS.find((r) => raisons.includes(r)) ?? 'verification';
      for (const v of [v0, v1]) {
        v.etatAnche = 'en cours';
        v.margeAnche = Math.max(v.margeAnche || 0, opts.MARGE_REFUS_C);
        v.refus = motif;
        v.tBesoin = null;
      }
    }
  },

  // Super musette (trois anches) : le modèle de la seconde lecture est celui de DEUX anches (nls-bessel.js) ; un trio n'est pas certifiable
  // en v63 (recommandation R3 : modèle à trois anches). Une lecture « sûre » d'un groupe à trois voix devient « en cours », raison 'trois'.
  certifierTrio(g) {
    if (this.cfg.certificat?.actif === false) return;
    for (const v of g.voices) {
      v.refus = null;
      if (v.tracked && (v.etatAnche === 'sur' || v.etatAnche == null || v.margeAnche === 0)) {
        v.etatAnche = 'en cours'; v.margeAnche = Math.max(v.margeAnche || 0, CERT.MARGE_REFUS_C); v.refus = 'trois'; v.tBesoin = null;
      }
    }
  },

  // Le certificat tient-il encore ? (le moteur reste proche de la seconde lecture, à la dérive près)
  certAccord(cert, v0, v1, tNow, opts) {
    if (!cert?.ok || !cert.f) return false;
    const calib = 1;
    void calib;
    const dt = Math.max(0, tNow - (cert.tMilieu ?? cert.t));
    const tol = opts.TENUE_C + Math.min(0.1, Math.abs(cert.nls?.derive ?? 0) * dt);
    const e = (a, b) => Math.abs(1200 * Math.log2(a / b));
    return e(v0.fMeas, cert.f[0]) <= tol && e(v1.fMeas, cert.f[1]) <= tol;
  },
};

function resumeNls(r) {
  if (!r?.ok) return { ok: false, raison: r?.raison ?? null };
  return { f: r.f, Om: r.Om, b: r.b, m: r.m, llr: r.llr, r: r.r, K: r.K, T: r.T, Ku: r.Ku, derive: r.derive, agit: r.agit, warpC: r.warpC, plancherDb: r.plancherDb, sigmaC: r.sigmaC, ms: r.ms };
}
