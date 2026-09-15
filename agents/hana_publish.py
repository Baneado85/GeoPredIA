"""Explicit, transactional replication of immutable local events to a team HANA schema."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
import re
from uuid import UUID

from .config import configured
from .integrations import IntegrationUnavailable


_PREFIXES = {"evaluation": "evaluation:", "agent_run": "run:",
             "telemetry": "telemetry:", "review": "review:"}


def _prepare(events: list[dict]) -> list[tuple[str, str, str, str, str]]:
    """Validate the whole batch before touching HANA. Preserve timestamp and payload."""
    if not isinstance(events, list) or len(events) > 1000:
        raise IntegrationUnavailable("Publica una lista de hasta 1000 eventos por lote.")
    prepared = []
    seen = {}
    try:
        for event in events:
            if not isinstance(event, dict) or set(event) != {"id", "type", "created_at", "payload"}:
                raise ValueError()
            event_id, kind, timestamp, payload = (
                event["id"], event["type"], event["created_at"], event["payload"])
            if not isinstance(kind, str) or kind not in _PREFIXES:
                raise ValueError()
            if not isinstance(event_id, str) or len(event_id) > 100 or not event_id.startswith(_PREFIXES[kind]):
                raise ValueError()
            UUID(event_id[len(_PREFIXES[kind]):])
            if not isinstance(timestamp, str) or not 1 <= len(timestamp) <= 40:
                raise ValueError()
            parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed_time.tzinfo is None or not isinstance(payload, dict):
                raise ValueError()
            encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True,
                                 separators=(",", ":"), allow_nan=False)
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            row = (event_id, kind, encoded, timestamp, digest)
            if event_id in seen and seen[event_id] != row:
                raise IntegrationUnavailable("Conflicto de identidad: un evento del lote tiene dos contenidos. No se publicó el lote.")
            seen[event_id] = row
            prepared.append(row)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise IntegrationUnavailable("El lote contiene un evento inválido: revisa ID, tipo, fecha con zona horaria y JSON finito.") from None
    return prepared


def publish_events(events: list[dict]) -> dict[str, int]:
    """Publish a bounded batch only when invoked; never create tables or alter an event.

    Repeating an ID with identical type/time/payload succeeds idempotently. Any
    conflict or database failure rolls back the entire batch. A concurrent insert
    can fail safely; a later explicit retry with the same events will deduplicate.
    """
    prepared = _prepare(events)
    if not prepared:
        return {"published": 0, "already_present": 0}
    if not configured("HANA_ADDRESS", "HANA_USER", "HANA_PASSWORD", "HANA_TEAM_SCHEMA"):
        raise IntegrationUnavailable("Configura HANA y HANA_TEAM_SCHEMA para publicar en un esquema propio del equipo.")
    schema = os.environ["HANA_TEAM_SCHEMA"]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,126}", schema):
        raise IntegrationUnavailable("HANA_TEAM_SCHEMA debe ser un identificador simple en mayúsculas.")
    try:
        port = int(os.getenv("HANA_PORT", "443"))
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError:
        raise IntegrationUnavailable("HANA_PORT debe ser un puerto válido.") from None
    try:
        from hdbcli import dbapi
    except ImportError:
        raise IntegrationUnavailable("Instala requirements-sap.txt para activar la publicación en HANA.") from None

    table = f'"{schema}"."GPI_EVENT_STORE"'  # Only a strictly validated identifier is interpolated.
    connection, cursor = None, None
    try:
        connection = dbapi.connect(
            address=os.environ["HANA_ADDRESS"], port=port,
            user=os.environ["HANA_USER"], password=os.environ["HANA_PASSWORD"],
            encrypt=True, sslValidateCertificate=True, autocommit=False,
        )
        connection.setautocommit(False)
        cursor = connection.cursor()
        published, already_present = 0, 0
        within_batch = set()
        for event_id, kind, payload, timestamp, digest in prepared:
            if event_id in within_batch:
                already_present += 1
                continue
            cursor.execute(
                f'SELECT "PAYLOAD_HASH", "EVENT_TYPE", "CREATED_AT" FROM {table} WHERE "EVENT_ID" = ?',
                (event_id,),
            )
            existing = cursor.fetchone()
            if existing is not None:
                if tuple(existing) != (digest, kind, timestamp):
                    raise IntegrationUnavailable("Conflicto con un evento inmutable existente. No se publicó el lote ni se sobrescribieron datos.")
                already_present += 1
            else:
                cursor.execute(
                    f'INSERT INTO {table} ("EVENT_ID", "EVENT_TYPE", "PAYLOAD", "CREATED_AT", "PAYLOAD_HASH") '
                    'VALUES (?, ?, ?, ?, ?)',
                    (event_id, kind, payload, timestamp, digest),
                )
                published += 1
            within_batch.add(event_id)
        connection.commit()
        return {"published": published, "already_present": already_present}
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        if isinstance(exc, IntegrationUnavailable):
            raise
        # Never expose driver messages, connection values or payload contents.
        raise IntegrationUnavailable(
            "HANA no confirmó la publicación. Revisa permisos y GPI_EVENT_STORE en el esquema del equipo; "
            "si reintentas, conserva los mismos IDs."
        ) from None
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
