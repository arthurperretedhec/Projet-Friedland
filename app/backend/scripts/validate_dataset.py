#!/usr/bin/env python3
"""Check Friedland fund and optional local transaction data (standard library only)."""

import argparse
import collections
import csv
import math
import sys
from pathlib import Path


def read(folder, name):
    p = folder / name
    with p.open(encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def unique(rows, key):
    ids = [r[key] for r in rows]
    assert all(ids) and len(ids) == len(set(ids)), f"Duplicate or empty {key}"


def numeric(row, key):
    v = row.get(key, "")
    if v == "":
        return
    assert math.isfinite(float(v)) and float(v) >= 0, (key, v)


def limits(row, lo, hi):
    numeric(row, lo)
    numeric(row, hi)
    if row.get(lo, "") != "" and row.get(hi, "") != "":
        assert float(row[lo]) <= float(row[hi]), (lo, hi, row)


def validate(data, local=None):
    f = read(data, "funds.csv")
    s = read(data, "strategies.csv")
    b = read(data, "buckets.csv")
    se = read(data, "sectors.csv")
    mem = read(data, "strategy_buckets.csv")
    tags = read(data, "strategy_sectors.csv")
    p = read(data, "portfolio.csv")
    deals = read(data, "deals.csv")
    finance = read(data, "financial_criteria.csv")
    amounts = read(data, "investment_amounts.csv")
    sources = read(data, "source_log.csv")
    for rows, col in [
        (f, "fund_id"),
        (s, "strategy_id"),
        (b, "bucket_id"),
        (se, "sector_code"),
        (deals, "deal_id"),
        (sources, "source_id"),
    ]:
        unique(rows, col)
    fids = {x["fund_id"] for x in f}
    sids = {x["strategy_id"] for x in s}
    bids = {x["bucket_id"] for x in b}
    scodes = {x["sector_code"] for x in se}
    assert len(f) == 112 and len(s) == 153, "Universe has changed: please review count changes"
    for x in s:
        assert x["fund_id"] in fids and x["primary_bucket"] in bids, x["strategy_id"]
        limits(x, "equity_ticket_min_eur_m", "equity_ticket_max_eur_m")
        limits(x, "target_ev_min_eur_m", "target_ev_max_eur_m")
        numeric(x, "target_ebitda_min_eur_m")
        assert all(z in scodes for z in x["normalized_sector_codes"].split(";") if z), x[
            "strategy_id"
        ]
    for rows in (mem, tags, finance, amounts):
        assert all(r["strategy_id"] in sids for r in rows), "Orphan strategy reference"
    for row in p + deals:
        strategy_id, fund_id = row["strategy_id"], row["fund_id"]
        assert (strategy_id in sids and not fund_id) or (fund_id in fids and not strategy_id), row
    for row in sources:
        assert row["evidence_status"] in ("SOURCE_REFERENCE", "RESEARCH_LEAD"), row["source_id"]
        assert not row["exact_source_quote"], row["source_id"]
        if "www.cfnews.net/" in row["source_url"]:
            assert row["evidence_status"] == "RESEARCH_LEAD" and not row["source_paraphrase"], row[
                "source_id"
            ]
    assert all(x["bucket_id"] in bids for x in mem)
    assert all(x["sector_code"] in scodes or not x["sector_code"] for x in tags)
    for r in finance:
        limits(r, "min_eur_m", "max_eur_m")
    for r in amounts:
        limits(r, "reported_min_eur_m", "reported_max_eur_m")
    print(
        f"CORE PASS: {len(f)} funds; {len(s)} strategies; {len(p)} portfolio; "
        f"{len(deals)} public deals; {len(sources)} sources"
    )
    if local and local.is_dir() and (local / "transactions.csv").exists():
        tx = read(local, "transactions.csv")
        roles = read(local, "transaction_investors.csv")
        activity = read(local, "fund_activity.csv")
        sec_activity = read(local, "fund_sector_activity.csv")
        unique(tx, "transaction_id")
        unique(activity, "fund_id")
        txids = {x["transaction_id"] for x in tx}
        assert set(x["transaction_id"] for x in roles) == txids
        assert len(roles) == len(
            set((x["transaction_id"], x["fund_id"], x["party_role"]) for x in roles)
        )
        assert set(x["fund_id"] for x in activity) == fids
        for x in roles:
            assert (
                x["fund_id"] in fids
                and x["party_role"] in ("BUYER", "SELLER")
                and x["attribution"] in ("EXACT", "BRAND", "GROUP", "RELATED", "REVIEW")
            )
        for t in tx:
            for k in ["deal_value_usd_m", "enterprise_value_usd_m", "equity_value_usd_m"]:
                numeric(t, k)
        counts = collections.Counter(
            x["fund_id"]
            for x in roles
            if x["party_role"] == "BUYER" and x["attribution"] in ("EXACT", "BRAND")
        )
        for a in activity:
            assert int(a["observed_direct_buyer_deals"]) == counts[a["fund_id"]], a["fund_id"]
        for r in sec_activity:
            assert r["sector_code"] in scodes | {"UNCLASSIFIED"}
        print(f"LOCAL PASS: {len(tx)} linked transactions; {len(roles)} investor roles")
    return True


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--data", type=Path, default=Path("app/backend/data"))
    a.add_argument("--local", type=Path, default=Path("app/backend/data/local"))
    args = a.parse_args()
    try:
        validate(args.data, args.local)
    except Exception as e:
        print("FAIL:", e, file=sys.stderr)
        sys.exit(1)
