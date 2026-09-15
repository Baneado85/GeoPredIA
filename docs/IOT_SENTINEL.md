# 📡 Extensión IoT: GeoRisk Sentinel

## 1. Propósito
**GeoRisk Sentinel** es una unidad de monitoreo ambiental en tiempo real instalada en áreas estratégicas de la zona de exploración minera. Envía datos de telemetría a la API de **SAP CAP** a través de **HTTPS TLS**.

---

## 2. Esquema de Hardware

```
[ ESP32 NodeMCU Wi-Fi Unit ]
   ├── GPIO 34 ──> Sensor SEN0193 (Humedad Capacitiva de Suelo)
   ├── GPIO 35 ──> Sensor TS-300B (Turbidez de Agua)
   ├── GPIO 32 ──> Sensor GP2Y1010AU0F / SDS011 (Partículas de Polvo PM2.5)
   └── Micro-USB ──> Fuente de Alimentación 5V / Batería Solar
```

### Sensores Recomendados
1. **SEN0193 (Sonda Capacitiva de Suelo)**:
   - Medición no corrosiva de humedad relativa.
   - Detecta saturación que pueda incrementar el riesgo geológico de deslizamiento.
2. **TS-300B (Módulo de Turbidez)**:
   - Medición óptica de partículas en suspensión en cuerpos de agua cercanos.
3. **GP2Y1010AU0F / SDS011 (Sensor de Polvo)**:
   - Emisión de pulso infrarrojo para medir concentración de PM2.5 generado por trabajos de exploración.

---

## 3. Formato del Payload (JSON)
El ESP32 transmite el siguiente formato a `https://<sap-cap-service>/api/iot/telemetry`:

```json
{
  "device_id": "SENTINEL-ESP32-001",
  "zone_id": "ZONE-PERU-ANCA-04",
  "timestamp": "2026-09-15T15:30:00Z",
  "readings": [
    {
      "sensor": "SEN0193_SOIL_MOISTURE",
      "value": 78.4,
      "unit": "%",
      "status": "NORMAL"
    },
    {
      "sensor": "TS300B_WATER_TURBIDITY",
      "value": 142.5,
      "unit": "NTU",
      "status": "WARNING"
    },
    {
      "sensor": "SDS011_PM25_DUST",
      "value": 45.2,
      "unit": "ug/m3",
      "status": "NORMAL"
    }
  ],
  "is_simulated": false
}
```

---

## 4. Simulador IoT (Fallback sin Hardware)
En caso de presentar el proyecto sin el hardware físico montado, se incluye el script de simulación `iot/simulator/iot_simulator.py` que transmite telemetría sintética realista con flag `"is_simulated": true`.
