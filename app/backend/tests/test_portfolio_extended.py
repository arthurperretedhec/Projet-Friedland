"""Chargeur de data/portfolio_extended.csv et règle « Latest investments in France » du bandeau."""

from __future__ import annotations

import csv

import pytest

from app.api.score import data_sector_codes
from app.data.portfolio_extended import (
    FILE_NAME,
    REQUIRED_COLUMNS,
    Holding,
    latest_in_france,
    latest_in_sector,
    load_portfolio_extended,
)


def holding(name, year=None, country="France", instrument="equity", order=0, sector=None):
    return Holding(
        "fund-x", name, year, country, instrument, None, None, False, "https://x", order, sector
    )


def test_latest_keeps_equity_in_france_or_unknown_country_newest_first():
    rows = (
        holding("Old", 2019, order=1),
        holding("Debt", 2026, instrument="debt", order=2),
        holding("Italian", 2026, country="Italy", order=3),
        holding("Unknown country", 2025, country=None, order=4),
        holding("New", 2026, order=5),
        holding("Mezz", 2025, instrument="mezzanine", order=6),
    )
    assert [h.company_name for h in latest_in_france(rows)] == ["New", "Unknown country", "Old"]


def test_latest_without_years_follows_the_source_page_order():
    rows = (
        holding("B", order=2),
        holding("A", order=1),
        holding("C", order=3),
        holding("D", order=4),
    )
    assert [h.company_name for h in latest_in_france(rows)] == ["A", "B", "C"]


def test_a_dated_holding_comes_before_an_undated_one():
    rows = (holding("Undated", order=1), holding("Dated", 2020, order=2))
    assert [h.company_name for h in latest_in_france(rows)] == ["Dated", "Undated"]


def test_sector_column_keeps_equity_of_the_target_sector_in_any_country():
    rows = (
        holding("Food FR", 2024, sector="FOOD_AGRI", order=1),
        holding("Food IT", 2025, country="Italy", sector="FOOD_AGRI", order=2),
        holding("Food mezz", 2026, instrument="mezzanine", sector="FOOD_AGRI", order=3),
        holding("Industry", 2026, sector="INDUSTRIALS", order=4),
        holding("No sector", 2026, order=5),
    )
    got = latest_in_sector(rows, frozenset({"FOOD_AGRI"}))
    assert [h.company_name for h in got] == ["Food IT", "Food FR"]
    assert latest_in_sector(rows, frozenset()) == []


def test_target_sector_maps_to_base_codes_with_the_shared_table():
    assert data_sector_codes("food_beverage") == {"FOOD_AGRI"}
    assert data_sector_codes("agriculture") == {"FOOD_AGRI"}
    assert data_sector_codes("industrials") == {"INDUSTRIALS"}
    assert data_sector_codes("education") == set()  # pas de code éducation dans la base
    assert data_sector_codes(None) == set()


def _write(tmp_path, rows, columns=REQUIRED_COLUMNS):
    with (tmp_path / FILE_NAME).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


BASE = {
    "fund_id": "fund-x",
    "company_name": "Alpha",
    "status": "held",
    "instrument": "equity",
    "source_url": "https://fund.example/portfolio",
    "collected_on": "2026-11-26",
}


def test_missing_file_means_no_data(tmp_path):
    assert dict(load_portfolio_extended(tmp_path)) == {}


def test_loader_reads_holdings_and_the_ai_flag(tmp_path):
    _write(
        tmp_path,
        [
            {
                **BASE,
                "entry_year": "2024",
                "description_short": "Maker of x",
                "description_short_by": "ai_summary",
            },
            {**BASE, "company_name": "Gone", "status": "exited"},
        ],
    )
    data = load_portfolio_extended(tmp_path)
    (alpha,) = data["fund-x"]
    assert (alpha.company_name, alpha.entry_year, alpha.description_short_by_ai) == (
        "Alpha",
        2024,
        True,
    )
    assert alpha.country is None  # vide = non publié


@pytest.mark.parametrize(
    "bad, message",
    [
        ({"source_url": ""}, "fund_id, company_name et source_url obligatoires"),
        ({"entry_year": "20x4"}, "entry_year invalide"),
        ({"entry_year": "1800"}, "entry_year invalide"),
        ({"description_short_by": "human?"}, "description_short_by inconnu"),
        ({"sector": "FOOD_AGRI"}, "sector et sector_by incohérents"),
        ({"sector_by": "guess"}, "sector et sector_by incohérents"),
    ],
)
def test_loader_refuses_bad_rows_and_names_the_line(tmp_path, bad, message):
    _write(tmp_path, [{**BASE, **bad}])
    with pytest.raises(ValueError, match=f"ligne 2 : {message}"):
        load_portfolio_extended(tmp_path)


def test_loader_refuses_a_file_without_a_required_column(tmp_path):
    _write(tmp_path, [BASE], columns=[c for c in REQUIRED_COLUMNS if c != "source_url"])
    with pytest.raises(ValueError, match="colonnes manquantes source_url"):
        load_portfolio_extended(tmp_path)


def test_shipped_file_loads_and_every_ai_summary_is_flagged():
    data = load_portfolio_extended()
    assert set(data) == {"fund-001", "fund-015", "fund-027", "fund-038", "fund-099"}
    summaries = [h for rows in data.values() for h in rows if h.description_short]
    assert summaries and all(h.description_short_by_ai for h in summaries)
    # Capelia et Abenex ne publient pas de secteur : tous leurs secteurs sont signalés « IA ».
    for fund in ("fund-001", "fund-027"):
        assert all(h.sector_by_ai for h in data[fund] if h.sector)
