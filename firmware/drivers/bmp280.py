# Pilote minimal BMP280 (pression + température) en I2C.
# Compensation entière/flottante d'après la fiche technique Bosch BMP280.
import struct


class BMP280:
    def __init__(self, i2c, addr=0x76):
        self.i2c = i2c
        self.addr = addr
        chip = self.i2c.readfrom_mem(addr, 0xD0, 1)[0]
        if chip not in (0x58, 0x60):  # 0x58 BMP280, 0x60 BME280
            raise OSError("BMP280 introuvable (chip id 0x%02x)" % chip)
        # Coefficients de calibration (0x88..0x9F).
        cal = self.i2c.readfrom_mem(addr, 0x88, 24)
        (self.T1, self.T2, self.T3,
         self.P1, self.P2, self.P3, self.P4, self.P5,
         self.P6, self.P7, self.P8, self.P9) = struct.unpack('<Hhh Hhhhhhhhh', cal)
        # Normal mode, oversampling ×2 temp / ×16 press, filtre IIR ×16.
        self.i2c.writeto_mem(addr, 0xF5, bytes([(0b100 << 2)]))       # config: filter
        self.i2c.writeto_mem(addr, 0xF4, bytes([(0b010 << 5) | (0b101 << 2) | 0b11]))  # ctrl_meas
        self._t_fine = 0

    def _read_raw(self):
        d = self.i2c.readfrom_mem(self.addr, 0xF7, 6)
        praw = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        traw = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        return praw, traw

    def read(self):
        """Renvoie (pression Pa, température °C)."""
        praw, traw = self._read_raw()
        # Température (compensation Bosch).
        v1 = (traw / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((traw / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        self._t_fine = v1 + v2
        temp = self._t_fine / 5120.0
        # Pression.
        v1 = self._t_fine / 2.0 - 64000.0
        v2 = v1 * v1 * self.P6 / 32768.0
        v2 = v2 + v1 * self.P5 * 2.0
        v2 = v2 / 4.0 + self.P4 * 65536.0
        v1 = (self.P3 * v1 * v1 / 524288.0 + self.P2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self.P1
        if v1 == 0:
            return 0.0, temp
        p = 1048576.0 - praw
        p = (p - v2 / 4096.0) * 6250.0 / v1
        v1 = self.P9 * p * p / 2147483648.0
        v2 = p * self.P8 / 32768.0
        p = p + (v1 + v2 + self.P7) / 16.0
        return p, temp
