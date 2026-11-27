"""Tests des critères v2 (configuration par défaut depuis le 2026-11-25), données SYNTHÉTIQUES.

Poids v2 : secteur 40, type de fonds 25, capacité à mener 15, géographie 10, spécialité 10 ; VE,
taille et âge du fonds désactivés. Base : opération A (LBO primaire, ticket 15 M€, VE 60 M€,
software_it, majoritaire, 2026-11-20) et le fonds fictif Alpha (BUYOUT, CONTROL_POSSIBLE, France,
transmission) : 100 / 100 en v2. Les valeurs attendues sont calculées à la main en commentaire.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from app.logic.reference import DEAL_TYPES, OPERATION_BUCKET
from app.logic.scoring import ConfigError, Fund, load_config, score_operation
from app.logic.scoring.config import SCORING_CONFIG
from app.logic.scoring.real_data import deal_types_from_tags
from tests.fixtures.synthetic_scoring_data import (
    FUNDS,
    OPERATION_B,
    compatible_fund,
    fund,
    funds,
    operation,
)


def score_one(fund_changes: dict | None = None, **op_changes):
    result = score_operation(operation(**op_changes), [compatible_fund(**(fund_changes or {}))])
    return (result.ranked or result.excluded)[0]


def criterion(result, criterion_id):
    return next(c for c in result.criteria if c.id == criterion_id)


def by_id(result, strategy_id):
    return next(r for r in [*result.ranked, *result.excluded] if r.strategy_id == strategy_id)


# --- Configuration v2 -------------------------------------------------------------------------


def test_default_configuration_is_v2():
    config = load_config()
    weights = {c.id: c.weight for c in config.graded if c.enabled}
    assert weights == {"G1": 40, "G5": 25, "G6": 15, "G7": 10, "G8": 10}
    assert sum(weights.values()) == 100
    disabled = {c.id for c in config.graded if not c.enabled}
    assert disabled == {"G2", "G3", "G4"}  # désactivés, code gardé
    assert config.tie_break_criterion is None
    assert config.tie_break_source_quality is True
    # Confiance (règle du 2026-11-25) : élevé si 0 ou 1 donnée manquante, moyen si 2 ou 3.
    assert (config.confidence_high_max_missing, config.confidence_medium_max_missing) == (1, 3)
    assert config.version == SCORING_CONFIG["version"] == "2026-11-25-v2"


def test_reference_fund_scores_100_and_disabled_criteria_do_not_appear():
    result = score_one()
    assert result.score == 100
    assert {c.id for c in result.criteria if c.kind == "graded"} == {"G1", "G5", "G6", "G7", "G8"}
    # La VE n'est plus utilisée : une VE non publiée n'est pas une donnée manquante.
    no_ev = score_one({"ev_min_eur_m": None, "ev_max_eur_m": None})
    assert no_ev.score == 100
    assert no_ev.missing_data == []


def test_g1_sector_weight_is_now_40():
    assert criterion(score_one(), "G1").points == 40
    assert criterion(score_one({"sectors": ["generalist"]}), "G1").points == 20  # 40 x 0,5
    assert criterion(score_one({"sectors": ["healthcare"]}), "G1").points == 0


# --- G5 Type de fonds (25) --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("primary", "secondary", "status", "points"),
    [
        ("BUYOUT", None, "full", 25),  # LBO -> BUYOUT attendu, bucket principal
        ("GROWTH_EQUITY", ["BUYOUT"], "partial", 12.5),  # BUYOUT en secondaire : 25 x 0,5
        ("GROWTH_EQUITY", None, "none", 0),
        ("REAL_ASSETS", ["GROWTH_EQUITY"], "none", 0),
        (None, None, "missing", 12.5),  # donnée manquante : 25 x 0,5
    ],
)
def test_g5_fund_type(primary, secondary, status, points):
    result = score_one({"primary_bucket": primary, "secondary_buckets": secondary})
    c = criterion(result, "G5")
    assert (c.status, c.points, c.max_points) == (status, points, 25)
    assert ("primary_bucket" in result.missing_data) == (status == "missing")


def test_g5_growth_operation_expects_growth_equity():
    # Opération growth : GROWTH_EQUITY attendu. Alpha avec deal_types growth et bucket
    # GROWTH_EQUITY.
    changes = {"deal_types": ["growth"], "primary_bucket": "GROWTH_EQUITY"}
    c = criterion(score_one(changes, deal_type="growth"), "G5")
    assert (c.status, c.points) == ("full", 25)


@pytest.mark.parametrize("deal_type", ["secondary_lbo", "build_up"])
def test_g5_buyout_family_for_lbo_and_build_up(deal_type):
    c = criterion(score_one(deal_type=deal_type), "G5")  # Alpha : BUYOUT
    assert c.status == "full"


def test_g5_carve_out_expects_buyout():
    c = criterion(score_one({"deal_types": ["carve_out"]}, deal_type="carve_out"), "G5")
    assert c.status == "full"


# --- G6 Capacité à mener (15) -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "stake_sought", "status", "points"),
    [
        ("CONTROL_POSSIBLE", "majority", "full", 15),
        ("CONTROL_NOT_VERIFIED", "majority", "partial", 7.5),  # 15 x 0,5
        ("MINORITY_CAPITAL_PARTNER", "majority", "none", 0),
        ("CO_INVESTOR_NOT_LEAD", "majority", "none", 0),
        ("MINORITY_CAPITAL_PARTNER", "minority", "full", 15),
        ("CONTROL_POSSIBLE", "minority", "partial", 7.5),
        ("CONTROL_NOT_VERIFIED", "minority", "partial", 7.5),
        ("CO_INVESTOR_NOT_LEAD", "minority", "none", 0),
        ("LENDER_OR_HYBRID_FINANCIER", "minority", "none", 0),
        (None, "majority", "missing", 7.5),
    ],
)
def test_g6_lead_capacity(role, stake_sought, status, points):
    # Alpha avec stake both pour accepter les deux positions (E4).
    result = score_one({"buyer_role": role, "stake": "both"}, stake_sought=stake_sought)
    c = criterion(result, "G6")
    assert (c.status, c.points, c.max_points) == (status, points, 15)


# --- G7 Géographie (10) -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tags", "status", "points"),
    [
        (["France"], "full", 10),
        (["France", "Italy"], "full", 10),  # la France est citée
        (["Nouvelle_Aquitaine"], "partial", 5),  # région française : 10 x 0,5
        (["Grand Est"], "partial", 5),
        (["Europe"], "partial", 5),  # zone large incluant la France
        (["Global"], "partial", 5),
        (["Italy", "Spain"], "none", 0),  # pays étrangers seuls
        (["Sub_Saharan_Africa"], "none", 0),
        (None, "missing", 5),
    ],
)
def test_g7_geography(tags, status, points):
    result = score_one({"geography_tags": tags})
    c = criterion(result, "G7")
    assert (c.status, c.points, c.max_points) == (status, points, 10)


# --- G8 Spécialité de transaction (10) --------------------------------------------------------


@pytest.mark.parametrize(
    ("modifiers", "deal_types", "deal_type", "status", "points"),
    [
        (["transmission"], None, "primary_lbo", "full", 10),
        (["transmission"], None, "secondary_lbo", "full", 10),
        (["buy_and_build"], None, "build_up", "full", 10),
        (["carve_out"], ["carve_out"], "carve_out", "full", 10),
        (["buy_and_build"], None, "primary_lbo", "none", 0),  # pas de transmission affichée
        (["thematic_sector_focus"], ["growth"], "growth", "partial", 5),  # growth : part neutre
        (None, None, "primary_lbo", "missing", 5),
    ],
)
def test_g8_transaction_speciality(modifiers, deal_types, deal_type, status, points):
    changes = {"transaction_modifiers": modifiers}
    if deal_types:
        changes["deal_types"] = deal_types
    result = score_one(changes, deal_type=deal_type)
    c = criterion(result, "G8")
    assert (c.status, c.points, c.max_points) == (status, points, 10)


# --- Départage v2 -----------------------------------------------------------------------------


def test_tie_break_missing_data_first():
    # Golf et Delta : 90 tous les deux pour l'opération A (calcul dans
    # test_ranking_for_operation_a).
    # Golf : 0 donnée manquante ; Delta : 3 -> Golf devant, malgré une source moins bonne.
    result = score_operation(operation(), funds())
    golf, delta = by_id(result, "syn-golf"), by_id(result, "syn-delta")
    assert golf.score == delta.score == 90
    assert golf.rank < delta.rank


def test_tie_break_source_quality_then_alphabetical():
    # Cinq copies d'Alpha (100 chacune, aucune donnée manquante), qualités de source différentes.
    def copy(sid, basis):
        return Fund.model_validate({**FUNDS[0], "strategy_id": sid, "classification_basis": basis})

    candidates = [
        copy("a-historical", "HISTORICAL_DIRECTORY_LABEL"),
        copy("b-none", None),
        copy("c-broad", "BROAD_MAPPING"),
        copy("d-interpreted", "INTERPRETED_DESCRIPTION"),
        copy("z-source", "SOURCE_DESCRIPTION"),
        copy("y-source", "SOURCE_DESCRIPTION"),
    ]
    result = score_operation(operation(), candidates)
    assert [r.score for r in result.ranked] == [100] * 6
    assert [r.strategy_id for r in result.ranked] == [
        "y-source",  # SOURCE_DESCRIPTION, puis ordre alphabétique : y avant z
        "z-source",
        "d-interpreted",
        "c-broad",
        "a-historical",
        "b-none",  # qualité non renseignée : en dernier
    ]


def test_sector_points_no_longer_break_ties():
    # En v1, à égalité, le fonds avec plus de points en secteur passait devant. En v2, non.
    # a-bucket : secteur healthcare 0 + BUYOUT 25 + CONTROL_POSSIBLE 15 + France 10 + 10 = 60.
    # x-sector : software_it 40 + REAL_ASSETS 0 + VENTURE_INVESTOR 0 + France 10 + 10 = 60.
    # Aucune donnée manquante, même qualité de source -> ordre alphabétique : a-bucket devant,
    # alors que la règle v1 (points en secteur) aurait mis x-sector devant.
    bucket = Fund.model_validate({**FUNDS[0], "strategy_id": "a-bucket", "sectors": ["healthcare"]})
    sector = Fund.model_validate(
        {
            **FUNDS[0],
            "strategy_id": "x-sector",
            "primary_bucket": "REAL_ASSETS",
            "secondary_buckets": None,
            "buyer_role": "VENTURE_INVESTOR",
        }
    )
    result = score_operation(operation(), [sector, bucket])
    assert [(r.strategy_id, r.score) for r in result.ranked] == [("a-bucket", 60), ("x-sector", 60)]


# --- Indice de confiance ----------------------------------------------------------------------


# Règle du 2026-11-25 : l'indice compte les 9 critères actifs (E1 à E4 et G1, G5 à G8) ;
# élevé = 0 ou 1 donnée manquante, moyen = 2 ou 3, faible = 4 ou plus.
@pytest.mark.parametrize(
    ("changes", "known", "level"),
    [
        ({}, 9, "high"),  # Alpha : tout est publié, 0 manquante
        ({"geography_tags": None}, 8, "high"),  # 1 manquante
        ({"geography_tags": None, "transaction_modifiers": None}, 7, "medium"),  # 2
        ({"ticket_min_eur_m": None, "ticket_max_eur_m": None}, 7, "medium"),  # 2 (éliminatoires)
        (
            {"geography_tags": None, "transaction_modifiers": None, "buyer_role": None},
            6,
            "medium",
        ),  # 3
        (
            {
                "geography_tags": None,
                "transaction_modifiers": None,
                "buyer_role": None,
                "stake": None,
            },
            5,
            "low",
        ),  # 4, dont la position (éliminatoire)
    ],
)
def test_confidence_levels(changes, known, level):
    result = score_one(changes)
    assert (result.confidence.criteria_known, result.confidence.criteria_total) == (known, 9)
    assert result.confidence.level == level


def test_confidence_counts_eliminatory_missing_data():
    # Ticket minimum (éliminatoire) et géographie (notée) non publiés : 2 manquantes sur 9.
    result = score_one({"ticket_min_eur_m": None, "geography_tags": None})
    assert result.confidence.missing_data == ["ticket_min_eur_m", "geography_tags"]
    assert result.confidence.missing_data == result.missing_data  # même liste, volontairement
    assert (result.confidence.criteria_known, result.confidence.level) == (7, "medium")


def test_confidence_thresholds_must_be_ordered():
    raw = copy.deepcopy(SCORING_CONFIG)
    raw["confidence_high_max_missing"] = 4  # plus permissif que « moyen » (3) : incohérent
    with pytest.raises(ConfigError, match="confidence_high_max_missing"):
        load_config(raw)


def test_growth_speciality_is_neutral_even_without_data():
    # Problème majeur de la relecture : pour un growth, aucune spécialité n'est cherchée ; un fonds
    # sans transaction_modifiers ne doit donc pas être compté en donnée manquante.
    changes = {"deal_types": ["growth"], "transaction_modifiers": None}
    result = score_one(changes, deal_type="growth")
    c = criterion(result, "G8")
    assert (c.status, c.points) == ("partial", 5)  # 10 x 0,5
    assert "transaction_modifiers" not in result.missing_data
    assert result.confidence.criteria_known == 9


def test_every_operation_type_has_an_expected_fund_type():
    assert set(OPERATION_BUCKET) == set(DEAL_TYPES)


def test_excluded_fund_has_no_confidence():
    result = score_one({"deal_types": ["secondary_lbo"]})
    assert result.excluded is True
    assert result.confidence is None


# --- Cas calculés à la main (acceptance.md, colonnes v2) --------------------------------------


def test_sc1_v2_bravo_is_45():
    # Bravo : primary_lbo + build_up, ticket 5-20, both, generalist, GROWTH_EQUITY (BUYOUT
    # secondaire), CONTROL_NOT_VERIFIED, Europe, thematic_sector_focus.
    # Éliminatoires : conservé (comme en v1).
    # G1 généraliste 40 x 0,5 = 20 ; G5 BUYOUT secondaire 25 x 0,5 = 12,5 ;
    # G6 CONTROL_NOT_VERIFIED 15 x 0,5 = 7,5 ; G7 Europe 10 x 0,5 = 5 ; G8 pas de transmission 0.
    # Total : 20 + 12,5 + 7,5 + 5 + 0 = 45.
    result = by_id(score_operation(operation(), funds()), "syn-bravo")
    assert result.score == 45


def test_sc2_v2_foxtrot_is_12_5():
    # Foxtrot : industrials, SPECIAL_SITUATIONS (pas de secondaire), CONTROL_NOT_VERIFIED,
    # Nouvelle_Aquitaine, carve_out.
    # G1 0 ; G5 0 ; G6 7,5 ; G7 région française 5 ; G8 carve_out au lieu de transmission 0.
    # Total : 0 + 0 + 7,5 + 5 + 0 = 12,5.
    result = by_id(score_operation(operation(), funds()), "syn-foxtrot")
    assert result.score == 12.5


def test_sc3_v2_decimal_ev_no_longer_counts_and_alpha_is_100():
    # SC3 (VE 60,3 face à un minimum de 80,4) : la VE est désactivée en v2.
    # Alpha : 40 + 25 + 15 + 10 + 10 = 100.
    result = score_one({"ev_min_eur_m": 80.4, "ev_max_eur_m": 200}, enterprise_value_eur_m=60.3)
    assert result.score == 100


def test_ranking_for_operation_a():
    # Alpha 100 ; Golf 90 (40 + 25 + 15 + Afrique 0 + transmission 10, 0 manquante) ;
    # Delta 90 (40 + 25 + 15 + géo manquante 5 + spécialité manquante 5, 3 manquantes) ;
    # Bravo 45 ; Foxtrot 12,5. Exclus : Charlie, Echo (inchangé).
    result = score_operation(operation(), funds())
    assert [(r.rank, r.strategy_id, r.score) for r in result.ranked] == [
        (1, "syn-alpha", 100),
        (2, "syn-golf", 90),
        (3, "syn-delta", 90),
        (4, "syn-bravo", 45),
        (5, "syn-foxtrot", 12.5),
    ]
    assert [r.strategy_id for r in result.excluded] == ["syn-charlie", "syn-echo"]
    assert result.config_version == "2026-11-25-v2"


def test_operation_b_charlie_v2_is_75():
    # Charlie, build-up minoritaire santé : G1 santé 40 ; G5 GROWTH_EQUITY au lieu de BUYOUT, pas
    # de secondaire 0 ; G6 MINORITY_CAPITAL_PARTNER en minoritaire 15 ; G7 France 10 ;
    # G8 buy_and_build 10. Total : 40 + 0 + 15 + 10 + 10 = 75.
    result = by_id(score_operation(operation(OPERATION_B), funds()), "syn-charlie")
    assert result.score == 75


# --- Traduction et validation -----------------------------------------------------------------


def test_family_succession_now_covers_primary_lbo_but_acquisition_stays_vague():
    assert deal_types_from_tags(("family_succession",)) == ["primary_lbo"]
    assert deal_types_from_tags(("acquisition",)) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("primary_bucket", "HEDGE_FUND"),
        ("secondary_buckets", ["HEDGE_FUND"]),
        ("buyer_role", "BOSS"),
        ("classification_basis", "RUMOUR"),
    ],
)
def test_unknown_v2_values_are_refused(field, value):
    with pytest.raises(ValidationError):
        Fund.model_validate({**FUNDS[0], field: value})


def test_fixture_charlie_still_excluded_from_operation_a():
    assert by_id(score_operation(operation(), [fund("syn-charlie")]), "syn-charlie").excluded
