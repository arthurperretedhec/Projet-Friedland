"""Tickets par société de gestion : data/fund_tickets.csv.

Tiré du classeur complété par Alexandre le 2026-11-27 (onglet « Tickets »). Une ligne par
ticket ; une société peut en avoir plusieurs (une par stratégie, `label` = nom de la
stratégie, vide = ticket général). `source_type` : `base` (base Friedland, lien), `internal`
(intelligence interne : les dossiers clients cités dans le classeur ne sont PAS recopiés),
`web` (recherche web, lien). `to_confirm` = source tierce à confirmer.
Affichage seul : le moteur de score garde les tickets de strategies.csv.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from app.data.investors import DATA_DIR

FILE_NAME = "fund_tickets.csv"
SOURCE_TYPES = ("base", "internal", "web")


@dataclass(frozen=True)
class FundTicket:
    label: str  # nom de la stratégie ; "" = ticket général de la société
    min_eur_m: float | None
    max_eur_m: float | None
    source_type: str
    source_url: str
    to_confirm: bool


def _amount(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def load_fund_tickets(directory: Path = DATA_DIR) -> Mapping[str, tuple[FundTicket, ...]]:
    """Tickets par fund_id, dans l'ordre du classeur. Fichier absent = aucun ticket."""
    path = directory / FILE_NAME
    if not path.exists():
        return MappingProxyType({})
    by_fund: dict[str, list[FundTicket]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            low, high = _amount(row["min_eur_m"]), _amount(row["max_eur_m"])
            if low is None and high is None:
                raise ValueError(f"{FILE_NAME}, line {line}: ticket without a bound")
            if low is not None and high is not None and low > high:
                raise ValueError(f"{FILE_NAME}, line {line}: minimum above maximum")
            if row["source_type"] not in SOURCE_TYPES:
                raise ValueError(f"{FILE_NAME}, line {line}: unknown source_type")
            by_fund.setdefault(row["fund_id"], []).append(
                FundTicket(
                    label=row["label"].strip(),
                    min_eur_m=low,
                    max_eur_m=high,
                    source_type=row["source_type"],
                    source_url=row["source_url"].strip(),
                    to_confirm=row["to_confirm"] == "yes",
                )
            )
    return MappingProxyType({k: tuple(v) for k, v in by_fund.items()})


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def choose_ticket(tickets: tuple[FundTicket, ...], strategy_name: str | None) -> FundTicket | None:
    """Le ticket de la stratégie affichée si le classeur la nomme, sinon le premier (le général)."""
    if not tickets:
        return None
    if strategy_name:
        wanted = _norm(strategy_name)
        for ticket in tickets:
            if ticket.label and _norm(ticket.label) == wanted:
                return ticket
        for ticket in tickets:
            if ticket.label and (_norm(ticket.label) in wanted or wanted in _norm(ticket.label)):
                return ticket
    return tickets[0]
