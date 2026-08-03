# Actionneurs du banc : axes pas-à-pas STEP/DIR (drivers A4988/DRV8825),
# turbine (PWM→RC), sorties tout-ou-rien, excitation EM (DDS + amplitude).
# Les mouvements longs sont découpés par l'appelant (tâche async) : ici on
# n'expose que des pas courts non bloquants.
import time
from machine import Pin, PWM
from drivers.ad9833 import AD9833


class Axis:
    """Axe pas-à-pas STEP/DIR avec fin de course et conversions mm / degrés.
    `enable` : /EN commun des drivers (actif bas), passé partagé."""
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
        self.pos = 0            # position en pas depuis l'origine

    def _en(self, on):
        if self.enable is not None:
            self.enable.value(0 if on else 1)   # actif bas

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


class Blower:
    """Turbine : consigne 0..4095 (compatibilité DAC historique), sortie PWM
    destinée à un filtre RC → tension de consigne du variateur."""
    def __init__(self, pin, en_pin, freq=20_000):
        self.pwm = PWM(Pin(pin), freq=freq, duty_u16=0)
        self.en = Digital(en_pin, init=False)
        self.level = 0

    def set(self, level):
        self.level = max(0, min(4095, int(level)))
        self.pwm.duty_u16(int(self.level * 65535 // 4095))
        self.en.set(self.level > 0)

    def off(self):
        self.set(0)


class EMExciter:
    """Excitation EM : fréquence via DDS AD9833 (sinus propre), amplitude via
    PWM vers le gain/VCA de l'ampli, enable de l'étage de puissance."""
    def __init__(self, spi, fsync, amp_pin, en_pin, mclk, fmin, fmax):
        self.dds = AD9833(spi, fsync, mclk)
        self.amp_pwm = PWM(Pin(amp_pin), freq=20_000, duty_u16=0)
        self.en = Pin(en_pin, Pin.OUT, value=0)
        self.fmin, self.fmax = fmin, fmax
        self.freq = 0
        self.amp = 0

    def set(self, freq, amp):
        self.amp = max(0, min(1000, int(amp)))
        if self.amp == 0 or freq <= 0:
            self.amp_pwm.duty_u16(0)
            self.en.value(0)
            self.dds.reset()
            self.freq = 0
            return
        self.freq = max(self.fmin, min(self.fmax, int(freq)))
        self.dds.set_freq(self.freq)
        self.amp_pwm.duty_u16(int(self.amp * 65535 // 1000))
        self.en.value(1)

    def off(self):
        self.set(0, 0)
