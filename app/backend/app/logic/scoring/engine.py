"""Moteur de score : compatibilité (0 à 100) entre une opération et chaque fonds, et classement.

Calcul 100 % déterministe (aucune IA, aucun hasard, aucune date du jour). Fonctions pures : ce
module ne lit aucun fichier et n'appelle aucun réseau (app/docs/architecture.md, partie « Logic »).

Étapes pour chaque fonds :
1. critères éliminatoires : un seul non rempli => fonds exclu, score 0, raisons listées ;
   une donnée manquante n'exclut pas (critère « non vérifiable », alerte « à vérifier avant
   contact ») ;
2. critères graduels : points = poids x part obtenue ; donnée manquante => `missing_data_ratio` des
   points, statut « Donnée manquante » ;
3. score = somme des points graduels (arrondi à 0,1), puis classement (voir `_ranking_key`).
Règles, poids et seuils : config.py. Documentation : app/docs/scoring.md.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import ValidationError

from .config import GENERALIST_SECTOR, NON_PE_DEAL_TYPE, SCORING_CONFIG
from .models import (
    STATUS_LABELS,
    CriterionConfig,
    CriterionResult,
    Fund,
    FundResult,
    Operation,
    ScoringConfig,
    ScoringResult,
)


class ConfigError(ValueError):
    """La configuration du score n'est pas cohérente (le message dit quelle règle est cassée)."""


@dataclass(frozen=True)
class _Outcome:
    """Résultat brut d'une règle, avant mise en forme."""

    status: str
    explanation: str = ""
    ratio: float | None = None  # critères graduels : part des points (0 à 1)
    missing_field: str | None = None  # renseigné quand status == "missing"
    # Champ non publié alors que le critère a pu être calculé avec les autres (ex. une seule borne
    # de VE) : listé dans missing_data.
    incomplete_field: str | None = None
    # Alerte à afficher au banquier (borne absente, année de fonds suspecte...).
    warning: str | None = None


def _missing(field: str) -> _Outcome:
    return _Outcome("missing", missing_field=field)


# Marge infime pour comparer des nombres décimaux : un ordinateur calcule 0,75 x 80,4 =
# 60,300000000000004 et 2,24 / 22,4 = 0,10000000000000002. Sans marge, une valeur exactement
# sur un seuil (bornes incluses) tomberait du mauvais côté. Un milliardième de M€ ne change
# aucun cas réel.
_EPS = 1e-9


def _at_most(value: float, limit: float) -> bool:
    """value <= limit, bornes incluses, sans erreur d'arrondi informatique."""
    return value <= limit + _EPS


def _at_least(value: float, limit: float) -> bool:
    """value >= limit, bornes incluses, sans erreur d'arrondi informatique."""
    return value >= limit - _EPS


def _round(value: Decimal, places: str) -> float:
    """Arrondi au plus proche, la moitié vers le haut (82,25 -> 82,3), comme à la main."""
    return float(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def _fmt(value: float) -> str:
    """15.0 -> "15", 7.5 -> "7,5" (format français, sans zéros inutiles)."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _pct(share: float) -> str:
    return f"{_fmt(share * 100)} %"


_STAKE_FUND = {
    "majority": "majoritaires",
    "minority": "minoritaires",
    "both": "majoritaires ou minoritaires",
}
_STAKE_OPERATION = {"majority": "majoritaire", "minority": "minoritaire"}

# --- Règles éliminatoires : (opération, fonds, paramètres) -> pass / fail / missing -----------


def _rule_deal_type(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    if not fund.deal_types:
        return _missing("deal_types")
    if op.deal_type in fund.deal_types:
        return _Outcome("pass", f"Le fonds accepte les opérations {op.deal_type}.")
    accepted = ", ".join(
        "aucun type de private equity (venture, dette, actifs réels...)"
        if t == NON_PE_DEAL_TYPE
        else t
        for t in fund.deal_types
    )
    return _Outcome(
        "fail", f"Le fonds n'accepte pas les opérations {op.deal_type} (accepte : {accepted})."
    )


def _rule_ticket_min(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    if fund.ticket_min_eur_m is None:
        return _missing("ticket_min_eur_m")
    ticket, minimum = op.equity_ticket_eur_m, fund.ticket_min_eur_m
    if ticket >= minimum:
        return _Outcome(
            "pass", f"Ticket de {_fmt(ticket)} M€ ≥ minimum du fonds ({_fmt(minimum)} M€)."
        )
    return _Outcome(
        "fail", f"Ticket de {_fmt(ticket)} M€ inférieur au minimum du fonds ({_fmt(minimum)} M€)."
    )


def _rule_ticket_max(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    if fund.ticket_max_eur_m is None:
        return _missing("ticket_max_eur_m")
    ticket, maximum = op.equity_ticket_eur_m, fund.ticket_max_eur_m
    if ticket <= maximum:
        return _Outcome(
            "pass", f"Ticket de {_fmt(ticket)} M€ ≤ maximum du fonds ({_fmt(maximum)} M€)."
        )
    return _Outcome(
        "fail", f"Ticket de {_fmt(ticket)} M€ supérieur au maximum du fonds ({_fmt(maximum)} M€)."
    )


def _rule_stake(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    if fund.stake is None:
        return _missing("stake")
    wanted = _STAKE_OPERATION[op.stake_sought]
    if fund.stake in ("both", op.stake_sought):
        return _Outcome(
            "pass",
            f"Le fonds prend des participations {_STAKE_FUND[fund.stake]} ; "
            f"l'opération est {wanted}.",
        )
    return _Outcome(
        "fail",
        f"Le fonds ne prend que des participations {_STAKE_FUND[fund.stake]} ; "
        f"l'opération est {wanted}.",
    )


# --- Règles graduelles : (opération, fonds, paramètres) -> full / partial / none / missing -----


def _rule_sector(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    if not fund.sectors:
        return _missing("sectors")
    if op.sector in fund.sectors:
        return _Outcome("full", f"Secteur {op.sector} ciblé par le fonds.", 1.0)
    if GENERALIST_SECTOR in fund.sectors:
        return _Outcome(
            "partial",
            f"Fonds généraliste : accepte {op.sector} sans en faire une spécialité.",
            params["generalist_ratio"],
        )
    targets = ", ".join(fund.sectors)
    return _Outcome("none", f"Secteur {op.sector} non ciblé (le fonds cible : {targets}).", 0.0)


def _rule_enterprise_value(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    low, high = fund.ev_min_eur_m, fund.ev_max_eur_m
    if low is None and high is None:
        return _missing("ev_min_eur_m, ev_max_eur_m")
    ev = op.enterprise_value_eur_m
    tolerance = params["near_tolerance"]
    # Une seule borne publiée : le calcul se fait sur la borne connue, et la borne absente est
    # listée dans missing_data avec une alerte (décision d'Arthur, 2026-11-20).
    incomplete_field = incomplete_warning = None
    if low is not None and high is not None:
        bounds = f"fourchette du fonds : {_fmt(low)} à {_fmt(high)} M€"
    elif low is not None:
        bounds = (
            f"VE minimum du fonds : {_fmt(low)} M€ ; une seule borne publiée, maximum non publié"
        )
        incomplete_field = "ev_max_eur_m"
        incomplete_warning = "VE maximum non publiée, calcul sur le minimum ; à vérifier."
    else:
        bounds = (
            f"VE maximum du fonds : {_fmt(high)} M€ ; une seule borne publiée, minimum non publié"
        )
        incomplete_field = "ev_min_eur_m"
        incomplete_warning = "VE minimum non publiée, calcul sur le maximum ; à vérifier."

    def outcome(status: str, text: str, ratio: float) -> _Outcome:
        return _Outcome(
            status,
            text,
            ratio,
            incomplete_field=incomplete_field,
            warning=incomplete_warning,
        )

    below = low is not None and not _at_least(ev, low)
    above = high is not None and not _at_most(ev, high)
    if not below and not above:
        return outcome("full", f"VE de {_fmt(ev)} M€ dans la cible ({bounds}).", 1.0)
    near_below = below and _at_least(ev, low * (1 - tolerance))
    near_above = above and _at_most(ev, high * (1 + tolerance))
    if near_below or near_above:
        return outcome(
            "partial",
            f"VE de {_fmt(ev)} M€ hors cible ({bounds}), mais à {_pct(tolerance)} au plus "
            "d'une borne.",
            params["near_ratio"],
        )
    return outcome("none", f"VE de {_fmt(ev)} M€ loin de la cible ({bounds}).", 0.0)


def _rule_fund_size(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    size = fund.last_fund_size_eur_m
    if size is None:
        return _missing("last_fund_size_eur_m")
    share = op.equity_ticket_eur_m / size
    base = f"Ticket = {_pct(share)} du dernier fonds ({_fmt(size)} M€)"
    if _at_most(share, params["full_max_share"]):
        return _Outcome("full", f"{base}, ≤ {_pct(params['full_max_share'])}.", 1.0)
    if _at_most(share, params["partial_max_share"]):
        return _Outcome(
            "partial",
            f"{base}, entre {_pct(params['full_max_share'])} et "
            f"{_pct(params['partial_max_share'])}.",
            params["partial_ratio"],
        )
    return _Outcome("none", f"{base}, > {_pct(params['partial_max_share'])}.", 0.0)


def _rule_investment_period(op: Operation, fund: Fund, params: Mapping[str, float]) -> _Outcome:
    year = fund.last_fund_year
    if year is None:
        return _missing("last_fund_year")
    age = op.analysis_date.year - year
    if age < 0:
        return _Outcome(
            "full",
            f"Dernier fonds daté de {year}, après la date d'analyse : traité comme fonds récent.",
            1.0,
            # Probable faute de frappe (2062 pour 2026) ou date d'analyse ancienne : on garde les
            # points mais on prévient le banquier.
            warning=(
                f"année du dernier fonds ({year}) postérieure à la date d'analyse "
                f"({op.analysis_date.isoformat()}) ; à vérifier."
            ),
        )
    base = f"Dernier fonds levé en {year}, il y a {age} an{'s' if age > 1 else ''}"
    full_max, partial_max = int(params["full_max_age"]), int(params["partial_max_age"])
    if age <= full_max:
        return _Outcome(
            "full", f"{base} (≤ {full_max} ans) : encore en période d'investissement.", 1.0
        )
    if age <= partial_max:
        return _Outcome(
            "partial",
            f"{base} : fin probable de période d'investissement.",
            params["partial_ratio"],
        )
    return _Outcome(
        "none",
        f"{base} (> {partial_max} ans) : période d'investissement probablement finie.",
        0.0,
    )


_Rule = Callable[[Operation, Fund, Mapping[str, float]], _Outcome]

ELIMINATORY_RULES: dict[str, _Rule] = {
    "deal_type": _rule_deal_type,
    "ticket_min": _rule_ticket_min,
    "ticket_max": _rule_ticket_max,
    "stake": _rule_stake,
}
GRADED_RULES: dict[str, _Rule] = {
    "sector": _rule_sector,
    "enterprise_value": _rule_enterprise_value,
    "fund_size": _rule_fund_size,
    "investment_period": _rule_investment_period,
}

# Paramètres obligatoires de chaque règle graduelle : nom -> (minimum, maximum) autorisés.
_PARAM_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "sector": {"generalist_ratio": (0, 1)},
    "enterprise_value": {"near_tolerance": (0, 1), "near_ratio": (0, 1)},
    "fund_size": {"full_max_share": (0, 1), "partial_max_share": (0, 1), "partial_ratio": (0, 1)},
    "investment_period": {
        "full_max_age": (0, 100),
        "partial_max_age": (0, 100),
        "partial_ratio": (0, 1),
    },
}
# Seuils dont le « partiel » ne peut pas être plus strict que le « complet ».
_ORDERED_PARAMS = {
    "fund_size": ("full_max_share", "partial_max_share"),
    "investment_period": ("full_max_age", "partial_max_age"),
}

# --- Configuration --------------------------------------------------------------------------------


def load_config(raw: Mapping[str, Any] | None = None) -> ScoringConfig:
    """Lit et vérifie une configuration (par défaut : SCORING_CONFIG de config.py).

    Lève ConfigError si une règle de cohérence est cassée.
    """
    raw = SCORING_CONFIG if raw is None else raw
    try:
        config = ScoringConfig.model_validate(raw)
    except ValidationError as error:
        raise ConfigError(f"Configuration du score mal formée : {error}") from error

    if config.active_criteria_min > config.active_criteria_max:
        raise ConfigError(
            f"active_criteria_min ({config.active_criteria_min}) supérieur à "
            f"active_criteria_max ({config.active_criteria_max})"
        )

    all_criteria = [*config.eliminatory, *config.graded]
    ids = [c.id for c in all_criteria]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ConfigError(f"Identifiants de critères en double : {duplicates}")

    for criterion in config.eliminatory:
        if criterion.enabled and criterion.rule not in ELIMINATORY_RULES:
            raise ConfigError(
                f"{criterion.id} : règle éliminatoire {criterion.rule!r} non programmée "
                f"(règles disponibles : {sorted(ELIMINATORY_RULES)})"
            )
        if criterion.weight is not None:
            raise ConfigError(f"{criterion.id} : un critère éliminatoire n'a pas de poids")
        if criterion.params:
            raise ConfigError(
                f"{criterion.id} : un critère éliminatoire n'a pas de paramètres "
                f"(paramètres inconnus {sorted(criterion.params)})"
            )

    active_graded = [c for c in config.graded if c.enabled]
    for criterion in active_graded:
        _check_graded(criterion)

    total = sum(c.weight or 0 for c in active_graded)
    if abs(total - 100) > 1e-9:
        raise ConfigError(
            f"Les poids des critères graduels actifs font {_fmt(total)}, ils doivent faire 100"
        )

    active = sum(c.enabled for c in all_criteria)
    if not config.active_criteria_min <= active <= config.active_criteria_max:
        raise ConfigError(
            f"{active} critères actifs : il en faut entre {config.active_criteria_min} "
            f"et {config.active_criteria_max}"
        )

    if config.tie_break_criterion is not None and config.tie_break_criterion not in {
        c.id for c in active_graded
    }:
        raise ConfigError(
            f"tie_break_criterion {config.tie_break_criterion!r} n'est pas un critère graduel actif"
        )
    return config


def _check_graded(criterion: CriterionConfig) -> None:
    if criterion.rule not in GRADED_RULES:
        raise ConfigError(
            f"{criterion.id} : règle graduelle {criterion.rule!r} non programmée "
            f"(règles disponibles : {sorted(GRADED_RULES)})"
        )
    if criterion.weight is None or criterion.weight <= 0:
        raise ConfigError(f"{criterion.id} : le poids doit être un nombre positif")
    ranges = _PARAM_RANGES[criterion.rule]
    for name, (low, high) in ranges.items():
        if name not in criterion.params:
            raise ConfigError(f"{criterion.id} : paramètre {name!r} manquant")
        if not low <= criterion.params[name] <= high:
            raise ConfigError(
                f"{criterion.id} : {name} = {criterion.params[name]} hors de [{low}, {high}]"
            )
    unknown = sorted(set(criterion.params) - set(ranges))
    if unknown:
        raise ConfigError(f"{criterion.id} : paramètres inconnus {unknown}")
    if criterion.rule in _ORDERED_PARAMS:
        strict, loose = _ORDERED_PARAMS[criterion.rule]
        if criterion.params[loose] < criterion.params[strict]:
            raise ConfigError(
                f"{criterion.id} : {loose} ({criterion.params[loose]}) doit être ≥ "
                f"{strict} ({criterion.params[strict]})"
            )


# La configuration par défaut est vérifiée dès le chargement du module : si config.py est
# incohérent, le moteur refuse de se charger.
DEFAULT_CONFIG = load_config()

# --- Calcul ---------------------------------------------------------------------------------------


def _share_text(ratio: float) -> str:
    return "la moitié des points" if ratio == 0.5 else f"{_pct(ratio)} des points"


def _score_fund(op: Operation, fund: Fund, config: ScoringConfig) -> FundResult:
    criteria: list[CriterionResult] = []
    missing: list[str] = []
    warnings: list[str] = []
    reasons: list[str] = []

    for criterion in (c for c in config.eliminatory if c.enabled):
        outcome = ELIMINATORY_RULES[criterion.rule](op, fund, criterion.params)
        explanation = outcome.explanation
        if outcome.status == "missing":
            missing.append(outcome.missing_field or "")
            explanation = (
                f"Donnée manquante ({outcome.missing_field}) : critère non vérifiable, "
                "fonds conservé ; à vérifier avant contact."
            )
            warnings.append(f"{criterion.label} : donnée manquante, à vérifier avant contact.")
        elif outcome.status == "fail":
            reasons.append(f"{criterion.label} : {explanation}")
        criteria.append(
            CriterionResult(
                id=criterion.id,
                label=criterion.label,
                kind="eliminatory",
                status=outcome.status,
                status_label=STATUS_LABELS[outcome.status],
                points=None,
                max_points=None,
                explanation=explanation,
            )
        )

    excluded = bool(reasons)
    score = 0.0
    if not excluded:
        total = Decimal(0)
        for criterion in (c for c in config.graded if c.enabled):
            weight = float(criterion.weight or 0)
            outcome = GRADED_RULES[criterion.rule](op, fund, criterion.params)
            explanation = outcome.explanation
            ratio = outcome.ratio
            if outcome.status == "missing":
                missing.append(outcome.missing_field or "")
                ratio = config.missing_data_ratio
                explanation = (
                    f"Donnée manquante ({outcome.missing_field}) : "
                    f"{_share_text(ratio)} (règle neutre)."
                )
            if outcome.incomplete_field:
                missing.append(outcome.incomplete_field)
            if outcome.warning:
                warnings.append(f"{criterion.label} : {outcome.warning}")
            # Calcul en décimal (pas en binaire) pour que 33 x 0,25 fasse exactement 8,25.
            exact = Decimal(str(weight)) * Decimal(str(ratio or 0))
            points = _round(exact, "0.01")
            total += Decimal(str(points))
            criteria.append(
                CriterionResult(
                    id=criterion.id,
                    label=criterion.label,
                    kind="graded",
                    status=outcome.status,
                    status_label=STATUS_LABELS[outcome.status],
                    points=points,
                    max_points=weight,
                    explanation=explanation,
                )
            )
        score = _round(total, "0.1")

    return FundResult(
        rank=None,
        strategy_id=fund.strategy_id,
        strategy_name=fund.strategy_name,
        management_company=fund.management_company,
        excluded=excluded,
        score=score,
        exclusion_reasons=reasons,
        criteria=criteria,
        missing_data=missing,
        warnings=warnings,
    )


def _points_of(result: FundResult, criterion_id: str | None) -> float:
    for criterion in result.criteria:
        if criterion.id == criterion_id:
            return criterion.points or 0.0
    return 0.0


def _ranking_key(result: FundResult, config: ScoringConfig) -> tuple[float, int, float, str]:
    """Ordre du classement, règle de départage incluse :
    1. score le plus haut ; 2. le moins de données manquantes ; 3. le plus de points sur le critère
    `tie_break_criterion` (secteur) ; 4. strategy_id par ordre alphabétique (toujours le même
    ordre).
    """
    return (
        -result.score,
        len(result.missing_data),
        -_points_of(result, config.tie_break_criterion),
        result.strategy_id,
    )


def score_operation(
    operation: Operation, funds: Iterable[Fund], config: ScoringConfig | None = None
) -> ScoringResult:
    """Score et classe chaque fonds pour une opération.

    `config` : par défaut celle de config.py. Une autre configuration est revérifiée par
    `load_config` (ConfigError si elle est incohérente), même si elle a été construite à la main.
    Lève ValueError si deux fonds ont le même strategy_id.
    """
    config = DEFAULT_CONFIG if config is None else load_config(config.model_dump())
    funds = list(funds)
    ids = [fund.strategy_id for fund in funds]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"strategy_id en double dans la liste des fonds : {duplicates}")

    results = [_score_fund(operation, fund, config) for fund in funds]
    kept = sorted((r for r in results if not r.excluded), key=lambda r: _ranking_key(r, config))
    ranked = [r.model_copy(update={"rank": i}) for i, r in enumerate(kept, start=1)]
    excluded = sorted((r for r in results if r.excluded), key=lambda r: r.strategy_id)
    return ScoringResult(
        operation_id=operation.operation_id,
        config_version=config.version,
        ranked=ranked,
        excluded=excluded,
    )
