import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from hdbcli import dbapi


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "georisk_evaluations.csv"
ENV_PATH = Path(__file__).with_name("default-env.json")
TABLE = "GPI_GEORISK_EVALUATIONS"

INTEGER_COLUMNS = {
    "ALTITUD_MSNM",
    "ANIO",
    "EVENTOS_GEOLOGICOS_12M",
    "PASIVOS_AMBIENTALES_NUM",
    "ESPECIES_SENSIBLES_NUM",
    "COMUNIDADES_INFLUENCIA_NUM",
    "POBLACION_INFLUENCIA",
    "CONFLICTOS_REGISTRADOS_12M",
    "DIAS_PARALIZACION_12M",
    "CONVENIOS_VIGENTES_NUM",
    "QUEJAS_REGISTRADAS_12M",
    "ACCIONES_MITIGACION_NUM",
}

DATE_COLUMNS = {"FECHA_EVALUACION", "FECHA_DECISION"}


def convert(column: str, value: str):
    value = value.strip()
    if value == "":
        return None
    if column in INTEGER_COLUMNS:
        return int(value)
    if column in DATE_COLUMNS:
        return date.fromisoformat(value)
    if column not in TEXT_COLUMNS:
        return Decimal(value)
    return value


TEXT_COLUMNS = {
    "EVALUACION_ID",
    "ZONA_ID",
    "ZONA_NOMBRE",
    "REGION",
    "PROVINCIA",
    "DISTRITO",
    "TIPO_YACIMIENTO",
    "MINERAL_PRINCIPAL",
    "CONCESION_ID",
    "ESTADO_CONCESION",
    "EMPRESA_OPERADORA",
    "FASE_EXPLORACION",
    "TRIMESTRE",
    "MES",
    "EVALUADOR",
    "METODO_EVALUACION",
    "ESTADO_REVISION",
    "REVISOR_ASIGNADO",
    "DECISION_ESPECIALISTA",
    "COMENTARIO_REVISION",
    "MONEDA",
}


def main():
    env = json.loads(ENV_PATH.read_text(encoding="utf-8"))
    credentials = env["VCAP_SERVICES"]["hana"][0]["credentials"]
    table_name = credentials["schema"] + '"."' + TABLE

    connection = dbapi.connect(
        address=credentials["host"],
        port=int(credentials["port"]),
        user=credentials["user"],
        password=credentials["password"],
        encrypt=True,
        sslValidateCertificate=True,
        sslCryptoProvider="openssl",
        sslTrustStore=credentials["certificate"],
    )

    try:
        with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            columns = reader.fieldnames
            if not columns:
                raise RuntimeError("El CSV no contiene encabezados")

            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            placeholders = ", ".join("?" for _ in columns)
            statement = (
                f'UPSERT "{table_name}" ({quoted_columns}) '
                f"VALUES ({placeholders}) WITH PRIMARY KEY"
            )

            cursor = connection.cursor()
            batch = []
            processed = 0
            for row in reader:
                batch.append(tuple(convert(column, row[column]) for column in columns))
                if len(batch) == 500:
                    cursor.executemany(statement, batch)
                    processed += len(batch)
                    batch.clear()
            if batch:
                cursor.executemany(statement, batch)
                processed += len(batch)

            connection.commit()
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            stored = cursor.fetchone()[0]
            print(f"CSV_PROCESSED={processed}")
            print(f"HANA_ROWS={stored}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
