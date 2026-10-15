"""Shared paths for the test scripts: finds the data pack the same way the backend does."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_candidates = [Path(p) for p in [os.environ.get("CAMPUS_CUSTOMS_DATA")] if p] + [ROOT / "data", ROOT / "data" / "data"]
DATA_DIR = next((d for d in _candidates if (d / "campus_customs.db").is_file()), _candidates[0])
DB_PATH = DATA_DIR / "campus_customs.db"
