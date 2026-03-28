"""
Generate OpenAPI snapshot used by contract gate tests.

Usage:
    python scripts/generate_openapi_snapshot.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    from api.main import app

    snapshot_path = REPO_ROOT / "docs" / "contracts" / "openapi.snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    payload = app.openapi()
    snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"OpenAPI snapshot written: {snapshot_path}")


if __name__ == "__main__":
    main()
