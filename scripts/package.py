"""Package only project sources, never keys, local databases, caches or git metadata."""
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIRS = {"agents", "analytics", "backend", "database", "docs", "frontend", "iot", "scripts", "tests", "workflows", ".github"}
ALLOWED_FILES = {".dockerignore", ".env.example", ".gitignore", "Dockerfile", "index.html", "LICENSE", "README.md", "requirements.txt", "requirements-sap.txt"}
FORBIDDEN_DIRS = {"__pycache__", ".local", ".venv", ".git", "node_modules", ".pio"}
FORBIDDEN_FILES = {"secrets.h", ".env", "default-env.json", "service-key.json", "credentials.json"}
SECRET_PATTERN = re.compile(rb"(?:gsk_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")


def files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(ROOT)
        if any(part in FORBIDDEN_DIRS for part in relative.parts):
            continue
        if relative.parts[0] not in ALLOWED_DIRS and str(relative) not in ALLOWED_FILES:
            continue
        if path.name.lower() in FORBIDDEN_FILES or path.suffix.lower() in {".db", ".sqlite", ".pyc", ".log", ".pem", ".key", ".p12", ".pfx"}:
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        if SECRET_PATTERN.search(path.read_bytes()):
            raise ValueError(f"Posible credencial en {relative}; no se creará el paquete.")
        yield path, relative.as_posix()


if __name__ == "__main__":
    sources = list(files())
    manifest = {"repository": "https://github.com/Baneado85/GeoPredIA.git",
                "base_commit": "a3330273eb7ac7a9eb0acf461ada9630a3bdfc76", "branch": "main",
                "files": [{"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path, relative in sources]}
    (ROOT / "delivery-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    destination = ROOT.parent / "outputs" / "GeoPredIA.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, relative in sources:
            archive.write(path, "GeoPredIA/" + relative)
        archive.write(ROOT / "delivery-manifest.json", "GeoPredIA/delivery-manifest.json")
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(json.dumps({"archive": str(destination), "files": len(sources) + 1, "bytes": destination.stat().st_size}, ensure_ascii=False))
