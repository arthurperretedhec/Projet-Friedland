"""Garde-fous ajoutés après le deuxième tour de relecture (2026-11-25).

Les listes ci-dessous sont recopiées À LA MAIN depuis app/docs/scoring.md (règles validées par
Arthur le 2026-11-25), pas importées du code : déplacer un libellé d'une famille à l'autre dans
reference.py fait échouer un test. Aucun test existant n'a été modifié.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from app.data.investors import load_investors
from app.logic.reference import (
    DATA_KNOWN_POLARITIES,
    DATA_KNOWN_SECTOR_SCOPES,
    DATA_NON_PE_DEAL_TAGS,
    DATA_VAGUE_DEAL_TAGS,
)
from app.logic.scoring import real_data
from app.logic.scoring.real_data import sectors_for, unclassified_sector_metadata


@pytest.fixture(scope="module")
def data():
    return load_investors()


def test_non_pe_tags_are_the_18_validated_ones():
    assert DATA_NON_PE_DEAL_TAGS == {
        "venture",
        "venture_growth",
        "mezzanine",
        "senior_debt",
        "quasi_equity",
        "hybrid_capital",
        "convertible_financing",
        "acquisition_financing",
        "sponsorless_financing",
        "infrastructure",
        "infrastructure_equity",
        "infrastructure_growth",
        "growth_infrastructure",
        "project_finance",
        "greenfield",
        "brownfield",
        "hospitality_real_estate",
        "company_creation",
    }


def test_vague_tags_are_the_20_validated_ones():
    assert DATA_VAGUE_DEAL_TAGS == {
        "impact",
        "long_term",
        "evergreen",
        "long_term_direct_investment",
        "technology",
        "transformation",
        "special_situations",
        "turnaround",
        "restructuring",
        "co_investment",
        "minority_co_investment",
        "flexible_capital",
        "international_expansion",
        "acquisition",
        "change_of_ownership",
        "family_succession",
        "shareholder_reorganisation",
        "public_to_private",
        "market_consolidation",
        "sponsorless",
    }


def test_known_sector_scopes_and_polarities_are_the_validated_ones(data):
    assert DATA_KNOWN_SECTOR_SCOPES == {
        "GENERALIST_OPEN",
        "GENERALIST_PLUS_PREFERENCES",
        "SECTOR_THEMES",
        "UNKNOWN_SECTOR",
    }
    assert DATA_KNOWN_POLARITIES == {"INCLUDED", "EXCLUDED_EXPLICIT"}
    assert unclassified_sector_metadata(data) == {"sector_scope": set(), "polarity": set()}


@pytest.mark.parametrize(
    "strategy_id",
    ["str-ext-alpha-private-equity", "str-ext-elais-buyout", "str-ext-phillimore-niche"],
)
def test_unknown_sector_scope_gives_missing_sector(data, strategy_id):
    # Les 3 stratégies dont sector_scope vaut UNKNOWN_SECTOR : aucun code secteur -> manquant.
    assert data.sector_summary[strategy_id]["sector_scope"] == "UNKNOWN_SECTOR"
    assert sectors_for(data, strategy_id) is None


def test_every_generalist_open_fund_without_exclusion_says_which_one_is_wrong(data):
    open_ids = [
        sid
        for sid, s in data.sector_summary.items()
        if s["sector_scope"] == "GENERALIST_OPEN"
        and not any(
            r["polarity"] == "EXCLUDED_EXPLICIT" for r in data.strategy_sectors.get(sid, ())
        )
    ]
    wrong = [sid for sid in open_ids if sectors_for(data, sid) != ["generalist"]]
    assert wrong == []


def test_real_data_module_reads_no_file():
    # La couche logique ne lit aucun fichier : la base lui est passée déjà chargée. On analyse le
    # code lui-même (imports, noms utilisés), pas les commentaires, qui peuvent citer le chargeur.
    tree = ast.parse(inspect.getsource(real_data))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom | ast.Import)
        for alias in node.names
    }
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    forbidden = {"load_investors", "open", "read_csv", "read_text", "Path"}
    assert not forbidden & (imported | used)
