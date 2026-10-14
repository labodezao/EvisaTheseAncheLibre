// Lecture d'un WAV PCM 16 ou 24 bits ou float 32 (mono ou canal `canal`, 0 par défaut).
import { readFileSync } from 'node:fs';
export function lireWav(chemin, canal = 0) {
  const b = readFileSync(chemin);
  let o = 12, data, sr, ch = 1, bits = 16, fmt = 1;
  while (o < b.length) {
    const id = b.toString('ascii', o, o + 4), n = b.readUInt32LE(o + 4);
    if (id === 'fmt ') { fmt = b.readUInt16LE(o + 8); ch = b.readUInt16LE(o + 10); sr = b.readUInt32LE(o + 12); bits = b.readUInt16LE(o + 22); }
    if (id === 'data') data = b.subarray(o + 8, o + 8 + Math.min(n, b.length - o - 8));
    o += 8 + n + (n & 1);
  }
  const pas = (bits / 8) * ch, x = new Float32Array(Math.floor(data.length / pas));
  const dec = canal * bits / 8;
  for (let i = 0; i < x.length; i++) {
    const p = i * pas + dec;
    x[i] = bits === 16 ? data.readInt16LE(p) / 32768 : bits === 24 ? data.readIntLE(p, 3) / 8388608 : fmt === 3 ? data.readFloatLE(p) : data.readInt32LE(p) / 2147483648;
  }
  return { x, sr };
}
