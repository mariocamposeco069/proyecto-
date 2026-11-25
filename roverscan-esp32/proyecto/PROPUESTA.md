# Propuesta de Proyecto: RoverScan (Vehículo Autónomo con Escaneo Ultrasónico)

## 1. Nombre del sistema y dominio
**RoverScan** es un sistema embebido de robótica móvil en el dominio de la **navegación autónoma y mapeo local de obstáculos**. El sistema monitorea continuamente la distancia frontal y, ante un obstáculo, ejecuta un barrido angular de 180° para evaluar el espacio libre y controlar en tiempo real la dirección y velocidad del vehículo mediante una máquina de estados local. Nos importa porque resuelve un problema real de toma de decisiones autónoma con telemetría y supervisión remota dentro de un alcance acotado, confiable y completamente demostrable en vivo.

## 2. Variables y hardware
* **Variables medidas y sensor:** Distancia a obstáculos (en cm) mediante un sensor ultrasónico **HC-SR04** (con divisor de voltaje en `ECHO` de 5 V a 3.3 V) acoplado a un servomotor para asociar cada lectura a un ángulo de barrido (30°–150°), además de métricas internas del enlace (`RSSI` y conteo de evasiones).
* **Actuadores:** Un servomotor **SG90** para orientar el sensor ultrasónico, dos motores DC con caja reductora (chasis 2WD) controlados por un puente H **L298N** con control de velocidad PWM, y un **LED indicador** de estado/alerta.
* **Microcontrolador:** **ESP32 DevKit V1** programado en **MicroPython**, con alimentación dedicada para la etapa de potencia (motores y servo) compartiendo tierra común (`GND`).

## 3. Protocolo tentativo de comunicación
Se usará **WiFi con MQTT** (`umqtt.simple` en MicroPython). Al tratarse de un sistema móvil, el enlace inalámbrico evita ataduras físicas durante la operación. El patrón publicación/suscripción de MQTT desacopla el firmware del Monitor y del Dashboard, habilita **comandos de regreso** en tiempo real (paro de emergencia, ajuste del umbral de distancia, velocidad PWM y disparo de escaneo manual) y permite implementar reconexión no bloqueante para que la evasión autónoma siga operando aunque se pierda la red.

## 4. Reparto inicial del equipo
*(Ajustar según los nombres e integrantes reales)*
* **Mario Alberto Camposeco Enriquez – Hardware y Firmware:** Ensamblaje del chasis, cableado del HC-SR04, SG90 y L298N, y máquina de estados local de evasión y barrido en MicroPython.
* **Rusell Alexis Caamal Uc (TRAVA) – Protocolo y Comunicación:** Configuración WiFi/MQTT, contrato de mensajes (telemetría y comandos de regreso) y resiliencia ante desconexiones.
* **Leonardo Aleman Gonzalez (ROBLOX) – Arquitectura POO y Monitor:** Diseño UML, contratos/interfaces, implementación del Monitor y soporte transparente para el modo simulado ↔ real.
* **Jabes Miguel Fernandes Hernandez (VACA) – Dashboard, Pruebas y Documentación:** Interfaz con vista de barrido/radar y envío de comandos, pruebas de desconexión/tortura, README y bitácora.

