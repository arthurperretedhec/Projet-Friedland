"""Exclusions de la liste de buyers, sans effacer les données historiques."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.api.score import build_scoring_base
from app.data.investors import load_investors
from app.data.screening_exclusions import load_screening_exclusions


def test_active_screening_hides_excluded_funds_but_preserves_raw_data():
    data = load_investors()
    excluded = load_screening_exclusions()
    assert excluded
    assert excluded <= set(data.funds)
    base = build_scoring_base(data)
    active = {data.strategies[fund.strategy_id]["fund_id"] for fund in base.funds}
    assert not (active & excluded)
    removed_strategies = sum(s["fund_id"] in excluded for s in data.strategies.values())
    assert len(base.funds) == len(data.strategies) - removed_strategies
    # The original 112/153 source universe is deliberately not deleted.
    assert len(data.funds) == 112
    assert len(data.strategies) == 153


def test_duplicate_exclusion_is_rejected(tmp_path: Path):
    path = tmp_path / "screening_exclusions.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "fund_id",
                "management_company",
                "strategy_id",
                "decision",
                "checked_on",
                "reason",
                "source_url",
            )
        )
        row = (
            "fund-test",
            "Test",
            "str-test",
            "exclude",
            "2026-11-28",
            "No published range",
            "https://example.com/",
        )
        writer.writerow(row)
        writer.writerow(row)
    with pytest.raises(ValueError, match="duplicate"):
        load_screening_exclusions(tmp_path)
