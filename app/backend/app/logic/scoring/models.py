"""Formats du moteur de score : fiche fonds et fiche opération (entrées), résultat (sortie).

Une valeur non publiée reste `None` (jamais 0) : le moteur la traite par la règle « donnée
manquante ».
Les noms des champs de la fiche fonds sont ceux de strategies.csv (app/docs/architecture.md).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import (
    BUCKETS,
    BUYER_ROLES,
    DEAL_TYPES,
    FUND_DEAL_TYPES,
    GENERALIST_SECTOR,
    SECTORS,
    SOURCE_QUALITY_ORDER,
    STAKES,
)

# --- Entrées -------------------------------------------------------------------------------------


def _split_multi(value: object) -> object:
    """Accepte une cellule CSV « a; b » ou une liste ; une cellule ou liste vide devient None."""
    if value is None:
        return None
    if isinstance(value, str):
        value = [part.strip() for part in value.split(";")]
    if isinstance(value, (list, tuple)):
        items = [item.strip() if isinstance(item, str) else item for item in value]
        items = [item for item in items if item != ""]
        return items or None
    return value


def _check_allowed(values: list[str] | None, allowed: tuple[str, ...], field: str) -> None:
    for item in values or []:
        if item not in allowed:
            raise ValueError(f"{field} : valeur inconnue {item!r} (valeurs autorisées : {allowed})")


class Fund(BaseModel):
    """Une stratégie de la base (une ligne de strategies.csv, colonnes utiles au score)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    strategy_id: str = Field(min_length=1)
    management_company: str | None = None
    strategy_name: str | None = None
    ticket_min_eur_m: float | None = Field(default=None, gt=0)
    ticket_max_eur_m: float | None = Field(default=None, gt=0)
    ev_min_eur_m: float | None = Field(default=None, gt=0)
    ev_max_eur_m: float | None = Field(default=None, gt=0)
    stake: str | None = None
    deal_types: list[str] | None = None
    sectors: list[str] | None = None
    last_fund_size_eur_m: float | None = Field(default=None, gt=0)
    # Année plausible : une faute de frappe (3000, 20201) est refusée au lieu de compter comme
    # « fonds récent ».
    last_fund_year: int | None = Field(default=None, ge=1980, le=2100)
    # Critères v2 (colonnes de strategies.csv ; None = non publié).
    primary_bucket: str | None = None
    secondary_buckets: list[str] | None = None
    buyer_role: str | None = None
    geography_tags: list[str] | None = None
    transaction_modifiers: list[str] | None = None
    # Qualité de la source de la fiche : sert au départage des ex æquo (critères v2).
    classification_basis: str | None = None

    @field_validator(
        "deal_types",
        "sectors",
        "secondary_buckets",
        "geography_tags",
        "transaction_modifiers",
        mode="before",
    )
    @classmethod
    def _multi_values(cls, value: object) -> object:
        return _split_multi(value)

    @field_validator(
        "management_company",
        "strategy_name",
        "stake",
        "ticket_min_eur_m",
        "ticket_max_eur_m",
        "ev_min_eur_m",
        "ev_max_eur_m",
        "last_fund_size_eur_m",
        "last_fund_year",
        "primary_bucket",
        "buyer_role",
        "classification_basis",
        mode="before",
    )
    @classmethod
    def _empty_cell_is_missing(cls, value: object) -> object:
        # Une cellule CSV vide arrive comme "" : c'est une donnée non publiée, pas un zéro.
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @model_validator(mode="after")
    def _check_values(self) -> Fund:
        # Un fonds peut avoir « non_pe » (activité hors PE publiée) ; une opération, jamais.
        _check_allowed(self.deal_types, FUND_DEAL_TYPES, "deal_types")
        _check_allowed(self.sectors, SECTORS, "sectors")
        if self.stake is not None:
            _check_allowed([self.stake], STAKES, "stake")
        if self.primary_bucket is not None:
            _check_allowed([self.primary_bucket], BUCKETS, "primary_bucket")
        _check_allowed(self.secondary_buckets, BUCKETS, "secondary_buckets")
        if self.buyer_role is not None:
            _check_allowed([self.buyer_role], BUYER_ROLES, "buyer_role")
        if self.classification_basis is not None:
            _check_allowed(
                [self.classification_basis], SOURCE_QUALITY_ORDER, "classification_basis"
            )
        for low, high, name in (
            (self.ticket_min_eur_m, self.ticket_max_eur_m, "ticket"),
            (self.ev_min_eur_m, self.ev_max_eur_m, "ev"),
        ):
            if low is not None and high is not None and low > high:
                raise ValueError(f"{name} : minimum ({low}) supérieur au maximum ({high})")
        return self


class Operation(BaseModel):
    """L'opération décrite par le banquier. Tous les champs sont obligatoires."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    deal_type: str
    # Montant de fonds propres recherché auprès du fonds, en millions d'euros.
    equity_ticket_eur_m: float = Field(gt=0)
    # Valeur d'entreprise estimée, en millions d'euros.
    enterprise_value_eur_m: float = Field(gt=0)
    sector: str
    stake_sought: Literal["majority", "minority"]
    # Date de l'analyse : sert à calculer l'âge du dernier fonds (jamais la date du jour, pour que
    # le même calcul donne toujours le même résultat).
    analysis_date: date

    @model_validator(mode="after")
    def _check_values(self) -> Operation:
        _check_allowed([self.deal_type], DEAL_TYPES, "deal_type")
        allowed_sectors = tuple(s for s in SECTORS if s != GENERALIST_SECTOR)
        _check_allowed([self.sector], allowed_sectors, "sector")
        return self


# --- Configuration (structure ; les règles de cohérence sont vérifiées par engine.load_config) ---


class CriterionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    rule: str
    label: str
    enabled: bool = True
    weight: float | None = None
    params: dict[str, float] = Field(default_factory=dict)
    description: str = ""


class ScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    missing_data_ratio: float = Field(ge=0, le=1)
    active_criteria_min: int = Field(ge=0)
    active_criteria_max: int = Field(ge=0)
    tie_break_criterion: str | None = None
    # Critères v2 : départager les ex æquo par la qualité de la source (classification_basis)
    # au lieu des points d'un critère.
    tie_break_source_quality: bool = False
    # Indice de confiance : nombre de données manquantes (critères éliminatoires ET notés actifs)
    # autorisé pour le niveau « élevé », puis « moyen » ; au-delà : « faible ».
    confidence_high_max_missing: int = Field(default=1, ge=0)
    confidence_medium_max_missing: int = Field(default=3, ge=0)
    eliminatory: list[CriterionConfig]
    graded: list[CriterionConfig]


# --- Sortie ---------------------------------------------------------------------------------------

CriterionKind = Literal["eliminatory", "graded"]
# pass / fail : critère éliminatoire rempli / non rempli.
# full / partial / none : critère graduel complet / partiel / non rempli.
# missing : donnée manquante (éliminatoire ou graduel).
CriterionStatus = Literal["pass", "fail", "full", "partial", "none", "missing"]

STATUS_LABELS: dict[str, str] = {
    "pass": "Critère rempli",
    "fail": "Critère éliminatoire non rempli",
    "full": "Correspondance complète",
    "partial": "Correspondance partielle",
    "none": "Pas de correspondance",
    "missing": "Donnée manquante",
}


class CriterionResult(BaseModel):
    id: str
    label: str
    kind: CriterionKind
    status: CriterionStatus
    status_label: str
    # Critère graduel : points obtenus et maximum. Critère éliminatoire : None (pas de points).
    points: float | None
    max_points: float | None
    explanation: str


ConfidenceLevel = Literal["élevé", "moyen", "faible"]


class Confidence(BaseModel):
    # Critères actifs (éliminatoires et notés) dont la donnée est publiée, sur le total des
    # critères actifs (9 en v2 : E1 à E4, puis G1, G5 à G8).
    criteria_known: int
    criteria_total: int
    level: ConfidenceLevel
    # Champs non publiés : la MÊME liste que FundResult.missing_data, recopiée volontairement pour
    # que l'indice de confiance se lise seul dans l'interface.
    missing_data: list[str]


class FundResult(BaseModel):
    rank: int | None
    strategy_id: str
    strategy_name: str | None
    management_company: str | None
    excluded: bool
    score: float
    exclusion_reasons: list[str]
    criteria: list[CriterionResult]
    # Champs de la fiche fonds non publiés et utilisés par un critère.
    missing_data: list[str]
    warnings: list[str]
    # Indice de confiance (fonds classés seulement ; None pour un fonds exclu).
    confidence: Confidence | None = None


class ScoringResult(BaseModel):
    operation_id: str
    config_version: str
    # Fonds qui passent les critères éliminatoires, du meilleur au moins bon.
    ranked: list[FundResult]
    # Fonds exclus (score 0, sans rang), par strategy_id.
    excluded: list[FundResult]
