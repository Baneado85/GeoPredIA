# 👥 Reparto de Trabajo y Matriz RACI (Equipo de 5 Personas)

## 1. Distribución de Responsabilidades

| Integrante | Rol Oficial | Herramientas Principales | Entregable Principal |
| :--- | :--- | :--- | :--- |
| **Persona 1** | **Ingeniero de Datos / SAP HANA Cloud** | SAP HANA Studio, SQL, DDL, CAP CDS | Base de datos limpia con dataset oficial del concurso y vistas SQL. |
| **Persona 2** | **Analista SAC / Modelo de Scoring** | SAP Analytics Cloud (SAC), Calculations | Dashboard interactivo con scoring dimensional y simulador de sensibilidad. |
| **Persona 3** | **Especialista Process Automation** | SAP Build Process Automation, Form Builder | Workflow de revisión técnica completo con formularios de decisión. |
| **Persona 4** | **Arquitecto de Integración & Portal** | SAP CAP (Node.js), SAP Build Work Zone, SAPUI5 | Portal unificado Work Zone con backend API expuesto. |
| **Persona 5** | **Especialista IA & IoT / Metodólogo** | Python, FastAPI, ESP32 (C++), Sensores | Sistema Multi-Agente de IA + Dispositivo GeoRisk Sentinel. |

---

## 2. Matriz RACI

- **R**: Responsable (quien realiza la tarea)
- **A**: Aprobador (quien rinde cuentas)
- **C**: Consultado (aporta información)
- **I**: Informado (se mantiene actualizado)

| Tarea / Hito | Persona 1 | Persona 2 | Persona 3 | Persona 4 | Persona 5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Modela Tablas e Ingesta Dataset en HANA | **R/A** | C | I | C | I |
| Diseña Fórmula de Scoring & Ponderaciones | C | **R** | I | I | **A** |
| Construye Dashboards SAC & Escenarios | I | **R/A** | I | C | C |
| Diseña Formulario & Workflow en SAP BPA | I | C | **R/A** | C | I |
| Desarrolla Servicio Backend CAP | C | C | C | **R/A** | C |
| Configura SAP Build Work Zone Portal | I | I | C | **R/A** | I |
| Desarrolla Sistema Multi-Agente de IA | I | I | I | C | **R/A** |
| Desarrolla Firmware ESP32 & Sensores IoT | I | I | I | C | **R/A** |
| Ensayo de la Demo & Presentación Final | C | C | C | C | **R/A** |

---

## 3. Plan de Trabajo Hito por Hito

### Hito 1: Recorrido Base Funcional (Horas 0-12)
- Persona 1 expone datos en HANA.
- Persona 2 crea el cálculo base en SAC.
- Persona 3 publica el formulario en BPA.
- Persona 4 prueba la conexión manual y portal Work Zone.

### Hito 2: Comparación y Explicación (Horas 12-24)
- Persona 2 añade ranking y desgloses.
- Persona 5 integra el servicio Multi-Agente en Python para generar la explicación cualitativa.

### Hito 3: Sensibilidad e Integración IoT (Horas 24-36)
- Persona 2 configura los 3 escenarios predefinidos en SAC.
- Persona 5 flashea el ESP32 o ejecuta el simulador IoT.
- Persona 4 conecta las alertas de IoT a SAP CAP y BPA.

### Hito 4: Ensayos y Entregables (Horas 36-48)
- Pruebas del flujo completo end-to-end.
- Grabación de video demostrativo (3 minutos) y slide deck ejecutiva.
