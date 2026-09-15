/* GeoPredIA console. All text received from APIs is inserted using textContent. */
"use strict";

const $ = (id) => document.getElementById(id);
const DIMENSIONS = { geological: "Geológico", environmental: "Ambiental", social: "Social" };
const DECISIONS = { pending: "Pendiente", approved: "Aprobada", observed: "Observada", rejected: "Rechazada" };
const AGENT_STATUSES = { ok: "Evidencia revisada", missing_data: "Faltan datos" };
const SCENARIOS = {
  base: { label: "Base · tres dimensiones", weights: { geological: 0.4, environmental: 0.35, social: 0.25 } },
  environmental: { label: "Mayor peso ambiental", weights: { geological: 0.25, environmental: 0.55, social: 0.2 } },
  social: { label: "Mayor peso social", weights: { geological: 0.25, environmental: 0.25, social: 0.5 } },
};
const VIEW_NAMES = { overview: "Panorama", agents: "Multiagentes", sentinel: "IoT Sentinel", reviews: "Revisión humana", data: "Datos e integración" };
const state = { zones: [], selectedId: null, status: null, offline: true, reviews: [], runs: [], telemetry: [], selectedRunId: null, selectionSequence: 0, loadSequence: 0, selectionLoading: false, scenarioKey: "base", busy: new Set() };
const numberFormat = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 });
const dateFormat = new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

function node(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined && text !== null) result.textContent = String(text);
  return result;
}
function add(parent, ...children) { children.flat().forEach((child) => { if (child !== null && child !== undefined && child !== false) parent.append(child); }); return parent; }
function icon(id) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${id}`); svg.setAttribute("aria-hidden", "true"); svg.append(use); return svg;
}
function finite(value) { return typeof value === "number" && Number.isFinite(value); }
function score(value) { return finite(value) ? numberFormat.format(value) : "—"; }
function date(value) { const d = new Date(value); return value && !Number.isNaN(d.getTime()) ? dateFormat.format(d) : "Sin fecha"; }
function currentZone() { return state.zones.find((zone) => zone.id === state.selectedId); }
function evaluation() { return currentZone()?.latest_evaluation; }
function origin(ev) { return ev?.source === "sac" ? "CSV · contrato SAC" : "DEMO"; }
function runMode(mode) { return mode === "llm" ? "LLM" : mode === "rules_fallback" ? "Reglas · respaldo por fallo del LLM" : "Reglas"; }
function weightDescription(weights) { return Object.entries(DIMENSIONS).map(([dimension, label]) => `${label}: ${finite(weights?.[dimension]) ? numberFormat.format(weights[dimension] * 100) : "—"}%`).join(" · "); }
function classification(ev) { return ["Bajo", "Medio", "Alto"].includes(ev?.classification) && finite(ev?.global_risk) ? ev.classification : "Sin datos"; }
function badge(value) { return node("span", `risk-badge ${{ Bajo: "risk-low", Medio: "risk-medium", Alto: "risk-high" }[value] || ""}`, value); }
function empty(text) { return node("div", "empty-state", text); }
function setError(error) { $("error-box").textContent = error ? (error.message || String(error)) : ""; $("error-box").hidden = !error; }
function setNotice(message, success = false) { $("notice").textContent = message; $("notice").className = `notice${success ? " success" : ""}`; $("notice").hidden = !message; }
function actionTitle() { return state.offline ? "Inicia el backend local para guardar datos y ejecutar acciones." : ""; }
function asArray(value) { return Array.isArray(value) ? value : []; }

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.method ? 60000 : 12000);
  try {
    const response = await fetch(`/api/${path}`, { ...options, signal: controller.signal, headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers } });
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("json")) throw new Error("El servicio no devolvió datos JSON. Verifica que el backend esté iniciado.");
    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail || data.message || `Error del servicio (${response.status}).`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("La solicitud tardó demasiado. Consulta la bitácora antes de repetir una acción de escritura.");
    throw error;
  } finally { clearTimeout(timeout); }
}

function demoZones() {
  const rows = [
    ["Z-001", "Andes Norte", "Cajamarca", 28, 34, 22],
    ["Z-002", "Cordillera Central", "Junín", 72, 64, 58],
    ["Z-003", "Valle Sur", "Arequipa", 43, 78, 46],
    ["Z-004", "Sierra Oriental", "Cusco", 36, 41, 81],
    ["Z-005", "Cuenca Alta", "Áncash", 55, null, 39],
    ["Z-006", "Altiplano", "Puno", 24, 26, 31],
  ];
  return rows.map(([id, name, region, geological, environmental, social]) => {
    const subindices = { geological, environmental, social };
    const missing = Object.entries(subindices).filter(([, value]) => value === null).map(([dimension]) => dimension);
    const total = missing.length ? null : Math.round((geological * 0.4 + environmental * 0.35 + social * 0.25) * 100) / 100;
    return { id, name, region, evidence: Object.entries(subindices).map(([dimension, value]) => ({ id: `${id}-${dimension}`, dimension, label: `Indicador ilustrativo ${DIMENSIONS[dimension].toLowerCase()}`, value, unit: "/100", source: "Datos sintéticos de la vista estática", quality: value === null ? "missing" : "synthetic" })), latest_evaluation: { id: `STATIC-${id}`, zone_id: id, source: "demo", subindices, global_risk: total, classification: total === null ? "Sin datos" : total < 40 ? "Bajo" : total < 70 ? "Medio" : "Alto", missing_fields: missing, model_version: "demo-illustrative-1", dataset_version: "static-v1", evaluated_at: "2026-09-15T12:00:00Z", review_status: "pending" } };
  });
}

function defaultNotice() {
  if (state.offline) return "Vista de demostración sin backend. Los datos son sintéticos y las acciones de escritura están desactivadas. Inicia el servicio siguiendo el README para ejecutar agentes, recibir sensores e importar SAC.";
  if (state.status?.mode === "demo") return "Modo demostración local · Los datos y pesos de ejemplo son ilustrativos. Las evaluaciones importadas conservan los valores del CSV; verifica su procedencia. Las integraciones externas requieren configuración.";
  return "Revisa el origen y la versión de cada evaluación antes de registrar una decisión.";
}

async function loadAll() {
  const sequence = ++state.loadSequence;
  state.selectionSequence++;
  $("loading").hidden = false; $("refresh-button").disabled = true; setError(null);
  let status;
  try { status = await api("status"); }
  catch (error) {
    if (sequence !== state.loadSequence) return;
    state.offline = true; state.status = null; state.zones = demoZones(); state.reviews = []; state.runs = []; state.telemetry = [];
    state.selectedId = state.zones.some((zone) => zone.id === state.selectedId) ? state.selectedId : state.zones[0]?.id;
    state.selectionLoading = false; renderAll(); setNotice(defaultNotice()); $("loading").hidden = true; $("refresh-button").disabled = false; return;
  }
  try {
    const [zones, reviews] = await Promise.all([api("zones"), api("reviews")]);
    if (sequence !== state.loadSequence) return;
    if (!Array.isArray(zones) || !Array.isArray(reviews)) throw new Error("La respuesta del servicio no coincide con el contrato esperado.");
    state.status = status; state.offline = false; state.zones = zones; state.reviews = reviews;
    state.selectedId = zones.some((zone) => zone.id === state.selectedId) ? state.selectedId : zones[0]?.id;
    state.runs = []; state.telemetry = []; state.selectedRunId = null;
    renderAll(); setNotice(defaultNotice()); await loadSelected();
  } catch (error) { if (sequence === state.loadSequence) setError(error); }
  finally { if (sequence === state.loadSequence) { $("loading").hidden = true; $("refresh-button").disabled = false; } }
}

async function loadSelected() {
  const sequence = ++state.selectionSequence;
  state.runs = []; state.telemetry = []; state.selectedRunId = null;
  if (state.offline || !state.selectedId) { state.selectionLoading = false; renderSelected(); return; }
  state.selectionLoading = true; renderSelected();
  const selected = state.selectedId;
  const ev = evaluation();
  const results = await Promise.allSettled([
    ev?.id ? api(`agent-runs?evaluation_id=${encodeURIComponent(ev.id)}`) : Promise.resolve([]),
    api(`telemetry?zone_id=${encodeURIComponent(selected)}`),
  ]);
  if (sequence !== state.selectionSequence || state.selectedId !== selected) return;
  state.selectionLoading = false;
  const errors = [];
  if (results[0].status === "fulfilled") { state.runs = asArray(results[0].value).sort((a, b) => (b.created_at || "").localeCompare(a.created_at || "")); state.selectedRunId = state.runs[0]?.id; } else errors.push(results[0].reason.message);
  if (results[1].status === "fulfilled") state.telemetry = asArray(results[1].value).sort((a, b) => (b.observed_at || "").localeCompare(a.observed_at || "")); else errors.push(results[1].reason.message);
  if (errors.length) setError(new Error(`No se pudieron cargar todos los detalles: ${errors.join(" ")}`));
  renderSelected();
}

function selectZone(id) {
  if (!state.zones.some((zone) => zone.id === id)) return;
  if (state.selectedId !== id) { $("decision").value = ""; $("justification").value = ""; }
  state.selectedId = id; setError(null); renderTable(); renderSelects(); renderDetail(); renderReviews(); updateButtons(); loadSelected();
}

function renderAll() { renderConnection(); renderKpis(); renderTable(); renderSelects(); renderDetail(); renderAgents(); renderTelemetry(); renderReviews(); renderIntegrations(); updateButtons(); }
function renderSelected() { renderAgents(); renderTelemetry(); updateButtons(); }

function renderConnection() {
  const label = $("connection-label"); label.replaceChildren(node("span", "dot"), document.createTextNode(state.offline ? "Vista estática" : state.status?.mode === "demo" ? "Servicio local · demo" : "Servicio disponible"));
  label.className = `connection${state.offline ? "" : " available"}`;
  $("agent-mode").textContent = state.status?.llm_mode === "llm" ? "Modo LLM configurado" : "Agentes por reglas";
}

function renderKpis() {
  const evaluations = state.zones.map((zone) => zone.latest_evaluation).filter(Boolean);
  const values = evaluations.map((ev) => ev.global_risk).filter(finite);
  const mean = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  const pending = evaluations.filter((ev) => ev.review_status === "pending").length;
  const complete = evaluations.filter((ev) => finite(ev.global_risk) && !asArray(ev.missing_fields).length).length;
  const specs = [
    ["Zonas de exploración", state.zones.length, "Portafolio registrado", "grid"],
    ["Riesgo global medio", score(mean), `De ${values.length} evaluaciones con datos`, "wave", "/100"],
    ["Pendientes de revisión", pending, "Requieren criterio humano", "check"],
    ["Evaluaciones completas", complete, `${evaluations.length - complete} con datos insuficientes`, "data"],
  ];
  $("kpis").replaceChildren(...specs.map(([title, value, foot, glyph, unit]) => add(node("article", "kpi"), add(node("div", "kpi-top"), node("span", "", title), icon(glyph)), add(node("strong", "kpi-number", value), unit ? node("small", "", unit) : null), node("span", "kpi-foot", foot))));
}

function renderTable() {
  const query = $("zone-search").value.trim().toLocaleLowerCase("es");
  const filter = $("risk-filter").value;
  const zones = state.zones.filter((zone) => `${zone.name} ${zone.region} ${zone.id}`.toLocaleLowerCase("es").includes(query) && (filter === "all" || classification(zone.latest_evaluation) === filter));
  $("zone-count").textContent = `${zones.length} zonas`;
  const rows = zones.map((zone) => {
    const ev = zone.latest_evaluation; const row = node("tr", zone.id === state.selectedId ? "selected" : "");
    const button = node("button", "zone-button", zone.name); button.type = "button"; button.setAttribute("aria-pressed", String(zone.id === state.selectedId)); button.addEventListener("click", () => selectZone(zone.id));
    add(row, add(node("td"), button, node("span", "zone-meta", `${zone.id} · ${zone.region || "Región sin registrar"}`)));
    Object.keys(DIMENSIONS).forEach((dimension) => {
      const value = ev?.subindices?.[dimension]; const bar = node("i"); bar.style.width = `${finite(value) ? Math.min(100, Math.max(0, value)) : 0}%`;
      add(row, add(node("td"), add(node("div", "mini-value"), node("span", "", score(value)), add(node("span", "mini-bar"), bar))));
    });
    add(row, add(node("td"), add(node("div", "global-cell"), node("strong", "", score(ev?.global_risk)), badge(classification(ev))))); return row;
  });
  if (!rows.length) { const cell = node("td", "muted", "No hay zonas que coincidan con el filtro."); cell.colSpan = 5; rows.push(add(node("tr"), cell)); }
  $("zones-table-body").replaceChildren(...rows);
}

function renderSelects() {
  document.querySelectorAll(".zone-select").forEach((select) => {
    select.replaceChildren(...state.zones.map((zone) => { const option = node("option", "", `${zone.id} · ${zone.name}`); option.value = zone.id; return option; }));
    select.value = state.selectedId || "";
  });
}

function scoreRing(value) {
  const wrap = node("div", "score-ring");
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("viewBox", "0 0 90 90"); svg.setAttribute("aria-hidden", "true");
  ["ring-bg", "ring-fill"].forEach((className) => { const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle"); circle.setAttribute("cx", "45"); circle.setAttribute("cy", "45"); circle.setAttribute("r", "38"); circle.setAttribute("class", className); if (className === "ring-fill") { circle.style.strokeDasharray = "238.762"; circle.style.strokeDashoffset = String(238.762 * (1 - (finite(value) ? Math.min(100, Math.max(0, value)) : 0) / 100)); } svg.append(circle); });
  return add(wrap, svg, add(node("div", "score-label", score(value)), node("small", "", "DE 100")));
}

function renderDetail() {
  const container = $("zone-detail"); const zone = currentZone(); const ev = evaluation();
  if (!zone) { container.replaceChildren(empty("Selecciona una zona para consultar su evaluación.")); return; }
  const header = add(node("div", "detail-top"), add(node("div"), node("h2", "", zone.name), node("p", "detail-meta", `${zone.region || "Región sin registrar"} · ${zone.id}`)), badge(classification(ev)));
  header.querySelector("h2").id = "detail-title";
  const summary = add(node("div", "risk-summary"), scoreRing(ev?.global_risk), add(node("div"), node("strong", "risk-summary-title", "Índice global de riesgo"), node("p", "", ev?.source === "sac" ? "Valores de archivo importado.\nVerifica su origen y versión en SAC." : "Evaluación ilustrativa local.\nPendiente de validación técnica.")));
  const dimensions = Object.entries(DIMENSIONS).map(([key, label]) => { const value = ev?.subindices?.[key]; const fill = node("div", `dimension-fill ${key}`); fill.style.width = `${finite(value) ? Math.min(100, Math.max(0, value)) : 0}%`; return add(node("div", "dimension-row"), add(node("div", "dimension-heading"), node("span", "", label), node("strong", "", score(value))), add(node("div", "dimension-track"), fill)); });
  const missing = asArray(ev?.missing_fields); const warning = missing.length ? node("p", "pending-text", `Datos faltantes: ${missing.join(", ")}. Se requiere revisión.`) : null;
  const snapshotEvidence = asArray(ev?.evidence ?? (ev?.source === "sac" ? [] : zone.evidence));
  const details = add(node("details", "evidence-details"), node("summary", "", `Consultar evidencia · ${snapshotEvidence.length} registros`));
  snapshotEvidence.forEach((item) => details.append(add(node("div", "evidence-item"), node("strong", "", item.label || item.metric || item.id), node("span", "", `${item.value === null || item.value === undefined ? "Sin dato" : String(item.value)} ${item.unit || ""}`), node("small", "", `Fuente: ${item.source || "No registrada"} · Calidad: ${item.quality || "No indicada"} · ${item.id}`))));
  const action = node("button", "button button-primary", "Actualizar evaluación demo"); action.type = "button"; action.id = "evaluate-button"; action.addEventListener("click", evaluateZone);
  const agentsLink = node("a", "button button-outline", "Ver análisis multiagente"); agentsLink.href = "#agents"; agentsLink.append(icon("arrow"));
  const scenarioSelect = node("select"); scenarioSelect.id = "scenario-select";
  scenarioSelect.replaceChildren(...Object.entries(SCENARIOS).map(([key, scenario]) => { const option = node("option", "", scenario.label); option.value = key; return option; }));
  scenarioSelect.value = state.scenarioKey;
  const scenarioLabel = node("label", "", "¿Qué pasa si cambiamos los pesos?"); scenarioLabel.htmlFor = "scenario-select";
  const scenarioWeights = node("p", "small muted", weightDescription(SCENARIOS[state.scenarioKey].weights)); scenarioWeights.id = "scenario-weights";
  scenarioSelect.addEventListener("change", () => { state.scenarioKey = scenarioSelect.value; scenarioWeights.textContent = weightDescription(SCENARIOS[state.scenarioKey].weights); });
  const scenarioBox = add(node("div", "scenario-box"), scenarioLabel, scenarioSelect, scenarioWeights, node("p", "small muted", "Genera otra evaluación de ejemplo con un ID nuevo. Pesos ilustrativos; no modifica los resultados importados."));
  scenarioBox.hidden = ev?.source === "sac";
  const savedWeights = ev?.weights ? node("p", "small muted", `Pesos de esta evaluación: ${weightDescription(ev.weights)}`) : null;
  const metadata = node("p", "evaluation-meta", ev ? `${origin(ev)} · ${ev.model_version || "Sin versión"} · ${ev.dataset_version || "Dataset sin versión"}\n${date(ev.evaluated_at)} · ${DECISIONS[ev.review_status] || "Sin revisión"}\nEvaluación: ${ev.id}` : "Esta zona aún no tiene una evaluación.");
  container.replaceChildren(header, summary, ...dimensions, ...(savedWeights ? [savedWeights] : []), ...(warning ? [warning] : []), details, scenarioBox, add(node("div", "detail-actions"), action, agentsLink), metadata);
  updateButtons();
}

function renderAgents() {
  const container = $("agents-results");
  if (state.selectionLoading) { container.replaceChildren(empty("Cargando ejecuciones de esta evaluación…")); return; }
  if (!state.runs.length) { container.replaceChildren(empty(state.offline ? "La vista estática no ejecuta agentes. Inicia el backend y pulsa «Ejecutar análisis» para obtener una ejecución registrada con evidencia." : "Esta evaluación aún no tiene análisis de agentes. Ejecuta el análisis para ver los tres especialistas y la síntesis del coordinador.")); return; }
  const run = state.runs.find((item) => item.id === state.selectedRunId) || state.runs[0];
  const select = node("select"); select.id = "run-select"; select.replaceChildren(...state.runs.map((item) => { const option = node("option", "", `${date(item.created_at)} · ${runMode(item.mode)} · ${item.id}`); option.value = item.id; return option; })); select.value = run.id; select.addEventListener("change", () => { state.selectedRunId = select.value; renderAgents(); });
  const label = node("label", "", "Ejecución registrada"); label.htmlFor = "run-select";
  const cards = asArray(run.findings).map((finding, index) => {
    const card = add(node("article", "card agent-card"), node("span", "agent-number", `0${index + 1}`), node("h3", "", DIMENSIONS[finding.dimension] ? `Especialista ${DIMENSIONS[finding.dimension].toLowerCase()}` : finding.agent), node("span", "muted-pill", AGENT_STATUSES[finding.status] || "Análisis registrado"), node("p", "", finding.summary || "Sin resumen registrado."));
    const reasons = asArray(finding.review_reasons); if (reasons.length) card.append(add(node("ul"), ...reasons.map((reason) => node("li", "", reason))));
    if (asArray(finding.missing_fields).length) card.append(node("p", "pending-text", `Falta información: ${finding.missing_fields.join(", ")}`));
    card.append(node("div", "agent-source", `Evidencia: ${asArray(finding.evidence_ids).join(" · ") || "Sin referencias"}`)); return card;
  });
  const coordinator = add(node("section", "coordinator-card"), node("div", "eyebrow", "COORDINADOR · SÍNTESIS PARA REVISIÓN"), node("h2", "", "La decisión sigue en manos del equipo"), node("p", "", run.coordinator?.summary || "Sin síntesis registrada."));
  if (asArray(run.coordinator?.review_reasons).length) coordinator.append(add(node("ul"), ...run.coordinator.review_reasons.map((reason) => node("li", "", reason))));
  const reviewLink = node("a", "button button-outline", "Ir a revisión humana"); reviewLink.href = "#reviews"; coordinator.append(reviewLink);
  container.replaceChildren(add(node("div", "run-list"), label, select), node("p", "run-meta", `${run.mode === "llm" ? "Análisis generado con LLM" : run.mode === "rules_fallback" ? "Agentes por reglas · respaldo: el LLM falló o no pasó la validación" : "Agentes por reglas · sin modelo de lenguaje"} · Evaluación ${run.evaluation_id} · ${date(run.created_at)}`), add(node("div", "agent-grid"), ...cards), coordinator);
}

function renderTelemetry() {
  const latest = state.telemetry[0]; const readings = latest?.readings || {};
  const specs = [["Temperatura del aire", "air_temperature_c", "°C", "DHT11"], ["Humedad del aire", "air_humidity_pct", "%", "DHT11"], ["Humedad del suelo", "soil_moisture_pct", "%", "Índice relativo calibrado"], ["Temperatura del agua", "water_temperature_c", "°C", "DS18B20"]];
  $("sensor-readings").replaceChildren(...specs.map(([label, key, unit, sensor]) => add(node("article", "sensor-card"), node("h3", "", label), add(node("div", "sensor-value", score(readings[key])), node("small", "", ` ${unit}`)), node("p", "", sensor), node("p", "", latest ? `${latest.source === "device" ? "Dispositivo" : "Simulador"} · ${date(latest.observed_at)}` : "Sin lecturas recibidas"))));
  const container = $("telemetry-list");
  if (state.selectionLoading) { container.replaceChildren(empty("Cargando observaciones…")); return; }
  if (!state.telemetry.length) { container.replaceChildren(empty(state.offline ? "Sin conexión al servicio de sensores. Esta vista no muestra lecturas inventadas." : "Aún no hay mediciones para esta zona. Conecta el ESP32 al servicio o genera una lectura marcada como simulada.")); return; }
  container.replaceChildren(...state.telemetry.slice(0, 8).map((reading) => add(node("article", "timeline-item"), node("h3", "", `${reading.source === "device" ? "Medición de dispositivo" : "Lectura simulada"} · ${date(reading.observed_at)}`), node("p", "", specs.map(([label, key, unit]) => `${label}: ${score(reading.readings?.[key])} ${unit}`).join(" · ")), node("small", "", `Zona: ${reading.zone_id || state.selectedId} · ${reading.device_id || "Dispositivo no indicado"}`))));
}

function renderReviews() {
  const pending = state.zones.filter((zone) => zone.latest_evaluation?.review_status === "pending");
  $("pending-count").textContent = String(pending.length);
  $("review-queue").replaceChildren(...(pending.length ? pending.map((zone, index) => {
    const button = node("button", "button button-outline", "Revisar"); button.type = "button"; button.addEventListener("click", () => { selectZone(zone.id); $("reviewer").focus(); });
    return add(node("div", "queue-item"), node("span", "queue-number", String(index + 1).padStart(2, "0")), add(node("div"), node("strong", "", zone.name), node("small", "", `${zone.latest_evaluation.id} · ${classification(zone.latest_evaluation)}`)), button);
  }) : [empty("No hay evaluaciones pendientes de revisión.")]));
  const ev = evaluation();
  $("review-evaluation-id").textContent = ev ? `${ev.id} · ${origin(ev)} · ${DECISIONS[ev.review_status] || "Sin revisión"}${ev.review_status !== "pending" ? ". Esta versión ya fue revisada. Genera otro escenario de demostración o importa una nueva evaluación para registrar otra decisión." : ". Se guardará la decisión sobre esta versión."}` : "Esta zona no tiene una evaluación vigente.";
  const reviews = [...state.reviews].sort((a, b) => (b.decided_at || b.created_at || b.reviewed_at || "").localeCompare(a.decided_at || a.created_at || a.reviewed_at || ""));
  $("review-history").replaceChildren(...(reviews.length ? reviews.map((review) => add(node("article", "timeline-item"), node("h3", "", `${DECISIONS[review.decision] || review.decision} · ${review.reviewer}`), node("p", "", review.justification), node("small", "", `${review.evaluation_id} · ${date(review.decided_at || review.created_at || review.reviewed_at)}`))) : [empty("Todavía no hay decisiones registradas.")]));
}

function renderIntegrations() {
  const specs = [["SAP HANA Cloud", "hana", "Lectura del catálogo de zonas autorizado"], ["SAP Analytics Cloud", "sac", "Cálculo oficial y exportación de valores"], ["SAP Build Process Automation", "bpa", "Flujo de revisión del equipo"], ["Modelo de lenguaje", "llm", "Explicaciones opcionales de agentes"]];
  $("integration-grid").replaceChildren(...specs.map(([name, key, description]) => {
    const configured = state.status?.integrations?.[key]?.configured === true;
    return add(node("article", "integration-card"), node("h3", "", name), node("span", "muted-pill", configured ? "Configuración presente" : "Sin configurar"), node("p", "", description), configured ? node("p", "small", "Configuración detectada; no confirma conexión al servicio.") : null);
  }));
}

function updateButtons() {
  const ev = evaluation(); const readonly = state.offline; const hasZone = Boolean(currentZone());
  const specs = [
    ["run-agents-button", readonly || !ev || state.busy.has("agents"), "agents", "Ejecutando análisis…", "Ejecutar análisis"],
    ["simulate-button", readonly || !hasZone || state.status?.mode !== "demo" || state.busy.has("simulate"), "simulate", "Generando lectura…", "Generar lectura simulada"],
    ["review-submit", readonly || !ev || ev.review_status !== "pending" || state.busy.has("review"), "review", "Guardando revisión…", ev && ev.review_status !== "pending" ? "Esta versión ya fue revisada" : "Guardar revisión"],
    ["import-submit", readonly || state.busy.has("import"), "import", "Validando importación…", "Validar e importar"],
    ["audit-button", readonly || state.busy.has("audit"), "audit", "Consultando…", "Consultar bitácora"],
    ["evaluate-button", readonly || !hasZone || ev?.source === "sac" || state.status?.mode !== "demo" || state.busy.has("evaluate"), "evaluate", "Evaluando…", ev?.source === "sac" ? "Valores conservados del CSV" : "Evaluar escenario demo"],
  ];
  specs.forEach(([id, disabled, key, loading, label]) => { const button = $(id); if (!button) return; button.disabled = disabled; button.textContent = state.busy.has(key) ? loading : label; button.title = actionTitle(); });
  ["reviewer", "decision", "justification"].forEach((id) => { $(id).disabled = readonly || state.busy.has("review"); });
  $("csv-file").disabled = readonly || state.busy.has("import");
  if ($("scenario-select")) $("scenario-select").disabled = readonly || ev?.source === "sac" || state.status?.mode !== "demo" || state.busy.has("evaluate");
}

async function mutate(key, work) {
  if (state.offline || state.busy.has(key)) return;
  state.busy.add(key); updateButtons(); setError(null);
  try { await work(); }
  catch (error) { setError(error); }
  finally { state.busy.delete(key); updateButtons(); }
}

async function refreshDataAfterWrite() {
  const previousEvaluationId = evaluation()?.id;
  const [zones, reviews] = await Promise.all([api("zones"), api("reviews")]);
  state.zones = asArray(zones); state.reviews = asArray(reviews);
  if (!state.zones.some((zone) => zone.id === state.selectedId)) state.selectedId = state.zones[0]?.id;
  if (evaluation()?.id !== previousEvaluationId) { $("decision").value = ""; $("justification").value = ""; }
  renderAll(); await loadSelected();
}

function evaluateZone() {
  const zoneId = state.selectedId;
  if (evaluation()?.source === "sac") return;
  const scenario = SCENARIOS[state.scenarioKey];
  const previousScore = evaluation()?.global_risk;
  return mutate("evaluate", async () => { const ev = await api("evaluations", { method: "POST", body: JSON.stringify({ zone_id: zoneId, weights: scenario.weights }) }); await refreshDataAfterWrite(); setNotice(`Escenario «${scenario.label}» registrado para ${zoneId}. Riesgo anterior: ${score(previousScore)}; nuevo: ${score(ev.global_risk)}. Evaluación ${ev.id}. Pesos ilustrativos.`, true); });
}

$("run-agents-button").addEventListener("click", () => {
  const ev = evaluation(); if (!ev) return;
  mutate("agents", async () => { const run = await api("agent-runs", { method: "POST", body: JSON.stringify({ evaluation_id: ev.id }) }); if (evaluation()?.id === ev.id) { await loadSelected(); state.selectedRunId = run.id; renderAgents(); } setNotice(`Análisis ${run.id} registrado para ${ev.id}. Revisa la evidencia antes de decidir.`, true); });
});
$("simulate-button").addEventListener("click", () => {
  const zoneId = state.selectedId;
  mutate("simulate", async () => { await api("telemetry/simulate", { method: "POST", body: JSON.stringify({ zone_id: zoneId }) }); if (state.selectedId === zoneId) await loadSelected(); setNotice(`Lectura simulada registrada para ${zoneId}. Su origen queda identificado como simulador.`, true); });
});
$("review-form").addEventListener("submit", (event) => {
  event.preventDefault(); const ev = evaluation(); if (!ev || !event.currentTarget.reportValidity()) return;
  const body = { evaluation_id: ev.id, reviewer: $("reviewer").value.trim(), decision: $("decision").value, justification: $("justification").value.trim() };
  if (body.reviewer.length < 2 || body.justification.length < 10) { setError(new Error("Completa tu nombre y una justificación de al menos 10 caracteres.")); return; }
  mutate("review", async () => { await api("reviews", { method: "POST", body: JSON.stringify(body) }); if (evaluation()?.id === ev.id) { $("decision").value = ""; $("justification").value = ""; } await refreshDataAfterWrite(); setNotice(`La revisión de ${ev.id} quedó registrada con la justificación de ${body.reviewer}.`, true); });
});
$("import-form").addEventListener("submit", (event) => {
  event.preventDefault(); const file = $("csv-file").files?.[0]; if (!file) return;
  if (file.size > 2 * 1024 * 1024) { setError(new Error("El archivo supera 2 MB. Exporta una tabla de evaluaciones más pequeña.")); return; }
  mutate("import", async () => { const csv = await file.text(); const result = await api("sac/import", { method: "POST", body: JSON.stringify({ csv }) }); await refreshDataAfterWrite(); $("import-result").textContent = `${result.imported} evaluaciones importadas. Se conservaron los valores y versiones del archivo SAC.`; setNotice("Importación validada y registrada. Consulta la evaluación de cada zona.", true); $("csv-file").value = ""; });
});
$("audit-button").addEventListener("click", () => mutate("audit", async () => {
  const events = asArray(await api("audit"));
  $("audit-list").className = "";
  $("audit-list").replaceChildren(...(events.length ? events.slice().reverse().slice(0, 50).map((item) => {
    const details = add(node("details"), node("summary", "small", "Ver evento completo"), node("pre", "audit-details", JSON.stringify(item, null, 2)));
    return add(node("article", "timeline-item"), node("h3", "", item.action || item.event_type || item.type || "Evento registrado"), node("small", "", date(item.created_at || item.timestamp)), details);
  }) : [empty("No hay eventos en la bitácora.")]));
}));

document.querySelectorAll(".zone-select").forEach((select) => select.addEventListener("change", () => selectZone(select.value)));
$("zone-search").addEventListener("input", renderTable); $("risk-filter").addEventListener("change", renderTable); $("refresh-button").addEventListener("click", loadAll);

function navigate() {
  const requested = location.hash.slice(1); const view = Object.hasOwn(VIEW_NAMES, requested) ? requested : "overview";
  document.querySelectorAll(".view").forEach((section) => { section.hidden = section.id !== `view-${view}`; });
  document.querySelectorAll(".nav-item").forEach((link) => { const active = link.dataset.view === view; link.classList.toggle("active", active); if (active) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current"); });
  $("breadcrumb-view").textContent = VIEW_NAMES[view]; document.title = `${VIEW_NAMES[view]} · GeoPredIA`;
}
window.addEventListener("hashchange", navigate);
navigate(); loadAll();
