# Sentinel: IoT de banco con presupuesto de S/100

El kit envía temperatura/humedad del aire, temperatura del agua y un índice relativo de humedad del suelo. Es evidencia ambiental local complementaria para GeoPredIA. No mide pH, metales, partículas, potabilidad ni predice deslizamientos. Agregar agua a una muestra sirve para mostrar una variación observada, sin atribuirla a actividad minera.

## Materiales

Presupuesto orientativo acordado el 15/09/2026; confirmar stock, versión y costo de envío antes de comprar. No se compró ningún componente. Se reutilizan laptop, conexión Wi-Fi y recipientes.

| Material | Cantidad | Subtotal S/ |
|---|---:|---:|
| ESP32 DevKit V1 clásico de 30 pines, con pines soldados | 1 | 32.00 |
| Módulo DHT11 compatible con alimentación de 3.3 V | 1 | 8.00 |
| Sensor capacitivo de suelo v1.2 | 1 | 4.10 |
| Sonda DS18B20 | 1 | 8.50 |
| Adaptador de terminales para DS18B20 | 1 | 5.00 |
| Protoboard de 400 puntos | 2 | 10.00 |
| Paquete de jumpers macho–macho + macho–hembra | 1 de cada | 8.70 |
| USB-C de datos, reutilizable | 1 | 10.00 estimado |
| Resistencias 4.7 kΩ y 10 kΩ de apoyo | Lote pequeño | 2.00 estimado |
| **Materiales** | | **88.30** |
| **Margen hasta S/100 para envío/imprevistos** | | **11.70** |

Referencias comerciales del presupuesto: [ESP32](https://www.electromania.pe/producto/esp32-devkit-v1-30p-tipo-c/), [DHT11](https://www.electromania.pe/producto/sensor-de-temperatura-y-humedad-dht11/), [suelo](https://www.electromania.pe/producto/higrometro-capacitivo-v1-2/), [DS18B20](https://www.electromania.pe/producto/sensor-de-temperatura-ds18b20/), [protoboard](https://www.electromania.pe/producto/protoboard-blanco-de-400-puntos/). Si el envío excede el margen, aplazar DS18B20 y adaptador reduce los materiales a S/74.80. En ese caso establecer `WATER_ENABLED = false`.

## Conexiones

Para un **ESP32 clásico DevKit V1**; los GPIO no son la posición física del pin. Verificar las etiquetas de la placa comprada, porque ESP32-C3/S3 y otras variantes tienen asignaciones diferentes. Cortar la alimentación mientras se cablea.

| Sensor | Alimentación | Tierra | Señal |
|---|---|---|---|
| DHT11 módulo 3.3 V | VCC → 3V3 | GND → GND | DATA/S → GPIO27 |
| Capacitivo de suelo v1.2 | VCC → 3V3 | GND → GND | AO → GPIO34 |
| DS18B20, mediante adaptador | VDD → 3V3 | GND → GND | DQ → GPIO26 |

Todas las tierras se unen. Alimentar el ESP32 por USB desde la laptop y los sensores desde 3V3. No conectar una salida de 5 V a un GPIO. En la sonda DS18B20, confirmar función de cada cable con su vendedor; los colores no son una garantía.

DS18B20 necesita una resistencia de aproximadamente **4.7 kΩ entre DQ y 3V3**, salvo que el adaptador ya la incluya. Para DHT11, comprobar si el módulo incluye pull-up; si no, añadir aproximadamente 10 kΩ entre DATA y 3V3. Elegir un módulo DHT11 cuya documentación admita 3.3 V: hay módulos que especifican 5 V y necesitan revisar la adaptación eléctrica.

GPIO34 utiliza ADC1 para poder leer el suelo mientras funciona Wi-Fi. El sensor genérico debe alimentarse a 3.3 V y verificarse con un multímetro; comprobar que su salida está dentro del rango permitido. El firmware usa ADC de 12 bits y promedia 16 lecturas. Esa configuración no convierte la placa en un instrumento calibrado.

Mantener secos protoboards, placa y conectores. Solo la parte encapsulada de la sonda toca el agua; el módulo/adaptador queda fuera. En el sensor de suelo, mantener la electrónica superior y el conector sobre la superficie. Esta versión es para una mesa de demostración, sin lluvia ni instalación permanente.

## Preparar el firmware

1. Instalar Arduino IDE y el paquete oficial [Arduino-ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).
2. Instalar desde Library Manager: **ArduinoJson 7**, **DHT sensor library by Adafruit**, **Adafruit Unified Sensor**, **OneWire** y **DallasTemperature**.
3. Abrir `iot/firmware/geopredia_sentinel_v1/geopredia_sentinel_v1.ino`. Seleccionar la placa ESP32 adecuada y su puerto.
4. Copiar `secrets.example.h` a `secrets.h` en la misma carpeta. Este último archivo está excluido de Git.
5. Configurar Wi-Fi, URL `https://.../api/telemetry`, clave, `DEVICE_ID` y `ZONE_ID`. El catálogo del backend debe contener la zona elegida.
6. Obtener del administrador del endpoint el certificado público de la CA que valida su servidor y copiarlo en `ROOT_CA`. No usar `setInsecure()` ni una URL HTTP en el dispositivo. La hora UTC se sincroniza por NTP para verificar certificados y fechar muestras.
7. Compilar y cargar. Abrir el monitor serie a 115200 baudios. El primer envío necesita conexión y hora válidas.

**Estado de verificación:** el código se entrega para compilar y probar con la placa; no se realizó validación eléctrica ni carga en hardware durante su generación. Se necesitan el endpoint HTTPS y la configuración real del equipo. No hay una CA o clave operativa preincluida.

La muestra se envía cada 30 segundos. Los errores digitales, lecturas inválidas y sensores desactivados producen `null`. No se reemplazan por cero. Si falta Wi-Fi o falla el envío, la muestra se descarta y se avisa por serial; esta versión no implementa almacenamiento offline. No se imprimen credenciales.

## Calibrar el sensor de suelo

1. Mantener `SOIL_CALIBRATED = false`. El monitor serie mostrará `Suelo raw=...`; la API recibirá `soil_moisture_pct: null`.
2. Usar una muestra de tierra seca representativa, con inserción y compactación constantes; registrar varias lecturas estables. Guardar la referencia en `SOIL_DRY_RAW`.
3. Humedecer otra muestra del mismo suelo de forma reproducible, dejando drenar el exceso y manteniendo la misma profundidad. Registrar su referencia en `SOIL_WET_RAW`.
4. Los extremos deben ser diferentes y estar dentro de 1–4094. El firmware exige separación de al menos 100 cuentas como comprobación básica; no es una certificación de calibración.
5. Cambiar `SOIL_CALIBRATED = true`, compilar y cargar de nuevo. Guardar sensor, fecha, tipo de suelo, alimentación, extremos y responsable en una ficha de calibración.
6. Repetir una muestra intermedia y comprobar que responde de manera coherente. Si cambia sensor, placa, suelo o alimentación, recalibrar.

El cálculo `100 × (raw − seco) / (húmedo − seco)` se limita a 0–100. Es un **índice relativo entre esas referencias**, no el porcentaje volumétrico de agua del suelo. Un cable analógico desconectado puede producir valores aparentemente válidos: el ADC no detecta todos los fallos. Si se retira el sensor, establecer `SOIL_ENABLED = false`.

## Contrato de envío

```http
POST /api/telemetry
Content-Type: application/json
X-Device-Key: CLAVE_DEL_DISPOSITIVO
```

```json
{
  "device_id": "sentinel-01",
  "zone_id": "Z-001",
  "observed_at": "2026-09-15T15:00:00Z",
  "source": "device",
  "readings": {
    "air_temperature_c": 22.0,
    "air_humidity_pct": 54.0,
    "soil_moisture_pct": null,
    "water_temperature_c": 18.5
  }
}
```

Este JSON muestra el formato, no una medición realizada. `source=device` se usa solo para sensores físicos y `source=simulator` para el programa de prueba. Las credenciales de HANA/SAP permanecen en el servidor; no entran en el ESP32. El prototipo autentica con una clave compartida: una instalación posterior requiere identidad y rotación por dispositivo.

## Probar sin comprar sensores

Desde la raíz del repositorio, con Python 3.10 o superior:

```powershell
python iot/simulator/sentinel_simulator.py --dry-run --once
```

Para enviar a la API local, configurar `GEOPREDIA_DEVICE_KEY` con la misma clave que el backend y ejecutar:

```powershell
python iot/simulator/sentinel_simulator.py --url http://127.0.0.1:8000/api/telemetry --once
python iot/simulator/sentinel_simulator.py --interval 30
```

La variable del simulador se llama `GEOPREDIA_DEVICE_KEY` y debe tener el mismo valor que `DEVICE_API_KEY` del servidor. No poner una clave real en un comando guardado en Git. `--device-key` existe como alternativa, pero las variables de entorno evitan dejarla en el historial de argumentos. `--ca-file ruta/ca.pem` permite añadir una CA de confianza. Fuera de localhost exige HTTPS; nunca sigue redirecciones con la clave.

## Demostración de 60 segundos

Mostrar origen y fecha → mostrar lectura base del suelo → humedecer la muestra → observar variación → registrar evidencia para revisión. No sumar automáticamente este índice al riesgo ambiental oficial: primero se define y valida su relación con los indicadores y umbrales en SAC.

## Fuentes técnicas

- [DHT11, fabricante Aosong/ASAIR](https://aosong.com/userfiles/files/media/DHT11%E6%95%B0%E5%AD%97%E6%B8%A9%E6%B9%BF%E5%BA%A6%E4%BC%A0%E6%84%9F%E5%99%A8%E6%A8%A1%E5%9D%97.pdf): alimentación y adquisición. Verificar la versión del módulo adquirido.
- [DS18B20, Analog Devices](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf): alimentación, bus 1-Wire y pull-up.
- [ADC en Arduino-ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html) y [ADC/Wi-Fi, Espressif](https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/peripherals/adc.html).
- [Principio de calibración capacitiva, DFRobot](https://wiki.dfrobot.com/sen0193): referencia metodológica; no certifica que el sensor genérico v1.2 tenga las mismas especificaciones.
