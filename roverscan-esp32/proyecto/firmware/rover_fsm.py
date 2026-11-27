import time


class RoverFSM:
    """Máquina de estados local para navegación y evasión autónoma."""

    def __init__(self, motors, sensor, servo, led, umbral_cm=25, speed_pct=75,
                 scan_angles=(30, 90, 150)):
        self.motors = motors
        self.sensor = sensor
        self.servo = servo
        self.led = led

        self.umbral_cm = umbral_cm
        self.speed_pct = speed_pct
        self.scan_angles = scan_angles

        self.state = "AVANZANDO"
        self.last_distance = 100.0
        self.evasiones = 0

        self._scan_idx = 0
        self._scan_results = {}
        self._action_until = 0
        self._evade_phase = 0
        self._turn_dir = "LEFT"

    def apply_command(self, cmd_dict):
        cmd = cmd_dict.get("cmd", "").upper()
        valor = cmd_dict.get("valor")

        if cmd == "STOP":
            self.state = "PAUSADO_REMOTO"
            self.motors.stop()
            self.led.value(1)
        elif cmd == "RESUME":
            self.servo.move(90)
            self.state = "AVANZANDO"
            self.led.value(0)
        elif cmd == "SET_UMBRAL" and valor is not None:
            self.umbral_cm = max(10, min(100, int(valor)))
        elif cmd == "SET_SPEED" and valor is not None:
            self.speed_pct = max(30, min(100, int(valor)))
        elif cmd == "SCAN":
            self._start_scan(manual=True)

    def _start_scan(self, manual=False):
        self.motors.stop()
        self.led.value(1)
        self.state = "ESCANEANDO_MANUAL" if manual else "ESCANEANDO"
        self._scan_idx = 0
        self._scan_results = {}
        self.servo.move(self.scan_angles[0])
        self._action_until = time.ticks_add(time.ticks_ms(), 320)

    def step(self):
        """Ejecuta un ciclo corto de control. Retorna True si hay nueva lectura relevante."""
        now = time.ticks_ms()

        if self.state == "PAUSADO_REMOTO":
            self.motors.stop()
            return False

        if self.state == "AVANZANDO":
            self.last_distance = self.sensor.read_cm()
            if self.last_distance <= self.umbral_cm:
                self._start_scan(manual=False)
                return True
            self.led.value(0)
            self.motors.forward(self.speed_pct)
            return False

        if self.state in ("ESCANEANDO", "ESCANEANDO_MANUAL"):
            if time.ticks_diff(now, self._action_until) < 0:
                return False

            angle = self.scan_angles[self._scan_idx]
            dist = self.sensor.read_cm()
            self.last_distance = dist
            self._scan_results[angle] = dist
            self._scan_idx += 1

            if self._scan_idx < len(self.scan_angles):
                self.servo.move(self.scan_angles[self._scan_idx])
                self._action_until = time.ticks_add(now, 320)
                return True

            # Fin del barrido: regresar al centro y decidir
            self.servo.move(90)
            if self.state == "ESCANEANDO_MANUAL":
                self.state = "PAUSADO_REMOTO"
                return True

            dist_right = self._scan_results.get(self.scan_angles[0], 0)
            dist_left = self._scan_results.get(self.scan_angles[-1], 0)
            self._turn_dir = "LEFT" if dist_left >= dist_right else "RIGHT"

            self.evasiones += 1
            self.state = "EVADIENDO"
            self._evade_phase = 0
            self.motors.backward(self.speed_pct)
            self._action_until = time.ticks_add(now, 350)
            return True

        if self.state == "EVADIENDO":
            if time.ticks_diff(now, self._action_until) < 0:
                return False

            if self._evade_phase == 0:
                self._evade_phase = 1
                if self._turn_dir == "LEFT":
                    self.motors.turn_left(self.speed_pct)
                else:
                    self.motors.turn_right(self.speed_pct)
                self._action_until = time.ticks_add(now, 450)
                return False

            self.motors.stop()
            self.led.value(0)
            self.state = "AVANZANDO"
            return True

        return False

    def telemetry_dict(self, rssi=-100):
        return {
            "ts": time.ticks_ms(),
            "modo": "REAL",
            "estado": self.state,
            "angulo": self.servo.angle,
            "distancia_cm": self.last_distance,
            "umbral_cm": self.umbral_cm,
            "velocidad": self.speed_pct,
            "evasiones": self.evasiones,
            "rssi": rssi,
        }
