"""Load every organizer CSV record into zone-level prototype snapshots.

The browser works at zone granularity.  This loader consumes all historical rows
and aggregates them per zone; it does not present the local score as an SAC result.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .data import DEFAULT_WEIGHTS, classify


def _number(row, key):
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return None


def _clip(value):
    return max(0.0, min(100.0, value))


def _mean(values):
    usable = [value for value in values if value is not None]
    return round(sum(usable) / len(usable), 2) if usable else None


def _inverse_1_to_5(value):
    return None if value is None else _clip((5 - value) * 25)


def _row_scores(row):
    seismicity = _number(row, "SISMICIDAD_INDICE")
    stability = _number(row, "ESTABILIDAD_TALUD_SCORE")
    slope = _number(row, "PENDIENTE_PROMEDIO_PCT")
    geological_events = _number(row, "EVENTOS_GEOLOGICOS_12M")
    geological = _mean([
        None if seismicity is None else _clip(seismicity * 10),
        _inverse_1_to_5(stability),
        None if slope is None else _clip(slope * 1.5),
        None if geological_events is None else _clip(geological_events * 12.5),
    ])

    water_stress = _number(row, "INDICE_ESTRES_HIDRICO")
    pm10 = _number(row, "CALIDAD_AIRE_PM10_UGM3")
    liabilities = _number(row, "PASIVOS_AMBIENTALES_NUM")
    sensitive_species = _number(row, "ESPECIES_SENSIBLES_NUM")
    environmental = _mean([
        None if water_stress is None else _clip(water_stress * 100),
        None if pm10 is None else _clip(pm10 / 1.5),
        None if liabilities is None else _clip(liabilities * 10),
        None if sensitive_species is None else _clip(sensitive_species * 8),
    ])

    conflicts = _number(row, "CONFLICTOS_REGISTRADOS_12M")
    stopped_days = _number(row, "DIAS_PARALIZACION_12M")
    acceptance = _number(row, "INDICE_ACEPTACION_SOCIAL")
    poverty = _number(row, "POBREZA_DISTRITAL_PCT")
    complaints = _number(row, "QUEJAS_REGISTRADAS_12M")
    social = _mean([
        None if conflicts is None else _clip(conflicts * 10),
        None if stopped_days is None else _clip(stopped_days * 2),
        None if acceptance is None else _clip((1 - acceptance) * 100),
        poverty,
        None if complaints is None else _clip(complaints * 2),
    ])
    return geological, environmental, social


def load_official_dataset(path: str | Path):
    groups = defaultdict(list)
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            groups[row["ZONA_ID"]].append(row)

    result = []
    for zone_id, rows in sorted(groups.items()):
        newest = max(rows, key=lambda row: row.get("FECHA_EVALUACION", ""))
        row_scores = [_row_scores(row) for row in rows]
        scores = {
            "geological": _mean([item[0] for item in row_scores]),
            "environmental": _mean([item[1] for item in row_scores]),
            "social": _mean([item[2] for item in row_scores]),
        }
        missing = [key for key, value in scores.items() if value is None]
        total = None if missing else round(sum(scores[key] * DEFAULT_WEIGHTS[key] for key in scores), 2)
        evidence = [
            {"id": f"{zone_id}-{dimension}-csv", "dimension": dimension,
             "metric": f"{dimension}_local_prototype", "label": f"Índice {dimension} agregado",
             "value": value, "unit": "índice /100",
             "source": f"Dataset oficial entregado; {len(rows)} registros históricos agregados localmente",
             "quality": "missing" if value is None else "derived-local"}
            for dimension, value in scores.items()
        ]
        zone = {
            "id": zone_id, "name": newest["ZONA_NOMBRE"], "region": newest["REGION"],
            "latitude": _number(newest, "LATITUD"), "longitude": _number(newest, "LONGITUD"),
            "source": "organizer-csv-local", "record_count": len(rows), "evidence": evidence,
        }
        evaluation = {
            "id": f"CSV-{zone_id}", "zone_id": zone_id, "source": "dataset-local",
            "subindices": scores, "global_risk": total, "classification": classify(total),
            "missing_fields": missing, "weights": DEFAULT_WEIGHTS,
            "model_version": "local-prototype-1", "dataset_version": "organizer-csv-11458",
            "evaluated_at": newest.get("FECHA_EVALUACION") or "", "review_status": "pending",
            "evidence": evidence, "records_aggregated": len(rows),
            "notice": "Usa todos los registros del CSV. El scoring local es demostrativo hasta validarlo en SAP Analytics Cloud.",
        }
        result.append((zone, evaluation))
    return result
