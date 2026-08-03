# Contrôleur du banc d'accordage — rig complet (repris des Pyboards
# MesAnche/ValControl, fusionnés sur une seule carte ESP32-S3).
# 3 axes STEP/DIR (pression/soufflet, section-vis, clapet), turbine, électro-
# vanne, bridage, excitation EM (DDS) + balayage, acquisition rapide P/Q/T,
# rampe de pression (seuil d'auto-entretien), télémétrie + affichage.
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
import time
import json
from machine import I2C, SPI, Pin

import config as C
from filters import Filtered
from display import Display
from drivers.bmp280 import BMP280
from drivers.sfm3000 import SFM3000
from drivers.actuators import Axis, Digital, Blower, EMExciter


def _ms():
    return time.ticks_ms()


class Bench:
    def __init__(self):
        self.i2c = I2C(C.I2C_ID, scl=Pin(C.PIN_SCL), sda=Pin(C.PIN_SDA), freq=C.I2C_FREQ)
        self.display = Display(self.i2c, C.OLED_W, C.OLED_H, C.ADDR_OLED)
        self.display.message("Banc anche libre", C.FW_VERSION, "init...")

        try:
            self.bmp = BMP280(self.i2c, C.ADDR_BMP280)
        except Exception:
            self.bmp = None
        try:
            self.sfm = SFM3000(self.i2c, C.ADDR_SFM3000)
        except Exception:
            self.sfm = None

        # Drivers pas-à-pas : /EN commun (actif bas).
        self.drv_en = Digital(C.PIN_DRV_ENABLE, active_high=False, init=False)
        mk = lambda d, mmpr=None: Axis(d["step"], d["dir"], d["sw"], d["spr"],
                                       mmpr, d["inv"], enable=self.drv_en.pin)
        self.ax = {
            "press": mk(C.AX_PRESS),
            "screw": mk(C.AX_SCREW, C.SCREW_MM_PER_REV),
            "clap":  mk(C.AX_CLAP),
        }
        self.q = {"press": 0, "screw": 0, "clap": 0}   # pas restant par axe
        self.xpos_mm = 0.0      # position section (vis) en mm
        self.clap_deg = 0.0     # angle clapet
        self.press_pos = 1      # sens soufflet

        # Turbine, vanne, bridage.
        self.blow = Blower(C.PIN_BLOW, C.PIN_BLOW_EN, C.BLOW_PWM_FREQ)
        self.valve = Digital(C.PIN_VANNE, init=False)
        self.clamp = Digital(C.PIN_CLAMP, init=False)

        # Excitation EM (DDS AD9833 + amplitude).
        self.spi = SPI(C.SPI_ID, baudrate=1_000_000, polarity=1, phase=0,
                       sck=Pin(C.PIN_SPI_SCK), mosi=Pin(C.PIN_SPI_MOSI))
        self.em = EMExciter(self.spi, C.PIN_AD9833_FSYNC, C.PIN_EM_AMP,
                            C.PIN_EM_EN, C.AD9833_MCLK, C.EM_MIN_HZ, C.EM_MAX_HZ)

        # État mesuré (filtré pour l'affichage/télémétrie ; l'acquisition rapide
        # lit le brut).
        self.fp = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.fq = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.ft = Filtered(C.MEDIAN_N, C.IIR_ALPHA)
        self.p0 = 0.0
        self.p = self.q_flow = self.t = 0.0

        self.state = "init"
        self.stream = True
        self.telem_hz = C.TELEM_HZ
        self._sweep = None      # (f0,f1,t0,dur_ms,amp)
        self._pramp = None      # (l0,l1,t0,dur_ms)
        self._busy = False      # séquence longue en cours (acquisition/homing)
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

    # ---- Lecture capteurs -----------------------------------------------------
    def _read(self):
        p = t = None
        if self.bmp:
            p, t = self.bmp.read()
        q = self.sfm.read() if self.sfm else None
        return p, t, q

    # ---- Séquences ------------------------------------------------------------
    async def home_axis(self, name):
        """Recule puis avance jusqu'au fin de course (passage à 0)."""
        ax = self.ax[name]
        for _ in range(20):                 # léger recul
            ax.step_block(-15)
            await asyncio.sleep_ms(0)
        for _ in range(4000 // 15):
            if not ax.sw.value():
                break
            ax.step_block(15)
            await asyncio.sleep_ms(0)
        ax.pos = 0
        ax.release()

    async def home_all(self):
        self._busy = True
        self.state = "homing"
        for name in ("press", "screw", "clap"):
            await self.home_axis(name)
        self.xpos_mm = 0.0
        self.clap_deg = 0.0
        self.press_pos = 1
        self.state = "pret"
        self._busy = False

    async def tare(self):
        self.state = "tare"
        self.valve.set(False)
        self.blow.off()
        await asyncio.sleep_ms(1500)
        if self.bmp:
            self.p0, _ = self.bmp.read()
        self.state = "pret"

    def move_screw_mm(self, mm_abs, speed=None):
        """Amène la section (vis) à la position absolue `mm_abs` (mm)."""
        d = mm_abs - self.xpos_mm
        self.q["screw"] += self.ax["screw"].steps_for_mm(d)
        self.xpos_mm = mm_abs

    def move_clap_deg(self, deg_abs):
        d = deg_abs - self.clap_deg
        self.q["clap"] += self.ax["clap"].steps_for_deg(d)
        self.clap_deg = deg_abs

    def invert_press(self):
        self.q["press"] += (-C.STEP_TRAVEL_PRESS if self.press_pos == 1 else C.STEP_TRAVEL_PRESS)
        self.press_pos ^= 1

    def surface_mm2(self):
        return abs(self.xpos_mm) * C.SECTION_WIDTH_MM

    async def valve_pulse(self, ms):
        self.valve.set(True)
        await asyncio.sleep_ms(int(ms))
        self.valve.set(False)

    async def acquire(self, dur_s, hz):
        """Rafale P/Q/T horodatée, streamée ligne à ligne ('A t p q temp')
        pour synchro avec l'audio du navigateur."""
        self._busy = True
        self.state = "acq"
        hz = max(10, min(C.ACQ_HZ, int(hz)))
        dt = 1000 // hz
        t0 = _ms()
        self._bcast("A BEGIN %d %d\n" % (hz, int(dur_s * 1000)))
        end = t0 + int(dur_s * 1000)
        while time.ticks_diff(end, _ms()) > 0:
            p, t, q = self._read()
            pr = (p - self.p0) if p is not None else 0.0
            self._bcast("A %d %.1f %.3f %.2f\n" % (
                time.ticks_diff(_ms(), t0), pr, q if q is not None else 0.0,
                t if t is not None else 0.0))
            await asyncio.sleep_ms(dt)
        self._bcast("A END\n")
        self.state = "pret"
        self._busy = False

    # ---- Tâches ---------------------------------------------------------------
    async def task_sample(self):
        dt = 1000 // C.SAMPLE_HZ
        while True:
            p, t, q = self._read()
            if p is not None:
                self.p = self.fp.update(p - self.p0)
                self.t = self.ft.update(t)
            if q is not None:
                self.q_flow = self.fq.update(q)
            await asyncio.sleep_ms(dt)

    async def task_control(self):
        while True:
            # Découpe des mouvements (max 40 pas/axe/tick → non bloquant).
            for name, ax in self.ax.items():
                if self.q[name]:
                    n = max(-40, min(40, self.q[name]))
                    ax.step_block(n)
                    self.q[name] -= n
                    if self.q[name] == 0:
                        ax.release()
            # Balayage EM.
            if self._sweep:
                f0, f1, t0, dur, amp = self._sweep
                fr = time.ticks_diff(_ms(), t0) / dur
                if fr >= 1.0:
                    self.em.set(f1, amp); self._sweep = None; self.state = "pret"
                else:
                    self.em.set(f0 + (f1 - f0) * fr, amp)
            # Rampe de pression (seuil d'auto-entretien).
            if self._pramp:
                l0, l1, t0, dur = self._pramp
                fr = time.ticks_diff(_ms(), t0) / dur
                if fr >= 1.0:
                    self.blow.set(l1); self._pramp = None; self.state = "pret"
                else:
                    self.blow.set(l0 + (l1 - l0) * fr)
            await asyncio.sleep_ms(20)

    def telem(self):
        return json.dumps({
            "t": _ms(), "p": round(self.p, 1), "q": round(self.q_flow, 3),
            "T": round(self.t, 2), "blow": self.blow.level,
            "emHz": self.em.freq, "emA": self.em.amp,
            "xmm": round(self.xpos_mm, 2), "surf": round(self.surface_mm2(), 1),
            "clap": round(self.clap_deg, 1), "pos": self.press_pos,
            "valve": int(self.valve.state), "clampd": int(self.clamp.state),
            "st": self.state,
        })

    async def task_telem(self):
        while True:
            if self.stream and self._writers and not self._busy:
                self._bcast(self.telem() + "\n")
            await asyncio.sleep_ms(max(20, 1000 // max(1, self.telem_hz)))

    async def task_display(self):
        while True:
            self.display.show(self.p, self.q_flow, self.t, self.state,
                              extra=("EM%d" % self.em.freq) if self.em.freq else
                                    ("S%.0f" % self.surface_mm2()),
                              link=self.link)
            await asyncio.sleep_ms(1000 // C.DISPLAY_HZ)

    def safe_stop(self):
        self._sweep = self._pramp = None
        self.blow.off()
        self.em.off()
        self.valve.set(False)
        for ax in self.ax.values():
            ax.release()
        self.q = {"press": 0, "screw": 0, "clap": 0}
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
            if cmd == "BLOW":
                self._pramp = None; self.blow.set(int(a[0])); return "OK"
            if cmd == "SECTION":
                self.move_screw_mm(float(a[0])); return "OK"
            if cmd == "CLAP":
                self.move_clap_deg(float(a[0])); return "OK"
            if cmd == "PRESSPOS":
                if int(a[0]) != self.press_pos:
                    self.invert_press()
                return "OK"
            if cmd == "VALVE":
                if a[0].upper() == "PULSE":
                    asyncio.create_task(self.valve_pulse(int(a[1])))
                else:
                    self.valve.set(int(a[0]))
                return "OK"
            if cmd == "CLAMP":
                self.clamp.set(int(a[0])); return "OK"
            if cmd == "EM":
                self._sweep = None; self.em.set(float(a[0]), int(a[1])); return "OK"
            if cmd == "SWEEP":
                amp = int(a[3]) if len(a) > 3 else 500
                self._sweep = (float(a[0]), float(a[1]), _ms(),
                               max(1, int(float(a[2]) * 1000)), amp)
                self.state = "sweep"; return "OK"
            if cmd == "PRAMP":                    # rampe pression (seuil)
                self._pramp = (int(a[0]), int(a[1]), _ms(),
                               max(1, int(float(a[2]) * 1000)))
                self.state = "pramp"; return "OK"
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
