"""Tests ajoutés après la revue du 2026-11-20 (relecteurs code et tests), données SYNTHÉTIQUES.

Les tests existants n'ont pas été modifiés. Chaque valeur attendue est calculée à la main en
commentaire. Base : opération A (LBO primaire, ticket 15 M€, VE 60 M€, software_it, majoritaire,
2026-11-20) et le fonds fictif Alpha (100 / 100), dont on change un ou deux champs.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from app.logic.scoring import ConfigError, Fund, load_config, score_operation
from app.logic.scoring.config import SCORING_CONFIG_V1 as SCORING_CONFIG
from app.logic.scoring.models import ScoringConfig
from tests.fixtures.synthetic_scoring_data import FUNDS, compatible_fund, fund, operation

# Critères v1 (2026-11-20) : ces tests vérifient les règles v1, toujours présentes dans le code.
# Depuis le 2026-11-25, la configuration par défaut est la v2 : on remet la v1 (tests/conftest.py).
pytestmark = pytest.mark.usefixtures("scoring_v1")


def score_one(fund_changes: dict | None = None, config=None, **op_changes):
    result = score_operation(
        operation(**op_changes), [compatible_fund(**(fund_changes or {}))], config
    )
    return (result.ranked or result.excluded)[0]


def criterion(result, criterion_id):
    return next(c for c in result.criteria if c.id == criterion_id)


def changed(edit) -> dict:
    raw = copy.deepcopy(SCORING_CONFIG)
    edit(raw)
    return raw


def graded(raw, criterion_id):
    return next(c for c in raw["graded"] if c["id"] == criterion_id)


# --- Revue n° 1 (majeur) : seuils exacts avec des montants décimaux ---------------------------


@pytest.mark.parametrize(
    ("ticket", "fund_size", "status", "points"),
    [
        (2.24, 22.4, "full", 20),  # 2,24 / 22,4 = 10 % exactement -> complet (bornes incluses)
        # 0,7 / 7 = 10 % exactement -> complet. Contrôle de borne seulement : ce calcul tombait déjà
        # juste avant la correction, il ne reproduit pas l'ancienne erreur.
        (0.7, 7, "full", 20),
        (2.25, 22.4, "partial", 10),  # 2,25 / 22,4 = 10,04 % : juste au-dessus de 10 % -> 20 x 0,5
        (4.48, 22.4, "partial", 10),  # 4,48 / 22,4 = 20 % exactement -> partiel, 20 x 0,5 = 10
        (4.49, 22.4, "none", 0),  # 4,49 / 22,4 = 20,04 % -> au-delà de 20 %
    ],
)
def test_g3_exact_decimal_shares_land_on_the_right_level(ticket, fund_size, status, points):
    result = score_one(
        {"ticket_min_eur_m": 0.5, "last_fund_size_eur_m": fund_size},
        equity_ticket_eur_m=ticket,
    )
    c = criterion(result, "G3")
    assert (c.status, c.points) == (status, points)


@pytest.mark.parametrize(
    ("ev_min", "ev_max", "ev", "status", "points"),
    [
        (80.4, 200, 60.3, "partial", 17.5),  # 0,75 x 80,4 = 60,3 exactement -> proche
        (81.2, 200, 60.9, "partial", 17.5),  # 0,75 x 81,2 = 60,9 exactement -> proche
        (81.2, 200, 60.89, "none", 0),  # 60,89 < 60,9 -> trop loin
        # 1,25 x 48,8 = 61 exactement -> proche. Contrôle de borne seulement : la multiplication
        # par 1,25 ne produit pas l'erreur d'arrondi, ce côté n'était pas touché par l'ancien bug.
        (10, 48.8, 61, "partial", 17.5),
        (10, 48.8, 61.01, "none", 0),  # 61,01 > 61 -> trop loin
        # VE = borne basse décimale -> dans la fourchette (contrôle de borne, sans calcul).
        (20.1, 100, 20.1, "full", 35),
    ],
)
def test_g2_exact_decimal_boundaries_land_on_the_right_level(ev_min, ev_max, ev, status, points):
    result = score_one({"ev_min_eur_m": ev_min, "ev_max_eur_m": ev_max}, enterprise_value_eur_m=ev)
    c = criterion(result, "G2")
    assert (c.status, c.points) == (status, points)


def test_full_score_with_a_decimal_near_boundary():
    # Alpha avec VE 80,4 à 200, opération A avec VE 60,3 (0,75 x 80,4 = 60,3 : proche) :
    # secteur 35 + VE 35 x 0,5 = 17,5 + taille 15 / 200 = 7,5 % -> 20 + période 3 ans -> 10
    # Total : 35 + 17,5 + 20 + 10 = 82,5
    result = score_one({"ev_min_eur_m": 80.4, "ev_max_eur_m": 200}, enterprise_value_eur_m=60.3)
    assert result.score == 82.5


# --- Revue n° 2 : arrondi au plus proche, la moitié vers le haut ------------------------------


def test_total_is_rounded_half_up():
    # Configuration modifiée : secteur 33 (généraliste 25 %), VE 37 ; fonds Bravo, opération A.
    # G1 : 33 x 0,25 = 8,25 ; G2 : 37 x 1 = 37 ; G3 : 20 x 0,5 = 10 ; G4 : 10 x 0,5 = 5
    # Total exact : 8,25 + 37 + 10 + 5 = 60,25 -> arrondi à 0,1, moitié vers le haut : 60,3
    # (l'arrondi par défaut de Python aurait donné 60,2).
    def edit(r):
        graded(r, "G1")["weight"] = 33
        graded(r, "G1")["params"]["generalist_ratio"] = 0.25
        graded(r, "G2")["weight"] = 37

    config = load_config(changed(edit))
    result = score_operation(operation(), [fund("syn-bravo")], config).ranked[0]
    assert criterion(result, "G1").points == 8.25
    assert result.score == 60.3


# --- Revue n° 3 : une seule borne de VE publiée -----------------------------------------------


def test_only_minimum_published_lists_the_missing_maximum_with_a_warning():
    # VE 60 >= minimum 50 -> 35 points, calcul sur la borne connue ; total Alpha toujours 100.
    result = score_one({"ev_min_eur_m": 50, "ev_max_eur_m": None})
    c = criterion(result, "G2")
    assert (c.status, c.points) == ("full", 35)
    assert result.score == 100
    assert result.missing_data == ["ev_max_eur_m"]
    assert any("maximum EV not published" in w for w in result.warnings)
    assert "maximum not published" in c.explanation
    assert "to not published" not in c.explanation


@pytest.mark.parametrize(
    ("ev_min", "ev_max", "status", "points", "missing"),
    [
        (None, 100, "full", 35, "ev_min_eur_m"),  # 60 <= 100
        (None, 48, "partial", 17.5, "ev_min_eur_m"),  # 1,25 x 48 = 60 -> proche
        (None, 47, "none", 0, "ev_min_eur_m"),  # 1,25 x 47 = 58,75 < 60
        (81, None, "none", 0, "ev_max_eur_m"),  # 0,75 x 81 = 60,75 > 60
    ],
)
def test_one_published_bound_levels(ev_min, ev_max, status, points, missing):
    result = score_one({"ev_min_eur_m": ev_min, "ev_max_eur_m": ev_max})
    c = criterion(result, "G2")
    assert (c.status, c.points) == (status, points)
    assert result.missing_data == [missing]
    assert "only one bound published" in c.explanation


def test_one_missing_bound_counts_in_the_tie_break():
    # Deux fonds à 100 : « aa-incomplete » n'a pas publié son maximum de VE. Malgré l'ordre
    # alphabétique, le fonds complet passe devant (règle 2 : moins de données manquantes).
    complete = Fund.model_validate({**FUNDS[0], "strategy_id": "zz-complete"})
    incomplete = Fund.model_validate(
        {**FUNDS[0], "strategy_id": "aa-incomplete", "ev_max_eur_m": None}
    )
    result = score_operation(operation(), [incomplete, complete])
    assert [r.score for r in result.ranked] == [100, 100]
    assert [r.strategy_id for r in result.ranked] == ["zz-complete", "aa-incomplete"]


def test_near_explanation_says_at_most():
    c = criterion(score_one({"ev_min_eur_m": 80, "ev_max_eur_m": 200}), "G2")
    assert c.status == "partial"
    assert "within 25% of a bound" in c.explanation


# --- Revue n° 4 : contrôles de la configuration, chacun avec son message ----------------------


def _disable_g4(r):
    graded(r, "G4")["enabled"] = False
    graded(r, "G3")["weight"] = 30  # garde un total de 100
    r["tie_break_criterion"] = "G4"


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda r: graded(r, "G2").update(id="G1"), "en double"),  # seul défaut : poids = 100
        (lambda r: graded(r, "G1").update(weight=0), "nombre positif"),
        (lambda r: graded(r, "G1").update(weight=None), "nombre positif"),
        (lambda r: r["eliminatory"][0].update(weight=5), "n'a pas de poids"),
        (lambda r: r["eliminatory"][0].update(params={"seuil": 1}), "n'a pas de paramètres"),
        (lambda r: graded(r, "G1").update(rule="regle_inexistante"), "règle graduelle"),
        (_disable_g4, "n'est pas un critère graduel actif"),
        (
            lambda r: graded(r, "G4")["params"].update(partial_max_age=3),
            r"partial_max_age .* doit être ≥",
        ),
        (lambda r: graded(r, "G2")["params"].update(near_ratio=-0.1), "hors de"),
        (lambda r: graded(r, "G2")["params"].pop("near_ratio"), "manquant"),
        (lambda r: graded(r, "G2")["params"].update(typo=1), "inconnus"),
        (lambda r: r.update(tie_break_criterion="G9"), "tie_break_criterion"),
        (lambda r: r.update(missing_data_ratio=2), "mal formée"),
        (lambda r: r.update(active_criteria_min=16), "supérieur à active_criteria_max"),
    ],
)
def test_each_config_rule_is_checked_with_its_own_message(edit, message):
    with pytest.raises(ConfigError, match=message):
        load_config(changed(edit))


def test_hand_built_config_is_rechecked_by_score_operation():
    # Une configuration construite sans load_config et avec une règle inconnue : ConfigError
    # clair (et non une erreur Python incompréhensible).
    raw = changed(lambda r: r["eliminatory"][0].update(rule="inconnue"))
    config = ScoringConfig.model_validate(raw)
    with pytest.raises(ConfigError, match="non programmée"):
        score_operation(operation(), [fund("syn-alpha")], config)


# --- Revue n° 5 : donnée manquante sur chaque critère éliminatoire ----------------------------


@pytest.mark.parametrize(
    ("criterion_id", "field"),
    [
        ("E1", "deal_types"),
        ("E2", "ticket_min_eur_m"),
        ("E3", "ticket_max_eur_m"),
        ("E4", "stake"),
    ],
)
def test_missing_eliminatory_data_keeps_the_fund_and_warns(criterion_id, field):
    result = score_one({field: None})
    c = criterion(result, criterion_id)
    assert result.excluded is False
    assert (c.status, c.status_label) == ("missing", "Missing data")
    assert result.missing_data == [field]
    assert any("to check before contact" in w for w in result.warnings)
    assert result.score == 100  # les critères graduels ne changent pas


# --- Revue n° 6 : année de fonds plausible ----------------------------------------------------


@pytest.mark.parametrize("year", [3000, 20201, 1979])
def test_implausible_fund_year_is_refused(year):
    with pytest.raises(ValidationError):
        Fund.model_validate({**FUNDS[0], "last_fund_year": year})


@pytest.mark.parametrize("year", [1980, 2100])
def test_fund_year_bounds_are_accepted(year):
    assert Fund.model_validate({**FUNDS[0], "last_fund_year": year}).last_fund_year == year


# --- Revue 2, test n° 4 : année de fonds postérieure à la date d'analyse ----------------------


def test_fund_year_after_analysis_date_keeps_points_but_warns():
    # Opération A analysée le 2026-11-20, dernier fonds daté de 2027 : âge négatif -> traité
    # comme récent (10 points, comportement inchangé), mais une alerte signale la donnée suspecte.
    result = score_one({"last_fund_year": 2027})
    assert criterion(result, "G4").points == 10
    assert result.score == 100
    assert any(
        w.startswith("Investment period:") and "after the analysis date" in w
        for w in result.warnings
    )
    assert result.missing_data == []


def test_normal_fund_year_has_no_warning():
    assert score_one({"last_fund_year": 2023}).warnings == []
