# Pilote minimal SFM3000 (débitmètre massique Sensirion) en I2C.
# ⚠ Offset et facteur d'échelle dépendent de la variante et du gaz : vérifie
# contre ta fiche technique (air : offset 32768, échelle 140 slm typiques).
import time


class SFM3000:
    def __init__(self, i2c, addr=0x40, offset=32768, scale=140.0):
        self.i2c = i2c
        self.addr = addr
        self.offset = offset
        self.scale = scale
        # Démarre la mesure continue (commande 0x1000).
        try:
            self.i2c.writeto(addr, b'\x10\x00')
            time.sleep_ms(15)
            # Première lecture souvent invalide : on la jette.
            self.i2c.readfrom(addr, 3)
        except OSError:
            pass

    @staticmethod
    def _crc_ok(b0, b1, crc):
        c = 0xFF
        for b in (b0, b1):
            c ^= b
            for _ in range(8):
                c = ((c << 1) ^ 0x31) & 0xFF if (c & 0x80) else (c << 1) & 0xFF
        return c == crc

    def read(self):
        """Débit en slm (standard litres/min), ou None si trame invalide."""
        try:
            d = self.i2c.readfrom(self.addr, 3)
        except OSError:
            return None
        if len(d) < 3 or not self._crc_ok(d[0], d[1], d[2]):
            return None
        raw = (d[0] << 8) | d[1]
        return (raw - self.offset) / self.scale
