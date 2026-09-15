# Servicio de integración

La versión funcional de esta entrega se inicia con `python -m uvicorn agents.api:app` desde la raíz. La API sirve el frontend y conserva datos localmente para el ensayo.

Los archivos iniciales de esta carpeta pueden conservarse como base para una futura variante SAP CAP. El adaptador real a HANA/BPA de esta versión está en `agents/integrations.py`. Express no es SAP CAP: para usar CAP se necesita implementar y desplegar su runtime, modelo y autenticación en el tenant.

Consulta `docs/SAP_GUIDE.md` antes de configurar el entorno del concurso.
