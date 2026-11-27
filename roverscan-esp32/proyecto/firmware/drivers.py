from machine import Pin, PWM, time_pulse_us
import time


class L293DShield:
    """Driver POO para el Shield Arduino L293D (registro 74HC595 + PWM)."""

    # Mapa oficial de bits del 74HC595 en el Shield L293D v1
    M1_A = 1 << 2
    M1_B = 1 << 3
    M2_A = 1 << 1
    M2_B = 1 << 4

    def __init__(self, latch, clk, data, enable, pwm_left, pwm_right,
                 invert_left=False, invert_right=False):
        self.latch = Pin(latch, Pin.OUT, value=0)
        self.clk = Pin(clk, Pin.OUT, value=0)
        self.data = Pin(data, Pin.OUT, value=0)
        self.enable = Pin(enable, Pin.OUT, value=0)  # LOW habilita salidas

        self.pwm_left = PWM(Pin(pwm_left), freq=1000)
        self.pwm_right = PWM(Pin(pwm_right), freq=1000)

        self.invert_left = invert_left
        self.invert_right = invert_right
        self._latch_state = 0
        self.stop()

    def _shift_out(self, byte_val):
        self.latch.value(0)
        for bit in range(7, -1, -1):
            self.clk.value(0)
            self.data.value((byte_val >> bit) & 1)
            self.clk.value(1)
        self.latch.value(1)

    def _set_motor_bits(self, bit_a, bit_b, direction, invert):
        if invert:
            direction = -direction
        self._latch_state &= ~(bit_a | bit_b)
        if direction > 0:
            self._latch_state |= bit_a
        elif direction < 0:
            self._latch_state |= bit_b

    def _pct_to_u16(self, speed_pct):
        clamped = max(0, min(100, int(speed_pct)))
        return int(clamped * 655.35)

    def drive(self, left_dir, right_dir, speed_pct):
        """left_dir y right_dir aceptan -1 (atrás), 0 (alto), 1 (adelante)."""
        self._set_motor_bits(self.M1_A, self.M1_B, left_dir, self.invert_left)
        self._set_motor_bits(self.M2_A, self.M2_B, right_dir, self.invert_right)
        self._shift_out(self._latch_state)

        duty = self._pct_to_u16(speed_pct)
        self.pwm_left.duty_u16(duty if left_dir != 0 else 0)
        self.pwm_right.duty_u16(duty if right_dir != 0 else 0)

    def forward(self, speed_pct):
        self.drive(1, 1, speed_pct)

    def backward(self, speed_pct):
        self.drive(-1, -1, speed_pct)

    def turn_left(self, speed_pct):
        self.drive(-1, 1, speed_pct)

    def turn_right(self, speed_pct):
        self.drive(1, -1, speed_pct)

    def stop(self):
        self.drive(0, 0, 0)


class UltrasonicHCSR04:
    """Sensor ultrasónico con timeout seguro para evitar cuelgues."""

    def __init__(self, trig_pin, echo_pin, timeout_us=25000):
        self.trig = Pin(trig_pin, Pin.OUT, value=0)
        self.echo = Pin(echo_pin, Pin.IN)
        self.timeout_us = timeout_us

    def read_cm(self):
        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)

        duration = time_pulse_us(self.echo, 1, self.timeout_us)
        if duration < 0:
            return 400.0  # Sin obstáculo en rango
        return round((duration * 0.0343) / 2.0, 1)


class ServoSG90:
    """Controlador PWM a 50 Hz para servomotor SG90 (0 a 180 grados)."""

    def __init__(self, pin_num):
        self.pwm = PWM(Pin(pin_num), freq=50)
        self.angle = 90
        self.move(90)

    def move(self, angle):
        angle = max(0, min(180, int(angle)))
        self.angle = angle
        # Pulso de 0.5 ms (0°) a 2.5 ms (180°) sobre periodo de 20 ms
        duty = int(((0.5 + (angle / 180.0) * 2.0) / 20.0) * 65535)
        self.pwm.duty_u16(duty)
