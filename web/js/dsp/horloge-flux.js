// Dérive de l'horloge du micro face à celle des dates du navigateur (ppm), lot F2 (c), 19/10/2026.
//
// Avant : (dernière date - première date) / (échantillons reçus / fréquence) - 1, sur la prise ENTIÈRE. Cette formule prend
// pour dérive tout ce qui n'en est pas : chaque trou (une perte décale les dates d'un palier : 667 ms de trous sur 2072 s
// = +322 ppm à eux seuls), le saut de démarrage, et surtout n'importe quelle date aberrante de la DERNIÈRE trame, puisque
// seules les deux extrémités comptaient. Le JSON de la session du 19/10 disait -27 105 ppm (-2,7 %) pour 0,04 % mesuré
// entre le WAV et l'horloge murale : valeur impossible pour un quartz (quelques centaines de ppm au plus).
//
// Maintenant : régression des dates sur le nombre d'échantillons, SANS les sauts. La prise est coupée en plages sans saut
// (un saut de date > SAUT_S entre deux trames successives, ou une coupure de la mesure) ; on pool les moindres carrés
// DANS chaque plage (pente = somme des Sxy / somme des Sxx), donc ni les trous ni les sauts n'y entrent, et une date
// isolée aberrante ne coupe qu'une plage de quelques trames. Rien n'est rendu avant 10 s de plages utiles. Une dérive
// au-delà de PPM_MAX n'est pas celle d'un quartz : elle n'est pas rendue (null), et le résumé garde la valeur brute.

export const SAUT_S = 0.005;     // écart entre deux dates successives et la durée du bloc au-delà duquel la plage est coupée
export const PPM_MAX = 2000;     // au-delà : pas une dérive d'horloge
export const UTILE_S = 10;       // plages utiles cumulées avant de rendre une valeur

export class HorlogeFlux {
  constructor(sr) {
    this.sr = sr;
    this.sxx = 0; this.sxy = 0; this.utile = 0;   // plages terminées (sommes centrées)
    this.coupure();
  }

  // Une nouvelle plage : la mesure a été coupée ou la date a sauté.
  coupure() {
    this.fermer();
    this.n = 0; this.mx = 0; this.my = 0; this.cxx = 0; this.cxy = 0;
    this.tsPrec = null; this.durPrec = 0; this.ts0 = null;
  }

  fermer() {
    if (this.n >= 2) { this.sxx += this.cxx; this.sxy += this.cxy; this.utile += this.dernierX - this.premierX; }
  }

  // `ts` : AudioData.timestamp (µs), `cum` : échantillons reçus AVANT ce bloc (dans la prise), `n` : taille du bloc.
  bloc(ts, cum, n) {
    if (!Number.isFinite(ts)) return;
    if (this.tsPrec !== null && Math.abs((ts - this.tsPrec) / 1e6 - this.durPrec) > SAUT_S) this.coupure();
    if (this.ts0 === null) { this.ts0 = ts; this.premierX = cum / this.sr; }
    const x = cum / this.sr, y = (ts - this.ts0) / 1e6;
    this.dernierX = x;
    // Welford, sommes centrées.
    this.n++;
    const dx = x - this.mx;
    this.mx += dx / this.n;
    const dy = y - this.my;
    this.my += dy / this.n;
    this.cxx += dx * (x - this.mx);
    this.cxy += dx * (y - this.my);
    this.tsPrec = ts; this.durPrec = n / this.sr;
  }

  // { ppm (rendu ou null), brut (toujours, si calculable) }
  lire() {
    const sxx = this.sxx + (this.n >= 2 ? this.cxx : 0);
    const sxy = this.sxy + (this.n >= 2 ? this.cxy : 0);
    const utile = this.utile + (this.n >= 2 ? this.dernierX - this.premierX : 0);
    if (!(sxx > 0) || utile < UTILE_S) return { ppm: null, brut: null };
    const brut = Math.round((sxy / sxx - 1) * 1e7) / 10;
    return { ppm: Math.abs(brut) <= PPM_MAX ? brut : null, brut };
  }
}
