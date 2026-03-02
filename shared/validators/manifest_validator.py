from __future__ import annotations

import json
from pathlib import Path


def validate_json_syntax(file_path: Path) -> dict:
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_capability_semantics(document: dict) -> None:
    capabilities = document.get("capabilities", [])
    if not capabilities:
        raise ValueError("capability manifest must include at least one capability")
    for capability in capabilities:
        timeout = capability.get("maxExecutionSeconds", 0)
        if timeout <= 0 or timeout > 300:
            raise ValueError("maxExecutionSeconds must be between 1 and 300")


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    doc = validate_json_syntax(base / "examples" / "capability-manifest.example.json")
    validate_capability_semantics(doc)
    print("manifest validation passed")
