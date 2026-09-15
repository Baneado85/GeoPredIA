# Registro de validación

**Fecha:** 15 de septiembre de 2026.  
**Alcance:** prototipo local GeoPredIA, con datos sintéticos y servicios externos simulados en las pruebas.

Este registro resume las verificaciones realizadas durante la implementación. No certifica una conexión al tenant SAP ni el funcionamiento de sensores físicos.

## Verificaciones completadas

| Verificación | Resultado observado |
|---|---|
| Pruebas unitarias de API, agentes y publicación en HANA | **45 pruebas aprobadas**. Las llamadas externas se simularon; no se accedió a un tenant HANA real. |
| Pruebas del simulador IoT | **5 pruebas aprobadas**. Validación del transporte y sus casos de error sin sensores físicos. |
| `node --check frontend/console/app.js` | Comprobación de sintaxis JavaScript aprobada. |
| Ejecutar agentes desde el navegador | Se mostró una ejecución de los tres especialistas y el coordinador en modo de reglas. |
| Simular IoT desde el navegador | Se generó y mostró una muestra identificada como sintética. |
| Guardar revisión desde el navegador | Se registró una decisión local con su justificación. La identidad escrita por el revisor no está autenticada por SAP. |
| Importar CSV desde el navegador | Se importó un snapshot en el formato del proyecto y se mostró en la interfaz. Su procedencia declarada como SAC no quedó autenticada. |
| Escenario de pesos en Altiplano | El escenario de demostración cambió de **26.5 a 28** al modificar los pesos. Es un cálculo ilustrativo sobre datos sintéticos. |
| Vista estática sin backend | Se mostraron datos de ejemplo y las operaciones de escritura quedaron deshabilitadas. |

Las pruebas de agentes incluyen conservación de las puntuaciones recibidas, tratamiento explícito de datos faltantes, rechazo de referencias inventadas y retorno a reglas si el proveedor LLM falla. Las pruebas locales no realizaron solicitudes pagadas a un LLM.

## Verificaciones pendientes

| Área | Trabajo que falta verificar |
|---|---|
| Tenant y credenciales SAP | Conectar HANA Cloud, implementar y validar el scoring dentro de SAC, ejecutar un proceso BPA real y comprobar el acceso desde Work Zone. Verificar permisos, identidad y persistencia en el entorno del evento. |
| Groq real | Ejecutar el modo LLM con credenciales válidas y comprobar respuesta, cuota, latencia y comportamiento de errores del proveedor. Las pruebas realizadas emplearon respuestas simuladas. |
| Arduino y hardware | Compilar el firmware para la placa elegida, cargarlo, comprobar conexiones, calibrar sensores y verificar mediciones y envío desde el ESP32 físico. |
| Docker | Construir la imagen y ejecutar el contenedor en un entorno con Docker disponible. |
| CI remoto | Ejecutar y revisar el resultado de los flujos de integración continua en GitHub. |
| Publicación en GitHub | Publicar los archivos y confirmar que el repositorio remoto contiene la versión entregada. La revisión local de scripts de publicación no equivale a un push realizado. |

## Límites de interpretación

- Una importación CSV comprueba formato y valores, pero no demuestra que el archivo haya sido generado por SAC.
- La telemetría simulada sirve para ensayar el flujo. No aporta evidencia de condiciones ambientales reales.
- El escenario de pesos es una demostración; sus pesos y umbrales requieren justificación con el dataset del concurso.
- El modo estático permite presentar la interfaz. Las operaciones de agentes, almacenamiento y recepción IoT requieren el backend.
