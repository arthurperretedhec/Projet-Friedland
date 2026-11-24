"""Read and validate the shipped investor reference data at application startup."""

import csv
from collections import defaultdict
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

Row = Mapping[str, str | Decimal | None]
Index = Mapping[str, Row]
Groups = Mapping[str, tuple[Row, ...]]

STRATEGY_RANGES = (
    ("equity_ticket_min_eur_m", "equity_ticket_max_eur_m"),
    ("target_ev_min_eur_m", "target_ev_max_eur_m"),
)


@dataclass(frozen=True)
class InvestorData:
    funds: Index
    strategies: Index
    buckets: Index
    sectors: Index
    strategy_buckets: Groups
    strategy_sectors: Groups
    sector_summary: Index
    financial_criteria: Groups
    investment_amounts: Groups
    portfolio: Groups
    fund_portfolio: Groups
    deals: Index
    sources: Index
    research_leads: Index


def tokens(value: str | None) -> tuple[str, ...]:
    return tuple(part.strip() for part in (value or "").split(";") if part.strip())


def _amount(value: str, context: str) -> Decimal | None:
    if not value.strip():
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{context}: invalid EUR m amount {value!r}") from error
    if not amount.is_finite() or amount <= 0:
        raise ValueError(
            f"{context}: expected a positive EUR m amount or an empty cell"
        )
    return amount


def _read(
    directory: Path,
    table: str,
    required: tuple[str, ...],
    *,
    amounts: tuple[str, ...] = (),
    ranges: tuple[tuple[str, str], ...] = (),
) -> list[Row]:
    rows = []
    amount_fields = (*amounts, *(field for pair in ranges for field in pair))
    with (directory / f"{table}.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        fields = reader.fieldnames or []
        missing = set((*required, *amount_fields)) - set(fields)
        if missing or len(fields) != len(set(fields)):
            raise ValueError(f"{table}.csv: invalid headers; missing {sorted(missing)}")
        for raw in reader:
            context = f"{table}.csv:{reader.line_num}"
            if None in raw or None in raw.values():
                raise ValueError(f"{context}: cell count differs from header")
            row = {key: value if value.strip() else None for key, value in raw.items()}
            for key in amount_fields:
                row[key] = _amount(raw[key], f"{context} {key}")
            for low, high in ranges:
                if (
                    row[low] is not None
                    and row[high] is not None
                    and row[low] > row[high]
                ):
                    raise ValueError(f"{context}: {low} exceeds {high}")
            rows.append(MappingProxyType(row))
    return rows


def _key(row: Row, field: str, table: str) -> str:
    value = row[field]
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{table}.csv: invalid {field} {value!r}")
    return value


def _index(rows: list[Row], field: str, table: str) -> Index:
    indexed = {}
    for row in rows:
        key = _key(row, field, table)
        if key in indexed:
            raise ValueError(f"{table}.csv: duplicate {field} {key!r}")
        indexed[key] = row
    return MappingProxyType(indexed)


def _require_ref(
    value: str | Decimal | None, index: Collection[str], table: str, field: str
) -> None:
    if value not in index:
        raise ValueError(f"{table}.csv: unknown {field} {value!r}")


def _group(
    rows: list[Row], parents: Index, table: str, key: str = "strategy_id"
) -> Groups:
    groups = defaultdict(list)
    for row in rows:
        parent_id = _key(row, key, table)
        _require_ref(parent_id, parents, table, key)
        groups[parent_id].append(row)
    return MappingProxyType({key: tuple(items) for key, items in groups.items()})


def _check_memberships(data: InvestorData) -> None:
    for strategy_id, strategy in data.strategies.items():
        _require_ref(strategy["fund_id"], data.funds, "strategies", "fund_id")
        buckets = {}
        for row in data.strategy_buckets.get(strategy_id, ()):
            code, membership = row["bucket_id"], row["membership"]
            _require_ref(code, data.buckets, "strategy_buckets", "bucket_id")
            if code in buckets or membership not in {"PRIMARY", "SECONDARY"}:
                raise ValueError(
                    f"strategy_buckets.csv: invalid membership for {strategy_id}"
                )
            buckets[code] = membership
        primary = [code for code, kind in buckets.items() if kind == "PRIMARY"]
        secondary = {code for code, kind in buckets.items() if kind == "SECONDARY"}
        if primary != [strategy["primary_bucket"]] or secondary != set(
            tokens(strategy["secondary_buckets"])
        ):
            raise ValueError(
                f"strategy_buckets.csv: inconsistent buckets for {strategy_id}"
            )

        seen = set()
        included = set()
        for row in data.strategy_sectors.get(strategy_id, ()):
            code, polarity = row["sector_code"], row["polarity"]
            if code is not None:
                _require_ref(code, data.sectors, "strategy_sectors", "sector_code")
            key = (code, row["raw_tag"], row["subsector"], polarity)
            if (
                key in seen
                or row["fund_id"] != strategy["fund_id"]
                or polarity not in {"INCLUDED", "EXCLUDED_EXPLICIT"}
            ):
                raise ValueError(
                    f"strategy_sectors.csv: invalid relationship for {strategy_id}"
                )
            seen.add(key)
            if code is not None and polarity == "INCLUDED":
                included.add(code)
        if included != set(tokens(strategy["normalized_sector_codes"])):
            raise ValueError(
                f"strategy_sectors.csv: inconsistent sector codes for {strategy_id}"
            )

        summary = data.sector_summary.get(strategy_id)
        if summary is not None and summary["fund_id"] != strategy["fund_id"]:
            raise ValueError(
                f"strategy_sector_summary.csv: wrong fund for {strategy_id}"
            )


def _check_transaction_parent(
    row: Row, strategies: Index, funds: Index, table: str
) -> None:
    strategy_id, fund_id = row["strategy_id"], row["fund_id"]
    if (strategy_id is None) == (fund_id is None):
        raise ValueError(
            f"{table}.csv: expected exactly one of strategy_id and fund_id"
        )
    if strategy_id is not None:
        _require_ref(strategy_id, strategies, table, "strategy_id")
    else:
        _require_ref(fund_id, funds, table, "fund_id")


def load_investors(directory: Path = DATA_DIR) -> InvestorData:
    """Load the public CSV snapshot, retaining original IDs and source fields."""

    def read_index(table: str, key: str, *fields: str, **options) -> Index:
        return _index(_read(directory, table, (key, *fields), **options), key, table)

    strategies = read_index(
        "strategies",
        "strategy_id",
        "fund_id",
        "management_company",
        "strategy_name",
        "primary_bucket",
        "secondary_buckets",
        "normalized_sector_codes",
        "stake",
        "deal_types",
        amounts=("target_ebitda_min_eur_m",),
        ranges=STRATEGY_RANGES,
    )

    def read_group(table: str, *fields: str, **options) -> Groups:
        rows = _read(directory, table, ("strategy_id", *fields), **options)
        return _group(rows, strategies, table)

    funds = read_index("funds", "fund_id", "management_company")
    portfolio = _read(
        directory,
        "portfolio",
        ("strategy_id", "fund_id", "company_name", "reported_vehicle"),
    )
    for row in portfolio:
        _check_transaction_parent(row, strategies, funds, "portfolio")
    all_sources = read_index(
        "source_log",
        "source_id",
        "entity_type",
        "entity_id",
        "source_url",
        "source_paraphrase",
        "evidence_status",
    )
    source_groups = {"SOURCE_REFERENCE": {}, "RESEARCH_LEAD": {}}
    for source_id, row in all_sources.items():
        status = row["evidence_status"]
        if status not in source_groups:
            raise ValueError(f"source_log.csv: invalid evidence_status for {source_id}")
        source_groups[status][source_id] = row

    data = InvestorData(
        funds=funds,
        strategies=strategies,
        buckets=read_index("buckets", "bucket_id", "bucket_name"),
        sectors=read_index("sectors", "sector_code", "label"),
        strategy_buckets=read_group("strategy_buckets", "bucket_id", "membership"),
        strategy_sectors=read_group(
            "strategy_sectors",
            "fund_id",
            "sector_code",
            "raw_tag",
            "subsector",
            "polarity",
        ),
        sector_summary=read_index(
            "strategy_sector_summary", "strategy_id", "fund_id", "sector_scope"
        ),
        financial_criteria=read_group(
            "financial_criteria",
            "metric",
            ranges=(("min_eur_m", "max_eur_m"),),
        ),
        investment_amounts=read_group(
            "investment_amounts",
            "amount_type",
            ranges=(("reported_min_eur_m", "reported_max_eur_m"),),
        ),
        portfolio=_group(
            [row for row in portfolio if row["strategy_id"] is not None],
            strategies,
            "portfolio",
        ),
        fund_portfolio=_group(
            [row for row in portfolio if row["fund_id"] is not None],
            funds,
            "portfolio",
            "fund_id",
        ),
        deals=read_index(
            "deals",
            "deal_id",
            "strategy_id",
            "fund_id",
            "reported_vehicle",
            amounts=("ev_eur_m",),
        ),
        sources=MappingProxyType(source_groups["SOURCE_REFERENCE"]),
        research_leads=MappingProxyType(source_groups["RESEARCH_LEAD"]),
    )
    _check_memberships(data)
    for strategy_id in data.sector_summary:
        _require_ref(strategy_id, strategies, "strategy_sector_summary", "strategy_id")
    for deal in data.deals.values():
        _check_transaction_parent(deal, strategies, funds, "deals")
    source_parents = {
        "strategy": strategies,
        "portfolio": set(data.portfolio)
        | {
            f"{strategy_id}|{row['company_name']}"
            for strategy_id, rows in data.portfolio.items()
            for row in rows
        },
        "fund_portfolio": {
            f"{fund_id}|{row['company_name']}"
            for fund_id, rows in data.fund_portfolio.items()
            for row in rows
        },
        "deal": data.deals,
        "management_company": {
            _key(row, "management_company", "funds") for row in data.funds.values()
        },
    }
    for source in all_sources.values():
        parents = source_parents.get(source["entity_type"])
        if parents is None:
            raise ValueError(
                f"source_log.csv: unknown entity_type {source['entity_type']!r}"
            )
        _require_ref(source["entity_id"], parents, "source_log", "entity_id")
    return data
