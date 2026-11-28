"""Reversible, source-backed exclusions from the active buyer screening only.

The investors stay in the research CSVs to retain provenance and relational integrity.
The scoring API must not show these funds as eligible, ranked or excluded buyers.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.data.investors import DATA_DIR

FILENAME = "screening_exclusions.csv"
REQUIRED = (
    "fund_id", "management_company", "strategy_id", "decision",
    "checked_on", "reason", "source_url",
)


def load_screening_exclusions(directory: Path = DATA_DIR) -> frozenset[str]:
    path = directory / FILENAME
    if not path.is_file():
        raise ValueError(f"Missing required exclusion register: {path}")
    fund_ids: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        if tuple(reader.fieldnames or ()) != REQUIRED:
            raise ValueError(f"{FILENAME}: unexpected columns")
        for row in reader:
            fund_id = row["fund_id"].strip()
            if not fund_id or fund_id in fund_ids:
                raise ValueError(f"{FILENAME}, line {reader.line_num}: duplicate/empty fund_id")
            if row["decision"] != "exclude" or not row["reason"].strip():
                raise ValueError(f"{FILENAME}, line {reader.line_num}: missing reason or decision")
            if not row["checked_on"].strip() or not row["source_url"].startswith("https://"):
                raise ValueError(f"{FILENAME}, line {reader.line_num}: source/date missing")
            fund_ids.add(fund_id)
    return frozenset(fund_ids)
