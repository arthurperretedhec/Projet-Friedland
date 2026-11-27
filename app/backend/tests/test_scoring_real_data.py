"""Tests du moteur de score sur la VRAIE base de fonds (app/backend/data/, chargeur de Simon).

Les valeurs attendues des trois fonds réels sont calculées à la main à partir de leurs lignes dans
strategies.csv (recopiées en commentaire), avec les règles de app/docs/scoring.md. Si la base est
corrigée, ces tests peuvent échouer : il faut alors refaire le calcul à la main, pas recopier la
sortie du moteur.
"""

from __future__ import annotations

import pytest

from app.data.investors import load_investors
from app.logic.scoring import Operation, load_config, score_operation
from app.logic.scoring.config import SCORING_CONFIG_V1
from app.logic.scoring.real_data import (
    best_strategy_per_management_company,
    deal_types_from_tags,
    fund_from_strategy,
    funds_from_base,
    score_operation_on_base,
    sectors_for,
    stake_from_tags,
    unclassified_values,
)

# Critères v1 (2026-11-20) pour les tests écrits avant les critères v2 : leurs valeurs attendues
# ne changent pas. Les valeurs v2 sont dans test_scoring_v2_*.py.
CONFIG_V1 = load_config(SCORING_CONFIG_V1)


@pytest.fixture(scope="module")
def data():
    return load_investors()


# Opération A : LBO majoritaire small cap, PME industrielle, VE 40 M€, ticket 15 M€.
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
# Opération B : build-up mid cap, services aux entreprises, VE 150 M€, ticket 40 M€.
BUILDUP_MID = Operation(
    operation_id="EX-BUILDUP-MID",
    company_name="ETI de services (exemple)",
    deal_type="build_up",
    equity_ticket_eur_m=40,
    enterprise_value_eur_m=150,
    sector="business_services",
    stake_sought="majority",
    analysis_date="2026-11-25",
)


def by_id(result, strategy_id):
    return next(r for r in [*result.ranked, *result.excluded] if r.strategy_id == strategy_id)


def points(fund_result):
    return {c.id: c.points for c in fund_result.criteria if c.kind == "graded"}


# --- La base se charge et chaque fonds passe dans le moteur -----------------------------------


def test_base_loads_with_153_strategies(data):
    assert len(data.strategies) == 153


def test_every_strategy_becomes_a_valid_fund(data):
    funds = funds_from_base(data)
    assert len(funds) == 153
    assert len({f.strategy_id for f in funds}) == 153


def test_every_value_of_the_base_has_a_translation(data):
    # Une nouvelle valeur dans le CSV doit être classée dans app/logic/reference.py.
    assert unclassified_values(data) == {"deal_types": set(), "stake": set(), "sectors": set()}


@pytest.mark.parametrize("operation", [LBO_SMALL, BUILDUP_MID], ids=["lbo-small", "buildup-mid"])
def test_both_example_operations_score_every_fund(data, operation):
    result = score_operation_on_base(operation, data)
    assert len(result.ranked) + len(result.excluded) == 153
    assert all(0 <= r.score <= 100 for r in result.ranked)
    assert all(r.score == 0 and r.exclusion_reasons for r in result.excluded)
    assert [r.rank for r in result.ranked] == list(range(1, len(result.ranked) + 1))
    # Même résultat si l'on recalcule, ou si l'on donne les fonds dans l'autre ordre.
    again = score_operation(operation, list(reversed(funds_from_base(data))))
    assert again.model_dump() == result.model_dump()


def test_g3_and_g4_have_no_data_and_give_15_neutral_points(data):
    result = score_operation_on_base(LBO_SMALL, data, CONFIG_V1)
    for r in result.ranked:
        assert {"last_fund_size_eur_m", "last_fund_year"} <= set(r.missing_data)
        assert points(r)["G3"] + points(r)["G4"] == 15  # 20 x 0,5 + 10 x 0,5


def test_one_line_per_management_company(data):
    result = score_operation_on_base(LBO_SMALL, data)
    longlist = best_strategy_per_management_company(data, result)
    companies = [data.strategies[r.strategy_id]["fund_id"] for r in longlist]
    assert len(companies) == len(set(companies))
    assert longlist[0].strategy_id == result.ranked[0].strategy_id


# --- Traductions (règles validées le 2026-11-25) ----------------------------------------------


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (("buyout", "growth"), ["primary_lbo", "secondary_lbo", "growth"]),  # union
        (("mbo",), ["primary_lbo"]),
        (("buy_and_build",), ["build_up"]),
        (("growth_buyout",), ["primary_lbo", "growth"]),
        (("venture", "growth"), ["growth"]),  # le hors-PE ne retire rien au PE publié
        (("infrastructure_equity",), ["non_pe"]),  # seulement hors PE -> non_pe
        (("impact", "long_term"), None),  # seulement des libellés vagues -> manquant
        ((), None),
    ],
)
def test_deal_type_translation(tags, expected):
    assert deal_types_from_tags(tags) == expected


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (("majority", "controlling_minority"), "both"),
        (("co-investor",), "minority"),
        (("reference_shareholder",), "minority"),
        (("control_not_explicit",), None),
        (("majority",), "majority"),
    ],
)
def test_stake_translation(tags, expected):
    assert stake_from_tags(tags) == expected


def test_sector_translation_with_approximations(data):
    # Amethis Europe : FOOD_AGRI;INDUSTRIALS;HEALTHCARE;TECH_SOFTWARE;BUSINESS_SERVICES, thèmes.
    assert sectors_for(data, "str-amethis-europe") == [
        "food_beverage",
        "agriculture",
        "industrials",
        "healthcare",
        "software_it",
        "business_services",
    ]
    # Argos Mid-Market : généraliste avec préférences -> préférences + generalist.
    assert sectors_for(data, "str-argos-midmarket") == [
        "business_services",
        "industrials",
        "generalist",
    ]
    # Exclusion explicite de secteur (cas repris de Simon) -> donnée manquante.
    assert sectors_for(data, "str-ext-pleiade-longterm") is None


# --- Trois fonds réels calculés à la main -----------------------------------------------------


def test_real_fund_1_abenex_industries_for_lbo_small_is_85(data):
    # strategies.csv, str-abenex-industries-90 (source : abenex.com, first closing) :
    #   deal_types buyout;growth -> primary_lbo, secondary_lbo, growth
    #   stake majority;controlling_minority -> both ; sectors INDUSTRIALS (thèmes)
    #   ticket 5 à 20 ; VE min vide, VE max 60 ; taille et année du fonds : absentes
    # E1 primary_lbo couvert : rempli. E2 15 >= 5, E3 15 <= 20 : remplis. E4 both : rempli.
    # G1 industrials ciblé : 35. G2 40 <= 60 (une seule borne) : 35, ev_min listé manquant.
    # G3 manquant : 20 x 0,5 = 10. G4 manquant : 10 x 0,5 = 5.
    # Total : 35 + 35 + 10 + 5 = 85.
    result = by_id(score_operation_on_base(LBO_SMALL, data, CONFIG_V1), "str-abenex-industries-90")
    assert result.excluded is False
    assert points(result) == {"G1": 35, "G2": 35, "G3": 10, "G4": 5}
    assert result.score == 85
    assert sorted(result.missing_data) == ["ev_min_eur_m", "last_fund_size_eur_m", "last_fund_year"]
    assert fund_from_strategy(data, "str-abenex-industries-90").stake == "both"


def test_real_fund_2_argos_midmarket_for_buildup_mid_is_85(data):
    # strategies.csv, str-argos-midmarket (source : argos.fund/fr/argos-mid-market) :
    #   deal_types buyout;build_up -> primary_lbo, secondary_lbo, build_up ; stake majority
    #   sectors BUSINESS_SERVICES;INDUSTRIALS, scope GENERALIST_PLUS_PREFERENCES
    #   ticket : vide (min et max) ; VE 50 à 250 ; taille et année du fonds : absentes
    # E1 build_up couvert : rempli. E2, E3 : donnée manquante (conservé, alerte). E4 : rempli.
    # G1 business_services ciblé : 35. G2 50 <= 150 <= 250 : 35.
    # G3 manquant : 10. G4 manquant : 5. Total : 35 + 35 + 10 + 5 = 85.
    result = by_id(score_operation_on_base(BUILDUP_MID, data, CONFIG_V1), "str-argos-midmarket")
    assert result.excluded is False
    assert points(result) == {"G1": 35, "G2": 35, "G3": 10, "G4": 5}
    assert result.score == 85
    statuses = {c.id: c.status for c in result.criteria if c.kind == "eliminatory"}
    assert statuses == {"E1": "pass", "E2": "missing", "E3": "missing", "E4": "pass"}
    assert sum("to check before contact" in w for w in result.warnings) == 2


def test_real_fund_3_antin_flagship_is_excluded_from_lbo_small(data):
    # strategies.csv, str-antin-flagship : deal_types infrastructure_equity (hors PE) -> non_pe ;
    #   ticket min 400 ; stake vide.
    # E1 : primary_lbo non couvert -> exclu. E2 : 15 < 400 -> exclu. E4 : donnée manquante.
    # Fonds exclu, score 0, deux raisons.
    result = by_id(score_operation_on_base(LBO_SMALL, data), "str-antin-flagship")
    assert result.excluded is True
    assert result.score == 0
    assert [r.split(": ")[0] for r in result.exclusion_reasons] == [
        "Deal type",
        "Minimum ticket",
    ]
    assert "no private equity deal type" in result.exclusion_reasons[0]
