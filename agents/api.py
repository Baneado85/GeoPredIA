"""Runnable GeoPredIA prototype. Official risk calculations stay in SAP SAC."""
import hmac
import os
import random
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .config import ROOT, configured
from .data import now, evaluate_demo
from .models import EvaluationRequest, AgentRequest, AssistantQuery, ReviewRequest, WorkflowCallback, TelemetryRequest, SimulationRequest, CSVImport
from .store import Store, Conflict
from .sac import parse_sac_csv
from .integrations import bpa_start, hana_import_zones, IntegrationUnavailable


def create_app(db_path=None):
    app = FastAPI(title="GeoPredIA · GeoRisk Decision Hub", version="0.2.0",
                  description="Prototipo local con agentes, snapshots SAC y revisión humana. Datos iniciales sintéticos.")
    store = Store(db_path or os.getenv("GEOPREDIA_DB", str(ROOT / ".local" / "geopredia.db")), seed_demo=os.getenv("SEED_DEMO", "true").lower() == "true")
    app.state.store = store
    allowed_hosts = ["localhost", "127.0.0.1", "[::1]", "testserver"]
    allowed_hosts.extend(host.strip() for host in os.getenv("GEOPREDIA_ALLOWED_HOSTS", "").split(",") if host.strip())
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware("http")
    async def access_control(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            try:
                content_length = int(request.headers.get("content-length", "0") or 0)
            except ValueError:
                return JSONResponse({"detail": "Content-Length inválido."}, status_code=400)
            if content_length > 600_000:
                return JSONResponse({"detail": "La solicitud excede 600 KB."}, status_code=413)
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.url.netloc:
                return JSONResponse({"detail": "Origen no permitido."}, status_code=403)
            device_route = request.url.path in ("/api/telemetry", "/api/integrations/bpa/callback") and request.method == "POST"
            if not device_route:
                key = os.getenv("APP_API_KEY", "")
                local = request.client and request.client.host in ("127.0.0.1", "::1", "testclient")
                public_demo = os.getenv("ALLOW_PUBLIC_DEMO", "false").lower() == "true"
                if (key and not hmac.compare_digest(request.headers.get("x-api-key", ""), key)) or (not key and not local and not public_demo):
                    return JSONResponse({"detail": "Acceso local únicamente. Configura APP_API_KEY para un cliente remoto."}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Conflict)
    async def conflict_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(IntegrationUnavailable)
    async def integration_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    def get_zone(zid):
        zone = next((z for z in store.zones() if z["id"] == zid), None)
        if zone is None:
            raise HTTPException(404, "Zona no encontrada.")
        return zone

    def get_evaluation(eid):
        evaluation = store.evaluation(eid)
        if evaluation is None:
            raise HTTPException(404, "Evaluación no encontrada.")
        return evaluation

    def require_secret(request, env_name, header):
        secret = os.getenv(env_name, "")
        if not secret:
            raise HTTPException(503, f"Configura {env_name} antes de habilitar este endpoint.")
        if not hmac.compare_digest(secret, request.headers.get(header, "")):
            raise HTTPException(401, "Credencial inválida.")

    @app.get("/api/status")
    def status():
        llm = configured("GROQ_API_KEY") and os.getenv("LLM_ENABLED", "false").lower() == "true"
        return {"mode": "demo" if os.getenv("SEED_DEMO", "true").lower() == "true" else "integration", "version": "0.2.0", "llm_mode": "llm" if llm else "rules",
                "storage": "sqlite-local", "integrations": {
                    "hana": {"configured": configured("HANA_ADDRESS", "HANA_USER", "HANA_PASSWORD", "HANA_ZONE_VIEW"), "verified": False},
                    "sac": {"configured": False, "method": "manual-csv-import"},
                    "bpa": {"configured": configured("BPA_API_URL", "BPA_TOKEN_URL", "BPA_CLIENT_ID", "BPA_CLIENT_SECRET", "BPA_DEFINITION_ID"), "verified": False},
                    "llm": {"configured": llm}},
                "notice": "Las conexiones SAP requieren el tenant del evento. Configurado no significa conexión verificada."}

    @app.get("/api/zones")
    def zones():
        return store.zones()

    @app.post("/api/evaluations", status_code=201)
    def evaluate(body: EvaluationRequest):
        zone = get_zone(body.zone_id)
        if zone["source"] != "synthetic" or (zone["latest_evaluation"] and zone["latest_evaluation"]["source"] == "sac"):
            raise HTTPException(409, "Esta zona usa datos importados. Calcula la nueva versión en SAC e importa su snapshot.")
        evaluation = evaluate_demo(zone, body.weights.model_dump())
        store.add_evaluations([evaluation])
        return evaluation

    @app.get("/api/evaluations/{eid}")
    def evaluation(eid: str):
        return get_evaluation(eid)

    @app.post("/api/sac/import", status_code=201)
    def sac_import(body: CSVImport):
        try:
            evaluations = parse_sac_csv(body.csv)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        store.add_evaluations(evaluations)
        return {"imported": len(evaluations), "evaluations": evaluations}

    @app.post("/api/agent-runs", status_code=201)
    def agents(body: AgentRequest):
        from .engine import run_agents
        evaluation = get_evaluation(body.evaluation_id)
        zone = deepcopy(get_zone(evaluation["zone_id"]))
        zone["evidence"] = evaluation.get("evidence", [])
        # Telemetry is complementary evidence; never folds into SAC indices.
        telemetry = store.list_records("telemetry", zone["id"])[:20]
        result = run_agents(evaluation, zone, telemetry, llm_enabled=os.getenv("LLM_ENABLED", "false").lower() == "true")
        result["input_snapshot"] = {"evaluation": evaluation, "telemetry": telemetry}
        store.add_run(result)
        return result

    @app.get("/api/agent-runs")
    def runs(evaluation_id: str | None = None):
        return store.list_records("runs", evaluation_id)

    @app.post("/api/assistant/query")
    def assistant_query(body: AssistantQuery):
        """Deterministic conversational facade ready to expose as a Joule Studio action."""
        zone = get_zone(body.zone_id)
        evaluation = zone.get("latest_evaluation")
        if not evaluation:
            return {"answer": f"{zone['name']} todavía no tiene una evaluación registrada.", "facts": [],
                    "suggested_actions": ["Completar la evaluación de las tres dimensiones"],
                    "mode": "local-rules", "joule_deployed": False}
        values = evaluation.get("subindices", {})
        labels = {"geological": "geológico", "environmental": "ambiental", "social": "social"}
        available = [(key, value) for key, value in values.items() if isinstance(value, (int, float))]
        dominant = max(available, key=lambda item: item[1]) if available else None
        missing = evaluation.get("missing_fields", [])
        facts = [
            f"Riesgo global: {evaluation.get('global_risk') if evaluation.get('global_risk') is not None else 'sin calcular'}",
            f"Clasificación: {evaluation.get('classification', 'sin clasificar')}",
            f"Versión del modelo: {evaluation.get('model_version', 'no registrada')}",
        ]
        if dominant:
            facts.append(f"Dimensión más alta: {labels.get(dominant[0], dominant[0])} ({dominant[1]}/100)")
        question = body.question.casefold().strip(" ¿?¡!.,")
        greetings = ("hola", "buenas", "buenos días", "buenas tardes", "buenas noches", "cómo estás", "como estas", "qué tal", "que tal")
        thanks = ("gracias", "muchas gracias", "te agradezco")
        capabilities = ("qué puedes hacer", "que puedes hacer", "cómo puedes ayudar", "como puedes ayudar", "ayuda")
        risk_terms = ("riesgo", "zona", "factor", "dimensión", "dimension", "falta", "dato", "evaluación", "evaluacion", "social", "ambiental", "geológico", "geologico", "resum")
        if any(phrase in question for phrase in greetings):
            answer = f"¡Hola! Estoy listo para ayudarte con GeoPredIA. Ahora está seleccionada {zone['name']}. Puedes pedirme un resumen de su riesgo, su factor principal o los datos que faltan."
            facts = []
        elif any(phrase in question for phrase in thanks):
            answer = "¡De nada! Si quieres, puedo resumir otra zona o explicar cuál de sus tres dimensiones presenta el valor más alto."
            facts = []
        elif any(phrase in question for phrase in capabilities):
            answer = "Puedo resumir el riesgo de una zona, comparar sus dimensiones geológica, ambiental y social, identificar datos faltantes y señalar qué evidencia debe revisar el equipo. No cambio puntuaciones ni tomo la decisión final."
            facts = []
        elif not any(term in question for term in risk_terms):
            answer = "Puedo ayudarte con las evaluaciones de GeoPredIA. Pregúntame, por ejemplo: «Resume el riesgo», «¿Cuál es el factor principal?» o «¿Qué información falta?»."
            facts = []
        elif missing or "falta" in question:
            detail = ", ".join(missing) if missing else "ninguno registrado"
            answer = f"En {zone['name']}, los campos faltantes son: {detail}. Un dato ausente requiere revisión y no se interpreta como riesgo cero."
        elif "por qué" in question or "porque" in question or "factor" in question:
            lead = f"La dimensión más alta es la {labels.get(dominant[0], dominant[0])}, con {dominant[1]}/100." if dominant else "No hay subíndices suficientes para identificar un factor dominante."
            answer = f"{zone['name']} tiene riesgo global {evaluation.get('global_risk') if evaluation.get('global_risk') is not None else 'sin calcular'} y clasificación {evaluation.get('classification', 'sin clasificar')}. {lead} Consulta la evidencia de la evaluación antes de atribuir causas."
        else:
            dimensions = ", ".join(f"{labels.get(key, key)} {value}/100" for key, value in available)
            answer = f"{zone['name']} ({zone.get('region') or 'región no registrada'}) presenta riesgo global {evaluation.get('global_risk') if evaluation.get('global_risk') is not None else 'sin calcular'}, clasificación {evaluation.get('classification', 'sin clasificar')}. Subíndices: {dimensions or 'sin datos'}."
        return {"answer": answer, "facts": facts,
                "suggested_actions": ["Ejecutar análisis multiagente", "Revisar evidencia", "Enviar a revisión humana"],
                "evaluation_id": evaluation.get("id"), "mode": "local-rules", "joule_deployed": False,
                "notice": "Asistente local compatible con una futura acción de Joule Studio; no es SAP Joule desplegado."}

    @app.get("/api/telemetry")
    def readings(zone_id: str | None = None):
        return store.list_records("telemetry", zone_id)

    @app.post("/api/telemetry", status_code=201)
    def telemetry(body: TelemetryRequest, request: Request):
        require_secret(request, "DEVICE_API_KEY", "x-device-key")
        get_zone(body.zone_id)
        record = body.model_dump(mode="json")
        quality = "missing" if all(value is None for value in record["readings"].values()) else "measured" if body.source == "device" else "synthetic"
        record.update(id=str(uuid4()), received_at=now(), quality=quality)
        return store.add_telemetry(record)

    @app.post("/api/telemetry/simulate", status_code=201)
    def simulate(body: SimulationRequest):
        get_zone(body.zone_id)
        record = {"id": str(uuid4()), "zone_id": body.zone_id, "device_id": "simulator-ui",
                  "observed_at": now(), "received_at": now(), "source": "simulator", "quality": "synthetic",
                  "readings": {"air_temperature_c": round(random.uniform(17, 25), 1),
                               "air_humidity_pct": round(random.uniform(40, 65), 1),
                               "soil_moisture_pct": round(random.uniform(20, 75), 1),
                               "water_temperature_c": round(random.uniform(13, 19), 1)}}
        return store.add_telemetry(record)

    @app.get("/api/reviews")
    def reviews():
        return store.list_records("reviews")

    @app.post("/api/reviews", status_code=201)
    def review(body: ReviewRequest):
        get_evaluation(body.evaluation_id)
        with store.connection() as db:
            flow = db.execute("SELECT status FROM workflows WHERE evaluation_id=?", (body.evaluation_id,)).fetchone()
            if flow:
                raise HTTPException(409, "La evaluación fue enviada a BPA; registra su decisión en ese proceso.")
        record = body.model_dump()
        record.update(id=str(uuid4()), decided_at=now(), source="local-demo", identity_verified=False)
        return store.add_review(record)

    @app.post("/api/integrations/bpa/start", status_code=201)
    def start_workflow(body: AgentRequest):
        evaluation = get_evaluation(body.evaluation_id)
        if evaluation["review_status"] != "pending":
            raise HTTPException(409, "Esta versión ya tiene decisión.")
        with store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM reviews WHERE evaluation_id=?", (body.evaluation_id,)).fetchone():
                raise HTTPException(409, "Esta versión ya tiene decisión.")
            if db.execute("SELECT 1 FROM workflows WHERE evaluation_id=?", (body.evaluation_id,)).fetchone():
                raise HTTPException(409, "El envío ya fue iniciado. Revisa BPA antes de volver a enviarlo.")
            if not configured("BPA_API_URL", "BPA_TOKEN_URL", "BPA_CLIENT_ID", "BPA_CLIENT_SECRET", "BPA_DEFINITION_ID", "BPA_CALLBACK_KEY"):
                raise IntegrationUnavailable("Configura BPA, su definición y la clave del callback antes de enviar.")
            db.execute("INSERT INTO workflows VALUES (?,NULL,'starting')", (body.evaluation_id,))
        try:
            instance_id = bpa_start(evaluation)
        except IntegrationUnavailable:
            with store.connection() as db:
                db.execute("UPDATE workflows SET status='uncertain' WHERE evaluation_id=?", (body.evaluation_id,))
                store.audit_in(db, "bpa.start_uncertain", body.evaluation_id, "Verificar monitor BPA; no reintentar automáticamente")
            raise
        with store.connection() as db:
            db.execute("UPDATE workflows SET instance_id=?,status='started' WHERE evaluation_id=?", (instance_id, body.evaluation_id))
            store.audit_in(db, "bpa.started", body.evaluation_id, instance_id)
        return {"evaluation_id": body.evaluation_id, "workflow_instance_id": instance_id, "status": "started"}

    @app.post("/api/integrations/bpa/callback")
    def workflow_callback(body: WorkflowCallback, request: Request):
        require_secret(request, "BPA_CALLBACK_KEY", "x-workflow-key")
        get_evaluation(body.evaluation_id)
        with store.connection() as db:
            flow = db.execute("SELECT instance_id,status FROM workflows WHERE evaluation_id=?", (body.evaluation_id,)).fetchone()
            if not flow or flow["instance_id"] != body.workflow_instance_id or flow["status"] != "started":
                raise HTTPException(409, "La instancia BPA no corresponde a esta evaluación.")
        existing = store.list_records("reviews", body.evaluation_id)
        if existing:
            if all(existing[0].get(key) == value for key, value in body.model_dump().items()):
                return existing[0]
            raise HTTPException(409, "Ya existe una decisión distinta para esta evaluación.")
        record = body.model_dump()
        record.update(id=str(uuid4()), decided_at=now(), source="bpa", identity_verified=False, callback_authenticated=True)
        return store.add_review(record)

    @app.post("/api/integrations/hana/sync")
    def hana_sync():
        import json
        zones = hana_import_zones()
        with store.connection() as db:
            for zone in zones:
                existing = db.execute("SELECT body FROM zones WHERE id=?", (zone["id"],)).fetchone()
                if existing and json.loads(existing[0])["source"] == "synthetic":
                    raise HTTPException(409, "Una zona oficial coincide con un ID de demo. Usa IDs oficiales distintos o una base de datos nueva sin fixtures.")
                db.execute("INSERT INTO zones(id,body) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (zone["id"], json.dumps(zone)))
            store.audit_in(db, "hana.zones_imported", "hana", str(len(zones)))
        return {"imported": len(zones), "source": "hana", "note": "Importa los scores desde SAC para estas zonas."}

    @app.get("/api/audit")
    def audit():
        return store.audit()

    @app.post("/api/integrations/hana/publish")
    def hana_publish():
        from .hana_publish import publish_events
        events = store.export_events()
        result = publish_events(events)
        store.mark_exported(events)
        return {**result, "batch_size": len(events), "more": bool(store.export_events())}

    @app.get("/")
    def frontend():
        return RedirectResponse("/frontend/console/index.html")

    app.mount("/frontend/console", StaticFiles(directory=ROOT / "frontend" / "console", check_dir=False), name="frontend")
    return app


app = create_app()
