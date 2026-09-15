# Proceso de revisión GeoPredIA en SAP Build Process Automation

Este documento especifica un proceso que debe construirse y desplegarse en el tenant. No representa un proceso SAP ya desplegado. El JSON de `forms/` es un contrato de datos, no un paquete nativo para importar.

## Datos de entrada

El adaptador envía `context: {"evaluation": <snapshot>}`. Definir un objeto de proceso `evaluation` con los campos del snapshot: `id`, `zone_id`, `evaluated_at`, `model_version`, `dataset_version`, `subindices` (`geological`, `environmental`, `social`), `global_risk`, faltantes y evidencia. Los campos numéricos ausentes deben conservarse como null según el tipo admitido por el proceso. Añadir un enlace al detalle como dato derivado si se necesita. El ID de evaluación es la correlación estable; nunca enviar una clave de dispositivo al proceso.

La API de inicio de GeoPredIA recibe `evaluation_id`, pero el snapshot interno lo llama `id`: mapear **`evaluation.id` → `evaluation_id`** al construir el callback. El identificador de instancia viene de BPA, no de ese snapshot. Adaptar los tipos de la definición al JSON real antes de desplegar.

## Pasos en el diseñador

1. Crear proyecto de proceso empresarial y un proceso «Revisar zona de exploración».
2. Configurar un disparador API y definir el contexto anterior. Alternativa de demostración si faltan permisos: formulario de inicio manual con esos campos.
3. Añadir una tarea/formulario de aprobación para el grupo real de revisores asignado por el organizador. Mostrar zona, versiones, fecha y scores como datos de solo lectura.
4. Recoger una decisión humana y una justificación obligatoria. Si el control nativo solo ofrece aprobar/rechazar, añadir antes un formulario con las tres opciones de negocio o una ruta explícita de subsanación; no confundir «observado» con rechazo definitivo.
5. Traducir a `approved` (priorizar para la siguiente evaluación), `observed` (solicitar datos/corrección) o `rejected` (no priorizar en esta evaluación). Ninguna opción constituye autorización minera, ambiental o de trabajo de campo.
6. Después de completar la tarea, invocar una acción HTTP de persistencia al backend mediante una destination/credencial configurada por el administrador.
7. Mapear `reviewer` desde la identidad de la tarea completada. No confiar en un nombre escrito por el navegador; conservar el log de BPA.
8. Si falla la persistencia, conservar la tarea/instancia y reintentar de forma controlada; no mostrar «registrado» si el backend no confirmó. Repetir el mismo resultado debe ser idempotente.
9. Publicar/desplegar la versión y probar con la cuenta del revisor. Registrar ID de definición, instancia y evaluación.

## Endpoints del adaptador GeoPredIA

Iniciar una instancia mediante el backend autenticado:

```http
POST /api/integrations/bpa/start
Content-Type: application/json

{"evaluation_id":"ID_REAL_DE_EVALUACION"}
```

La aplicación usa las variables del servidor `BPA_API_URL`, `BPA_TOKEN_URL`, `BPA_CLIENT_ID`, `BPA_CLIENT_SECRET` y `BPA_DEFINITION_ID`. En este adaptador, `BPA_API_URL` es la base que precede a `/workflow/rest/v1/workflow-instances`; no duplicar ese sufijo. `BPA_TOKEN_URL` es el endpoint completo de token. Las URLs/IDs salen del service key y de la definición del tenant. Si la base del service key termina en `/public`, conservarla cuando corresponda al endpoint documentado del tenant. No deducir rutas de otro subaccount ni introducir secretos en el frontend.

Retorno del resultado desde BPA:

```http
POST /api/integrations/bpa/callback
Content-Type: application/json
X-Workflow-Key: CLAVE_CONFIGURADA_EN_BPA_Y_BACKEND

{
  "evaluation_id": "ID_REAL_DE_EVALUACION",
  "reviewer": "IDENTIDAD_DEL_REVISOR_DE_LA_TAREA",
  "decision": "observed",
  "justification": "Falta el indicador ambiental requerido para completar esta evaluación.",
  "workflow_instance_id": "ID_REAL_DEVUELTO_POR_BPA"
}
```

`X-Workflow-Key` coincide con `BPA_CALLBACK_KEY`, se configura como secreto del lado servidor/BPA y solo se envía por HTTPS. Es un mecanismo de integración del prototipo: antes de producción, usar autenticación de servicio apropiada al tenant, rotación, autorización por proceso y verificación de la instancia/correlación. Una clave compartida no identifica por sí sola a un revisor humano.

## Evidencia para el jurado

Mostrar: snapshot de SAC, instancia en BPA, usuario que completó la tarea, justificación y resultado registrado para el mismo `evaluation_id`. La revisión local de la demo debe identificarse como local, sin presentarse como ejecución de BPA.

Fuentes: [API de SAP Build Process Automation y OAuth](https://help.sap.com/docs/build-process-automation/sap-build-process-automation/using-sap-build-process-automation-apis?locale=en-US), [crear un disparador API](https://developers.sap.com/tutorials/spa-create-process-api-trigger..html).
