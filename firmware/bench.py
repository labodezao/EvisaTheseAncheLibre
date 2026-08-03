# Contrôleur du banc d'accordage. Boucle asyncio robuste : échantillonnage +
# filtrage capteurs, régulation de pression, moteur/vanne/turbine, excitation
# EM et balayage, télémétrie et affichage. Toutes les tâches sont non
# bloquantes (les mouvements longs du moteur sont découpés).
try:
    import asyncio
except ImportError:  # anciens builds
    import uasyncio as asyncio
import time
import json
from machine import I2C, Pin

import config as C
from filters import Filtered
from display import Display
from drivers.bmp280 import BMP280
from drivers.sfm3000 import SFM3000
from drivers.actuators import Stepper, Digital, Blower, EMExciter


def _now_ms():
    return time.ticks_ms()


class Bench:
    def __init__(self):
        self.i2c = I2C(C.I2C_ID, scl=Pin(C.PIN_SCL), sda=Pin(C.PIN_SDA), freq=C.I2C_FREQ)
        self.display = Display(self.i2c, C.OLED_W, C.OLED_H, C.ADDR_OLED)
        self.display.message("Banc anche libre", C.FW_VERSION, "init capteurs...")

        # Capteurs (tolérants à l'absence : le banc démarre quand même).
        try:
            self.bmp = BMP280(self.i2c, C.ADDR_BMP280)
        except Exception as e:
            self.bmp = None
        try:
            self.sfm = SFM3000(self.i2c, C.ADDR_SFM3000)
        except Exception as e:
            self.sfm = None

        # Actionneurs.
        self.stepper = Stepper(C.PIN_STEP)
        self.valve = Digital(C.PIN_VALVE, init=True)     # ouverte au repos
        self.blow = Blower(C.PIN_BLOW, C.BLOW_PWM_FREQ)
        self.clamp = Digital(C.PIN_CLAMP, init=False)
        self.em = EMExciter(C.PIN_EM, C.PIN_EM_EN, C.EM_MIN_HZ, C.EM_MAX_HZ)
        self.sw1 = Pin(C.STEP_SW1, Pin.IN, Pin.PULL_UP)
        self.sw2 = Pin(C.STEP_SW2, Pin.IN, Pin.PULL_UP)

        # État mesuré (filtré).
        self.fp = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.fq = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.ft = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.p0 = 0.0            # pression de référence (tare)
        self.p = 0.0            # pression relative filtrée (Pa)
        self.q = 0.0            # débit filtré (slm)
        self.t = 0.0            # température (°C)

        # Consignes / état de commande.
        self.press_sp = None    # consigne de pression (None = régulation off)
        self.kp = 0.5           # gain proportionnel régulation turbine (à régler)
        self.pos = 1            # position de pression (0/1)
        self.state = "pret"
        self.stream = True
        self.telem_hz = C.TELEM_HZ
        self._step_queue = 0    # pas restant à exécuter (découpés)
        self._sweep = None      # (f0, f1, t0_ms, dur_ms, amp)
        self.link = "-"
        self._writers = []      # transports abonnés à la télémétrie

    def add_writer(self, fn):
        self._writers.append(fn)

    # ---- Séquences -----------------------------------------------------------
    async def home(self):
        """Référence le moteur sur le fin de course SW1."""
        self.state = "homing"
        for _ in range(4000 // 20):
            if not self.sw1.value():
                break
            self.stepper.step_block(20)
            await asyncio.sleep_ms(0)
        self.stepper.release()
        self.pos = 1
        self.state = "pret"

    async def tare(self):
        """Capture la pression ambiante (vanne fermée, turbine coupée)."""
        self.state = "tare"
        self.valve.set(False)
        self.blow.off()
        await asyncio.sleep_ms(1500)
        if self.bmp:
            pr, _ = self.bmp.read()
            self.p0 = pr
        self.valve.set(True)
        self.state = "pret"

    def invert(self):
        """Inverse le sens du soufflet (position haute ↔ basse)."""
        self._step_queue += (-C.STEP_TRAVEL if self.pos == 1 else C.STEP_TRAVEL)
        self.pos ^= 1

    # ---- Tâches --------------------------------------------------------------
    async def task_sample(self):
        dt = 1000 // C.SAMPLE_HZ
        while True:
            if self.bmp:
                pr, tp = self.bmp.read()
                self.p = self.fp.update(pr - self.p0)
                self.t = self.ft.update(tp)
            if self.sfm:
                self.q = self.fq.update(self.sfm.read())
            await asyncio.sleep_ms(dt)

    async def task_control(self):
        while True:
            # Découpe des mouvements moteur (max 40 pas / tick → non bloquant).
            if self._step_queue:
                n = max(-40, min(40, self._step_queue))
                self.stepper.step_block(n)
                self._step_queue -= n
                if self._step_queue == 0:
                    self.stepper.release()
            # Régulation de pression (proportionnelle sur la turbine).
            if self.press_sp is not None:
                err = self.press_sp - self.p
                lvl = self.blow.level + self.kp * err
                self.blow.set(lvl)
            # Balayage EM.
            if self._sweep:
                f0, f1, t0, dur, amp = self._sweep
                frac = time.ticks_diff(_now_ms(), t0) / dur
                if frac >= 1.0:
                    self.em.set(f1, amp)
                    self._sweep = None
                    self.state = "pret"
                else:
                    self.em.set(f0 + (f1 - f0) * frac, amp)
            await asyncio.sleep_ms(20)

    def telem(self):
        return json.dumps({
            "t": _now_ms(), "p": round(self.p, 1), "q": round(self.q, 3),
            "T": round(self.t, 2), "emHz": self.em.freq, "emA": self.em.amp,
            "blow": self.blow.level, "valve": int(self.valve.state),
            "clamp": int(self.clamp.state), "pos": self.pos, "st": self.state,
            "sp": self.press_sp,
        })

    async def task_telem(self):
        while True:
            if self.stream and self._writers:
                msg = self.telem() + "\n"
                for w in self._writers:
                    try:
                        w(msg)
                    except Exception:
                        pass
            await asyncio.sleep_ms(max(20, 1000 // max(1, self.telem_hz)))

    async def task_display(self):
        while True:
            self.display.show(self.p, self.q, self.t, self.state,
                              extra="EM%d" % self.em.freq if self.em.freq else None,
                              link=self.link)
            await asyncio.sleep_ms(1000 // C.DISPLAY_HZ)

    def safe_stop(self):
        self.press_sp = None
        self._sweep = None
        self.blow.off()
        self.em.off()
        self.stepper.release()
        self.state = "arret"

    # ---- Commandes -----------------------------------------------------------
    def handle(self, line):
        """Traite une commande texte, renvoie une réponse (str)."""
        parts = line.strip().split()
        if not parts:
            return ""
        cmd = parts[0].upper()
        a = parts[1:]
        try:
            if cmd == "PING":
                return "PONG"
            if cmd == "ID":
                return "%s %s" % (C.FW_ID, C.FW_VERSION)
            if cmd == "VALVE":
                self.valve.set(int(a[0])); return "OK"
            if cmd == "CLAMP":
                self.clamp.set(int(a[0])); return "OK"
            if cmd == "BLOW":
                self.press_sp = None; self.blow.set(int(a[0])); return "OK"
            if cmd == "PRESSURE":
                self.press_sp = float(a[0]); return "OK"    # consigne en Pa relatifs
            if cmd == "STEP":
                self._step_queue += int(a[0]); return "OK"
            if cmd == "INVERT":
                self.invert(); return "OK"
            if cmd == "TARE":
                asyncio.create_task(self.tare()); return "OK"
            if cmd == "HOME":
                asyncio.create_task(self.home()); return "OK"
            if cmd == "EM":
                self._sweep = None; self.em.set(float(a[0]), int(a[1])); return "OK"
            if cmd == "SWEEP":
                f0, f1, dur = float(a[0]), float(a[1]), float(a[2])
                amp = int(a[3]) if len(a) > 3 else 500
                self._sweep = (f0, f1, _now_ms(), max(1, int(dur * 1000)), amp)
                self.state = "sweep"; return "OK"
            if cmd == "STREAM":
                self.stream = bool(int(a[0]))
                if len(a) > 1:
                    self.telem_hz = int(a[1])
                return "OK"
            if cmd == "STOP":
                self.safe_stop(); return "OK"
            return "ERR cmd"
        except (IndexError, ValueError):
            return "ERR args"

    async def run(self):
        await self.home()
        await self.tare()
        for coro in (self.task_sample, self.task_control, self.task_telem, self.task_display):
            asyncio.create_task(coro())
