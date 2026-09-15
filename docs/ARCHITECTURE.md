# Arquitectura y decisiones de implementación

## Problema

Comparar zonas de exploración exige reunir riesgos geológicos, ambientales y sociales que suelen estar dispersos. GeoPredIA organiza una evaluación reproducible, evidencia y revisión humana. No predice deslizamientos ni declara viabilidad minera automáticamente.

## Componentes y responsabilidades

| Componente | Responsabilidad | Estado de esta versión |
|---|---|---|
| SAP HANA Cloud | Fuente del dataset común y tablas propias del equipo | Adaptadores de lectura y réplica explícita de eventos + DDL; requiere tenant |
| SAP Analytics Cloud | Scoring oficial, tres KPIs, rankings y escenarios | Especificación y contrato CSV; construir story en SAC |
| API FastAPI | Validación, snapshots, agentes, telemetría y adaptadores | Funcional localmente |
| SQLite | Persistencia para ensayo del prototipo local | Funcional; no sustituye HANA para la entrega |
| Multiagentes | Interpretar evidencia disponible y señalar vacíos | Reglas funcionales; selección LLM opcional |
| SAP BPA | Revisión, decisión y justificación por especialista | Adaptador OAuth + callback; requiere proceso desplegado |
| SAP Work Zone | Acceso a aplicaciones, story SAC y tareas | Guía de configuración; requiere tenant |
| Frontend | Operar y presentar la demo | HTML/CSS/JS; modo estático explícito sin backend |
| Sentinel | Capturar parámetros ambientales del kit S/100 | Firmware y simulador; falta prueba física |

## Contratos

- `Evaluation`: ID nuevo por versión, zona, fecha con timezone, versiones de modelo/dataset, origen, tres subíndices, global, evidencia y campos ausentes.
- `AgentRun`: referencia a evaluación, tres hallazgos, coordinador, modo ejecutado, fecha y copia de entradas/telemetría. No cambia el snapshot.
- `Telemetry`: identificador de dispositivo/zona, fecha observada, origen dispositivo/simulador y lecturas con unidades fijas. Reintentar la misma fecha/dispositivo conserva ID; un contenido distinto produce conflicto.
- `Review`: evaluación, nombre del especialista, decisión, justificación, origen y fecha. Una decisión por versión. La identidad escrita en demo no se verifica.
- `Audit`: registro acumulado de operaciones. Es una traza de aplicación local, no un registro inviolable frente a un administrador de SQLite.

Las validaciones rechazadas no crean registros parciales. Los CSV se validan completos antes de guardarse. Todas las consultas con datos de usuario usan parámetros.

## Adaptación multiagente

Se toma la separación conceptual del proyecto financiero entre propuesta, reglas y ejecución. Se cambia el dominio: las dimensiones son geología, ambiente y sociedad; la salida es un expediente para revisión. No hay órdenes financieras ni credenciales Alpaca. Implementación original, sin copiar su código.

Los tres especialistas reciben el mismo snapshot y pueden correr en paralelo. El coordinador recopila sus hallazgos. Un LLM opcional solo selecciona enfoques y evidencia entre opciones permitidas. La lógica de integridad sigue siendo determinística y la aprobación siempre humana.

## Autenticación y operación

El arranque recomendado escucha en `127.0.0.1`, deshabilita confianza en headers de proxy y acepta hosts explícitos. Los clientes API remotos necesitan `APP_API_KEY` en `X-API-Key`; el frontend de esta entrega está pensado para uso local. Sensores requieren `DEVICE_API_KEY`; callbacks BPA requieren `BPA_CALLBACK_KEY` y una instancia vinculada a la evaluación.

El callback autentica al servicio que envía la decisión. El nombre del revisor solo será una identidad verificada cuando el proceso BPA lo derive de la tarea autenticada y se valide ese vínculo. Una clave compartida por sí sola no prueba la identidad humana.

HANA y BPA no se contactan en el arranque ni se simulan como conectados. Los adaptadores se activan mediante acciones explícitas y variables del servidor. `.env`, certificados privados, claves, bases locales y firmware `secrets.h` están excluidos de Git.

## Pendiente para el tenant del evento

1. Confirmar columnas y diccionario del dataset común; mapear IDs sin mezclarlos con fixtures.
2. Justificar y construir el scoring dentro de SAC.
3. Publicar formularios/tareas BPA y probar el callback con la identidad del especialista.
4. Vincular UI, SAC y tareas en Work Zone mediante mecanismos permitidos por el tenant.
5. Crear `GPI_EVENT_STORE` en el esquema propio, ejecutar `/api/integrations/hana/publish` y verificar la réplica. Probar roles, acceso, conectividad y recuperación. SQLite sigue siendo el almacén operativo del prototipo; la réplica es explícita, no sincronización continua.
6. Compilar firmware y validar sensor por sensor con el hardware real.
