# Asistente GeoPredIA y futura integración con Joule

El frontend incluye un asistente local que consulta una evaluación existente mediante `POST /api/assistant/query`. Responde con el riesgo global, la dimensión más alta, datos faltantes, versión e ID de evaluación. Funciona por reglas y no requiere un modelo de lenguaje.

Esta función deja preparado el contrato de una futura acción de Joule Studio en `joule/geopredia_action.json`. No debe presentarse como SAP Joule desplegado mientras NTT DATA no habilite Joule Studio para el equipo.

## Publicación cuando exista acceso

1. Desplegar la API GeoPredIA con HTTPS y autenticación en BTP.
2. Crear una destination hacia la API sin exponer secretos en el navegador.
3. En Joule Studio, crear una acción que reciba `zone_id` y `question` y llame `POST /api/assistant/query`.
4. Crear intenciones de resumen, factor principal y datos faltantes.
5. Mostrar `evaluation_id` y `notice` en la respuesta para conservar trazabilidad.
6. Probar que la skill no altera scores ni registra decisiones.

La decisión sigue perteneciendo al flujo humano de SAP Build Process Automation.
