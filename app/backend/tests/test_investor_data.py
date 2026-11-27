import csv
import shutil
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.data.investors import DATA_DIR, load_investors
from app.logic.investor_scoring import buyer_longlist, scoring_input
from app.main import app


def test_import_is_available_at_app_startup():
    with TestClient(app) as client:
        data = client.app.state.investor_data
        assert (len(data.funds), len(data.strategies)) == (112, 153)
        assert (len(data.buckets), len(data.sectors)) == (8, 10)
        strategy = data.strategies["str-abenex-industries-90"]
        assert strategy["fund_id"] == "fund-001"
        assert strategy["strategy_name"] == "Abenex Industries 9.0"
        assert strategy["equity_ticket_min_eur_m"] == Decimal("5")
        assert strategy["target_ev_min_eur_m"] is None
        assert [r["membership"] for r in data.strategy_buckets[strategy["strategy_id"]]] == [
            "PRIMARY",
            "SECONDARY",
        ]
        assert any(r["subsector"] for r in data.strategy_sectors[strategy["strategy_id"]])
        assert any(
            r["polarity"] == "EXCLUDED_EXPLICIT"
            for rows in data.strategy_sectors.values()
            for r in rows
        )


def test_loader_rejects_orphan_relationship(tmp_path):
    shutil.copytree(DATA_DIR, tmp_path / "data")
    path = tmp_path / "data" / "strategy_sectors.csv"
    with path.open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(
            ["missing", "fund-001", "Name", "Tag", "HEALTHCARE", "", "INCLUDED", "", ""]
        )
    with pytest.raises(ValueError, match="strategy_sectors.*missing"):
        load_investors(tmp_path / "data")


def test_scoring_projection_keeps_unknowns_and_does_not_infer_lbo_subtype():
    data = load_investors()
    row = scoring_input(data, "str-abenex-industries-90")
    assert row["ticket_min_eur_m"] == Decimal("5")
    assert row["ev_min_eur_m"] is None
    assert row["last_fund_year"] is None
    assert row["stake"] == "both"
    assert row["deal_types"] is None
    assert row["sectors"] == ["industrials"]


@dataclass
class Result:
    strategy_id: str
    excluded: bool = False


def test_longlist_keeps_first_eligible_strategy_per_fund_in_rank_order():
    data = load_investors()
    first = Result("str-abenex-smallcap-ii", excluded=True)
    other = Result("str-adaxtra-pme")
    winner = Result("str-abenex-industries-90")
    later = Result("str-abenex-smallcap-ii")
    assert buyer_longlist(data, [first, other, winner, later]) == [other, winner]
    assert buyer_longlist(data, [later, winner, other]) == [later, other]


@pytest.mark.parametrize(
    ("filename", "field", "value", "message"),
    [
        ("strategies", "equity_ticket_min_eur_m", "0", "positive EUR m"),
        ("strategies", "target_ev_min_eur_m", "10000", "exceeds"),
        ("strategy_buckets", "membership", "SECONDARY", "inconsistent buckets"),
        ("strategy_sectors", "fund_id", "fund-002", "invalid relationship"),
    ],
)
def test_loader_rejects_inconsistent_values(tmp_path, filename, field, value, message):
    shutil.copytree(DATA_DIR, tmp_path / "data")
    path = tmp_path / "data" / f"{filename}.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames
    rows[0][field] = value
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match=message):
        load_investors(tmp_path / "data")


def test_scoring_projection_preserves_generalist_preferences():
    data = load_investors()
    assert scoring_input(data, "str-abenex-smallcap-ii")["sectors"] == [
        "healthcare",
        "business_services",
        "generalist",
    ]


def test_scoring_projection_cannot_claim_unrestricted_fit_with_explicit_exclusions():
    data = load_investors()
    assert scoring_input(data, "str-ext-pleiade-longterm")["sectors"] is None


def test_dangel_is_attributed_to_the_reported_vehicle_outside_strategy_history():
    data = load_investors()
    deal = data.deals["deal-pr-001"]
    assert deal["strategy_id"] is None
    assert (deal["fund_id"], deal["reported_vehicle"]) == ("fund-030", "ReBest")
    assert not data.portfolio.get("str-capital-grand-est-direct")
    assert data.fund_portfolio["fund-030"][0]["company_name"] == "Automobiles Dangel"
    assert data.sources["src-pr-005"]["entity_id"] == "fund-030|Automobiles Dangel"


def test_directory_leads_do_not_supply_screening_criteria():
    data = load_investors()
    for number in range(13, 18):
        source_id = f"src-v2-{number:03}"
        assert source_id not in data.sources
        assert data.research_leads[source_id]["source_paraphrase"] is None
    for strategy_id in ("str-ext-elais-buyout", "str-ext-phillimore-niche"):
        assert data.financial_criteria[strategy_id][0]["min_eur_m"] is None
        assert data.financial_criteria[strategy_id][0]["max_eur_m"] is None
        assert scoring_input(data, strategy_id)["sectors"] is None


def test_paraphrases_and_deal_specific_provenance():
    data = load_investors()
    observation = data.sources["webcheck-20261123-01"]
    assert observation["exact_source_quote"] is None
    assert observation["source_paraphrase"]
    for number in range(1, 5):
        deal_id = f"deal-ext-{number:03}"
        assert data.sources[f"src-{deal_id}"]["source_url"] == data.deals[deal_id]["source_url"]
