# Pilote minimal Sensirion SDP8xx / SDP3x (pression différentielle) en I2C.
#
# Pourquoi : le BMP280 lit la pression ABSOLUE (~101 300 Pa) ; la pression de
# jeu (20 à 3 000 Pa) n'en est qu'une petite différence, et son filtre interne
# la retarde. Un capteur différentiel lit directement l'écart dedans/dehors,
# vite (~1 kHz) et sans dérive météo. Il sert aussi de débitmètre bon marché :
# branché de part et d'autre d'un diaphragme étalonné (orifice), q ∝ √Δp.
#
# ⚠ NON TESTÉ SUR MATÉRIEL. Vérifier contre la fiche technique Sensirion :
#   adresse 0x25 (SDP8xx, SDP31) ou 0x26 / 0x22 (autres variantes) ;
#   mesure continue « pression différentielle, moyenne jusqu'à lecture » =
#   commande 0x3615 ; trame de 9 octets : Δp, température, facteur d'échelle,
#   chacun suivi d'un CRC-8 (polynôme 0x31, départ 0xFF). Le facteur
#   d'échelle est lu dans la trame (il dépend de la variante : 500 Pa, 125 Pa).
import time


class SDP8xx:
    def __init__(self, i2c, addr=0x25):
        self.i2c = i2c
        self.addr = addr
        self.scale = None
        try:
            self.i2c.writeto(addr, b'\x3f\xf9')      # arrêt d'une mesure en cours
        except OSError:
            pass
        time.sleep_ms(2)
        self.i2c.writeto(addr, b'\x36\x15')          # mesure continue Δp, moyenne
        time.sleep_ms(20)
        if self.read() is None:
            raise OSError("SDP8xx : pas de trame valide à 0x%02x" % addr)

    @staticmethod
    def _crc(b0, b1):
        c = 0xFF
        for b in (b0, b1):
            c ^= b
            for _ in range(8):
                c = ((c << 1) ^ 0x31) & 0xFF if (c & 0x80) else (c << 1) & 0xFF
        return c

    @staticmethod
    def _s16(hi, lo):
        v = (hi << 8) | lo
        return v - 65536 if v & 0x8000 else v

    def read(self):
        """Renvoie (Δp en Pa, température en °C), ou None si trame invalide."""
        try:
            d = self.i2c.readfrom(self.addr, 9)
        except OSError:
            return None
        if len(d) < 9:
            return None
        for k in (0, 3, 6):
            if self._crc(d[k], d[k + 1]) != d[k + 2]:
                return None
        scale = (d[6] << 8) | d[7]
        if not scale:
            return None
        self.scale = scale
        return self._s16(d[0], d[1]) / scale, self._s16(d[3], d[4]) / 200.0
