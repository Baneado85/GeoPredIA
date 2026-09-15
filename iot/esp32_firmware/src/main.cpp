#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "https://your-sap-cap-service.cfapps.us10.hana.ondemand.com/api/iot/telemetry";

const int SOIL_PIN = 34;
const int TURBIDITY_PIN = 35;

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    Serial.print("Conectando a WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Conectado!");
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        http.addHeader("Content-Type", "application/json");

        int rawSoil = analogRead(SOIL_PIN);
        float soilMoisturePercent = map(rawSoil, 4095, 0, 0, 100);

        int rawTurbidity = analogRead(TURBIDITY_PIN);
        float turbidityNTU = (rawTurbidity / 4095.0) * 500.0;

        String payload = "{";
        payload += "\"device_id\":\"SENTINEL-ESP32-001\",";
        payload += "\"zone_id\":\"ZONE-PERU-ANCA-04\",";
        payload += "\"readings\":[";
        payload += "{\"sensor\":\"SEN0193_SOIL\",\"value\":" + String(soilMoisturePercent) + ",\"unit\":\"%\",\"status\":\"" + (soilMoisturePercent > 75 ? "WARNING" : "NORMAL") + "\"},";
        payload += "{\"sensor\":\"TS300B_TURBIDITY\",\"value\":" + String(turbidityNTU) + ",\"unit\":\"NTU\",\"status\":\"" + (turbidityNTU > 200 ? "WARNING" : "NORMAL") + "\"}";
        payload += "],\"is_simulated\":false}";

        int httpResponseCode = http.POST(payload);
        Serial.print("HTTP Code: ");
        Serial.println(httpResponseCode);
        http.end();
    }
    delay(10000); // Envia telemetria cada 10 segundos
}
