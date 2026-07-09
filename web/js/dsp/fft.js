// FFT complexe radix-2 itérative, en place, avec tables précalculées.
// Module pur, sans dépendance.

const cache = new Map();

export class FFT {
  constructor(n) {
    if ((n & (n - 1)) !== 0) throw new Error(`FFT: taille non puissance de 2 (${n})`);
    this.n = n;
    this.levels = Math.log2(n) | 0;
    this.cos = new Float64Array(n / 2);
    this.sin = new Float64Array(n / 2);
    for (let i = 0; i < n / 2; i++) {
      this.cos[i] = Math.cos((2 * Math.PI * i) / n);
      this.sin[i] = Math.sin((2 * Math.PI * i) / n);
    }
    this.rev = new Uint32Array(n);
    for (let i = 0; i < n; i++) {
      let r = 0;
      for (let b = 0; b < this.levels; b++) r = (r << 1) | ((i >>> b) & 1);
      this.rev[i] = r;
    }
  }

  static get(n) {
    let f = cache.get(n);
    if (!f) { f = new FFT(n); cache.set(n, f); }
    return f;
  }

  // Transformée en place de (re, im), longueur n.
  transform(re, im) {
    const { n, rev, cos, sin } = this;
    for (let i = 0; i < n; i++) {
      const j = rev[i];
      if (j > i) {
        let t = re[i]; re[i] = re[j]; re[j] = t;
        t = im[i]; im[i] = im[j]; im[j] = t;
      }
    }
    for (let size = 2; size <= n; size <<= 1) {
      const half = size >> 1;
      const step = n / size;
      for (let i = 0; i < n; i += size) {
        for (let j = i, k = 0; j < i + half; j++, k += step) {
          const l = j + half;
          const tre = re[l] * cos[k] + im[l] * sin[k];
          const tim = im[l] * cos[k] - re[l] * sin[k];
          re[l] = re[j] - tre;
          im[l] = im[j] - tim;
          re[j] += tre;
          im[j] += tim;
        }
      }
    }
  }
}

export function hannWindow(n) {
  const w = new Float64Array(n);
  for (let i = 0; i < n; i++) w[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1));
  return w;
}
