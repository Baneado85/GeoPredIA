# Estado verificable de integraciones

Fecha de corte: 2026-10-02.

| Componente | Estado actual | Evidencia en el repositorio | Falta para entrega |
|---|---|---|---|
| Frontend + multiagentes | Desplegado en SAP BTP Cloud Foundry | `manifest.yml`, `agents/`, `frontend/console/` | Volver a desplegar después de integrar el dataset oficial |
| Dataset oficial | Recuperado: 11,458 filas | `analytics/dataset_tema2_georisk.csv` al sincronizar el commit creado en BAS | Ejecutar `backend/scripts/prepare_data.py` y comprobar 140 zonas |
| SAP CAP + SQLite | Implementado | `backend/db/schema.cds`, `backend/srv/`, `manifest-cap.yml` | Instalar dependencias, cargar CSV y desplegar `geopredia-cap-ac374882u14` |
| SAP HANA Cloud | No disponible por restricción del entorno | Adaptadores y DDL en `agents/integrations.py` y `database/` | Vincular servicio real cuando el organizador lo habilite; no es requisito del fallback autorizado |
| SAP Analytics Cloud | Tenant disponible; modelo final pendiente | `analytics/` y contrato de snapshot | Importar el mismo CSV, crear modelo y story con 3 KPI, ranking y comparación |
| Build Process Automation | Adaptador implementado; proceso GeoRisk no verificado | `workflows/`, endpoint `/api/integrations/bpa/start` | Crear/publicar proceso y completar variables OAuth/destination |
| Work Zone | Site de práctica existente; GeoPredIA no verificado como app | `docs/SAP_GUIDE.md` | Registrar URL de GeoPredIA, asignar rol, agregar SAC y bandeja BPA, publicar site |
| Joule Studio | OpenAPI y fachada preparados; agente no publicado | `integrations/geopredia-assistant-openapi.json`, `joule/` | Crear acción en tenant NTT, probar y publicar; sigue siendo opcional |

## Principio de honestidad para la demo

La interfaz y la presentación deben distinguir entre **implementado**, **desplegado** y **verificado**. La presencia de un archivo CDS, una URL o un adaptador no prueba por sí sola una conexión viva.

## Orden de cierre

1. Sincronizar el commit del CSV oficial desde BAS hacia GitHub.
2. Preparar la carga CAP: `cd backend && npm run prepare:data`.
3. Instalar, desplegar SQLite y probar: `npm install`, `npm run deploy:sqlite`, `npm test`.
4. Desplegar `manifest-cap.yml` y registrar la URL OData.
5. Importar `analytics/dataset_tema2_georisk.csv` en SAC y construir la story.
6. Publicar el proceso BPA y conectar el callback.
7. Registrar las aplicaciones en Work Zone.
8. Publicar la acción Joule únicamente si el tenant permite su despliegue.

