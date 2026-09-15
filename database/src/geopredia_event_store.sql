-- GeoPredIA: registro auxiliar de eventos en SAP HANA Cloud.
-- Un administrador selecciona PRIMERO el esquema propio del equipo en
-- Database Explorer. Debe coincidir con HANA_TEAM_SCHEMA del backend.
-- NO ejecutar en el esquema oficial compartido del reto.
-- El servicio no crea tablas automáticamente ni concede permisos.
-- CREATE falla si ya existe: revisar su estructura antes de migrar.

CREATE COLUMN TABLE "GPI_EVENT_STORE" (
  "EVENT_ID" NVARCHAR(100) PRIMARY KEY,
  "EVENT_TYPE" VARCHAR(20) NOT NULL,
  "PAYLOAD" NCLOB NOT NULL,
  "CREATED_AT" NVARCHAR(40) NOT NULL,
  "PAYLOAD_HASH" VARCHAR(64) NOT NULL,
  CONSTRAINT "GPI_EVENT_TYPE_CK" CHECK (
    "EVENT_TYPE" IN ('evaluation', 'agent_run', 'telemetry', 'review')
  )
);

-- CREATED_AT conserva la fecha ISO 8601 con offset original. Convertirla
-- explícitamente al modelar series temporales: no ordenar offsets mezclados
-- como si todos los strings estuvieran expresados en la misma zona horaria.
-- PAYLOAD contiene JSON canónico UTF-8 serializado con claves ordenadas,
-- ensure_ascii=true, separadores compactos y sin NaN/Infinity.
-- PAYLOAD_HASH es su SHA-256 hexadecimal; no es una firma de autenticidad.
-- El backend solo consulta/inserta y verifica identidad + hash en reintentos.
-- Conceder SELECT/INSERT a su usuario técnico; no requiere UPDATE/DELETE.
-- Una cuenta administradora aún puede modificar tablas: la inmutabilidad
-- de aplicación no sustituye controles de acceso y auditoría del tenant.
