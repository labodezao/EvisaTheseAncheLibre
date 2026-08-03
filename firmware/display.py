# Affichage OLED SSD1306 (I2C) : pression, débit, température, état.
# Utilise le pilote framebuf standard `ssd1306` (présent dans la plupart des
# builds MicroPython ESP32 ; sinon `mip.install("ssd1306")`).
try:
    from ssd1306 import SSD1306_I2C
except ImportError:  # pragma: no cover
    SSD1306_I2C = None


class Display:
    def __init__(self, i2c, w, h, addr=0x3C):
        self.ok = SSD1306_I2C is not None
        if self.ok:
            try:
                self.oled = SSD1306_I2C(w, h, i2c, addr=addr)
            except Exception:
                self.ok = False

    def show(self, p, flow, temp, state, extra=None, link=""):
        """p en Pa (affiché en hPa relatif), flow en slm, temp en °C."""
        if not self.ok:
            return
        o = self.oled
        o.fill(0)
        o.text("BANC ANCHE {}".format(link), 0, 0)
        o.hline(0, 10, 128, 1)
        o.text("P  {:7.2f} hPa".format(p / 100.0), 0, 16)
        o.text("Q  {:7.2f} slm".format(flow), 0, 28)
        o.text("T  {:7.2f} C".format(temp), 0, 40)
        line = state[:16]
        if extra:
            line = (state + " " + extra)[:16]
        o.text(line, 0, 54)
        o.show()

    def message(self, *lines):
        if not self.ok:
            return
        o = self.oled
        o.fill(0)
        for i, ln in enumerate(lines[:6]):
            o.text(str(ln)[:16], 0, i * 10)
        o.show()
