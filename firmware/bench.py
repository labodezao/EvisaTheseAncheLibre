# Contrôleur du banc d'ACCORDAGE (ESP32-S3). Source d'air = soufflet motorisé
# (axe pas-à-pas + table X) ; boutons pressés par matrice d'électro-aimants
# (74HC595 → TPL7407) ; capteurs P/T + débit ; OLED. L'excitation EM et sa
# mesure fine sont sur le banc de RECHERCHE (PC + Behringer), pas ici.
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
import time
import json
from machine import I2C, Pin

import config as C
from filters import Filtered
from display import Display
from drivers.bmp280 import BMP280
from drivers.sfm3000 import SFM3000
from drivers.actuators import Axis, Digital
from drivers.shiftreg import Buttons


def _ms():
    return time.ticks_ms()


class Bench:
    def __init__(self):
        self.i2c = I2C(C.I2C_ID, scl=Pin(C.PIN_SCL), sda=Pin(C.PIN_SDA), freq=C.I2C_FREQ)
        self.display = Display(self.i2c, C.OLED_W, C.OLED_H, C.ADDR_OLED)
        self.display.message("Banc accordage", C.FW_VERSION, "init...")

        try:
            self.bmp = BMP280(self.i2c, C.ADDR_BMP280)
        except Exception:
            self.bmp = None
        try:
            self.sfm = SFM3000(self.i2c, C.ADDR_SFM3000)
        except Exception:
            self.sfm = None

        self.drv_en = Digital(C.PIN_DRV_ENABLE, active_high=False, init=False)
        mk = lambda d: Axis(d["step"], d["dir"], d["sw"], d["spr"],
                            d["mm_per_rev"], d["inv"], enable=self.drv_en.pin)
        self.ax = {"bellows": mk(C.AX_BELLOWS), "screw": mk(C.AX_SCREW), "clap": mk(C.AX_CLAP)}
        self.q = {"screw": 0, "clap": 0}         # files des axes de positionnement
        self.xpos_mm = 0.0
        self.clap_deg = 0.0

        # Soufflet motorisé : vitesse (pas/s), sens, bornes de course.
        self.bell_v = 0.0
        self.bell_dir = 1
        self.bell_travel = self.ax["bellows"].steps_for_mm(C.BELLOWS_TRAVEL_MM) or 20000
        self.press_sp = None    # consigne de pression (Pa) → asservit la vitesse
        self.kp = 0.02

        self.valve = Digital(C.PIN_VANNE, init=False)
        self.clamp = Digital(C.PIN_CLAMP, init=False)

        # Matrice d'électro-aimants (boutons).
        self.buttons = Buttons(C.PIN_SR_DATA, C.PIN_SR_CLOCK, C.PIN_SR_LATCH,
                               C.BTN_LH + C.BTN_RH, C.PIN_SR_OE,
                               C.HOLD_DUTY, C.HOLD_PWM_FREQ)

        self.fp = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.fq = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.ft = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.p0 = 0.0
        self.p = self.q_flow = self.t = 0.0

        self.state = "init"
        self.stream = True
        self.telem_hz = C.TELEM_HZ
        self._busy = False
        self.link = "-"
        self._writers = []

    def add_writer(self, fn):
        self._writers.append(fn)

    def _bcast(self, s):
        for w in self._writers:
            try:
                w(s)
            except Exception:
                pass

    def _read(self):
        p = t = None
        if self.bmp:
            p, t = self.bmp.read()
        q = self.sfm.read() if self.sfm else None
        return p, t, q

    # ---- Séquences ------------------------------------------------------------
    async def home_axis(self, name):
        ax = self.ax[name]
        for _ in range(20):
            ax.step_block(-15)
            await asyncio.sleep_ms(0)
        for _ in range(6000 // 15):
            if not ax.sw.value():
                break
            ax.step_block(15)
            await asyncio.sleep_ms(0)
        ax.pos = 0
        ax.release()

    async def home_all(self):
        self._busy = True
        self.state = "homing"
        for name in ("bellows", "screw", "clap"):
            await self.home_axis(name)
        self.xpos_mm = self.clap_deg = 0.0
        self.bell_dir = 1
        self.state = "pret"
        self._busy = False

    async def tare(self):
        self.state = "tare"
        self.valve.set(False)
        self.bell_v = 0.0
        await asyncio.sleep_ms(1500)
        if self.bmp:
            self.p0, _ = self.bmp.read()
        self.state = "pret"

    def move_screw_mm(self, mm_abs):
        self.q["screw"] += self.ax["screw"].steps_for_mm(mm_abs - self.xpos_mm)
        self.xpos_mm = mm_abs

    def move_clap_deg(self, deg_abs):
        self.q["clap"] += self.ax["clap"].steps_for_deg(deg_abs - self.clap_deg)
        self.clap_deg = deg_abs

    def surface_mm2(self):
        return abs(self.xpos_mm) * C.SECTION_WIDTH_MM

    async def valve_pulse(self, ms):
        self.valve.set(True)
        await asyncio.sleep_ms(int(ms))
        self.valve.set(False)

    async def acquire(self, dur_s, hz):
        self._busy = True
        self.state = "acq"
        hz = max(10, min(C.ACQ_HZ, int(hz)))
        dt = 1000 // hz
        t0 = _ms()
        self._bcast("A BEGIN %d %d\n" % (hz, int(dur_s * 1000)))
        while time.ticks_diff(t0 + int(dur_s * 1000), _ms()) > 0:
            p, t, qf = self._read()
            pr = (p - self.p0) if p is not None else 0.0
            self._bcast("A %d %.1f %.3f %.2f\n" % (
                time.ticks_diff(_ms(), t0), pr, qf if qf is not None else 0.0,
                t if t is not None else 0.0))
            await asyncio.sleep_ms(dt)
        self._bcast("A END\n")
        self.state = "pret"
        self._busy = False

    # ---- Tâches ---------------------------------------------------------------
    async def task_sample(self):
        dt = 1000 // C.SAMPLE_HZ
        while True:
            p, t, qf = self._read()
            if p is not None:
                self.p = self.fp.update(p - self.p0)
                self.t = self.ft.update(t)
            if qf is not None:
                self.q_flow = self.fq.update(qf)
            await asyncio.sleep_ms(dt)

    async def task_control(self):
        last = _ms()
        while True:
            now = _ms()
            dt = time.ticks_diff(now, last) / 1000.0
            last = now
            # Axes de positionnement (section, clapet) : découpe non bloquante.
            for name in ("screw", "clap"):
                if self.q[name]:
                    n = max(-40, min(40, self.q[name]))
                    self.ax[name].step_block(n)
                    self.q[name] -= n
                    if self.q[name] == 0:
                        self.ax[name].release()
            # Asservissement de pression → vitesse du soufflet.
            if self.press_sp is not None:
                self.bell_v = max(0.0, self.bell_v + self.kp * (self.press_sp - self.p))
            # Déplacement continu du soufflet à la vitesse voulue (auto-inversion
            # aux bornes de course — comme un joueur qui pousse puis tire).
            if self.bell_v > 0:
                bax = self.ax["bellows"]
                steps = int(self.bell_v * dt) * self.bell_dir
                if steps:
                    steps = max(-60, min(60, steps))
                    bax.step_block(steps)
                    if bax.pos >= self.bell_travel:
                        self.bell_dir = -1
                    elif bax.pos <= 0:
                        self.bell_dir = 1
            await asyncio.sleep_ms(15)

    def telem(self):
        return json.dumps({
            "t": _ms(), "p": round(self.p, 1), "q": round(self.q_flow, 3),
            "T": round(self.t, 2), "bellv": round(self.bell_v, 0),
            "sp": self.press_sp, "xmm": round(self.xpos_mm, 2),
            "surf": round(self.surface_mm2(), 1), "clap": round(self.clap_deg, 1),
            "valve": int(self.valve.state), "clampd": int(self.clamp.state),
            "btn": len(self.buttons.active()), "st": self.state,
        })

    async def task_telem(self):
        while True:
            if self.stream and self._writers and not self._busy:
                self._bcast(self.telem() + "\n")
            await asyncio.sleep_ms(max(20, 1000 // max(1, self.telem_hz)))

    async def task_display(self):
        while True:
            self.display.show(self.p, self.q_flow, self.t, self.state,
                              extra="S%.0f" % self.surface_mm2(), link=self.link)
            await asyncio.sleep_ms(1000 // C.DISPLAY_HZ)

    def safe_stop(self):
        self.press_sp = None
        self.bell_v = 0.0
        self.valve.set(False)
        self.buttons.all_off()
        for ax in self.ax.values():
            ax.release()
        self.q = {"screw": 0, "clap": 0}
        self.state = "arret"

    # ---- Commandes ------------------------------------------------------------
    def handle(self, line):
        p = line.strip().split()
        if not p:
            return ""
        cmd, a = p[0].upper(), p[1:]
        try:
            if cmd == "PING":
                return "PONG"
            if cmd == "ID":
                return "%s %s" % (C.FW_ID, C.FW_VERSION)
            if cmd == "HOME":
                asyncio.create_task(self.home_all()); return "OK"
            if cmd == "TARE":
                asyncio.create_task(self.tare()); return "OK"
            if cmd == "BELLOWS":            # vitesse directe (pas/s), coupe l'asserv.
                self.press_sp = None; self.bell_v = max(0.0, float(a[0])); return "OK"
            if cmd == "PRESSURE":           # consigne de pression (Pa) → asserv soufflet
                self.press_sp = float(a[0]); return "OK"
            if cmd == "SECTION":
                self.move_screw_mm(float(a[0])); return "OK"
            if cmd == "CLAP":
                self.move_clap_deg(float(a[0])); return "OK"
            if cmd == "VALVE":
                if a[0].upper() == "PULSE":
                    asyncio.create_task(self.valve_pulse(int(a[1])))
                else:
                    self.valve.set(int(a[0]))
                return "OK"
            if cmd == "CLAMP":
                self.clamp.set(int(a[0])); return "OK"
            if cmd == "PRESS":              # PRESS <canal> <0|1> : électro-aimant
                self.buttons.set(int(a[0]), int(a[1])); return "OK"
            if cmd == "ALLOFF":
                self.buttons.all_off(); return "OK"
            if cmd == "ACQUIRE":
                hz = int(a[1]) if len(a) > 1 else C.ACQ_HZ
                asyncio.create_task(self.acquire(float(a[0]), hz)); return "OK"
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
        await self.home_all()
        await self.tare()
        for coro in (self.task_sample, self.task_control, self.task_telem, self.task_display):
            asyncio.create_task(coro())
