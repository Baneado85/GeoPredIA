# Servicio GeoPredIA en SAP CAP

Esta carpeta es una aplicación SAP CAP real. Usa SQLite porque esa fue la alternativa autorizada por los organizadores durante las restricciones de HANA Cloud.

```bash
npm run prepare:data
npm install
npm run deploy:sqlite
npm start
```

Endpoints principales:

- `GET /odata/v4/geopredia/health()`
- `GET /odata/v4/geopredia/OfficialEvaluations?$top=10`
- `GET /odata/v4/geopredia/RiskScores`
- `POST /odata/v4/geopredia/IoTReadings`
- `POST /odata/v4/geopredia/submitForReview`

`submitForReview` guarda una solicitud trazable. Solo marca `READY_FOR_BPA` cuando existen variables de conexión BPA; no inventa un ID de proceso ni afirma que HANA recibió datos.
