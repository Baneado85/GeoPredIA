# 🏛️ Arquitectura del Sistema GeoPredIA

## Visión General
GeoPredIA (GeoRisk Decision Hub) integra servicios analíticos, gobernanza de procesos, inteligencia artificial multi-agente e ingesta de IoT en tiempo real sobre la infraestructura de SAP Business Technology Platform (SAP BTP).

```mermaid
flowchart TD
    subgraph Client ["Capa de Presentación"]
        Fiori["SAP Build Work Zone (Portal Standard)"]
        UI5["SAPUI5 Custom App (Fiori Launchpad)"]
    end

    subgraph Analytical ["Capa Analítica & Scoring"]
        SAC["SAP Analytics Cloud (SAC)"]
        Scoring["Motor de Ponderación (Geo/Env/Soc)"]
        Sensitivity["Simulación de Sensibilidad"]
    end

    subgraph Core_Services ["Capa Backend & Servicios CAP"]
        CAP["SAP CAP Integration Service (Node.js)"]
        OData["OData V4 Endpoints"]
        IoT_Ingest["Endpoint Ingesta HTTPS IoT"]
    end

    subgraph Governance ["Capa de Gobernanza"]
        BPA["SAP Build Process Automation"]
        Workflow["Flujo de Revisión por Especialista"]
    end

    subgraph AI_Services ["Capa Multi-Agente IA"]
        Agent_Server["GeoPredIA AI Orchestrator (Python)"]
        Geo_Agent["Agente Geológico"]
        Env_Agent["Agente Ambiental"]
        Soc_Agent["Agente Social"]
        Coord_Agent["Agente Coordinador / Síntesis"]
    end

    subgraph Database ["Capa de Datos"]
        HANA[("SAP HANA Cloud (In-Memory DB)")]
    end

    subgraph Edge ["Capa IoT Sentinel"]
        ESP32["ESP32 Microcontroller Unit"]
        Sensors["Sensores (Humedad, Turbidez, Polvo PM2.5)"]
    end

    %% Flujos
    Client --> Analytical
    Client --> CAP
    Analytical --> Scoring --> Sensitivity
    HANA --> Analytical
    Sensitivity -->|"Exportación POV / Carga"| CAP
    CAP --> HANA
    CAP --> BPA
    CAP --> Agent_Server
    Agent_Server --> Geo_Agent & Env_Agent & Soc_Agent --> Coord_Agent
    Coord_Agent --> CAP
    Sensors --> ESP32 -->|"HTTPS POST /telemetry"| CAP
    BPA -->|"Decisión & Feedback"| CAP
```

## Flujo End-to-End de una Evaluación
1. **Ingesta e Integración**: SAP HANA Cloud almacena el dataset unificado del reto GeoRisk.
2. **Cálculo de Scoring**: SAC consulta HANA Cloud y aplica la fórmula dimensional de riesgo (40% Geológico, 35% Ambiental, 25% Social).
3. **Simulación de Escenarios**: El especialista interactúa en SAC probando supuestos alternativos (Escenario Base, Alta Prioridad Ambiental, Adverso).
4. **Registro y Carga POV**: Se exporta el estado visible de la tabla analítica (Point of View) y se registra en la aplicación de integración SAP CAP.
5. **Evaluación Multi-Agente**: La API de CAP envía la evaluación al sistema Multi-Agente de IA, el cual genera explicaciones cualitativas detalladas por dimensión.
6. **Revisión en SAP BPA**: El resultado y la explicación de los agentes inician una solicitud de revisión técnica en SAP Build Process Automation.
7. **Monitoreo IoT Continuo**: Los sensores GeoRisk Sentinel envían lecturas periódicas. Si un sensor detecta turbidez anormal o saturación de humedad en suelo, emite una alerta automática hacia CAP que escala una nueva revisión en BPA.
8. **Decisión e Histórico**: El especialista aprueba, observa o rechaza la evaluación, quedando registrada con firma de usuario y versión del modelo en HANA Cloud.
