/* GeoPredIA Sentinel: prototipo de banco ESP32 clásico DevKit V1, 30 pines.
 * DHT11 DATA=27; DS18B20 DQ=26; suelo AO=34 (ADC1). Todo sensor a 3.3 V.
 * Bibliotecas: ArduinoJson 7, DHT sensor library + Adafruit Unified Sensor,
 * OneWire y DallasTemperature. Consultar docs/IOT_SENTINEL.md.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <time.h>
#include <math.h>
#include <string.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copiar secrets.example.h a secrets.h y configurar Wi-Fi, endpoint, clave y CA."
#endif

static const uint8_t DHT_PIN = 27;
static const uint8_t WATER_PIN = 26;
static const uint8_t SOIL_PIN = 34;
static const unsigned long SAMPLE_INTERVAL_MS = 30000;
static const unsigned long WIFI_TIMEOUT_MS = 12000;
DHT dht(DHT_PIN, DHT11);
OneWire oneWire(WATER_PIN);
DallasTemperature water(&oneWire);
bool configReady = false;
unsigned long lastSample = 0;

bool validConfig() {
  return String(TELEMETRY_URL).startsWith("https://") &&
         String(TELEMETRY_URL).endsWith("/api/telemetry") &&
         strlen(DEVICE_KEY) >= 16 && strlen(DEVICE_ID) > 0 &&
         strlen(ZONE_ID) > 0 &&
         strstr(DEVICE_KEY, "REEMPLAZAR") == nullptr &&
         strstr(ROOT_CA, "REEMPLAZAR") == nullptr &&
         strstr(ROOT_CA, "-----BEGIN CERTIFICATE-----") != nullptr;
}

bool connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(200);
  }
  return WiFi.status() == WL_CONNECTED;
}

void setReading(JsonObject readings, const char* key, float value,
                float minimum, float maximum) {
  if (!isfinite(value) || value < minimum || value > maximum) {
    readings[key] = nullptr;
  } else {
    readings[key] = roundf(value * 100.0f) / 100.0f;
  }
}

float readSoil() {
  if (!SOIL_ENABLED) return NAN;
  long sum = 0;
  for (int i = 0; i < 16; i++) {
    sum += analogRead(SOIL_PIN);
    delay(5);
  }
  int raw = sum / 16;
  // Lectura para calibración, nunca contiene credenciales.
  Serial.printf("Suelo raw=%d; calibrado=%s\n", raw, SOIL_CALIBRATED ? "si" : "no");
  if (!SOIL_CALIBRATED || abs(SOIL_DRY_RAW - SOIL_WET_RAW) < 100 ||
      SOIL_DRY_RAW < 1 || SOIL_DRY_RAW > 4094 ||
      SOIL_WET_RAW < 1 || SOIL_WET_RAW > 4094 || raw <= 10 || raw >= 4085) {
    return NAN;
  }
  // Índice relativo entre dos referencias locales; NO humedad volumétrica.
  float pct = 100.0f * (raw - SOIL_DRY_RAW) / (SOIL_WET_RAW - SOIL_DRY_RAW);
  return constrain(pct, 0.0f, 100.0f);
}

void sampleAndSend() {
  time_t observedTime = time(nullptr);
  // Obtener lecturas incluso sin red permite calibrar por el monitor serie.
  float airTemp = DHT_ENABLED ? dht.readTemperature() : NAN;
  float airHumidity = DHT_ENABLED ? dht.readHumidity() : NAN;
  float soil = readSoil();
  float waterTemp = NAN;
  if (WATER_ENABLED) {
    water.requestTemperatures();  // Conversión bloqueante antes de leer.
    float measured = water.getTempCByIndex(0);
    if (measured != DEVICE_DISCONNECTED_C) waterTemp = measured;
  }
  if (!configReady) {
    Serial.println("Configurar endpoint HTTPS, clave y CA antes de transmitir.");
    return;
  }
  if (!connectWifi()) {
    Serial.println("Sin Wi-Fi: muestra descartada; se intentará en el siguiente ciclo.");
    return;
  }
  if (observedTime < 1704067200) {
    Serial.println("Sin hora UTC sincronizada: no se transmite ni se inventa una fecha.");
    return;
  }
  struct tm utc;
  gmtime_r(&observedTime, &utc);
  char observedAt[25];
  strftime(observedAt, sizeof(observedAt), "%Y-%m-%dT%H:%M:%SZ", &utc);

  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["zone_id"] = ZONE_ID;
  doc["observed_at"] = observedAt;
  doc["source"] = "device";
  JsonObject readings = doc["readings"].to<JsonObject>();
  setReading(readings, "air_temperature_c", airTemp, 0.0f, 50.0f);
  setReading(readings, "air_humidity_pct", airHumidity, 0.0f, 100.0f);
  setReading(readings, "soil_moisture_pct", soil, 0.0f, 100.0f);
  setReading(readings, "water_temperature_c", waterTemp, -55.0f, 125.0f);
  String payload;
  serializeJson(doc, payload);

  WiFiClientSecure client;
  client.setCACert(ROOT_CA);
  HTTPClient http;
  http.setTimeout(10000);
  http.setConnectTimeout(10000);
  http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
  if (!http.begin(client, TELEMETRY_URL)) {
    Serial.println("No se pudo iniciar HTTPS.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  int code = http.POST(payload);
  Serial.printf("Telemetría HTTP=%d; dispositivo=%s\n", code, DEVICE_ID);
  if (code < 200 || code >= 300) {
    Serial.println("Muestra no confirmada; no hay almacenamiento offline en esta versión.");
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  if (DHT_ENABLED) dht.begin();
  if (WATER_ENABLED) {
    water.begin();
    water.setResolution(12);
    water.setWaitForConversion(true);
  }
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  configReady = validConfig();
  if (configReady) connectWifi();
  // NTP también queda configurado para cuando se recupere la conexión.
  configTime(0, 0, "pool.ntp.org", "time.cloudflare.com");
  delay(2500);  // DHT11: permitir estabilización inicial.
  lastSample = millis() - SAMPLE_INTERVAL_MS;
}

void loop() {
  if (millis() - lastSample >= SAMPLE_INTERVAL_MS) {
    lastSample = millis();
    sampleAndSend();
  }
  delay(20);
}
