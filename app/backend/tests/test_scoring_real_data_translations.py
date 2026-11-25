"""Tests ajoutés après la relecture du 2026-11-25 : chaque traduction de la base vers le moteur.

Les valeurs attendues sont les règles validées par Arthur le 2026-11-25 (app/docs/scoring.md,
« Branchement sur la vraie base »), recopiées ici à la main : si quelqu'un change une traduction
dans reference.py, un test échoue et la règle doit être rejustifiée. Les comptes sur la vraie base
viennent du diagnostic du 2026-11-25 ; si strategies.csv change, refaire ce diagnostic.
"""

from __future__ import annotations

import inspect

import pytest

from app.data.investors import load_investors
from app.logic.reference import (
    DATA_DEAL_TYPE_COVERAGE,
    DATA_NON_PE_DEAL_TAGS,
    DATA_SECTORS,
    DATA_VAGUE_DEAL_TAGS,
)
from app.logic.scoring import Operation
from app.logic.scoring.real_data import (
    best_strategy_per_management_company,
    deal_types_from_tags,
    funds_from_base,
    score_operation_on_base,
    sectors_for,
    stake_from_tags,
    unclassified_sector_metadata,
)

DATA_CHANGED = "strategies.csv a changé : refaire le diagnostic et les calculs à la main"


@pytest.fixture(scope="module")
def data():
    return load_investors()


LBO_SMALL = Operation(
    operation_id="EX-LBO-SMALL",
    company_name="PME industrielle (exemple)",
    deal_type="primary_lbo",
    equity_ticket_eur_m=15,
    enterprise_value_eur_m=40,
    sector="industrials",
    stake_sought="majority",
    analysis_date="2026-11-25",
)


# --- Tables de traduction : recopie à la main des règles validées -----------------------------


def test_deal_type_coverage_table_is_the_validated_one():
    lbo = ("primary_lbo", "secondary_lbo")
    assert DATA_DEAL_TYPE_COVERAGE == {
        "buyout": lbo,
        "lbo": lbo,
        "transmission": lbo,
        "primary_lbo": ("primary_lbo",),
        "mbo": ("primary_lbo",),
        "mbi": ("primary_lbo",),
        "obo": ("primary_lbo",),
        "management_buyout": ("primary_lbo",),
        "primary_buyout": ("primary_lbo",),
        "growth": ("growth",),
        "growth_capital": ("growth",),
        "growth_equity": ("growth",),
        "growth_buyout": ("growth", "primary_lbo"),
        "build_up": ("build_up",),
        "buy_and_build": ("build_up",),
        "add_on": ("build_up",),
        "carve_out": ("carve_out",),
    }


def test_sector_table_is_the_validated_one():
    assert DATA_SECTORS == {
        "TECH_SOFTWARE": ("software_it",),
        "HEALTHCARE": ("healthcare",),
        "BUSINESS_SERVICES": ("business_services",),
        "INDUSTRIALS": ("industrials",),
        "CONSUMER": ("consumer_retail",),
        "FINANCIAL_SERVICES": ("financial_services",),
        "ENERGY_ENV": ("energy_environment",),
        "FOOD_AGRI": ("food_beverage", "agriculture"),
        "INFRA_TRANSPORT": ("transport_logistics",),
        "REAL_ESTATE_HOSPITALITY": ("construction_real_estate",),  # approximation documentée
    }


def test_the_three_deal_tag_families_do_not_overlap():
    coverage = set(DATA_DEAL_TYPE_COVERAGE)
    assert not coverage & DATA_NON_PE_DEAL_TAGS
    assert not coverage & DATA_VAGUE_DEAL_TAGS
    assert not DATA_NON_PE_DEAL_TAGS & DATA_VAGUE_DEAL_TAGS


@pytest.mark.parametrize("tag", sorted(DATA_NON_PE_DEAL_TAGS))
def test_each_non_pe_tag_alone_gives_non_pe(tag):
    assert deal_types_from_tags((tag,)) == ["non_pe"]


@pytest.mark.parametrize("tag", sorted(DATA_VAGUE_DEAL_TAGS))
def test_each_vague_tag_alone_is_missing_data(tag):
    assert deal_types_from_tags((tag,)) is None


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (("lbo",), ["primary_lbo", "secondary_lbo"]),
        (("transmission",), ["primary_lbo", "secondary_lbo"]),
        (("mbi",), ["primary_lbo"]),
        (("obo",), ["primary_lbo"]),
        (("management_buyout",), ["primary_lbo"]),
        (("primary_buyout",), ["primary_lbo"]),
        (("growth_capital",), ["growth"]),
        (("growth_equity",), ["growth"]),
        (("add_on",), ["build_up"]),
        (("carve_out",), ["carve_out"]),
        (("turnaround", "carve_out"), ["carve_out"]),  # vague ignoré, PE gardé
    ],
)
def test_remaining_deal_tags(tags, expected):
    assert deal_types_from_tags(tags) == expected


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (("significant_minority",), "minority"),
        (("lead_minority",), "minority"),
        (("majority", "minority"), "both"),
        (("majority", "co-investor"), "both"),
        (("control_not_explicit", "majority"), "majority"),  # vague ignoré
        ((), None),
    ],
)
def test_remaining_stake_tags(tags, expected):
    assert stake_from_tags(tags) == expected


# --- Cas réels : généraliste et secteurs approximés -------------------------------------------


def test_generalist_open_fund_is_generalist_not_missing(data):
    # str-adaxtra-pme : sector_scope GENERALIST_OPEN, aucune exclusion -> ["generalist"].
    # deal_types transmission;growth_capital (transmission couvre le LBO primaire), stake
    # majority;minority -> both, tickets non publiés : conservé pour le LBO small cap.
    assert sectors_for(data, "str-adaxtra-pme") == ["generalist"]
    result = score_operation_on_base(LBO_SMALL, data)
    fund = next(r for r in result.ranked if r.strategy_id == "str-adaxtra-pme")
    g1 = next(c for c in fund.criteria if c.id == "G1")
    assert (g1.status, g1.points) == ("partial", 17.5)  # généraliste : 35 x 0,5
    assert "sectors" not in fund.missing_data


def test_all_39_generalist_open_funds_without_exclusion_are_generalist(data):
    open_ids = [
        sid
        for sid, s in data.sector_summary.items()
        if s["sector_scope"] == "GENERALIST_OPEN"
        and not any(
            r["polarity"] == "EXCLUDED_EXPLICIT" for r in data.strategy_sectors.get(sid, ())
        )
    ]
    assert len(open_ids) == 39, DATA_CHANGED
    assert all(sectors_for(data, sid) == ["generalist"] for sid in open_ids)


@pytest.mark.parametrize(
    ("strategy_id", "expected"),
    [
        ("str-ext-trail-slam", ["consumer_retail"]),  # CONSUMER seul
        ("str-sodero-transition", ["energy_environment"]),  # ENERGY_ENV seul
        ("str-extendam-hotels", ["construction_real_estate"]),  # REAL_ESTATE_HOSPITALITY (approx.)
        ("str-merieux-buyout", ["healthcare"]),  # HEALTHCARE seul
    ],
)
def test_real_single_sector_funds(data, strategy_id, expected):
    assert sectors_for(data, strategy_id) == expected


# --- Garde-fous sur la base -------------------------------------------------------------------


def test_sector_scope_and_polarity_values_are_all_known(data):
    assert unclassified_sector_metadata(data) == {"sector_scope": set(), "polarity": set()}


def test_translation_counts_match_the_documented_diagnostic(data):
    # Chiffres de scoring.md, « Qualité des données, critère par critère ».
    funds = funds_from_base(data)
    assert sum(f.deal_types == ["non_pe"] for f in funds) == 14, DATA_CHANGED
    assert sum(f.deal_types is None for f in funds) == 5, DATA_CHANGED
    assert sum(f.stake is None for f in funds) == 57, DATA_CHANGED
    assert sum(f.sectors is None for f in funds) == 5, DATA_CHANGED
    assert sum(f.ticket_min_eur_m is None for f in funds) == 124, DATA_CHANGED
    no_ev = sum(f.ev_min_eur_m is None and f.ev_max_eur_m is None for f in funds)
    one_ev = sum((f.ev_min_eur_m is None) != (f.ev_max_eur_m is None) for f in funds)
    assert (no_ev, one_ev) == (131, 3), DATA_CHANGED
    assert len({row["fund_id"] for row in data.strategies.values()}) == 109, DATA_CHANGED


def test_base_still_has_no_fund_size_or_year_column(data):
    columns = set(next(iter(data.strategies.values())))
    assert not {"last_fund_size_eur_m", "last_fund_year"} & columns, (
        "La base contient maintenant la taille ou l'année du dernier fonds : les brancher dans "
        "real_data.fund_from_strategy (G3, G4) au lieu de None."
    )


def test_longlist_keeps_the_best_strategy_of_every_company(data):
    result = score_operation_on_base(LBO_SMALL, data)
    longlist = best_strategy_per_management_company(data, result)
    fund_of = {sid: row["fund_id"] for sid, row in data.strategies.items()}
    first_per_company = {}
    for r in result.ranked:
        first_per_company.setdefault(fund_of[r.strategy_id], r.strategy_id)
    assert len(longlist) == len(first_per_company)
    assert [r.strategy_id for r in longlist] == list(first_per_company.values())


def test_score_operation_on_base_requires_an_already_loaded_base():
    # La couche logique ne lit aucun fichier : la base doit être passée en paramètre.
    parameter = inspect.signature(score_operation_on_base).parameters["data"]
    assert parameter.default is inspect.Parameter.empty
