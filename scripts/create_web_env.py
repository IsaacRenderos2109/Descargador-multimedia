"""Create a private local .env with random web access/session secrets."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    example = ROOT / ".env.example"
    target = ROOT / ".env"
    if target.exists():
        raise SystemExit(".env ya existe; no se ha modificado.")
    content = example.read_text(encoding="utf-8")
    replacements = {
        "ACCESS_CODE": secrets.token_urlsafe(24),
        "SESSION_SECRET": secrets.token_urlsafe(48),
    }
    for name, value in replacements.items():
        content, count = re.subn(rf"(?m)^{name}=.*$", f"{name}={value}", content, count=1)
        if count != 1:
            raise SystemExit(f"No se encontró {name} en .env.example.")
    target.write_text(content, encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass  # Windows uses ACLs instead of POSIX mode bits.
    print(".env creado con secretos aleatorios. No publiques ese archivo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
