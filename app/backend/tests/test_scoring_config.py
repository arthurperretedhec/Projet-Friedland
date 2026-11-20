"""Tests de la configuration du moteur de score (config.py) : règles de cohérence et paramétrage."""

from __future__ import annotations

import copy

import pytest

from app.logic.scoring import ConfigError, load_config, score_operation
from app.logic.scoring.config import SCORING_CONFIG
from tests.fixtures.synthetic_scoring_data import fund, operation


def changed(edit) -> dict:
    raw = copy.deepcopy(SCORING_CONFIG)
    edit(raw)
    return raw


def graded(raw, criterion_id):
    return next(c for c in raw["graded"] if c["id"] == criterion_id)


def test_default_config_is_valid_and_weights_are_the_agreed_ones():
    config = load_config()
    weights = {c.id: c.weight for c in config.graded if c.enabled}
    assert weights == {"G1": 35, "G2": 35, "G3": 20, "G4": 10}
    assert sum(weights.values()) == 100
    assert config.missing_data_ratio == 0.5


def test_weights_not_summing_to_100_are_refused():
    raw = changed(lambda r: graded(r, "G1").update(weight=30))
    with pytest.raises(ConfigError, match="doivent faire 100"):
        load_config(raw)


def test_too_few_active_criteria_are_refused():
    def disable(r):
        for c in r["eliminatory"]:
            c["enabled"] = False  # il reste 4 critères graduels actifs

    with pytest.raises(ConfigError, match="entre 5 et 15"):
        load_config(changed(disable))


def test_too_many_active_criteria_are_refused():
    raw = changed(lambda r: r.update(active_criteria_max=7))  # 8 critères actifs
    with pytest.raises(ConfigError, match="entre 5 et 7"):
        load_config(raw)


def test_enabling_the_unprogrammed_fund_type_criterion_is_refused():
    raw = changed(lambda r: r["eliminatory"][4].update(enabled=True))
    with pytest.raises(ConfigError, match="non programmée"):
        load_config(raw)


def test_partial_threshold_stricter_than_full_is_refused():
    raw = changed(lambda r: graded(r, "G3")["params"].update(partial_max_share=0.05))
    with pytest.raises(ConfigError, match="partial_max_share"):
        load_config(raw)


@pytest.mark.parametrize(
    "edit",
    [
        lambda r: graded(r, "G1")["params"].update(generalist_ratio=1.5),  # ratio > 1
        lambda r: graded(r, "G2")["params"].pop("near_ratio"),  # paramètre manquant
        lambda r: graded(r, "G2")["params"].update(typo=1),  # paramètre inconnu
        lambda r: r.update(tie_break_criterion="G9"),  # critère de départage inconnu
        lambda r: r["graded"].append({**graded(r, "G1")}),  # identifiant en double
        lambda r: r.update(missing_data_ratio=2),  # ratio hors [0, 1]
    ],
)
def test_inconsistent_config_is_refused(edit):
    with pytest.raises(ConfigError):
        load_config(changed(edit))


def test_changing_weights_in_the_config_changes_the_score_without_touching_the_logic():
    # Fonds Bravo, opération A, avec secteur 50 et VE 20 (au lieu de 35 / 35) :
    # 50 x 0,5 + 20 x 1 + 20 x 0,5 + 10 x 0,5 = 25 + 20 + 10 + 5 = 60
    def reweight(r):
        graded(r, "G1")["weight"] = 50
        graded(r, "G2")["weight"] = 20
        r["version"] = "test-poids"

    config = load_config(changed(reweight))
    result = score_operation(operation(), [fund("syn-bravo")], config)
    assert result.ranked[0].score == 60
    assert result.config_version == "test-poids"


def test_missing_data_ratio_is_configurable():
    # Fonds Delta (3 données manquantes sur G2, G3 et E2), opération A, ratio 0 au lieu de 0,5 :
    # G1 35 + G2 0 + G3 0 + G4 (6 ans) 5 = 40
    config = load_config(changed(lambda r: r.update(missing_data_ratio=0)))
    result = score_operation(operation(), [fund("syn-delta")], config)
    assert result.ranked[0].score == 40
