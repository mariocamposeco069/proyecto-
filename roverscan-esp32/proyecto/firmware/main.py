import time
import json
import network
from machine import Pin
from umqtt.simple import MQTTClient

import config
from drivers import L293DShield, UltrasonicHCSR04, ServoSG90
from rover_fsm import RoverFSM


class ResilientMQTT:
    """Enlace WiFi/MQTT no bloqueante que tolera desconexiones."""

    def __init__(self, on_command):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.client = None
        self.connected = False
        self.on_command = on_command
        self._last_attempt = -10000

    def _mqtt_cb(self, topic, msg):
        try:
            data = json.loads(msg.decode())
            self.on_command(data)
        except Exception as exc:
            print("Comando inválido:", exc)

    def ensure_connection(self):
        now = time.ticks_ms()
        if not self.wlan.isconnected():
            self.connected = False
            if time.ticks_diff(now, self._last_attempt) > 5000:
                self._last_attempt = now
                try:
                    self.wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
                except Exception:
                    pass
            return

        if not self.connected and time.ticks_diff(now, self._last_attempt) > 4000:
            self._last_attempt = now
            try:
                self.client = MQTTClient(
                    config.CLIENT_ID,
                    config.MQTT_BROKER,
                    port=config.MQTT_PORT,
                    keepalive=15,
                )
                self.client.set_callback(self._mqtt_cb)
                self.client.connect()
                self.client.subscribe(config.TOPIC_COMMANDS)
                self.connected = True
                print("MQTT conectado")
            except Exception as exc:
                self.connected = False
                print("Sin MQTT (modo autónomo local):", exc)

    def poll(self):
        if not self.connected:
            return
        try:
            self.client.check_msg()
        except Exception:
            self.connected = False

    def publish(self, payload_dict):
        if not self.connected:
            return
        try:
            self.client.publish(config.TOPIC_TELEMETRY, json.dumps(payload_dict))
        except Exception:
            self.connected = False

    def get_rssi(self):
        if self.wlan.isconnected():
            try:
                return self.wlan.status("rssi")
            except Exception:
                pass
        return -100


def run():
    motors = L293DShield(
        config.PIN_LATCH, config.PIN_CLK, config.PIN_DATA, config.PIN_ENABLE,
        config.PIN_PWM_LEFT, config.PIN_PWM_RIGHT,
        config.INVERT_LEFT, config.INVERT_RIGHT,
    )
    sensor = UltrasonicHCSR04(config.PIN_TRIG, config.PIN_ECHO)
    servo = ServoSG90(config.PIN_SERVO)
    led = Pin(config.PIN_LED, Pin.OUT, value=0)

    rover = RoverFSM(
        motors, sensor, servo, led,
        umbral_cm=config.DEFAULT_UMBRAL_CM,
        speed_pct=config.DEFAULT_SPEED_PCT,
        scan_angles=config.SCAN_ANGLES,
    )

    net = ResilientMQTT(on_command=rover.apply_command)
    last_pub = 0

    while True:
        # 1. Prioridad máxima: control físico local (funciona sin red)
        important_event = rover.step()

        # 2. Enlace de red oportunista (nunca bloquea la evasión)
        net.ensure_connection()
        net.poll()

        now = time.ticks_ms()
        if important_event or time.ticks_diff(now, last_pub) >= 250:
            last_pub = now
            net.publish(rover.telemetry_dict(rssi=net.get_rssi()))

        time.sleep_ms(40)


run()
