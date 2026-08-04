"""Micropython module for stepper motor driven by Easy Driver."""
import machine
from time import sleep_us
from math import floor


class Stepper:
    def __init__(self, step_pin , dir_pin,  sleep_pin):
        """Initialise stepper."""
        self.stp = step_pin
        self.dir = dir_pin
        self.slp = sleep_pin

        self.stp.init(machine.Pin.OUT)
        self.dir.init(machine.Pin.OUT)
        self.slp.init(machine.Pin.OUT)
        
        self.power_on() 
        self.step_time = 120  # us
        self.min_step_time = 60  # us
        self.steps_per_rev = 1600
        self.current_position = 0

    def power_on(self):
        """Power on stepper."""
        self.slp.value(0)

    def power_off(self):
        """Power off stepper."""
        self.slp.value(1)
        self.current_position = 0

    def steps(self, step_count, speed = 1000):
        """Rotate stepper for given steps."""
        print(self.step_time)
        self.calc_pulse_per_sec(speed)
        
        self.dir.value(0 if step_count > 0 else 1)
        
        for i in range(abs(step_count)):
            self.stp.high()
            sleep_us(20)
            self.stp.low()
            sleep_us(self.step_time)
        self.current_position += step_count

    def rel_angle(self, angle):
        """Rotate stepper for given relative angle."""
        steps = int(angle / 360 * self.steps_per_rev)
        self.steps(steps)

    def abs_angle(self, angle):
        """Rotate stepper for given absolute angle since last power on."""
        steps = int(angle / 360 * self.steps_per_rev)
        steps -= self.current_position % self.steps_per_rev
        self.steps(steps)

    def revolution(self, rev_count):
        """Perform given number of full revolutions."""
        self.steps(rev_count * self.steps_per_rev)
        
    def calc_pulse_per_sec(self, speed):
        """calcultate speed."""
        self.step_time =  floor(10**6 / speed) + 50 
        if self.step_time < self.min_step_time :
            self.step_time  = self.min_step_time

    def set_step_time(self, us):
        """Set time in microseconds between each step."""
        if us < 20:  # 20 us is the shortest possible for esp8266
            self.step_time = 20
        else:
            self.step_time = us