"""Tests du moteur de score, critère par critère (données SYNTHÉTIQUES, voir tests/fixtures).

Point de départ de chaque test : l'opération A (LBO primaire, ticket 15 M€, VE 60 M€, logiciel,
majoritaire, analyse 2026-11-20) et le fonds fictif Alpha, compatible en tout (100 / 100).
Chaque test ne change qu'un champ, pour isoler la règle testée. Les valeurs attendues viennent des
règles validées (app/docs/scoring.md), jamais de la sortie du moteur.
"""

from __future__ import annotations

import pytest

from app.logic.scoring import FundResult, score_operation
from tests.fixtures.synthetic_scoring_data import compatible_fund, operation


def score_one(fund_changes: dict | None = None, **op_changes) -> FundResult:
    result = score_operation(operation(**op_changes), [compatible_fund(**(fund_changes or {}))])
    return (result.ranked or result.excluded)[0]


def criterion(result: FundResult, criterion_id: str):
    return next(c for c in result.criteria if c.id == criterion_id)


def test_reference_fund_scores_100():
    result = score_one()
    assert result.excluded is False
    assert result.score == 100
    assert result.missing_data == []


# --- E1 Type d'opération -------------------------------------------------------------------------


def test_e1_accepted_deal_type_passes():
    assert criterion(score_one(), "E1").status == "pass"


def test_e1_deal_type_not_accepted_excludes_the_fund():
    result = score_one({"deal_types": ["secondary_lbo", "growth"]})
    assert result.excluded is True
    assert result.score == 0
    assert result.rank is None
    assert criterion(result, "E1").status == "fail"
    assert len(result.exclusion_reasons) == 1
    assert result.exclusion_reasons[0].startswith("Type d'opération")


def test_e1_missing_deal_types_keeps_the_fund_with_a_warning():
    result = score_one({"deal_types": None})
    assert result.excluded is False
    assert criterion(result, "E1").status == "missing"
    assert criterion(result, "E1").status_label == "Donnée manquante"
    assert "deal_types" in result.missing_data
    assert any("à vérifier avant contact" in w for w in result.warnings)
    # Les critères graduels ne changent pas : toujours 100.
    assert result.score == 100


# --- E2 Ticket minimum ----------------------------------------------------------------------------


def test_e2_ticket_exactly_equal_to_minimum_is_accepted():
    result = score_one({"ticket_min_eur_m": 15})  # ticket de l'opération = 15
    assert criterion(result, "E2").status == "pass"
    assert result.excluded is False


def test_e2_ticket_below_minimum_excludes_the_fund():
    result = score_one({"ticket_min_eur_m": 15.5})
    assert result.excluded is True
    assert criterion(result, "E2").status == "fail"
    assert "inférieur au minimum" in result.exclusion_reasons[0]


def test_e2_missing_minimum_keeps_the_fund():
    result = score_one({"ticket_min_eur_m": None})
    assert result.excluded is False
    assert criterion(result, "E2").status == "missing"
    assert "ticket_min_eur_m" in result.missing_data


# --- E3 Ticket maximum ----------------------------------------------------------------------------


def test_e3_ticket_exactly_equal_to_maximum_is_accepted():
    result = score_one({"ticket_max_eur_m": 15})
    assert criterion(result, "E3").status == "pass"
    assert result.excluded is False


def test_e3_ticket_above_maximum_excludes_the_fund():
    result = score_one({"ticket_max_eur_m": 14.9})
    assert result.excluded is True
    assert criterion(result, "E3").status == "fail"
    assert "supérieur au maximum" in result.exclusion_reasons[0]


def test_e3_missing_maximum_keeps_the_fund():
    result = score_one({"ticket_max_eur_m": None})
    assert result.excluded is False
    assert criterion(result, "E3").status == "missing"


# --- E4 Position recherchée ----------------------------------------------------------------------


@pytest.mark.parametrize("stake_sought", ["majority", "minority"])
def test_e4_fund_taking_both_accepts_any_stake(stake_sought):
    result = score_one({"stake": "both"}, stake_sought=stake_sought)
    assert criterion(result, "E4").status == "pass"


@pytest.mark.parametrize(
    ("fund_stake", "stake_sought"), [("majority", "minority"), ("minority", "majority")]
)
def test_e4_incompatible_stake_excludes_the_fund(fund_stake, stake_sought):
    result = score_one({"stake": fund_stake}, stake_sought=stake_sought)
    assert result.excluded is True
    assert criterion(result, "E4").status == "fail"


def test_e4_missing_stake_keeps_the_fund():
    result = score_one({"stake": None})
    assert result.excluded is False
    assert criterion(result, "E4").status == "missing"


# --- G1 Secteur (35 points) -----------------------------------------------------------------------


def test_g1_targeted_sector_gets_all_35_points():
    c = criterion(score_one(), "G1")
    assert (c.status, c.points, c.max_points) == ("full", 35, 35)


def test_g1_generalist_fund_gets_half_17_5():
    c = criterion(score_one({"sectors": ["generalist"]}), "G1")
    assert (c.status, c.points) == ("partial", 17.5)  # 35 x 0,5


def test_g1_other_sector_gets_0():
    c = criterion(score_one({"sectors": ["healthcare", "industrials"]}), "G1")
    assert (c.status, c.points) == ("none", 0)


def test_g1_missing_sectors_gets_half_and_says_so():
    result = score_one({"sectors": None})
    c = criterion(result, "G1")
    assert (c.status, c.points) == ("missing", 17.5)
    assert c.status_label == "Donnée manquante"
    assert c.explanation.startswith("Donnée manquante")
    assert "sectors" in result.missing_data


def test_g1_csv_cell_with_semicolons_is_read_as_a_list():
    c = criterion(score_one({"sectors": "healthcare; software_it"}), "G1")
    assert c.status == "full"


# --- G2 Adéquation de taille, VE (35 points) -----------------------------------------------------


@pytest.mark.parametrize(
    ("ev_min", "ev_max", "status", "points"),
    [
        (20, 100, "full", 35),  # 60 dans [20, 100]
        (60, 100, "full", 35),  # VE = borne basse : dans la fourchette
        (20, 60, "full", 35),  # VE = borne haute : dans la fourchette
        (80, 200, "partial", 17.5),  # 0,75 x 80 = 60 : exactement à 25 % sous la borne basse
        (81, 200, "none", 0),  # 0,75 x 81 = 60,75 > 60 : trop loin
        (10, 48, "partial", 17.5),  # 1,25 x 48 = 60 : exactement à 25 % au-dessus de la borne haute
        (10, 47, "none", 0),  # 1,25 x 47 = 58,75 < 60 : trop loin
    ],
)
def test_g2_enterprise_value_levels_and_boundaries(ev_min, ev_max, status, points):
    c = criterion(score_one({"ev_min_eur_m": ev_min, "ev_max_eur_m": ev_max}), "G2")
    assert (c.status, c.points, c.max_points) == (status, points, 35)


def test_g2_only_minimum_published_uses_that_bound():
    c = criterion(score_one({"ev_min_eur_m": 50, "ev_max_eur_m": None}), "G2")
    assert (c.status, c.points) == ("full", 35)
    assert "une seule borne publiée" in c.explanation


def test_g2_no_bound_published_is_missing_data():
    result = score_one({"ev_min_eur_m": None, "ev_max_eur_m": None})
    c = criterion(result, "G2")
    assert (c.status, c.points) == ("missing", 17.5)
    assert "ev_min_eur_m, ev_max_eur_m" in result.missing_data


# --- G3 Taille du fonds (20 points) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("fund_size", "status", "points"),
    [
        (200, "full", 20),  # 15 / 200 = 7,5 %
        (150, "full", 20),  # 15 / 150 = 10 % exactement : complet
        (149, "partial", 10),  # 15 / 149 = 10,07 %
        (75, "partial", 10),  # 15 / 75 = 20 % exactement : partiel
        (74, "none", 0),  # 15 / 74 = 20,27 %
    ],
)
def test_g3_ticket_share_of_fund_levels_and_boundaries(fund_size, status, points):
    c = criterion(score_one({"last_fund_size_eur_m": fund_size}), "G3")
    assert (c.status, c.points, c.max_points) == (status, points, 20)


def test_g3_missing_fund_size_gets_half():
    c = criterion(score_one({"last_fund_size_eur_m": None}), "G3")
    assert (c.status, c.points) == ("missing", 10)


# --- G4 Période d'investissement (10 points) -----------------------------------------------------


@pytest.mark.parametrize(
    ("fund_year", "status", "points"),
    [
        (2022, "full", 10),  # 2026 - 2022 = 4 ans
        (2021, "partial", 5),  # 5 ans
        (2020, "partial", 5),  # 6 ans
        (2019, "none", 0),  # 7 ans
        (2027, "full", 10),  # année après la date d'analyse : traité comme récent
    ],
)
def test_g4_fund_age_levels_and_boundaries(fund_year, status, points):
    c = criterion(score_one({"last_fund_year": fund_year}), "G4")
    assert (c.status, c.points, c.max_points) == (status, points, 10)


def test_g4_uses_the_analysis_date_not_today():
    # Même fonds (2021), deux dates d'analyse : 2026 -> 5 ans (partiel), 2025 -> 4 ans (complet).
    assert criterion(score_one({"last_fund_year": 2021}), "G4").status == "partial"
    later = score_one({"last_fund_year": 2021}, analysis_date="2025-06-30")
    assert criterion(later, "G4").status == "full"


def test_g4_missing_year_gets_half():
    c = criterion(score_one({"last_fund_year": None}), "G4")
    assert (c.status, c.points) == ("missing", 5)
