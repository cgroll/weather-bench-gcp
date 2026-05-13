"""Provenance metadata helpers.

Each pipeline artifact gets a metadata.json written alongside its data.zarr.
This gives you a complete record of what was produced, from what source,
at what time, and with what git state.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def write(path: Path | str, **fields: Any) -> None:
    """Write a metadata.json file at the given path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        **fields,
    }
    path.write_text(json.dumps(record, indent=2, default=str))
    print(f"Metadata → {path}")


def read(path: Path | str) -> dict:
    return json.loads(Path(path).read_text())
