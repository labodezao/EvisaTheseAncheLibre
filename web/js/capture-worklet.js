// AudioWorkletProcessor de capture : tourne sur le thread audio temps réel
// et transmet l'audio par blocs de 512 échantillons directement au Worker
// DSP via un MessagePort (latence de transport ≈ 10 ms, thread audio léger).

class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buf = new Float32Array(512);
    this.pos = 0;
    this.out = null;
    this.port.onmessage = (e) => {
      if (e.data && e.data.port) this.out = e.data.port;
    };
  }

  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch && this.out) {
      let i = 0;
      while (i < ch.length) {
        const n = Math.min(ch.length - i, this.buf.length - this.pos);
        this.buf.set(ch.subarray(i, i + n), this.pos);
        this.pos += n;
        i += n;
        if (this.pos === this.buf.length) {
          const copy = new Float32Array(this.buf);
          this.out.postMessage(copy, [copy.buffer]);
          this.pos = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor('capture', CaptureProcessor);
