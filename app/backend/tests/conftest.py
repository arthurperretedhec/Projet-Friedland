"""Fixtures partagées des tests.

Depuis le 2026-11-25, la configuration par défaut du moteur est celle des critères v2
(app/logic/scoring/config.py, SCORING_CONFIG). Les tests écrits pour les critères v1 (fonds
fictifs, poids 35 / 35 / 20 / 10) vérifient des règles qui existent toujours dans le code : ils
utilisent la fixture `scoring_v1`, qui remet la configuration v1 par défaut pendant le test. Leurs
valeurs attendues ne changent pas.
"""

from __future__ import annotations

import pytest

from app.logic.scoring import engine, load_config
from app.logic.scoring.config import SCORING_CONFIG_V1


@pytest.fixture
def scoring_v1(monkeypatch):
    monkeypatch.setattr(engine, "DEFAULT_CONFIG", load_config(SCORING_CONFIG_V1))
