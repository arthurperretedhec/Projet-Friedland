"""Moteur de score : compatibilité (0 à 100) entre une opération et chaque fonds de la base.

Point d'entrée : `score_operation(operation, funds)`. Documentation : app/docs/scoring.md.
Les critères, poids et seuils sont dans `config.py` (le seul fichier à modifier pour les ajuster).
"""

from .engine import ConfigError, load_config, score_operation
from .models import CriterionResult, Fund, FundResult, Operation, ScoringResult

__all__ = [
    "ConfigError",
    "CriterionResult",
    "Fund",
    "FundResult",
    "Operation",
    "ScoringResult",
    "load_config",
    "score_operation",
]
