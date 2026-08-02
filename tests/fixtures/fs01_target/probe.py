"""Permanent deterministic before/after fixture probe."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

root = Path(__file__).parent
observation = {
    "artifact": (root / "artifact.txt").read_text(encoding="utf-8"),
    "sentinel_sha256": hashlib.sha256((root / "sentinel.txt").read_bytes()).hexdigest(),
}
print(json.dumps(observation, separators=(",", ":"), sort_keys=True))
