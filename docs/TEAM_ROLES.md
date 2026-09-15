# Equipo de cinco: orden y dependencias

Objetivo del MVP: una zona evaluada en SAC a partir del dataset del reto, un informe de especialistas basado en esa evaluación y una decisión humana trazable en BPA, accesibles desde Work Zone. Un frontend básico y Sentinel permiten demostrar el recorrido. Priorizar primero ese recorrido completo.

## Responsables

| Persona | Frente | Entregables | Depende de |
|---|---|---|---|
| 1 | Datos HANA + contrato | Diccionario real, IDs/unidades, faltantes, vistas y versiones; extensión HANA si hay permisos | Acceso al dataset; acuerdos con persona 2 |
| 2 | Metodología + SAC | Reglas justificadas, tres subíndices, score, KPIs, ranking, escenarios y export reproducible | Contrato/datos de 1; apoyo de 5 para casos de prueba |
| 3 | Multiagentes + API | Especialistas geológico/ambiental/social y coordinador, evidencia, informe, carga de snapshots e integración del proceso | Contrato de 1+2; payload BPA acordado con 4 |
| 4 | BPA + frontend + Work Zone | Formulario/revisión, callback, interfaz básica y accesos del sitio | Puede iniciar con snapshot sintético; cierre requiere SAC + API de 3 |
| 5 | IoT + pruebas + presentación | Kit ≤S/100, calibración, telemetría, pruebas del recorrido, video y guion | Contrato de telemetría con 3; integra evidencia con 2 |

La persona 4 tiene tres entregables: primero la revisión local/interfaz mínima, luego el proceso BPA y finalmente los accesos Work Zone. La persona 3 apoya la integración del frontend cuando el motor de especialistas y la API estén listos. La persona 5 prepara el guion desde el inicio y recibe de cada responsable sus evidencias; no escribe toda la presentación al final.

## Empezar aquí, en paralelo

1. **Todos:** revisar la problemática, criterios de evaluación y accesos; acordar una única demostración y distinguir datos oficiales/sintéticos.
2. **1 + 2:** inspeccionar el dataset y cerrar claves, unidades, reglas de faltantes y normalización. Este es el primer desbloqueo crítico.
3. **3 + 4:** cerrar JSON/CSV de evaluación y callback; arrancar API/frontend y formulario con un snapshot sintético etiquetado.
4. **5 + 3:** ejecutar el simulador contra la API; después cablear un sensor cada vez, sin esperar a tener SAP listo.
5. **2 + 5:** definir tres casos de aceptación: evaluación completa, datos insuficientes y condición que requiere revisión humana.

## Hitos y dependencias

| Hito | Qué debe existir | Qué desbloquea |
|---|---|---|
| A. Contrato | Campos reales, IDs y versiones; formato de snapshot acordado | SAC, API, UI y proceso pueden avanzar sin cambiar nombres |
| B. Evaluación | Fórmulas SAC verificadas y al menos tres KPIs | Ranking, escenario y export oficial |
| C. Snapshot | Export adaptado y validado con ID de evaluación | Agentes explican datos concretos; revisión conserva versión |
| D. Revisión | BPA recibe caso, humano decide y callback registra resultado | Historia completa de una decisión |
| E. Acceso | Frontend/API desplegados y URLs reales | Sitio Work Zone usable por el jurado |
| F. Sentinel | Medición física calibrada o simulación explícita | Evidencia ambiental complementaria, sin bloquear el MVP SAP |
| G. Ensayo | Recorrido repetible y fallos controlados | Video de 3 minutos y exposición de 10 minutos |

**Cadena crítica:** datos entendidos → reglas acordadas → evaluación SAC correcta → snapshot → revisión BPA. IoT y explicaciones multiagente avanzan en paralelo; una falla de sensor debe mostrarse como dato ausente sin detener la evaluación de otras zonas.

## Papel de los multiagentes

- Geológico: interpreta indicadores geológicos disponibles y sus incertidumbres.
- Ambiental: interpreta indicadores ambientales y separa telemetría observada/simulada.
- Social: interpreta la evidencia social disponible; no inventa comunidades, conflictos o aceptación.
- Coordinador: reúne hallazgos, contradicciones, faltantes y pasos sugeridos para el revisor.

Todos reciben la misma versión de evaluación; sus respuestas enlazan evidencia. Ninguno modifica el score SAC ni firma la decisión humana. Un modo de reglas local permite ensayar sin consumo de API; si se conecta un modelo, conservar procedencia, validar estructura y evitar enviar datos sensibles sin autorización.

## Antes de presentar

Cada responsable aporta una captura verificable y una frase sobre su resultado. Preparar un plan de contingencia con snapshots previamente exportados, distinguiéndolos de datos en vivo. Ensayar los estados sin datos, sensor desconectado, API no disponible y usuario sin permisos. No afirmar que una pantalla local prueba una conexión a SAP.
