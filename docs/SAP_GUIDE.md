# Integración SAP de GeoPredIA

## Qué está disponible y qué requiere el tenant

El código local permite desarrollar la aplicación, trabajar con ejemplos identificados como sintéticos y preparar los contratos. Las conexiones SAP, modelos/historias, tablas HANA, proceso BPA y sitio Work Zone necesitan las cuentas, permisos y servicios del organizador. **Este repositorio no los provisiona ni demuestra que ya estén conectados.**

| Pieza obligatoria | Función en el proyecto | Entregable de referencia |
|---|---|---|
| SAP HANA Cloud | Dataset común y registro auxiliar de eventos del equipo | `database/src/geopredia_event_store.sql`; modelo relacional opcional en `geopredia_extension.sql` |
| SAP Analytics Cloud | Normalizar indicadores, calcular subíndices/score y comparar zonas | `analytics/sac_model_spec.md` |
| SAP Build Process Automation | Revisión humana, decisión e historial de instancia | `workflows/geopredia_process_blueprint.md` |
| SAP Build Work Zone, standard edition | Punto de acceso a GeoPredIA, SAC y bandeja de revisión | Sección Work Zone de esta guía |

Flujo analítico: **dataset HANA → cálculos SAC → snapshot → especialistas/coordinador → decisión humana BPA**. Los agentes explican evidencia y vacíos; no reemplazan las fórmulas de SAC ni aprueban la zona. Sentinel añade observaciones ambientales con fecha/fuente. Work Zone abre las aplicaciones y no actúa como motor de procesamiento.

## 1. Validar acceso y dataset

Con el administrador del evento, identificar: subaccount/región, usuarios y roles, conexión HANA, conexión SAC habilitada, tablas/vistas oficiales, permisos de lectura y si existe esquema escribible para el equipo. Confirmar suscripción/instancia BPA y Work Zone, posibilidad de service keys y runtime para backend. Tener un trial no garantiza todos esos permisos.

La persona de datos inspecciona columnas, unidades, claves y valores faltantes y completa el mapeo de `analytics/`. Guardar la versión de datos. No sobrescribir ni incorporar filas sintéticas al dataset común.

El backend local usa SQLite y dispone de una **acción explícita de publicación en HANA** mediante el registro de eventos descrito abajo. Las credenciales nunca se envían al frontend ni al ESP32. `database/src/geopredia_extension.sql` conserva un modelo relacional opcional de tablas por entidad; la publicación implementada utiliza `GPI_EVENT_STORE`, sin depender de migrar a esas tablas.

El adaptador de lectura `agents/integrations.py` permite sincronizar el catálogo de zonas con `POST /api/integrations/hana/sync`, tras instalar/configurar `hdbcli` y los parámetros HANA de `.env.example`. `HANA_ZONE_VIEW` identifica una vista autorizada `ESQUEMA.VISTA` con columnas `ZONE_ID`, `NAME`, `REGION`, `LATITUDE`, `LONGITUDE`. Crear o mapear esa vista en el esquema del equipo según el dataset real, sin modificar el oficial; usar null cuando no existan coordenadas. Esta sincronización importa el catálogo y no calcula riesgo. Probarla en el tenant con conexión TLS y permisos de lectura.

### Publicar eventos locales en HANA

La acción `POST /api/integrations/hana/publish`, protegida por la autenticación normal de la API, recoge los registros locales y llama a `agents/hana_publish.py`. **No se publica al arrancar la aplicación.** Invocar la acción significa copiar esos registros al esquema del equipo; los datos locales se conservan.

Preparación por el administrador:

1. Crear o asignar un esquema propio del equipo, separado del dataset oficial.
2. Seleccionarlo explícitamente en Database Explorer y ejecutar `database/src/geopredia_event_store.sql`. El código de publicación no crea tablas automáticamente.
3. Configurar `HANA_TEAM_SCHEMA` con el nombre exacto en mayúsculas, por ejemplo `GEOPREDIA_TEAM`; solo se admiten letras, números y guion bajo, comenzando con letra.
4. Configurar `HANA_ADDRESS`, `HANA_PORT` (habitualmente 443 en HANA Cloud), `HANA_USER` y `HANA_PASSWORD`, e instalar `requirements-sap.txt`.
5. Dar al usuario técnico permisos de lectura/inserción en `GPI_EVENT_STORE`. Esta integración no necesita actualizar ni borrar eventos.
6. Invocar la publicación desde el cliente autorizado y comprobar su respuesta `published`/`already_present`, después contrastar en Database Explorer la cantidad y los IDs.

El adaptador transmite mediante TLS con validación de certificado. Publica lotes de hasta 1000 eventos y utiliza consultas parametrizadas. Cada evento tiene un ID estable, tipo, fecha ISO 8601, payload JSON completo y hash SHA-256 del JSON canónico. Las evaluaciones, informes, telemetría y decisiones conservan su procedencia: las muestras sintéticas siguen siendo sintéticas aunque se almacenen en HANA. No se insertan fixtures en el dataset compartido del reto.

La publicación es transaccional por lote. Un ID existente con el mismo contenido, tipo y fecha cuenta como `already_present`. Si cambia su contenido, la operación informa conflicto y revierte ese lote; no sobrescribe evidencia. Las correcciones/reevaluaciones se registran con nuevos IDs. El estado mutable de una revisión debe representarse mediante sus eventos, sin modificar un snapshot previamente publicado.

Si la conexión falla durante la confirmación, el resultado puede ser incierto; revisar el registro HANA y reintentar con los mismos IDs permite evitar duplicados. Una publicación concurrente también puede requerir reintento. El hash detecta cambios al comparar eventos, pero no es una firma que pruebe autoría; controlar permisos y auditoría en el tenant.

Esta réplica guarda evidencia JSON en HANA y mantiene SQLite como almacenamiento operativo del prototipo. Modelar vistas analíticas sobre el contenido publicado, automatizar publicación o convertir HANA en almacenamiento principal son ampliaciones independientes. El scoring oficial continúa dentro de SAC. Las pruebas automatizadas del publicador usan un driver simulado; falta comprobar conexión, DDL y permisos en el tenant real.

## 2. Implementar la evaluación en SAC

Crear modelo/historia sobre la conexión que habilite el organizador. Conexión live y adquisición de datos tienen capacidades y procedimientos distintos: utilizar el tipo disponible y documentarlo. La especificación de `analytics/sac_model_spec.md` describe los cálculos y pruebas sin inventar los nombres de las columnas oficiales.

Habilitar tres subíndices, resultado global, cobertura de datos, ranking y comparación. Mostrar el estado «sin evaluar» cuando faltan datos requeridos. Registrar una versión por modificación de reglas/pesos. Los pesos 40/35/25 solo son una demostración pendiente de justificación técnica. El resultado oficial debe obtenerse dentro de SAC.

No sustituir el cálculo SAC con el motor de ejemplo del backend para afirmar cumplimiento del reto. En la demo local mostrar la etiqueta «datos sintéticos / scoring ilustrativo».

## 3. Capturar resultados de SAC

La ruta inicial verificable es manual: tabla SAC → export de valores visibles → adaptación al CSV → carga al backend con usuario autorizado. `analytics/sac_snapshot_contract.md` contiene el contrato plano y las validaciones.

Usar **Point of view** para exportar el contenido calculado visible cuando esté soportado por esa tabla y confirmar la salida. Evitar abreviaturas/escala como millones y verificar los decimales; la configuración de exportación puede conservar el formato mostrado. No asumir que un API genérico de SAC devolverá todas las fórmulas de historia.

El backend valida el archivo y guarda una evaluación con ID propio, valores, versiones y origen. Conservar también el export original, filtros y evidencia de importación. Un resultado incompleto puede revisarse como caso con datos faltantes, pero no debe aparecer como riesgo cero.

Si solo existe acceso a las cuatro herramientas obligatorias y no hay runtime/credenciales para la API, usar un formulario de inicio de BPA con copia manual de zona, ID/versión de evaluación, resultados y enlace SAC. Registrar quién hizo la copia y verificarla. Describir esa captura como manual en la presentación.

## 4. Conectar el proceso humano BPA

Construir el proceso del blueprint y asignar un revisor real. La aplicación inicia una instancia con `POST /api/integrations/bpa/start`; configurar en el backend el endpoint del tenant, token endpoint, client ID/secret y definition ID. Un tenant con APIs requiere instancia/subscripción y autorización apropiadas; OAuth client credentials corresponde a integración técnica.

El proceso recibe una evaluación existente y su copia de datos; la tarea no altera scores. Después de la decisión ejecuta el callback `POST /api/integrations/bpa/callback`, con `X-Workflow-Key` coincidente con `BPA_CALLBACK_KEY` y el cuerpo definido en `workflows/forms/geopredia_review.schema.json`.

Comprobar que el ID de instancia corresponde a esa evaluación, que la identidad proviene de la tarea autenticada y que repetir el callback no genera decisiones duplicadas. Reintentar el mismo evento después de un fallo de red. La aprobación solo queda registrada cuando el backend confirma. La clave compartida del prototipo no sustituye los controles de identidad de una integración productiva.

Los archivos JSON/Markdown del repositorio **no son paquetes BPA desplegables**. No activar notificaciones a terceros hasta que el equipo configure y autorice los destinatarios. Los adjuntos pueden requerir servicios adicionales; usar enlaces/evidencia textual si el tenant no los habilita.

## 5. Configurar Work Zone standard edition

Para el frontend web básico, la opción inicial es una **URL app**:

1. Desplegar frontend/API en un runtime autorizado con HTTPS. GitHub aloja el código; tener un repositorio no implica tener la API desplegada. Un servidor en localhost de una laptop no es el destino de producción del sitio.
2. En Site Manager/Content Manager, crear una app local de tipo URL, título «GeoPredIA», sistema «No System» y la URL HTTPS del frontend.
3. Configurar navegación, por ejemplo objeto semántico `GeoPredIA` y acción `display`; asignar visualización/tile y roles del sitio a los usuarios del equipo.
4. Preferir apertura en nueva pestaña para el prototipo. La apertura interna depende de que la aplicación permita iframe y de las políticas de sesión del tenant.
5. Crear entradas equivalentes a la historia SAC y a la bandeja de tareas disponible para los revisores, usando las URLs reales autorizadas.
6. Probar desde una cuenta de participante: abrir historia, entrar a GeoPredIA, seguir una evaluación y localizar la tarea BPA.

Si el equipo decide implementar una **aplicación SAPUI5 nativa** después, crear un proyecto UI5 real con `manifest.json`, desplegar en el repositorio HTML5 soportado por su subaccount, configurar destination/approuter y registrar/federar el contenido según la documentación del tenant. El frontend web básico de este repositorio no se convierte en SAPUI5 por renombrarlo. La alternativa CAP también requiere un servicio CAP real y despliegue; es una ampliación, no una capacidad ya implementada.

## 6. Evidencia de integración final

| Prueba | Evidencia que debe conservar el equipo |
|---|---|
| HANA oficial leído | Vista/modelo, versión y muestra de IDs sin exponer credenciales |
| Cálculo SAC correcto | Historia con fórmulas, tres casos contrastados y un faltante |
| Snapshot consistente | Export original + fila importada con mismo score, fecha y versión |
| Multiagentes | Informe vinculado a ese snapshot, evidencias y faltantes explícitos |
| Revisión BPA | Instancia, revisor, decisión, justificación y correlación registrada |
| Work Zone | Usuario participante abre los accesos publicados |
| Sentinel | Lectura física etiquetada `device` o simulación etiquetada `simulator` |

## Fuentes primarias

- [HANA: conexión Python y propiedad autocommit](https://help.sap.com/docs/hana-cloud-database/f1b440ded6144a54ada97ff95dac7adf/ee592e89dcce4480a99571a4ae7a702f.html).
- [SAC: exportar datos de tablas](https://help.sap.com/doc/00f68c2e08b941f081002fd3691d86a7/2023.20/en-US/ff5f1e052b5e400da990dad8408604da.html).
- [BPA: API, prerrequisitos y autenticación](https://help.sap.com/docs/build-process-automation/sap-build-process-automation/using-sap-build-process-automation-apis?locale=en-US).
- [Work Zone standard: URL apps](https://help.sap.com/docs/build-work-zone-standard-edition/sap-build-work-zone-standard-edition/url-and-dynamic-url-apps).
- [Work Zone standard: restricciones](https://help.sap.com/docs/build-work-zone-standard-edition/sap-build-work-zone-standard-edition/restrictions-general?locale=en-).

Consultar siempre la versión y servicios habilitados por el organizador; los nombres exactos de las opciones pueden variar.
