# 📘 Guía SAP: Integración y Tecnologías Exigidas en GeoPredIA

## 1. ¿Qué es SAP?
**SAP** (*Systemanalyse Programmentwicklung*) es la empresa líder en soluciones de software para la gestión integral de procesos de negocio, procesamiento analítico en tiempo real y gobernanza empresarial.

En el contexto del reto **GeoRisk (ULatinHack)**, utilizamos las 4 tecnologías SAP solicitadas para construir una arquitectura lista para producción:

---

## 2. Componentes SAP en GeoPredIA

### 2.1 SAP HANA Cloud
- **Rol**: Base de Datos Relacional En Memoria (*In-Memory Database*).
- **Función**: Almacenar el dataset unificado de zonas mineras, registrar evaluaciones históricas, tablas de auditoría de revisiones y telemetría de sensores IoT.
- **Acceso**: Vistas SQL expuestas vía JDBC/OData a SAP Analytics Cloud y SAP CAP.

### 2.2 SAP Analytics Cloud (SAC)
- **Rol**: Motor de Business Intelligence, Analítica Predictiva y Modelado.
- **Función**:
  - Normalizar indicadores en escala 0 a 100.
  - Calcular medidas ponderadas:
    - `Riesgo_Geologico` = $f(\text{fallas}, \text{sismicidad}, \text{pendiente})$
    - `Riesgo_Ambiental` = $f(\text{calidad\_agua}, \text{polvo\_aire}, \text{biodiversidad})$
    - `Riesgo_Social` = $f(\text{conflictividad}, \text{licencia\_social})$
  - Permitir simulación dinámica de escenarios mediante tablas analíticas.

### 2.3 SAP Build Process Automation (BPA)
- **Rol**: Plataforma No-Code / Low-Code para la automatización de flujos de trabajo (*workflows*).
- **Función**:
  - Enviar formularios interactivos a especialistas cuando se registra una nueva evaluación o una alerta IoT.
  - Gestionar las decisiones: **Aprobar**, **Observar (pedir información)** o **Rechazar**.
  - Mantener trazabilidad completa con fecha, responsable y justificación.

### 2.4 SAP Build Work Zone (Standard Edition)
- **Rol**: Portal Fiori centralizado y uniforme para aplicaciones empresariales.
- **Función**:
  - Agrupar la interfaz de SAC, la aplicación de registro SAPUI5 y las tareas pendientes de BPA en un solo panel de control accesible por roles de usuario.

---

## 3. Integración SAC con SAP CAP (Point of View - POV)
Para enviar los resultados calculados por SAC hacia SAP Build Process Automation:
1. En SAC se selecciona la tabla con la evaluación y se ejecuta **Export -> Point of View (POV)**.
2. El archivo de exportación consolida los valores visibles de la simulación.
3. Se realiza la ingesta mediante la API del backend SAP CAP `/api/evaluations/upload-pov`.
4. SAP CAP persiste la evaluación en HANA Cloud e inicia automáticamente la instancia del proceso en SAP BPA.
