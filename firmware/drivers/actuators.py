# Actionneurs : stepper (position de pression / inversion), vanne, turbine,
# bridage, excitation électromagnétique. Non bloquants autant que possible.
import time
from machine import Pin, PWM


class Stepper:
    """Pas-à-pas unipolaire/bipolaire 4 fils, séquence demi-pas simplifiée.
    Mouvement bloquant volontairement court ; les longs trajets sont découpés
    par l'appelant (tâche async) pour ne pas figer la boucle."""
    SEQ = (
        (1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
        (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1),
    )

    def __init__(self, pins):
        self.pins = [Pin(p, Pin.OUT, value=0) for p in pins]
        self.phase = 0

    def _apply(self, s):
        for pin, v in zip(self.pins, s):
            pin.value(v)

    def step_block(self, n, delay_us=1200):
        """Fait n pas (signe = sens). Bloquant : garde n petit (< ~50)."""
        d = 1 if n >= 0 else -1
        for _ in range(abs(n)):
            self.phase = (self.phase + d) % 8
            self._apply(self.SEQ[self.phase])
            time.sleep_us(delay_us)

    def release(self):
        for pin in self.pins:
            pin.value(0)


class Digital:
    """Sortie tout-ou-rien à logique explicite (actif haut par défaut)."""
    def __init__(self, pin, active_high=True, init=False):
        self.pin = Pin(pin, Pin.OUT)
        self.active_high = active_high
        self.set(init)

    def set(self, on):
        self.state = bool(on)
        self.pin.value(1 if (on == self.active_high) else 0)


class Blower:
    """Turbine centrifuge pilotée en PWM (régime 0..1000) ou tout-ou-rien."""
    def __init__(self, pin, freq=20_000):
        self.pwm = PWM(Pin(pin), freq=freq)
        self.set(0)

    def set(self, level):
        self.level = max(0, min(1000, int(level)))
        self.pwm.duty_u16(int(self.level * 65535 / 1000))

    def off(self):
        self.set(0)


class EMExciter:
    """Excitation électromagnétique de l'anche : PWM à fréquence variable
    (sinus approché par le filtre passe-bas de l'étage de puissance/bobine).
    amp 0..1000 = rapport cyclique moyen."""
    def __init__(self, pin, en_pin, fmin=20, fmax=5000):
        self.pwm = PWM(Pin(pin), freq=fmin, duty_u16=0)
        self.en = Pin(en_pin, Pin.OUT, value=0)
        self.fmin = fmin
        self.fmax = fmax
        self.freq = 0
        self.amp = 0

    def set(self, freq, amp):
        self.amp = max(0, min(1000, int(amp)))
        if self.amp == 0 or freq <= 0:
            self.pwm.duty_u16(0)
            self.en.value(0)
            self.freq = 0
            return
        self.freq = max(self.fmin, min(self.fmax, int(freq)))
        self.pwm.freq(self.freq)
        self.pwm.duty_u16(int(self.amp * 65535 / 1000))
        self.en.value(1)

    def off(self):
        self.set(0, 0)
