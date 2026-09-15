"""Import already calculated SAC values; never recalculate an official snapshot."""
import csv
import io
import math
from datetime import datetime
from uuid import uuid4
from .data import DIMENSIONS, classify, now

REQUIRED = {"zone_id", "evaluated_at", "model_version", "dataset_version", "geological", "environmental", "social", "global_risk"}


def parse_score(value, field, line):
    if value is None or not value.strip() or value.strip().lower() == "null":
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Fila {line}: {field} debe ser un número o estar vacío.")
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise ValueError(f"Fila {line}: {field} debe estar entre 0 y 100.")
    return number


def parse_sac_csv(text):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise ValueError("Columnas requeridas: " + ",".join(sorted(REQUIRED)))
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("El CSV contiene encabezados duplicados.")
    result = []
    for line, row in enumerate(reader, 2):
        if line > 501:
            raise ValueError("Importa como máximo 500 evaluaciones por archivo.")
        if None in row or any(row.get(key) is None for key in REQUIRED):
            raise ValueError(f"Fila {line}: cantidad de columnas incorrecta.")
        for key in ("zone_id", "model_version", "dataset_version"):
            maximum = 64 if key == "zone_id" else 100
            if not row[key].strip() or len(row[key]) > maximum:
                raise ValueError(f"Fila {line}: falta {key} o excede {maximum} caracteres.")
        try:
            timestamp = datetime.fromisoformat(row["evaluated_at"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError(f"Fila {line}: evaluated_at debe ser ISO 8601 con zona horaria.")
        scores = {d: parse_score(row[d], d, line) for d in DIMENSIONS}
        total = parse_score(row["global_risk"], "global_risk", line)
        missing = [key for key, value in scores.items() if value is None]
        if missing and total is not None:
            raise ValueError(f"Fila {line}: no se acepta un global con dimensiones ausentes.")
        if total is None:
            missing.append("global_risk")
        eid = str(uuid4())
        evidence = [{"id": f"{eid}-{d}", "dimension": d, "metric": f"{d}_sac_index",
                     "label": f"Subíndice {d} importado de SAC", "value": scores[d],
                     "unit": "índice /100", "source": "CSV declarado como exportación SAC; procedencia pendiente de verificación",
                     "quality": "missing" if scores[d] is None else "imported"} for d in DIMENSIONS]
        result.append({"id": eid, "zone_id": row["zone_id"].strip(), "source": "sac",
                       "subindices": scores, "global_risk": total, "classification": classify(total),
                       "missing_fields": missing, "model_version": row["model_version"].strip(),
                       "dataset_version": row["dataset_version"].strip(), "evaluated_at": timestamp.isoformat(),
                       "imported_at": now(), "review_status": "pending", "evidence": evidence,
                       "provenance_verified": False,
                       "notice": "Valores conservados del CSV. El importador no autentica su origen ni calcula el score."})
    if not result:
        raise ValueError("El CSV no contiene evaluaciones.")
    return result
