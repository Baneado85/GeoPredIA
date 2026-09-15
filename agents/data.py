"""Entirely fictional demo fixtures. These are NOT the organizer's dataset."""
from datetime import datetime, timezone
from uuid import uuid4

DIMENSIONS = ("geological", "environmental", "social")
DEFAULT_WEIGHTS = dict(zip(DIMENSIONS, (.4, .35, .25)))


def now():
    return datetime.now(timezone.utc).isoformat()


def classify(value):
    return "Sin datos" if value is None else "Alto" if value >= 70 else "Medio" if value >= 40 else "Bajo"


def seed_zones():
    definitions = [
        ("Z-001", "Andes Norte", "Cajamarca", -6.7, -78.5, (28, 34, 22)),
        ("Z-002", "Cordillera Central", "Junín", -11.5, -75.8, (72, 64, 58)),
        ("Z-003", "Valle Sur", "Arequipa", -15.8, -72.0, (43, 78, 46)),
        ("Z-004", "Sierra Oriental", "Cusco", -13.3, -71.5, (36, 41, 81)),
        ("Z-005", "Cuenca Alta", "Áncash", -9.4, -77.4, (55, None, 39)),
        ("Z-006", "Altiplano", "Puno", -15.1, -70.2, (24, 26, 31)),
    ]
    labels = ("Incertidumbre geológica de ejemplo", "Presión ambiental de ejemplo", "Riesgo de relacionamiento de ejemplo")
    zones = []
    for zid, name, region, lat, lng, scores in definitions:
        zones.append({"id": zid, "name": name, "region": region,
                      "latitude": lat, "longitude": lng, "source": "synthetic",
                      "evidence": [{"id": f"{zid}-{dim}", "dimension": dim,
                                    "metric": f"{dim}_demo_index", "label": label,
                                    "value": value, "unit": "índice de ejemplo /100",
                                    "source": "Fixture sintético GeoPredIA; no es el dataset oficial",
                                    "quality": "missing" if value is None else "synthetic"}
                                   for dim, label, value in zip(DIMENSIONS, labels, scores)]})
    return zones


def evaluate_demo(zone, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    scores = {d: next((e["value"] for e in zone["evidence"] if e["dimension"] == d), None) for d in DIMENSIONS}
    missing = [d for d, value in scores.items() if value is None]
    total = None if missing else round(sum(scores[d] * weights[d] for d in DIMENSIONS), 2)
    return {"id": str(uuid4()), "zone_id": zone["id"], "source": "demo",
            "subindices": scores, "global_risk": total, "classification": classify(total),
            "missing_fields": missing, "weights": weights, "model_version": "demo-illustrative-1",
            "dataset_version": "synthetic-local-1", "evaluated_at": now(),
            "review_status": "pending", "evidence": zone["evidence"],
            "notice": "Simulación ilustrativa local; el cálculo oficial se implementa en SAP Analytics Cloud."}
