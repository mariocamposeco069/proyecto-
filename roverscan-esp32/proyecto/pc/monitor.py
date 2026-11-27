from collections import deque
from datetime import datetime
import threading
import time
from typing import Deque, Dict, Optional

from contracts import RoverCommand, RoverSource, TelemetryPacket


class RoverMonitor:
    """Núcleo de monitoreo agnóstico a la fuente de datos (Simulada o Real)."""

    def __init__(self, source: RoverSource, timeout_sec: float = 4.0):
        self._lock = threading.Lock()
        self._source: Optional[RoverSource] = None
        self._timeout_sec = timeout_sec

        self._latest: Optional[TelemetryPacket] = None
        self._last_rx_time: float = 0.0
        self._radar_map: Dict[int, float] = {30: 100.0, 90: 100.0, 150: 100.0}
        self._history: Deque[dict] = deque(maxlen=60)
        self._events: Deque[str] = deque(maxlen=25)
        self._last_state: str = ""

        self.set_source(source)

    def set_source(self, new_source: RoverSource) -> None:
        """Cambia entre modo simulado y real sin alterar la lógica del Monitor."""
        with self._lock:
            if self._source is not None:
                self._source.stop()
            self._source = new_source
            self._latest = None
            self._last_rx_time = 0.0
            self._log(f"Fuente cambiada a modo {new_source.mode_name()}")
        new_source.start(self.on_packet)

    def on_packet(self, packet: TelemetryPacket) -> None:
        with self._lock:
            self._latest = packet
            self._last_rx_time = time.time()
            self._radar_map[packet.angulo] = packet.distancia_cm
            self._history.append(packet.to_dict())

            if packet.estado != self._last_state:
                self._log(f"Estado -> {packet.estado} ({packet.distancia_cm} cm a {packet.angulo}°)")
                self._last_state = packet.estado

            if packet.distancia_cm <= packet.umbral_cm and packet.estado == "AVANZANDO":
                self._log(f"ALERTA: Obstáculo a {packet.distancia_cm} cm (umbral {packet.umbral_cm} cm)")

    def dispatch_command(self, command: RoverCommand) -> None:
        with self._lock:
            if self._source is None:
                return
            self._source.send_command(command)
            self._log(f"Comando enviado: {command.to_dict()}")

    def _log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self._events.appendleft(f"[{stamp}] {text}")

    def get_snapshot(self) -> dict:
        with self._lock:
            online = (time.time() - self._last_rx_time) <= self._timeout_sec if self._last_rx_time else False
            return {
                "modo_activo": self._source.mode_name() if self._source else "NINGUNO",
                "online": online,
                "latest": self._latest.to_dict() if self._latest else None,
                "radar": dict(self._radar_map),
                "events": list(self._events),
            }

    def shutdown(self) -> None:
        with self._lock:
            if self._source is not None:
                self._source.stop()
