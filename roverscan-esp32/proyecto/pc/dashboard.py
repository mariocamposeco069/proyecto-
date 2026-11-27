from flask import Flask, jsonify, render_template_string, request

from contracts import RoverCommand
from monitor import RoverMonitor
from sources import MqttRoverSource, SimulatedRoverSource

MQTT_BROKER = "broker.hivemq.com"   # Igualar con firmware/config.py
MQTT_PORT = 1883

app = Flask(__name__)
monitor = RoverMonitor(SimulatedRoverSource())

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>RoverScan Dashboard</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }
    .grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; max-width: 1100px; margin: auto; }
    .card { background: #1e293b; border-radius: 12px; padding: 18px; box-shadow: 0 4px 16px rgba(0,0,0,.3); }
    h1, h2 { margin-top: 0; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
    button { border: none; padding: 10px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; color: #fff; background: #3b82f6; }
    button.danger { background: #ef4444; }
    button.success { background: #10b981; }
    button.secondary { background: #475569; }
    .badge { padding: 4px 10px; border-radius: 999px; font-size: 0.85rem; font-weight: 700; }
    .ok { background: #065f46; color: #a7f3d0; }
    .off { background: #7f1d1d; color: #fecaca; }
    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
    .metric { background: #0f172a; padding: 12px; border-radius: 8px; text-align: center; }
    .metric strong { display: block; font-size: 1.35rem; color: #38bdf8; }
    canvas { width: 100%; background: #020617; border-radius: 8px; display: block; }
    ul { list-style: none; padding: 0; max-height: 220px; overflow-y: auto; font-family: monospace; font-size: 0.85rem; }
    li { padding: 4px 0; border-bottom: 1px solid #334155; }
  </style>
</head>
<body>
  <div class="grid">
    <div class="card">
      <div class="row" style="justify-content: space-between;">
        <h1>RoverScan Monitor</h1>
        <div>
          <span id="badge-mode" class="badge ok">SIMULADO</span>
          <span id="badge-conn" class="badge off">SIN SEÑAL</span>
        </div>
      </div>

      <div class="metrics">
        <div class="metric">Estado<strong id="m-state">--</strong></div>
        <div class="metric">Distancia<strong id="m-dist">-- cm</strong></div>
        <div class="metric">Ángulo<strong id="m-ang">--°</strong></div>
        <div class="metric">Umbral<strong id="m-umb">-- cm</strong></div>
        <div class="metric">Evasiones<strong id="m-eva">0</strong></div>
        <div class="metric">WiFi RSSI<strong id="m-rssi">-- dBm</strong></div>
      </div>

      <canvas id="radar" width="520" height="290"></canvas>
    </div>

    <div class="card">
      <h2>Modo de Operación (Req. 8)</h2>
      <div class="row">
        <button class="secondary" onclick="setMode('SIMULADO')">Usar Simulado</button>
        <button onclick="setMode('REAL')">Usar ESP32 Real (MQTT)</button>
      </div>

      <h2>Comandos de Regreso</h2>
      <div class="row">
        <button class="danger" onclick="sendCmd('STOP')">Paro de Emergencia</button>
        <button class="success" onclick="sendCmd('RESUME')">Reanudar</button>
        <button onclick="sendCmd('SCAN')">Barrido Manual</button>
      </div>

      <div class="row">
        <label>Umbral (cm): <span id="lbl-umb">25</span></label>
        <input id="inp-umb" type="range" min="15" max="80" value="25" oninput="document.getElementById('lbl-umb').textContent=this.value" />
        <button class="secondary" onclick="sendCmd('SET_UMBRAL', document.getElementById('inp-umb').value)">Aplicar</button>
      </div>

      <div class="row">
        <label>Velocidad (%): <span id="lbl-spd">75</span></label>
        <input id="inp-spd" type="range" min="40" max="100" value="75" oninput="document.getElementById('lbl-spd').textContent=this.value" />
        <button class="secondary" onclick="sendCmd('SET_SPEED', document.getElementById('inp-spd').value)">Aplicar</button>
      </div>

      <h2>Bitácora del Monitor</h2>
      <ul id="events"></ul>
    </div>
  </div>

<script>
const canvas = document.getElementById('radar');
const ctx = canvas.getContext('2d');

function drawRadar(radarMap, currentAngle, umbral) {
  const w = canvas.width, h = canvas.height;
  const cx = w / 2, cy = h - 20, maxR = h - 40, maxCm = 150;
  ctx.clearRect(0, 0, w, h);

  // Arcos de referencia
  ctx.strokeStyle = '#1e3a5f';
  ctx.lineWidth = 1;
  [50, 100, 150].forEach(cm => {
    ctx.beginPath();
    ctx.arc(cx, cy, (cm / maxCm) * maxR, Math.PI, 0);
    ctx.stroke();
  });

  // Arco de umbral crítico
  ctx.strokeStyle = '#ef4444';
  ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.arc(cx, cy, (Math.min(umbral, maxCm) / maxCm) * maxR, Math.PI, 0);
  ctx.stroke();
  ctx.setLineDash([]);

  // Rayo actual del servo
  const radNow = Math.PI - (currentAngle * Math.PI / 180);
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(radNow) * maxR, cy - Math.sin(radNow) * maxR);
  ctx.stroke();

  // Puntos detectados
  Object.entries(radarMap).forEach(([ang, dist]) => {
    const rad = Math.PI - (Number(ang) * Math.PI / 180);
    const r = (Math.min(dist, maxCm) / maxCm) * maxR;
    const x = cx + Math.cos(rad) * r;
    const y = cy - Math.sin(rad) * r;
    ctx.fillStyle = dist <= umbral ? '#ef4444' : '#22c55e';
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI * 2);
    ctx.fill();
  });
}

async function sendCmd(cmd, valor = null) {
  await fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd, valor })
  });
}

async function setMode(mode) {
  await fetch('/api/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  });
}

async function poll() {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();

    document.getElementById('badge-mode').textContent = data.modo_activo;
    const conn = document.getElementById('badge-conn');
    conn.textContent = data.online ? 'EN LÍNEA' : 'DESCONECTADO';
    conn.className = 'badge ' + (data.online ? 'ok' : 'off');

    if (data.latest) {
      const l = data.latest;
      document.getElementById('m-state').textContent = l.estado;
      document.getElementById('m-dist').textContent = l.distancia_cm + ' cm';
      document.getElementById('m-ang').textContent = l.angulo + '°';
      document.getElementById('m-umb').textContent = l.umbral_cm + ' cm';
      document.getElementById('m-eva').textContent = l.evasiones;
      document.getElementById('m-rssi').textContent = l.rssi + ' dBm';
      drawRadar(data.radar, l.angulo, l.umbral_cm);
    }

    const ul = document.getElementById('events');
    ul.innerHTML = data.events.map(e => `<li>${e}</li>`).join('');
  } catch (e) {
    console.error(e);
  }
}

setInterval(poll, 250);
poll();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/state")
def api_state():
    return jsonify(monitor.get_snapshot())


@app.route("/api/command", methods=["POST"])
def api_command():
    body = request.get_json(force=True)
    cmd = RoverCommand(cmd=body["cmd"], valor=body.get("valor"))
    monitor.dispatch_command(cmd)
    return jsonify({"ok": True})


@app.route("/api/mode", methods=["POST"])
def api_mode():
    mode = request.get_json(force=True).get("mode", "SIMULADO").upper()
    if mode == "REAL":
        monitor.set_source(MqttRoverSource(broker=MQTT_BROKER, port=MQTT_PORT))
    else:
        monitor.set_source(SimulatedRoverSource())
    return jsonify({"ok": True, "mode": mode})


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        monitor.shutdown()
