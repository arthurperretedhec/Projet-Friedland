"""Critères v2 sur la VRAIE base (app/backend/data/) : cas réels calculés à la main, classement par
société de gestion, garde-fous.

Valeurs recopiées de strategies.csv en commentaire ; si la base change, refaire le calcul à la main.
"""

from __future__ import annotations

import pytest

from app.data.investors import load_investors
from app.logic.reference import (
    GEO_FRENCH_REGIONS,
    GEO_OTHER,
    GEO_WIDE_INCLUDING_FRANCE,
)
from app.logic.scoring import Operation, load_config
from app.logic.scoring.config import SCORING_CONFIG_V1
from app.logic.scoring.real_data import (
    rank_management_companies,
    score_operation_on_base,
    unclassified_geography,
)

DATA_CHANGED = "strategies.csv a changé : refaire le calcul à la main"


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


# --- Cas réels calculés à la main -------------------------------------------------------------


def test_sc5_v2_abenex_industries_for_lbo_small_is_90(data):
    # strategies.csv ligne 2, str-abenex-industries-90 :
    #   deal_types buyout;growth ; stake majority;controlling_minority ; INDUSTRIALS ; ticket 5-20
    #   primary_bucket BUYOUT ; buyer_role CONTROL_POSSIBLE ; geography_tags France;Italy;Benelux
    #   transaction_modifiers thematic_sector_focus ; classification_basis INTERPRETED_DESCRIPTION
    # Éliminatoires : conservé (inchangé). G1 industrials ciblé 40 ; G5 BUYOUT = BUYOUT 25 ;
    # G6 CONTROL_POSSIBLE (majoritaire) 15 ; G7 France 10 ; G8 pas de transmission 0.
    # Total : 40 + 25 + 15 + 10 + 0 = 90. Aucune donnée manquante : confiance 9 / 9, élevé.
    result = by_id(score_operation_on_base(LBO_SMALL, data), "str-abenex-industries-90")
    assert points(result) == {"G1": 40, "G5": 25, "G6": 15, "G7": 10, "G8": 0}, DATA_CHANGED
    assert result.score == 90
    assert result.missing_data == []
    assert (result.confidence.criteria_known, result.confidence.level) == (9, "élevé")


def test_sc6_v2_argos_midmarket_for_buildup_mid_is_100(data):
    # strategies.csv ligne 46, str-argos-midmarket :
    #   deal_types buyout;build_up ; stake majority ; BUSINESS_SERVICES;INDUSTRIALS ; tickets vides
    #   primary_bucket BUYOUT ; buyer_role CONTROL_POSSIBLE ;
    #   geography_tags France;Benelux;Germany;Italy;Europe
    #   transaction_modifiers buy_and_build ; classification_basis SOURCE_DESCRIPTION
    # Éliminatoires : conservé, tickets non vérifiables (2 alertes). G1 business_services 40 ;
    # G5 BUYOUT 25 ; G6 15 ; G7 France 10 ; G8 buy_and_build 10. Total : 100.
    # Confiance : 2 données manquantes sur 9 (les 2 tickets, éliminatoires) -> moyen.
    result = by_id(score_operation_on_base(BUILDUP_MID, data), "str-argos-midmarket")
    assert points(result) == {"G1": 40, "G5": 25, "G6": 15, "G7": 10, "G8": 10}, DATA_CHANGED
    assert result.score == 100
    assert (result.confidence.criteria_known, result.confidence.level) == (7, "moyen")
    assert result.confidence.missing_data == ["ticket_min_eur_m", "ticket_max_eur_m"]


def test_sc7_v2_antin_flagship_still_excluded(data):
    # Inchangé : infrastructure_equity (hors PE) et ticket minimum 400 -> exclu, pas de confiance.
    result = by_id(score_operation_on_base(LBO_SMALL, data), "str-antin-flagship")
    assert result.excluded is True
    assert result.confidence is None


def test_aldebaran_now_eligible_thanks_to_family_succession(data):
    # str-aldebaran-transform : deal_types carve_out;turnaround;family_succession;
    #   market_consolidation -> family_succession couvre le LBO primaire (v2) ; ticket 10-50 ;
    #   majority ; INDUSTRIALS (généraliste avec préférences) ; SPECIAL_SITUATIONS, BUYOUT en
    #   secondaire ; CONTROL_POSSIBLE ; France ; buy_and_build;carve_out;turnaround.
    # G1 40 ; G5 BUYOUT secondaire 12,5 ; G6 15 ; G7 10 ; G8 pas de transmission 0. Total 77,5.
    result = by_id(score_operation_on_base(LBO_SMALL, data), "str-aldebaran-transform")
    assert result.excluded is False
    assert points(result) == {"G1": 40, "G5": 12.5, "G6": 15, "G7": 10, "G8": 0}, DATA_CHANGED
    assert result.score == 77.5


def test_family_succession_also_applies_to_the_v1_configuration(data):
    # La traduction est partagée (reference.py) : en v1, Aldebaran n'est plus exclu non plus.
    # v1 : industrials 35 ; VE : aucune borne publiée -> 35 x 0,5 = 17,5 ; taille du fonds absente
    # 20 x 0,5 = 10 ; année absente 10 x 0,5 = 5. Total : 35 + 17,5 + 10 + 5 = 67,5.
    config_v1 = load_config(SCORING_CONFIG_V1)
    result = by_id(score_operation_on_base(LBO_SMALL, data, config_v1), "str-aldebaran-transform")
    assert result.excluded is False
    assert points(result) == {"G1": 35, "G2": 17.5, "G3": 10, "G4": 5}, DATA_CHANGED
    assert result.score == 67.5


# --- Classement par société de gestion --------------------------------------------------------


@pytest.mark.parametrize("operation", [LBO_SMALL, BUILDUP_MID], ids=["lbo-small", "buildup-mid"])
def test_company_ranking(data, operation):
    result = score_operation_on_base(operation, data)
    companies = rank_management_companies(data, result)
    fund_of = {sid: row["fund_id"] for sid, row in data.strategies.items()}
    # Une ligne par société, dans l'ordre de sa meilleure stratégie.
    first = {}
    for r in result.ranked:
        first.setdefault(fund_of[r.strategy_id], r.strategy_id)
    assert [c.best_strategy_id for c in companies] == list(first.values())
    assert [c.rank for c in companies] == list(range(1, len(companies) + 1))
    for company in companies:
        best = by_id(result, company.best_strategy_id)
        assert (company.score, company.confidence) == (best.score, best.confidence)
        assert company.criteria == best.criteria
        # Autres stratégies : toutes celles de la société, sauf la meilleure, exclues comprises.
        all_ids = {sid for sid, fid in fund_of.items() if fid == company.fund_id}
        assert {o.strategy_id for o in company.other_strategies} == all_ids - {
            company.best_strategy_id
        }
        for other in company.other_strategies:
            assert other.excluded == (other.rank is None)


def test_company_with_all_strategies_excluded_is_absent(data):
    # Antin Infrastructure Partners : 3 stratégies hors PE, toutes exclues d'un LBO small.
    result = score_operation_on_base(LBO_SMALL, data)
    companies = rank_management_companies(data, result)
    antin = {sid for sid in data.strategies if sid.startswith("str-antin-")}
    assert antin and all(by_id(result, sid).excluded for sid in antin)
    assert not any(c.best_strategy_id in antin for c in companies)


# --- Garde-fous v2 ----------------------------------------------------------------------------


def test_every_geography_tag_is_classified(data):
    assert unclassified_geography(data) == set()


def test_geography_lists_do_not_overlap():
    assert not GEO_FRENCH_REGIONS & GEO_WIDE_INCLUDING_FRANCE
    assert not GEO_FRENCH_REGIONS & GEO_OTHER
    assert not GEO_WIDE_INCLUDING_FRANCE & GEO_OTHER
    assert "France" not in GEO_FRENCH_REGIONS | GEO_WIDE_INCLUDING_FRANCE | GEO_OTHER


def test_confidence_level_follows_the_number_of_missing_data(data):
    # Propriété, pour chaque stratégie classée : niveau = règle appliquée au nombre de données
    # manquantes (0-1 élevé, 2-3 moyen, 4+ faible) ; ce nombre = longueur de missing_data.
    for operation in (LBO_SMALL, BUILDUP_MID):
        for r in score_operation_on_base(operation, data).ranked:
            missing = r.confidence.criteria_total - r.confidence.criteria_known
            assert missing == len(r.missing_data)
            expected = "élevé" if missing <= 1 else "moyen" if missing <= 3 else "faible"
            assert r.confidence.level == expected, r.strategy_id


def test_confidence_spread_snapshot(data):
    # Instantané de non-régression (sortie du moteur, pas un calcul à la main) du 2026-11-25,
    # LBO small, 95 stratégies classées : élevé 13, moyen 77, faible 5.
    result = score_operation_on_base(LBO_SMALL, data)
    levels = [r.confidence.level for r in result.ranked]
    assert (levels.count("élevé"), levels.count("moyen"), levels.count("faible")) == (
        13,
        77,
        5,
    ), DATA_CHANGED
