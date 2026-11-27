"""Tests du moteur de score : cas calculés à la main, classement, exclusions, entrées invalides.

Données SYNTHÉTIQUES (tests/fixtures/synthetic_scoring_data.py). Poids : secteur 35, VE 35, taille
du fonds 20, période d'investissement 10 (config.py, validés le 2026-11-20).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.logic.scoring import Fund, score_operation
from tests.fixtures.synthetic_scoring_data import (
    FUNDS,
    OPERATION_A,
    OPERATION_B,
    OPERATION_C,
    fund,
    funds,
    operation,
)

# Critères v1 (2026-11-20) : ces tests vérifient les règles v1, toujours présentes dans le code.
# Depuis le 2026-11-25, la configuration par défaut est la v2 : on remet la v1 (tests/conftest.py).
pytestmark = pytest.mark.usefixtures("scoring_v1")


def by_id(result, strategy_id):
    return next(r for r in [*result.ranked, *result.excluded] if r.strategy_id == strategy_id)


def points(fund_result):
    return {c.id: c.points for c in fund_result.criteria if c.kind == "graded"}


# --- Deux cas complets calculés à la main (aussi dans app/docs/acceptance.md, SC1 et SC2) -------


def test_hand_case_1_bravo_for_operation_a_is_67_5():
    # Opération A : LBO primaire, ticket 15 M€, VE 60 M€, software_it, majoritaire, 2026-11-20.
    # Fonds Bravo : primary_lbo + build_up, ticket 5-20, VE 20-100, stake both, generalist,
    #               dernier fonds 100 M€ levé en 2021.
    # Éliminatoires : primary_lbo accepté ; 5 <= 15 <= 20 ; both accepte majoritaire -> conservé.
    # G1 secteur : généraliste -> 35 x 0,5 = 17,5
    # G2 VE      : 20 <= 60 <= 100 -> 35 x 1 = 35
    # G3 taille  : 15 / 100 = 15 %, entre 10 % et 20 % -> 20 x 0,5 = 10
    # G4 période : 2026 - 2021 = 5 ans, entre 5 et 6 -> 10 x 0,5 = 5
    # Total      : 17,5 + 35 + 10 + 5 = 67,5
    result = by_id(score_operation(operation(), funds()), "syn-bravo")
    assert result.excluded is False
    assert points(result) == {"G1": 17.5, "G2": 35, "G3": 10, "G4": 5}
    assert result.score == 67.5


def test_hand_case_2_foxtrot_for_operation_a_is_27_5():
    # Opération A (voir cas 1).
    # Fonds Foxtrot : primary_lbo, ticket 10-15, VE 70-150, stake both, industrials,
    #                 dernier fonds 75 M€ levé en 2019.
    # Éliminatoires : primary_lbo accepté ; 10 <= 15 <= 15 (ticket = maximum : accepté) ; both.
    # G1 secteur : industrials, pas software_it, pas généraliste -> 0
    # G2 VE      : 60 < 70, mais 0,75 x 70 = 52,5 <= 60 -> proche -> 35 x 0,5 = 17,5
    # G3 taille  : 15 / 75 = 20 % exactement, <= 20 % -> 20 x 0,5 = 10
    # G4 période : 2026 - 2019 = 7 ans, > 6 -> 0
    # Total      : 0 + 17,5 + 10 + 0 = 27,5
    result = by_id(score_operation(operation(), funds()), "syn-foxtrot")
    assert result.excluded is False
    assert points(result) == {"G1": 0, "G2": 17.5, "G3": 10, "G4": 0}
    assert result.score == 27.5


# --- Classement -----------------------------------------------------------------------------------


def test_ranking_for_operation_a():
    # Alpha 100 ; Bravo 67,5 ; Delta 67,5 (35 + 17,5 manquant + 10 manquant + 5) ; Golf 65
    # (35 + 0 + 20 + 10) ; Foxtrot 27,5. Exclus : Charlie et Echo.
    result = score_operation(operation(), funds())
    assert [(r.rank, r.strategy_id, r.score) for r in result.ranked] == [
        (1, "syn-alpha", 100),
        (2, "syn-bravo", 67.5),
        (3, "syn-delta", 67.5),
        (4, "syn-golf", 65),
        (5, "syn-foxtrot", 27.5),
    ]
    assert [r.strategy_id for r in result.excluded] == ["syn-charlie", "syn-echo"]
    assert result.operation_id == "SYN-OP-A"
    assert result.config_version == "2026-11-20"


def test_tie_break_fewer_missing_data_wins_before_sector_points():
    # Bravo et Delta : 67,5 tous les deux. Delta a plus de points en secteur (35 contre 17,5) mais
    # 3 données manquantes contre 0 : la règle 2 (moins de données manquantes) passe avant la
    # règle 3.
    result = score_operation(operation(), funds())
    bravo, delta = by_id(result, "syn-bravo"), by_id(result, "syn-delta")
    assert bravo.score == delta.score == 67.5
    assert len(bravo.missing_data) == 0
    assert sorted(delta.missing_data) == sorted(
        ["ticket_min_eur_m", "ev_min_eur_m, ev_max_eur_m", "last_fund_size_eur_m"]
    )
    assert bravo.rank < delta.rank


def test_tie_break_sector_points_then_alphabetical_id():
    base = {**FUNDS[0], "ev_min_eur_m": 80, "ev_max_eur_m": 200}  # VE proche : G2 = 17,5
    # Même score 82,5, aucune donnée manquante :
    # zulu : secteur 35 + VE 17,5 + 20 + 10 = 82,5
    # yankee : généraliste 17,5 + VE 35 + 20 + 10 = 82,5 -> moins de points en secteur
    # xray et alpha2 : identiques à zulu -> départagés par strategy_id
    zulu = Fund.model_validate({**base, "strategy_id": "zulu"})
    xray = Fund.model_validate({**base, "strategy_id": "xray"})
    alpha2 = Fund.model_validate({**base, "strategy_id": "alpha2"})
    yankee = Fund.model_validate({**FUNDS[0], "strategy_id": "yankee", "sectors": ["generalist"]})
    result = score_operation(operation(), [yankee, zulu, xray, alpha2])
    assert [r.score for r in result.ranked] == [82.5, 82.5, 82.5, 82.5]
    assert [r.strategy_id for r in result.ranked] == ["alpha2", "xray", "zulu", "yankee"]


def test_input_order_does_not_change_the_result():
    forward = score_operation(operation(), funds())
    backward = score_operation(operation(), list(reversed(funds())))
    again = score_operation(operation(), funds())
    assert forward.model_dump() == backward.model_dump() == again.model_dump()


def test_operation_b_ranks_charlie_first_with_100():
    # Charlie : build_up accepté ; 20 <= 40 <= 60 ; minoritaire ; healthcare 35 ; 100 <= 250 <= 400
    # 35 ; 40 / 500 = 8 % -> 20 ; 2026 - 2024 = 2 ans -> 10 ; total 100.
    result = score_operation(operation(OPERATION_B), funds())
    assert (result.ranked[0].strategy_id, result.ranked[0].score) == ("syn-charlie", 100)


def test_scores_stay_between_0_and_100():
    for raw in (OPERATION_A, OPERATION_B, OPERATION_C):
        result = score_operation(operation(raw), funds())
        for r in [*result.ranked, *result.excluded]:
            assert 0 <= r.score <= 100


# --- Exclusions -----------------------------------------------------------------------------------


def test_excluded_fund_lists_every_reason():
    # Charlie pour l'opération A : n'accepte pas primary_lbo, ticket min 20 > 15, minoritaire
    # seulement.
    charlie = by_id(score_operation(operation(), [fund("syn-charlie")]), "syn-charlie")
    assert charlie.excluded is True
    assert charlie.score == 0
    assert charlie.rank is None
    assert [reason.split(": ")[0] for reason in charlie.exclusion_reasons] == [
        "Deal type",
        "Minimum ticket",
        "Stake sought",
    ]
    # Les critères graduels ne sont pas calculés pour un fonds exclu.
    assert all(c.kind == "eliminatory" for c in charlie.criteria)


def test_no_compatible_fund_gives_an_empty_ranking():
    result = score_operation(operation(OPERATION_C), funds())
    assert result.ranked == []
    assert len(result.excluded) == len(FUNDS)


def test_every_criterion_has_a_french_explanation():
    result = score_operation(operation(), funds())
    for r in [*result.ranked, *result.excluded]:
        for c in r.criteria:
            assert c.explanation.strip() != ""


# --- Entrées invalides ---------------------------------------------------------------------------


def test_duplicate_strategy_id_is_refused():
    with pytest.raises(ValueError, match="en double"):
        score_operation(operation(), [fund("syn-alpha"), fund("syn-alpha")])


@pytest.mark.parametrize(
    "field",
    [
        "deal_type",
        "equity_ticket_eur_m",
        "enterprise_value_eur_m",
        "sector",
        "stake_sought",
        "analysis_date",
    ],
)
def test_operation_with_a_missing_field_is_refused(field):
    raw = {k: v for k, v in OPERATION_A.items() if k != field}
    with pytest.raises(ValidationError):
        operation(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sector", "generalist"),
        ("sector", "aerospace"),
        ("deal_type", "seed"),
        ("equity_ticket_eur_m", 0),
        ("stake_sought", "both"),
    ],
)
def test_operation_with_an_invalid_value_is_refused(field, value):
    with pytest.raises(ValidationError):
        operation(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sectors", ["aerospace"]),
        ("stake", "lender"),
        ("ticket_min_eur_m", 0),
        ("ticket_min_eur_m", 30),
    ],  # 30 > maximum 20
)
def test_fund_with_an_invalid_value_is_refused(field, value):
    with pytest.raises(ValidationError):
        Fund.model_validate({**FUNDS[0], field: value})


def test_empty_csv_cell_is_missing_not_zero():
    alpha = Fund.model_validate({**FUNDS[0], "last_fund_size_eur_m": "", "sectors": ""})
    assert alpha.last_fund_size_eur_m is None
    assert alpha.sectors is None
