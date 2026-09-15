"""Send explicitly synthetic Sentinel data; only Python's standard library is used."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
import random
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler


class NoRedirect(HTTPRedirectHandler):
    """Never forward the device key to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def valid_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as exc:
        raise argparse.ArgumentTypeError("URL inválida") from exc
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise argparse.ArgumentTypeError("Usa una URL sin credenciales, query ni fragmento")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise argparse.ArgumentTypeError("HTTPS obligatorio; HTTP solo para localhost")
    if parsed.path.rstrip("/") != "/api/telemetry":
        raise argparse.ArgumentTypeError("La URL debe terminar en /api/telemetry")
    return value


def positive_interval(value: str) -> float:
    interval = float(value)
    if not math.isfinite(interval) or interval < 1:
        raise argparse.ArgumentTypeError("El intervalo debe ser de al menos 1 segundo")
    return interval


def make_payload(device_id: str, zone_id: str, step: int, rng: random.Random) -> dict:
    # Ondas y ruido inventados para probar la UI; no representar riesgo real.
    variation = math.sin(step / 6)
    return {
        "device_id": device_id,
        "zone_id": zone_id,
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "simulator",
        "readings": {
            "air_temperature_c": round(20 + 2 * variation + rng.uniform(-0.5, 0.5), 2),
            "air_humidity_pct": round(55 + 8 * variation + rng.uniform(-1, 1), 2),
            "soil_moisture_pct": round(40 + 15 * variation + rng.uniform(-2, 2), 2),
            "water_temperature_c": round(17 + variation + rng.uniform(-0.2, 0.2), 2),
        },
    }


def send(payload: dict, url: str, key: str, ca_file: str | None = None) -> int:
    context = ssl.create_default_context(cafile=ca_file)
    opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
    request = Request(
        url,
        data=json.dumps(payload, allow_nan=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Device-Key": key},
        method="POST",
    )
    with opener.open(request, timeout=10) as response:
        return response.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telemetría SINTÉTICA de GeoPredIA Sentinel")
    parser.add_argument("--url", type=valid_url, default="http://127.0.0.1:8000/api/telemetry")
    parser.add_argument("--device-key", default=os.getenv("GEOPREDIA_DEVICE_KEY"),
                        help="Preferir variable GEOPREDIA_DEVICE_KEY para evitar historial de terminal")
    parser.add_argument("--device-id", default="sentinel-01")
    parser.add_argument("--zone-id", default="Z-001")
    parser.add_argument("--interval", type=positive_interval, default=30.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Imprime JSON sin enviar ni requerir clave")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ca-file", help="CA PEM opcional; siempre valida el certificado HTTPS")
    args = parser.parse_args(argv)
    if not args.device_id.strip() or not args.zone_id.strip():
        parser.error("device-id y zone-id no pueden estar vacíos")
    if not args.dry_run and not args.device_key:
        parser.error("Configura GEOPREDIA_DEVICE_KEY o --device-key")
    rng = random.Random(args.seed)
    print("SIMULADOR: todas las mediciones son sintéticas.", file=sys.stderr)
    step = 0
    try:
        while True:
            payload = make_payload(args.device_id, args.zone_id, step, rng)
            try:
                if args.dry_run:
                    print(json.dumps(payload, ensure_ascii=False, allow_nan=False), flush=True)
                else:
                    status = send(payload, args.url, args.device_key, args.ca_file)
                    print(f"SIMULADOR {payload['observed_at']} HTTP {status}", flush=True)
            except (HTTPError, URLError, OSError, ValueError) as exc:
                # No imprimir request, cabeceras, claves ni cuerpo de respuesta.
                detail = f"HTTP {exc.code}" if isinstance(exc, HTTPError) else type(exc).__name__
                print(f"No se confirmó la muestra: {detail}", file=sys.stderr)
                if args.once:
                    return 1
            if args.once:
                return 0
            step += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Simulador detenido.", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
