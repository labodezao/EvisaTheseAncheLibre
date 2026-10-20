// Le registre réglé correspond-il à ce qui sonne ? (lot F2 (b), 19/10/2026)
//
// Session du 19/10 : le registre réglé était « Q » (quinte) alors que la prise donnait deux anches à l'unisson (8' + 8'+) :
// le moteur cherchait une quinte qui ne sonnait pas. Ici, en mode registre, on regarde si une voix du registre réglé reste
// SANS mesure alors que la note sonne et qu'une autre voix du même registre est mesurée. Si cela dure plus de HOLD_S, l'image
// porte `registreEcart` { regle, manque: [voix], depuis_s } ; l'écran en fait une phrase courte (accorder.js). Sinon null.
// Pur : pas d'état hors de l'objet.

export const HOLD_S = 5;       // l'écart doit durer ce temps avant d'être dit
const GRACE_S = 1;             // une voix qui revient moins d'une seconde n'efface pas le décompte

export class SuiviRegistre {
  constructor() { this.depuis = null; this.vuBon = null; this.cle = ''; }

  // `r` : image du moteur ; `cfg` : réglages du moteur. Rend null ou { regle, manque, depuis_s }.
  maj(r, cfg) {
    const t = r?.time;
    if (!(t >= 0)) return null;
    const cle = `${cfg?.mode}|${cfg?.register}`;
    if (cle !== this.cle) { this.cle = cle; this.depuis = null; this.vuBon = null; }
    if (cfg?.mode !== 'register' || r.quiet || r.playedMidi == null) { this.depuis = null; return null; }
    const voix = [];
    for (const g of r.groups ?? []) {
      if (g.isHarmonic || g.isSub) continue;
      for (const v of g.voices) voix.push({ nom: v.def?.label || v.def?.id || g.key, suivie: !!v.tracked });
    }
    const manque = voix.filter((v) => !v.suivie).map((v) => v.nom);
    const ecart = voix.length > 1 && manque.length > 0 && manque.length < voix.length;
    if (ecart) {
      this.vuBon = t;
      this.depuis ??= t;
    } else if (this.depuis != null && this.vuBon != null && t - this.vuBon > GRACE_S) {
      this.depuis = null;
    }
    if (this.depuis == null || t - this.depuis < HOLD_S || !ecart) return null;
    return { regle: cfg.register, manque, depuis_s: Math.round((t - this.depuis) * 10) / 10 };
  }
}
