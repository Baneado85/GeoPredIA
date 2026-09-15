import time
import random
import requests
import json

CAP_ENDPOINT = "http://localhost:4004/api/iot/telemetry"

def generate_telemetry():
    soil_moisture = round(random.uniform(20.0, 85.0), 2)
    turbidity = round(random.uniform(10.0, 350.0), 2)
    dust_pm25 = round(random.uniform(5.0, 60.0), 2)

    soil_status = "WARNING" if soil_moisture > 75.0 else "NORMAL"
    turbidity_status = "CRITICAL" if turbidity > 250.0 else ("WARNING" if turbidity > 150.0 else "NORMAL")

    payload = {
        "device_id": "SENTINEL-SIMULATOR-001",
        "zone_id": "ZONE-PERU-ANCA-04",
        "readings": [
            {
                "sensor": "SEN0193_SOIL_MOISTURE",
                "value": soil_moisture,
                "unit": "%",
                "status": soil_status
            },
            {
                "sensor": "TS300B_WATER_TURBIDITY",
                "value": turbidity,
                "unit": "NTU",
                "status": turbidity_status
            },
            {
                "sensor": "SDS011_PM25_DUST",
                "value": dust_pm25,
                "unit": "ug/m3",
                "status": "NORMAL"
            }
        ],
        "is_simulated": True
    }
    return payload

def main():
    print("📡 Iniciando Simulador de Telemetría IoT GeoRisk Sentinel...")
    print(f"Objetivo Endpoint: {CAP_ENDPOINT}\n")
    
    while True:
        data = generate_telemetry()
        print(f"Sending Telemetry: Soil={data['readings'][0]['value']}% | Turbidity={data['readings'][1]['value']} NTU")
        try:
            res = requests.post(CAP_ENDPOINT, json=data, timeout=3)
            print(f"-> Respuesta Servidor: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"-> Transmisión simulada (Offline test): {data['readings']}")
        time.sleep(5)

if __name__ == "__main__":
    main()
