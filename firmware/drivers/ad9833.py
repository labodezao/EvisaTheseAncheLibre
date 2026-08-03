# Pilote AD9833 (générateur DDS sinus/triangle/carré) sur SPI.
# On écrit la fréquence dans le registre FREQ0 ; le composant sort une sinus
# propre — idéal pour balayer l'excitation EM sans DSP côté MCU.
from machine import Pin

_CTRL_RESET = 0x0100        # RESET=1
_CTRL_SINE = 0x2000         # B28=1, sortie sinus
_FREQ0 = 0x4000             # écriture registre FREQ0


class AD9833:
    def __init__(self, spi, fsync_pin, mclk=25_000_000):
        self.spi = spi
        self.fsync = Pin(fsync_pin, Pin.OUT, value=1)
        self.mclk = mclk
        self.reset()

    def _write(self, word):
        self.fsync.value(0)
        self.spi.write(bytes((word >> 8 & 0xFF, word & 0xFF)))
        self.fsync.value(1)

    def reset(self):
        self._write(_CTRL_RESET)

    def set_freq(self, hz):
        """Programme FREQ0 puis sort une sinus continue à `hz`."""
        reg = int(hz * (1 << 28) / self.mclk) & 0x0FFFFFFF
        self._write(_CTRL_SINE)                       # B28=1 : freq en 2 écritures
        self._write(_FREQ0 | (reg & 0x3FFF))          # 14 bits de poids faible
        self._write(_FREQ0 | ((reg >> 14) & 0x3FFF))  # 14 bits de poids fort
        self._write(_CTRL_SINE)                        # sortie active (RESET=0)
