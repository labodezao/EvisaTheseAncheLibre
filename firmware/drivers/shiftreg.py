# Matrice d'électro-aimants pilotée par une chaîne de 74HC595 → drivers
# TPL7407L (ou ULN2803). Chaque bit = un solénoïde (bouton d'accordéon).
# Maintien basse puissance : PWM sur /OE (pleine actuation puis maintien).
from machine import Pin, PWM


class Buttons:
    def __init__(self, data, clock, latch, n_channels, oe=None,
                 hold_duty=400, hold_freq=1000):
        self.data = Pin(data, Pin.OUT, value=0)
        self.clock = Pin(clock, Pin.OUT, value=0)
        self.latch = Pin(latch, Pin.OUT, value=0)
        self.n = n_channels
        self.nbytes = (n_channels + 7) // 8
        self.state = bytearray(self.nbytes)     # bit i = canal i
        self.oe = None
        if oe is not None:
            self.oe = PWM(Pin(oe), freq=hold_freq, duty_u16=0)   # /OE actif bas
        self.hold_duty = hold_duty
        self._flush()

    def _flush(self):
        # Émet les octets, MSB en dernier (le dernier registre = premiers bits).
        for b in range(self.nbytes - 1, -1, -1):
            byte = self.state[b]
            for bit in range(7, -1, -1):
                self.data.value((byte >> bit) & 1)
                self.clock.value(1)
                self.clock.value(0)
        self.latch.value(1)
        self.latch.value(0)

    def _enable_outputs(self):
        # /OE bas = sorties actives. En PWM : duty faible = souvent actif
        # (maintien), 0 = toujours actif (pleine puissance).
        if self.oe is not None:
            any_on = any(self.state)
            duty = int((1000 - self.hold_duty) * 65535 // 1000) if any_on else 65535
            self.oe.duty_u16(duty)

    def set(self, ch, on):
        if ch < 0 or ch >= self.n:
            return
        mask = 1 << (ch & 7)
        i = ch >> 3
        if on:
            self.state[i] |= mask
        else:
            self.state[i] &= ~mask & 0xFF
        self._flush()
        self._enable_outputs()

    def all_off(self):
        for i in range(self.nbytes):
            self.state[i] = 0
        self._flush()
        self._enable_outputs()

    def active(self):
        return [i for i in range(self.n) if (self.state[i >> 3] >> (i & 7)) & 1]
