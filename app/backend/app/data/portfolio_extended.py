"""Portefeuilles collectés sur les sites des fonds (pilote du 2026-11-26).

Fichier : data/portfolio_extended.csv.

Fichier séparé de portfolio.csv (base de Simon, inchangée). Une ligne par participation actuelle,
avec l'URL de la page source. `description_short` est un RÉSUMÉ PAR L'IA au format des slides
(`description_short_by = "ai_summary"`), jamais un texte publié par le fonds.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from app.data.investors import DATA_DIR

FILE_NAME = "portfolio_extended.csv"
REQUIRED_COLUMNS = (
    "fund_id",
    "company_name",
    "company_description",
    "entry_year",
    "country",
    "status",
    "instrument",
    "source_url",
    "collected_on",
    "description_short",
    "description_short_by",
    "sector",
    "sector_by",
)
ALLOWED_SHORT_BY = ("", "ai_summary")
ALLOWED_SECTOR_BY = ("", "published", "ai_classified")


@dataclass(frozen=True)
class Holding:
    fund_id: str
    company_name: str
    entry_year: int | None
    country: str | None
    instrument: str
    description: str | None  # texte publié par le fonds (peut finir par « … » s'il était tronqué)
    description_short: str | None  # résumé IA au format des slides
    description_short_by_ai: bool
    source_url: str
    order: int  # position dans le fichier = ordre de la page source
    sector: str | None = None  # code de sectors.csv (ex. FOOD_AGRI)
    sector_by_ai: bool = False  # True = classé par l'IA d'après la description, pas publié


def _year(value: str, line: int) -> int | None:
    if not value:
        return None
    if not value.isdigit() or not 1950 <= int(value) <= 2100:
        raise ValueError(f"{FILE_NAME}, ligne {line} : entry_year invalide « {value} »")
    return int(value)


def load_portfolio_extended(
    directory: Path = DATA_DIR,
) -> MappingProxyType[str, tuple[Holding, ...]]:
    """Participations actuelles par fund_id. Fichier absent = aucune donnée (pas d'erreur)."""
    path = directory / FILE_NAME
    if not path.exists():
        return MappingProxyType({})
    by_fund: dict[str, list[Holding]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{FILE_NAME} : colonnes manquantes {', '.join(missing)}")
        for line, row in enumerate(reader, start=2):
            if not row["fund_id"] or not row["company_name"] or not row["source_url"]:
                raise ValueError(
                    f"{FILE_NAME}, ligne {line} : fund_id, company_name et source_url obligatoires"
                )
            if row["description_short_by"] not in ALLOWED_SHORT_BY:
                raise ValueError(f"{FILE_NAME}, ligne {line} : description_short_by inconnu")
            if row["sector_by"] not in ALLOWED_SECTOR_BY or bool(row["sector"]) != bool(
                row["sector_by"]
            ):
                raise ValueError(f"{FILE_NAME}, ligne {line} : sector et sector_by incohérents")
            if row["status"] != "held" and not row["status"].startswith("held"):
                continue  # le pilote ne garde que les participations actuelles
            by_fund.setdefault(row["fund_id"], []).append(
                Holding(
                    fund_id=row["fund_id"],
                    company_name=row["company_name"].strip(),
                    entry_year=_year(row["entry_year"].strip(), line),
                    country=row["country"].strip() or None,
                    instrument=row["instrument"].strip(),
                    description=row["company_description"].strip() or None,
                    description_short=row["description_short"].strip() or None,
                    description_short_by_ai=row["description_short_by"] == "ai_summary",
                    source_url=row["source_url"].strip(),
                    order=line,
                    sector=row["sector"].strip() or None,
                    sector_by_ai=row["sector_by"] == "ai_classified",
                )
            )
    return MappingProxyType({k: tuple(v) for k, v in by_fund.items()})


def latest_in_france(holdings: tuple[Holding, ...], limit: int = 3) -> list[Holding]:
    """Dernières participations en equity pour la colonne « Latest investments in France ».

    Règle : instrument equity (la dette et la mezzanine ne comptent pas) ; pays France, ou pays non
    publié (l'interface l'indique) ; les plus récentes d'abord ; sans année, l'ordre de la page
    source (les sites listent les plus récentes en premier). Un pays étranger publié est exclu.
    """
    candidates = [h for h in holdings if h.instrument == "equity" and h.country in (None, "France")]
    candidates.sort(key=lambda h: (-(h.entry_year or 0), h.order))
    return candidates[:limit]


def latest_in_sector(
    holdings: tuple[Holding, ...], sector_codes: frozenset[str], limit: int = 3
) -> list[Holding]:
    """Colonne « Investments in <secteur> sector » : participations en equity dont le secteur
    (publié ou classé par l'IA) est celui de la cible, tous pays, les plus récentes d'abord."""
    candidates = [h for h in holdings if h.instrument == "equity" and h.sector in sector_codes]
    candidates.sort(key=lambda h: (-(h.entry_year or 0), h.order))
    return candidates[:limit]
