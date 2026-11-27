import json
import random
import threading
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from contracts import RoverCommand, RoverSource, TelemetryPacket


class SimulatedRoverSource(RoverSource):
    """Simulador fiel de la FSM del RoverScan (cumple el mismo contrato que el ESP32)."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[TelemetryPacket], None]] = None

        self._estado = "AVANZANDO"
        self._angulo = 90
        self._distancia = 110.0
        self._umbral = 25
        self._velocidad = 75
        self._evasiones = 0
        self._lock = threading.Lock()

    def mode_name(self) -> str:
        return "SIMULADO"

    def start(self, on_telemetry: Callable[[TelemetryPacket], None]) -> None:
        self._callback = on_telemetry
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def send_command(self, command: RoverCommand) -> None:
        with self._lock:
            cmd = command.cmd.upper()
            if cmd == "STOP":
                self._estado = "PAUSADO_REMOTO"
            elif cmd == "RESUME":
                self._estado = "AVANZANDO"
                self._angulo = 90
            elif cmd == "SET_UMBRAL" and command.valor is not None:
                self._umbral = max(10, min(100, int(command.valor)))
            elif cmd == "SET_SPEED" and command.valor is not None:
                self._velocidad = max(30, min(100, int(command.valor)))
            elif cmd == "SCAN":
                self._estado = "ESCANEANDO_MANUAL"

    def _emit(self) -> None:
        if not self._callback:
            return
        pkt = TelemetryPacket(
            ts=time.time(),
            modo="SIMULADO",
            estado=self._estado,
            angulo=self._angulo,
            distancia_cm=round(self._distancia, 1),
            umbral_cm=self._umbral,
            velocidad=self._velocidad,
            evasiones=self._evasiones,
            rssi=random.randint(-62, -52),
        )
        self._callback(pkt)

    def _loop(self) -> None:
        while self._running:
            with self._lock:
                estado = self._estado

            if estado == "AVANZANDO":
                with self._lock:
                    self._angulo = 90
                    self._distancia = max(10.0, self._distancia - random.uniform(4.0, 9.0))
                    if self._distancia <= self._umbral:
                        self._estado = "ESCANEANDO"
                    self._emit()
                time.sleep(0.25)

            elif estado in ("ESCANEANDO", "ESCANEANDO_MANUAL"):
                for ang in (30, 90, 150):
                    if not self._running:
                        return
                    with self._lock:
                        self._angulo = ang
                        self._distancia = random.uniform(18.0, 140.0)
                        self._emit()
                    time.sleep(0.35)
                with self._lock:
                    self._angulo = 90
                    if self._estado == "ESCANEANDO_MANUAL":
                        self._estado = "PAUSADO_REMOTO"
                    else:
                        self._evasiones += 1
                        self._estado = "EVADIENDO"
                    self._emit()

            elif estado == "EVADIENDO":
                time.sleep(0.6)
                with self._lock:
                    self._distancia = random.uniform(85.0, 150.0)
                    self._estado = "AVANZANDO"
                    self._emit()

            else:  # PAUSADO_REMOTO
                with self._lock:
                    self._emit()
                time.sleep(0.4)


class MqttRoverSource(RoverSource):
    """Fuente real conectada al ESP32 mediante MQTT."""

    def __init__(self, broker="broker.hivemq.com", port=1883,
                 topic_telemetry="roverscan/telemetria",
                 topic_commands="roverscan/comandos"):
        self.broker = broker
        self.port = port
        self.topic_telemetry = topic_telemetry
        self.topic_commands = topic_commands
        self._callback: Optional[Callable[[TelemetryPacket], None]] = None

        # Compatible con paho-mqtt v1 y v2
        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            self._client = mqtt.Client()

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def mode_name(self) -> str:
        return "REAL"

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        client.subscribe(self.topic_telemetry)

    def _on_message(self, client, userdata, msg):
        if not self._callback:
            return
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            data["modo"] = "REAL"
            self._callback(TelemetryPacket.from_dict(data))
        except Exception as exc:
            print("Paquete MQTT inválido:", exc)

    def start(self, on_telemetry: Callable[[TelemetryPacket], None]) -> None:
        self._callback = on_telemetry
        self._client.connect_async(self.broker, self.port, keepalive=15)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def send_command(self, command: RoverCommand) -> None:
        payload = json.dumps(command.to_dict())
        self._client.publish(self.topic_commands, payload)
