# Actionneurs du banc d'accordage : axes pas-à-pas STEP/DIR (soufflet motorisé,
# section, clapet) et sorties tout-ou-rien (vanne, bridage). L'air vient du
# soufflet motorisé (axe `bellows`) et non plus d'une turbine.
import time
from machine import Pin


class Axis:
    """Axe pas-à-pas STEP/DIR avec fin de course et conversions mm / degrés.
    `enable` : /EN commun des drivers (actif bas)."""
    def __init__(self, step, dir, sw, spr=1600, mm_per_rev=None, inv=False,
                 enable=None, sw_pullup=True):
        self.step = Pin(step, Pin.OUT, value=0)
        self.dir = Pin(dir, Pin.OUT, value=0)
        self.sw = Pin(sw, Pin.IN, Pin.PULL_UP if sw_pullup else None)
        self.enable = enable
        self.spr = spr
        self.inv = inv
        self.steps_per_mm = (spr / mm_per_rev) if mm_per_rev else None
        self.steps_per_deg = spr / 360.0
        self.pos = 0

    def _en(self, on):
        if self.enable is not None:
            self.enable.value(0 if on else 1)

    def step_block(self, n, delay_us=800):
        """Fait n pas (signe = sens). Bloquant : garde n court (< ~60)."""
        if n == 0:
            return
        self._en(True)
        d = 1 if n >= 0 else -1
        self.dir.value(1 if (d > 0) != self.inv else 0)
        for _ in range(abs(n)):
            self.step.value(1)
            time.sleep_us(3)
            self.step.value(0)
            time.sleep_us(delay_us)
            self.pos += d

    def steps_for_mm(self, mm):
        return int(round(mm * (self.steps_per_mm or 0)))

    def steps_for_deg(self, deg):
        return int(round(deg * self.steps_per_deg))

    def release(self):
        self._en(False)


class Digital:
    """Sortie tout-ou-rien à logique explicite."""
    def __init__(self, pin, active_high=True, init=False):
        self.pin = Pin(pin, Pin.OUT)
        self.active_high = active_high
        self.set(init)

    def set(self, on):
        self.state = bool(on)
        self.pin.value(1 if (on == self.active_high) else 0)
