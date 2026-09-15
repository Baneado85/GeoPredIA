"""Local configuration. Real credentials are never committed or returned by the API."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


load_env()


def configured(*names):
    return all(bool(os.getenv(name, "").strip()) for name in names)
