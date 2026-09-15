"""Explicit SAP adapters. Configuration is not proof of a successful connection."""
import os
import re
import httpx
from .config import configured


class IntegrationUnavailable(Exception):
    pass


def bpa_start(evaluation):
    names = ("BPA_API_URL", "BPA_TOKEN_URL", "BPA_CLIENT_ID", "BPA_CLIENT_SECRET", "BPA_DEFINITION_ID")
    if not configured(*names):
        raise IntegrationUnavailable("Configura el servicio y despliega una definición BPA antes de enviar una evaluación.")
    if not all(os.environ[key].startswith("https://") for key in ("BPA_API_URL", "BPA_TOKEN_URL")):
        raise IntegrationUnavailable("Los endpoints BPA deben utilizar HTTPS.")
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.post(os.environ["BPA_TOKEN_URL"], data={"grant_type": "client_credentials"},
                                   auth=(os.environ["BPA_CLIENT_ID"], os.environ["BPA_CLIENT_SECRET"]))
            response.raise_for_status()
            token = response.json()["access_token"]
            response = client.post(os.environ["BPA_API_URL"].rstrip("/") + "/workflow/rest/v1/workflow-instances",
                                   headers={"Authorization": f"Bearer {token}"},
                                   json={"definitionId": os.environ["BPA_DEFINITION_ID"],
                                         "context": {"evaluation": evaluation}})
            response.raise_for_status()
            result = response.json()
            if not isinstance(result.get("id"), str) or not result["id"]:
                raise ValueError("Missing workflow id")
            return result["id"]
    except (httpx.HTTPError, KeyError, ValueError):
        # Never return upstream responses: they may contain credentials or tenant data.
        raise IntegrationUnavailable("BPA no confirmó el inicio. Revisa el monitor del tenant antes de reintentar.")


def hana_import_zones():
    """Read a team-owned mapping view; never alter the organizer's shared dataset."""
    if not configured("HANA_ADDRESS", "HANA_USER", "HANA_PASSWORD", "HANA_ZONE_VIEW"):
        raise IntegrationUnavailable("Falta configurar HANA y la vista de mapeo del dataset.")
    view = os.environ["HANA_ZONE_VIEW"]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*", view):
        raise IntegrationUnavailable("HANA_ZONE_VIEW debe tener formato ESQUEMA.VISTA con identificadores simples.")
    try:
        from hdbcli import dbapi
    except ImportError:
        raise IntegrationUnavailable("Instala requirements-sap.txt para activar el adaptador HANA.")
    connection = None
    try:
        connection = dbapi.connect(address=os.environ["HANA_ADDRESS"], port=int(os.getenv("HANA_PORT", "443")),
                                   user=os.environ["HANA_USER"], password=os.environ["HANA_PASSWORD"],
                                   encrypt=True, sslValidateCertificate=True)
        cursor = connection.cursor()
        schema, table = view.split(".")
        cursor.execute(f'SELECT ZONE_ID, NAME, REGION, LATITUDE, LONGITUDE FROM "{schema}"."{table}" LIMIT 500')
        rows = cursor.fetchall()
        zones = []
        for row in rows:
            if row[0] is None or row[1] is None or not str(row[0]).strip() or len(str(row[0])) > 64:
                raise ValueError("Invalid zone id")
            lat = None if row[3] is None else float(row[3])
            lng = None if row[4] is None else float(row[4])
            if (lat is not None and not -90 <= lat <= 90) or (lng is not None and not -180 <= lng <= 180):
                raise ValueError("Invalid coordinates")
            zones.append({"id": str(row[0]), "name": str(row[1]), "region": str(row[2] or ""),
                          "latitude": lat, "longitude": lng, "source": "hana", "evidence": []})
        return zones
    except Exception:
        raise IntegrationUnavailable("No se pudo leer la vista HANA. Verifica credenciales, permisos y columnas de mapeo.")
    finally:
        if connection is not None:
            connection.close()
