#pragma once

// Copiar como secrets.h. Ese archivo se ignora en Git. Nunca subir claves reales.
static const char WIFI_SSID[] = "REEMPLAZAR_WIFI";
static const char WIFI_PASSWORD[] = "REEMPLAZAR_PASSWORD";
static const char TELEMETRY_URL[] = "https://api.example.com/api/telemetry";
static const char DEVICE_KEY[] = "REEMPLAZAR_CLAVE_DISPOSITIVO";
static const char DEVICE_ID[] = "sentinel-01";
static const char ZONE_ID[] = "Z-001";

// Certificado PEM de la CA que verifica TU servidor HTTPS, obtenido de su
// administrador/proveedor. No pegar aquí la clave privada del servidor.
// Sin una CA válida el firmware NO transmite. No utilizar setInsecure().
static const char ROOT_CA[] = R"PEM(
-----BEGIN CERTIFICATE-----
REEMPLAZAR_CON_CERTIFICADO_CA_VALIDO
-----END CERTIFICATE-----
)PEM";

static const bool DHT_ENABLED = true;
static const bool WATER_ENABLED = true;
static const bool SOIL_ENABLED = true;

// Medir ambos extremos con TU placa, sensor, tierra y alimentación 3.3 V.
// Los valores cero son placeholders; el sensor envía null hasta calibrarlo.
static const bool SOIL_CALIBRATED = false;
static const int SOIL_DRY_RAW = 0;
static const int SOIL_WET_RAW = 0;
