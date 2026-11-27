#!/usr/bin/env python3
"""Demonstrate data access without modifying the application's matching algorithm."""

import argparse
import csv
from pathlib import Path


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def compatibility(v, lo, hi):
    if not lo and not hi:
        return "UNKNOWN"
    if lo and v < float(lo):
        return "OUTSIDE_DISCLOSED_RANGE"
    if hi and v > float(hi):
        return "OUTSIDE_DISCLOSED_RANGE"
    return "WITHIN_DISCLOSED_RANGE"


def geographic_status(geo, target):
    tokens = [t.strip().lower().replace(" ", "_") for t in geo.split(";") if t.strip()]
    if not tokens:
        return "UNKNOWN"
    if target.lower() == "france":
        france_tokens = ("france", "europe", "eurozone", "global", "international", "oecd")
        french_regions = (
            "grand_ouest",
            "grand_est",
            "nouvelle_aquitaine",
            "occitanie",
            "normandie",
            "bretagne",
            "pays_de_la_loire",
            "hauts_de_france",
            "ile_de_france",
            "sud_est",
            "provence",
        )
        if any(any(z in t for z in france_tokens + french_regions) for t in tokens):
            return "MATCH"
        return "OUTSIDE_STATED_FOCUS"
    return "UNKNOWN"


def main():
    p = argparse.ArgumentParser(description="Quick data-only smoke test, NOT a buyer ranking")
    p.add_argument("--data", type=Path, default=Path("app/backend/data"))
    p.add_argument("--sector", default="HEALTHCARE")
    p.add_argument(
        "--geography", default="France", help="Target country, demonstration supports France"
    )
    p.add_argument("--ev-eur-m", type=float, default=150)
    p.add_argument("--max-rows", type=int, default=12)
    a = p.parse_args()
    s = rows(a.data / "strategies.csv")
    valid_sectors = {x["sector_code"] for x in rows(a.data / "sectors.csv")}
    if a.sector not in valid_sectors:
        raise SystemExit("Unknown sector code: " + a.sector)
    potential = []
    for st in s:
        if st["screening_lane"] in (
            "FINANCING_PARTNER",
            "VENTURE_FINANCING",
            "NOT_STANDALONE",
            "HISTORICAL_REVIEW",
        ):
            continue
        sectors = st["normalized_sector_codes"].split(";")
        # Empty standardized tags mean UNKNOWN/generalist, not an explicit exclusion.
        sector_fit = (
            "MATCH"
            if a.sector in sectors
            else "UNKNOWN"
            if not st["normalized_sector_codes"]
            else "NOT_TAGGED"
        )
        geography_fit = geographic_status(st["geography_tags"], a.geography)
        if geography_fit == "OUTSIDE_STATED_FOCUS":
            continue
        if sector_fit == "NOT_TAGGED":
            continue
        size_fit = compatibility(a.ev_eur_m, st["target_ev_min_eur_m"], st["target_ev_max_eur_m"])
        if size_fit == "OUTSIDE_DISCLOSED_RANGE":
            continue
        potential.append(
            (
                st["management_company"],
                st["strategy_name"],
                st["strategy_id"],
                sector_fit,
                geography_fit,
                size_fit,
            )
        )
    # No unverified weighted score is provided. Include unknowns as review candidates.
    potential.sort(key=lambda x: (x[3] != "MATCH", x[5] != "WITHIN_DISCLOSED_RANGE", x[0]))
    print(
        f"Candidate strategies: {len(potential)} | sector={a.sector}, "
        f"geography={a.geography}, EV={a.ev_eur_m} EUR m"
    )
    print(
        "CAUTION: illustrative eligibility only; "
        "not an investment recommendation or finalized score"
    )
    for x in potential[: a.max_rows]:
        print(" | ".join(x))


if __name__ == "__main__":
    main()
