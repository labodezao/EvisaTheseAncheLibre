// Lecture d'un WAV PCM 16 bits ou float 32 (mono ou premier canal).
import { readFileSync } from 'node:fs';
export function lireWav(chemin) {
  const b = readFileSync(chemin);
  let o = 12, data, sr, ch = 1, bits = 16;
  while (o < b.length) {
    const id = b.toString('ascii', o, o + 4), n = b.readUInt32LE(o + 4);
    if (id === 'fmt ') { ch = b.readUInt16LE(o + 10); sr = b.readUInt32LE(o + 12); bits = b.readUInt16LE(o + 22); }
    if (id === 'data') data = b.subarray(o + 8, o + 8 + n);
    o += 8 + n + (n & 1);
  }
  const pas = (bits / 8) * ch, x = new Float32Array(Math.floor(data.length / pas));
  for (let i = 0; i < x.length; i++) x[i] = bits === 16 ? data.readInt16LE(i * pas) / 32768 : data.readFloatLE(i * pas);
  return { x, sr };
}
