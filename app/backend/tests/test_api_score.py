"""Tests de la route POST /api/score (vraie base, critères v2 par défaut).

Valeurs attendues : cas SC5 d'acceptance.md, calculé à la main (Abenex Industries 9.0, 90).
"""

from __future__ import annotations

import dataclasses
from datetime import date
from types import MappingProxyType

import pytest
from fastapi.testclient import TestClient

import app.api.score as score_module
from app.api.score import build_scoring_base
from app.main import app

LBO_SMALL = {
    "deal_type": "primary_lbo",
    "sector": "industrials",
    "equity_ticket_eur_m": 15,
    "stake_sought": "majority",
    "enterprise_value_eur_m": 40,
    "company_name": "PME industrielle (exemple)",
    "analysis_date": "2026-11-25",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# --- Appel réussi -----------------------------------------------------------------------------


def test_lbo_small_returns_the_company_ranking_with_abenex_at_90(client):
    response = client.post("/api/score", json=LBO_SMALL)
    assert response.status_code == 200
    body = response.json()
    assert body["config_version"] == "2026-11-25-v2"
    assert body["message"] is None
    assert body["counts"] == {
        "strategies_total": 153,
        "strategies_ranked": 95,
        "strategies_excluded": 58,
        "companies_ranked": 82,
    }
    # Abenex Capital (SC5, calculé à la main) : meilleure stratégie Abenex Industries 9.0,
    # 40 + 25 + 15 + 10 + 0 = 90, aucune donnée manquante, confiance élevée.
    abenex = next(c for c in body["companies"] if c["management_company"] == "Abenex Capital SAS")
    assert abenex["best_strategy_id"] == "str-abenex-industries-90"
    assert abenex["score"] == 90
    assert abenex["missing_data"] == []
    assert abenex["confidence"] == {
        "criteria_known": 9,
        "criteria_total": 9,
        "level": "élevé",
        "missing_data": [],
    }
    graded = {c["id"]: c["points"] for c in abenex["criteria"] if c["kind"] == "graded"}
    assert graded == {"G1": 40, "G5": 25, "G6": 15, "G7": 10, "G8": 0}
    assert all(c["explanation"] for c in abenex["criteria"])
    assert [o["strategy_id"] for o in abenex["other_strategies"]] == ["str-abenex-smallcap-ii"]


def test_ranking_is_ordered_and_excluded_funds_have_a_reason(client):
    body = client.post("/api/score", json=LBO_SMALL).json()
    companies = body["companies"]
    assert [c["rank"] for c in companies] == list(range(1, len(companies) + 1))
    scores = [c["score"] for c in companies]
    assert scores == sorted(scores, reverse=True)
    assert len(body["excluded"]) == 58
    assert all(e["exclusion_reasons"] for e in body["excluded"])
    antin = next(e for e in body["excluded"] if e["strategy_id"] == "str-antin-flagship")
    assert antin["exclusion_reasons"][0].startswith("Type d'opération")


def test_optional_fields_have_defaults(client):
    payload = {k: v for k, v in LBO_SMALL.items() if k not in ("company_name", "analysis_date")}
    body = client.post("/api/score", json=payload).json()
    assert body["company_name"] == "Opération sans nom"
    assert body["analysis_date"] == date.today().isoformat()
    assert body["counts"]["companies_ranked"] == 82  # en v2, la date ne change pas le score


# --- Entrées invalides ------------------------------------------------------------------------


def test_invalid_values_are_refused_with_french_messages(client):
    payload = {
        **LBO_SMALL,
        "deal_type": "seed",
        "sector": "aerospace",
        "equity_ticket_eur_m": 0,
        "stake_sought": "both",
        "unexpected": 1,
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    details = {d["field"]: d["message"] for d in error["details"]}
    assert details["deal_type"].startswith("type d'opération inconnu « seed »")
    assert "primary_lbo" in details["deal_type"]  # les valeurs autorisées sont listées
    assert details["sector"].startswith("secteur inconnu « aerospace »")
    assert "generalist" not in details["sector"]  # pas un secteur d'opération
    assert details["equity_ticket_eur_m"] == "doit être strictement supérieur à 0"
    assert details["stake_sought"].startswith("position inconnue « both »")
    assert details["unexpected"] == "champ inconnu"
    assert error["message"].startswith("Requête invalide : ")


@pytest.mark.parametrize(
    ("change", "field", "message"),
    [
        ({"equity_ticket_eur_m": -5}, "equity_ticket_eur_m", "doit être strictement supérieur à 0"),
        ({"equity_ticket_eur_m": "quinze"}, "equity_ticket_eur_m", "doit être un nombre"),
        ({"analysis_date": "25/11/2026"}, "analysis_date", "date invalide"),
    ],
)
def test_single_invalid_field(client, change, field, message):
    response = client.post("/api/score", json={**LBO_SMALL, **change})
    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert len(details) == 1
    assert details[0]["field"] == field
    assert details[0]["message"].startswith(message)


def test_missing_required_field(client):
    payload = {k: v for k, v in LBO_SMALL.items() if k != "sector"}
    details = client.post("/api/score", json=payload).json()["error"]["details"]
    assert details == [{"field": "sector", "message": "champ obligatoire manquant"}]


def test_body_that_is_not_json(client):
    response = client.post(
        "/api/score", content="pas du json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0] == {
        "field": "corps de la requête",
        "message": "JSON invalide",
    }


# --- Aucun fonds compatible -------------------------------------------------------------------


def test_no_compatible_fund_returns_an_empty_ranking_and_a_message(client):
    # Sur la base complète, aucune opération n'exclut les 153 stratégies (une donnée manquante
    # n'exclut jamais). On utilise donc une sous-partie de la vraie base : les 3 stratégies
    # d'Antin Infrastructure Partners, toutes hors PE (infrastructure_equity), donc exclues
    # d'un LBO.
    full = app.state.scoring_base
    antin = {sid: row for sid, row in full.data.strategies.items() if sid.startswith("str-antin-")}
    assert len(antin) == 3
    subset = dataclasses.replace(full.data, strategies=MappingProxyType(antin))
    app.state.scoring_base = build_scoring_base(subset)
    try:
        response = client.post("/api/score", json=LBO_SMALL)
    finally:
        app.state.scoring_base = full
    assert response.status_code == 200
    body = response.json()
    assert body["companies"] == []
    assert body["message"] == "Aucun fonds de la base n'est compatible avec cette opération."
    assert body["counts"] == {
        "strategies_total": 3,
        "strategies_ranked": 0,
        "strategies_excluded": 3,
        "companies_ranked": 0,
    }
    assert all("Type d'opération" in e["exclusion_reasons"][0] for e in body["excluded"])


# --- Chargement unique ------------------------------------------------------------------------


def test_base_is_translated_once_at_startup_not_per_call(client, monkeypatch):
    base = app.state.scoring_base

    def fail(*args, **kwargs):
        raise AssertionError("la base ne doit pas être retraduite à chaque appel")

    monkeypatch.setattr(score_module, "funds_from_base", fail)
    for _ in range(2):
        assert client.post("/api/score", json=LBO_SMALL).status_code == 200
    assert app.state.scoring_base is base
    assert len(base.funds) == 153


# --- Fiche publiée de la meilleure stratégie (écran de classement, 2026-11-26) ----------------


def test_each_company_carries_the_published_profile_of_its_best_strategy(client):
    # Valeurs lues à la main dans data/strategies.csv, ligne 2 (Abenex Industries 9.0) :
    # ticket 5-20 M€, VE min non publiée, VE max 60 M€, site et source renseignés.
    body = client.post("/api/score", json=LBO_SMALL).json()
    abenex = next(c for c in body["companies"] if c["management_company"] == "Abenex Capital SAS")
    assert abenex["profile"] == {
        "website": "https://www.abenex.com/en",
        "source_url": "https://www.abenex.com/en/publications/abenex-industries-9-fund-first-closing",
        "last_fund_name": "Abenex Industries 9.0",
        "equity_ticket_min_eur_m": 5,
        "equity_ticket_max_eur_m": 20,
        "target_ev_min_eur_m": None,
        "target_ev_max_eur_m": 60,
    }
    assert all("profile" in c for c in body["companies"])


def test_profile_turns_blank_text_into_none():
    from app.api.score import _text

    assert _text("  ") is None
    assert _text(None) is None
    assert _text(" https://x.fr ") == "https://x.fr"
