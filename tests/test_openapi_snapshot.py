import json
from pathlib import Path

import api.main as api_main


def test_openapi_snapshot_matches_current_api_contract():
    snapshot_path = (
        Path(__file__).resolve().parents[1] / "docs" / "contracts" / "openapi.snapshot.json"
    )
    assert (
        snapshot_path.exists()
    ), "OpenAPI snapshot missing. Run scripts/generate_openapi_snapshot.py"

    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    current = api_main.app.openapi()

    assert current == expected
