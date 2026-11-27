# --- Red WiFi y MQTT ---
WIFI_SSID = "TU_RED_WIFI"
WIFI_PASS = "TU_PASSWORD"
MQTT_BROKER = "broker.hivemq.com"   # O la IP local de tu PC con Mosquitto
MQTT_PORT = 1883
CLIENT_ID = "roverscan_esp32_01"

TOPIC_TELEMETRY = b"roverscan/telemetria"
TOPIC_COMMANDS = b"roverscan/comandos"

# --- Pines Shield L293D (74HC595 + PWM M1/M2) ---
PIN_LATCH = 16
PIN_CLK = 17
PIN_DATA = 18
PIN_ENABLE = 19
PIN_PWM_LEFT = 25   # M1 (D11 en shield)
PIN_PWM_RIGHT = 26  # M2 (D3 en shield)

# Cambia a True si algún motor gira al revés sin tener que recablear
INVERT_LEFT = False
INVERT_RIGHT = False

# --- Pines Sensores y Actuadores ---
PIN_SERVO = 27
PIN_TRIG = 32
PIN_ECHO = 33
PIN_LED = 23

# --- Parámetros iniciales de navegación ---
DEFAULT_UMBRAL_CM = 25
DEFAULT_SPEED_PCT = 75
SCAN_ANGLES = (30, 90, 150)
