namespace geopredia;

using { cuid, managed } from '@sap/cds/common';

/** Dataset oficial del reto. Se conservan sus nombres para importar el CSV sin alterar el contrato. */
entity OfficialEvaluations {
  key EVALUACION_ID                  : String(20);
      ZONA_ID                        : String(20);
      ZONA_NOMBRE                    : String(200);
      REGION                         : String(100);
      PROVINCIA                      : String(100);
      DISTRITO                       : String(100);
      LATITUD                        : Decimal(10,6);
      LONGITUD                       : Decimal(10,6);
      ALTITUD_MSNM                   : Integer;
      SUPERFICIE_HA                  : Decimal(15,2);
      TIPO_YACIMIENTO                : String(100);
      MINERAL_PRINCIPAL              : String(80);
      CONCESION_ID                   : String(30);
      ESTADO_CONCESION               : String(50);
      EMPRESA_OPERADORA              : String(200);
      ACCESIBILIDAD_SCORE            : Decimal(10,3);
      DISPONIBILIDAD_AGUA_SCORE      : Decimal(10,3);
      DISTANCIA_VIA_PRINCIPAL_KM     : Decimal(15,3);
      DISTANCIA_PLANTA_KM            : Decimal(15,3);
      FASE_EXPLORACION               : String(100);
      ANIO                           : Integer;
      TRIMESTRE                      : String(4);
      MES                            : String(7);
      FECHA_EVALUACION               : Date;
      EVALUADOR                      : String(150);
      METODO_EVALUACION              : String(150);
      SISMICIDAD_INDICE              : Decimal(10,3);
      DISTANCIA_FALLA_GEOLOGICA_KM   : Decimal(15,3);
      ESTABILIDAD_TALUD_SCORE        : Decimal(10,3);
      PENDIENTE_PROMEDIO_PCT         : Decimal(10,3);
      NIVEL_FREATICO_M               : Decimal(15,3);
      CAUDAL_INFILTRACION_LPS        : Decimal(15,3);
      POTENCIAL_DRENAJE_ACIDO_PH     : Decimal(10,3);
      EVENTOS_GEOLOGICOS_12M         : Integer;
      DISTANCIA_AREA_PROTEGIDA_KM    : Decimal(15,3);
      DISTANCIA_CUERPO_AGUA_KM       : Decimal(15,3);
      INDICE_ESTRES_HIDRICO          : Decimal(10,4);
      COBERTURA_VEGETAL_PCT          : Decimal(10,3);
      CALIDAD_AIRE_PM10_UGM3         : Decimal(15,3);
      PASIVOS_AMBIENTALES_NUM        : Integer;
      ESPECIES_SENSIBLES_NUM         : Integer;
      CONSUMO_AGUA_M3_MES            : Decimal(18,3);
      HUELLA_CARBONO_TCO2E_MES       : Decimal(18,3);
      COMUNIDADES_INFLUENCIA_NUM     : Integer;
      POBLACION_INFLUENCIA           : Integer;
      DISTANCIA_COMUNIDAD_KM         : Decimal(15,3);
      CONFLICTOS_REGISTRADOS_12M     : Integer;
      DIAS_PARALIZACION_12M          : Integer;
      INDICE_ACEPTACION_SOCIAL       : Decimal(10,4);
      CONVENIOS_VIGENTES_NUM         : Integer;
      EMPLEO_LOCAL_PCT               : Decimal(10,3);
      IDH_DISTRITAL                  : Decimal(10,4);
      POBREZA_DISTRITAL_PCT          : Decimal(10,3);
      QUEJAS_REGISTRADAS_12M         : Integer;
      COSTO_MITIGACION_EJECUTADO_USD : Decimal(20,2);
      ACCIONES_MITIGACION_NUM        : Integer;
      ESTADO_REVISION                : String(50);
      REVISOR_ASIGNADO               : String(150);
      DECISION_ESPECIALISTA          : String(300);
      FECHA_DECISION                 : Date;
      COMENTARIO_REVISION            : String(1000);
      MONEDA                         : String(10);
}

/** Resultados versionados del scoring calculado en SAC o importado desde SAC. */
entity RiskScores : cuid, managed {
  evaluationId  : String(64) not null;
  zoneId        : String(20) not null;
  scenario      : String(50) default 'base';
  modelVersion  : String(40) not null;
  geological    : Decimal(7,2);
  environmental : Decimal(7,2);
  social        : Decimal(7,2);
  globalRisk    : Decimal(7,2);
  riskClass     : String(20);
  source        : String(30) default 'sac_import';
  evaluatedAt   : Timestamp;
}

entity ReviewRequests : cuid, managed {
  evaluationId       : String(64) not null;
  zoneId             : String(20) not null;
  status             : String(30) default 'PENDING';
  workflowInstanceId : String(128);
  reviewer            : String(255);
  decision            : String(20);
  justification       : String(2000);
}

entity IoTReadings : cuid, managed {
  deviceId          : String(64) not null;
  zoneId            : String(20) not null;
  observedAt        : Timestamp not null;
  source            : String(20) default 'device';
  airTemperatureC   : Decimal(7,2);
  airHumidityPct    : Decimal(5,2);
  soilMoisturePct   : Decimal(5,2);
  waterTemperatureC : Decimal(7,2);
  quality           : String(30);
}
