from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Callable, Optional


@dataclass
class TelemetryPacket:
    ts: float
    modo: str            # "SIMULADO" o "REAL"
    estado: str          # "AVANZANDO", "ESCANEANDO", "EVADIENDO", "PAUSADO_REMOTO"
    angulo: int          # 0 a 180
    distancia_cm: float
    umbral_cm: int
    velocidad: int
    evasiones: int
    rssi: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryPacket":
        return cls(
            ts=float(data.get("ts", 0)),
            modo=str(data.get("modo", "REAL")),
            estado=str(data.get("estado", "DESCONOCIDO")),
            angulo=int(data.get("angulo", 90)),
            distancia_cm=float(data.get("distancia_cm", 0.0)),
            umbral_cm=int(data.get("umbral_cm", 25)),
            velocidad=int(data.get("velocidad", 75)),
            evasiones=int(data.get("evasiones", 0)),
            rssi=int(data.get("rssi", -100)),
        )


@dataclass
class RoverCommand:
    cmd: str                     # "STOP", "RESUME", "SET_UMBRAL", "SET_SPEED", "SCAN"
    valor: Optional[int] = None

    def to_dict(self) -> dict:
        payload = {"cmd": self.cmd.upper()}
        if self.valor is not None:
            payload["valor"] = int(self.valor)
        return payload


class RoverSource(ABC):
    """Contrato común para fuentes de datos simuladas y reales."""

    @abstractmethod
    def start(self, on_telemetry: Callable[[TelemetryPacket], None]) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def send_command(self, command: RoverCommand) -> None:
        pass

    @abstractmethod
    def mode_name(self) -> str:
        pass
