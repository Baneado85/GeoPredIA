# Estado verificable de integraciones

Fecha de corte: 2026-10-02.

| Componente | Estado actual | Evidencia en el repositorio | Falta para entrega |
|---|---|---|---|
| Frontend + multiagentes | Desplegado y verificado en SAP BTP Cloud Foundry (HTTP 200) | `manifest.yml`, `agents/`, `frontend/console/` | Conectar sus consultas al OData CAP si se desea una sola API |
| Dataset oficial | Publicado y validado: 11,458 filas, 140 zonas y 62 columnas | `analytics/dataset_tema2_georisk.csv` | Importarlo en SAC para crear el modelo analítico |
| SAP CAP + SQLite | Desplegado y verificado en BTP; OData devuelve 11,458 filas | `backend/db/schema.cds`, `backend/srv/`, `manifest-cap.yml` | Sustituir SQLite por HANA cuando el organizador habilite el servicio |
| SAP HANA Cloud | No disponible por restricción del entorno | Adaptadores y DDL en `agents/integrations.py` y `database/` | Vincular servicio real cuando el organizador lo habilite; no es requisito del fallback autorizado |
| SAP Analytics Cloud | Tenant disponible; modelo final pendiente | `analytics/` y contrato de snapshot | Importar el mismo CSV, crear modelo y story con 3 KPI, ranking y comparación |
| Build Process Automation | Adaptador implementado; proceso GeoRisk no verificado | `workflows/`, endpoint `/api/integrations/bpa/start` | Crear/publicar proceso y completar variables OAuth/destination |
| Work Zone | Site de práctica existente; GeoPredIA no verificado como app | `docs/SAP_GUIDE.md` | Registrar URL de GeoPredIA, asignar rol, agregar SAC y bandeja BPA, publicar site |
| Joule Studio | OpenAPI y fachada preparados; agente no publicado | `integrations/geopredia-assistant-openapi.json`, `joule/` | Crear acción en tenant NTT, probar y publicar; sigue siendo opcional |

## Principio de honestidad para la demo

La interfaz y la presentación deben distinguir entre **implementado**, **desplegado** y **verificado**. La presencia de un archivo CDS, una URL o un adaptador no prueba por sí sola una conexión viva.

## Orden de cierre

1. Importar `analytics/dataset_tema2_georisk.csv` en SAC y construir la story.
2. Publicar el proceso BPA y conectar el callback.
3. Registrar las aplicaciones en Work Zone.
4. Publicar la acción Joule únicamente si el tenant permite su despliegue.

## URLs verificadas

- Frontend: `https://geopredia-ac374882u14.cfapps.us10-001.hana.ondemand.com/frontend/console/index.html`
- OData CAP: `https://geopredia-cap-ac374882u14.cfapps.us10-001.hana.ondemand.com/odata/v4/geopredia/OfficialEvaluations`

