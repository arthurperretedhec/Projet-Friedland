"""Run the dataset validator (app/backend/scripts/validate_dataset.py) on the real CSV files.

The validator was written as a standalone script; these tests make `npm run verify` and CI run it.
"""

from __future__ import annotations

import csv
import importlib.util
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
SCRIPT = BACKEND_DIR / "scripts" / "validate_dataset.py"


def _load_validator() -> Callable[[Path], bool]:
    """Load the script as a module (scripts/ is not a Python package) and return validate()."""
    spec = importlib.util.spec_from_file_location("validate_dataset", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


validate = _load_validator()


def test_real_dataset_passes_all_checks() -> None:
    assert validate(DATA_DIR) is True


def test_validator_rejects_a_ticket_minimum_above_its_maximum(tmp_path: Path) -> None:
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data)
    strategies = data / "strategies.csv"
    with strategies.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["equity_ticket_min_eur_m"] = "50"
    rows[0]["equity_ticket_max_eur_m"] = "10"
    with strategies.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(AssertionError, match="equity_ticket_min_eur_m"):
        validate(data)
