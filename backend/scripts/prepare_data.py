"""Prepare the organizer-provided CSV for CAP's automatic initial-data loader."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SOURCE = REPO / "analytics" / "dataset_tema2_georisk.csv"
TARGET = BACKEND / "db" / "data" / "geopredia-OfficialEvaluations.csv"
EXPECTED_COLUMNS = {
    "EVALUACION_ID", "ZONA_ID", "ZONA_NOMBRE", "REGION",
    "SISMICIDAD_INDICE", "INDICE_ESTRES_HIDRICO",
    "INDICE_ACEPTACION_SOCIAL", "ESTADO_REVISION"
}


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"No se encontró el dataset oficial: {SOURCE}")
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(EXPECTED_COLUMNS - headers)
        if missing:
            raise SystemExit("El CSV no cumple el contrato. Faltan: " + ", ".join(missing))
        rows = sum(1 for _ in reader)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, TARGET)
    print(f"CAP_DATASET={TARGET}")
    print(f"ROWS={rows}")


if __name__ == "__main__":
    main()
