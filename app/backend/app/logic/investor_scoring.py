"""Translate strategies for the teammate's scoring interface and group ranked buyers."""

from collections.abc import Iterable
from typing import Protocol, TypeVar

from app.data.investors import InvestorData, tokens

# Map comparable categories only. The imported sector relationships remain authoritative.
LEGACY_SECTORS = {
    "TECH_SOFTWARE": "software_it",
    "HEALTHCARE": "healthcare",
    "BUSINESS_SERVICES": "business_services",
    "INDUSTRIALS": "industrials",
    "CONSUMER": "consumer_retail",
    "FINANCIAL_SERVICES": "financial_services",
    "ENERGY_ENV": "energy_environment",
}
LEGACY_DEAL_TYPES = {
    "primary_lbo": "primary_lbo",
    "secondary_lbo": "secondary_lbo",
    "build_up": "build_up",
    "growth": "growth",
    "growth_capital": "growth",
    "growth_equity": "growth",
    "carve_out": "carve_out",
}
LEGACY_STAKES = {
    "majority": "majority",
    "minority": "minority",
    "controlling_minority": "minority",
    "significant_minority": "minority",
    "lead_minority": "minority",
}


def scoring_input(data: InvestorData, strategy_id: str) -> dict[str, object]:
    """Return keyword arguments accepted by the scoring branch's Fund model."""

    row = data.strategies[strategy_id]
    stakes = {LEGACY_STAKES[tag] for tag in tokens(row["stake"]) if tag in LEGACY_STAKES}
    deal_types = tokens(row["deal_types"])
    return {
        "strategy_id": strategy_id,
        "management_company": row["management_company"],
        "strategy_name": row["strategy_name"],
        "ticket_min_eur_m": row["equity_ticket_min_eur_m"],
        "ticket_max_eur_m": row["equity_ticket_max_eur_m"],
        "ev_min_eur_m": row["target_ev_min_eur_m"],
        "ev_max_eur_m": row["target_ev_max_eur_m"],
        "stake": "both" if len(stakes) == 2 else next(iter(stakes), None),
        # The old engine excludes deal-type mismatches. A partial map could wrongly exclude buyers.
        "deal_types": _project(deal_types, LEGACY_DEAL_TYPES),
        "sectors": _scoring_sectors(data, strategy_id),
        "last_fund_size_eur_m": None,
        "last_fund_year": None,
    }


def _scoring_sectors(data: InvestorData, strategy_id: str) -> list[str] | None:
    # The legacy model has no way to express a sector or subsector exclusion.
    if any(
        row["polarity"] == "EXCLUDED_EXPLICIT" for row in data.strategy_sectors.get(strategy_id, ())
    ):
        return None

    scope = data.sector_summary.get(strategy_id, {}).get("sector_scope")
    if scope == "GENERALIST_OPEN":
        return ["generalist"]

    codes = tokens(data.strategies[strategy_id]["normalized_sector_codes"])
    projected = _project(codes, LEGACY_SECTORS)
    if scope == "GENERALIST_PLUS_PREFERENCES" and projected is not None:
        return [*projected, "generalist"]
    return projected


def _project(values: tuple[str, ...], mapping: dict[str, str]) -> list[str] | None:
    if not values or any(value not in mapping for value in values):
        return None
    return list(dict.fromkeys(mapping[value] for value in values))


class RankedStrategy(Protocol):
    @property
    def strategy_id(self) -> str: ...

    @property
    def excluded(self) -> bool: ...


Result = TypeVar("Result", bound=RankedStrategy)


def buyer_longlist(data: InvestorData, ranked_strategies: Iterable[Result]) -> list[Result]:
    """Keep the first eligible strategy per fund from a best-first ranking."""

    seen = set()
    buyers = []
    for result in ranked_strategies:
        if result.excluded:
            continue
        fund_id = data.strategies[result.strategy_id]["fund_id"]
        if fund_id not in seen:
            buyers.append(result)
            seen.add(fund_id)
    return buyers
