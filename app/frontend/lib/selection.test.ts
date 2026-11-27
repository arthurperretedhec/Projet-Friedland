import { describe, expect, it } from "vitest";

import type { ExcludedCompany, Investment, RankedCompany, ScoreResponse } from "./score";
import {
  initialSelection,
  investmentLine,
  investmentText,
  selectedRows,
  selectionCsv,
  setIncluded,
  fundTicket,
  ticketSourceLabel,
  ticketForSlide,
  toggle,
} from "./selection";

const profile = (extra: Partial<RankedCompany["profile"]> = {}): RankedCompany["profile"] => ({
  website: null,
  source_url: null,
  last_fund_name: null,
  equity_ticket_min_eur_m: null,
  equity_ticket_max_eur_m: null,
  target_ev_min_eur_m: null,
  target_ev_max_eur_m: null,
  latest_investments_france: [],
  sector_investments: [],
  holdings_collected: false,
  ...extra,
});

function ranked(rank: number, score: number, fundId: string): RankedCompany {
  return {
    rank,
    fund_id: fundId,
    management_company: `Fund ${fundId}`,
    best_strategy_id: `str-${fundId}`,
    best_strategy_name: `Strategy ${fundId}`,
    score,
    criteria: [],
    confidence: { criteria_known: 9, criteria_total: 9, level: "high", missing_data: [] },
    missing_data: [],
    warnings: [],
    other_strategies: [],
    profile: profile(),
  };
}

const excluded: ExcludedCompany = {
  fund_id: "fund-x",
  management_company: "Excluded Partners",
  strategies: [
    { strategy_id: "str-x", fund_id: "fund-x", strategy_name: "X Fund", management_company: "Excluded Partners", exclusion_reasons: ["Maximum ticket: too small"] },
  ],
  profile: profile(),
};

const data = {
  companies: [ranked(1, 90, "a"), ranked(2, 65, "b"), ranked(3, 40, "c")],
  excluded_companies: [excluded],
} as unknown as ScoreResponse;

describe("initialSelection", () => {
  it("checks Tier 1 only; excluded funds start unchecked", () => {
    const s = initialSelection(data);
    expect([s.a.included, s.b.included, s.c.included, s["fund-x"].included]).toEqual([true, false, false, false]);
  });
});

describe("toggle and selectedRows", () => {
  it("unchecks a ranked fund and adds an excluded fund after the ranking", () => {
    let s = initialSelection(data);
    s = toggle(s, "a", "included");
    s = toggle(s, "b", "included");
    s = toggle(s, "fund-x", "included");
    const rows = selectedRows(data, s);
    expect(rows.map((r) => [r.fundId, r.origin])).toEqual([
      ["b", "ranked"],
      ["fund-x", "added"],
    ]);
  });
  it("starring a fund also selects it", () => {
    const s = toggle(initialSelection(data), "c", "starred");
    expect(s.c).toEqual({ included: true, starred: true });
    expect(selectedRows(data, s).find((r) => r.fundId === "c")?.starred).toBe(true);
  });
  it("setIncluded checks or unchecks several funds at once", () => {
    const s = setIncluded(initialSelection(data), ["a", "b", "c"], false);
    expect(selectedRows(data, s)).toEqual([]);
  });
});

describe("ticketForSlide", () => {
  it("uses the slide format", () => {
    expect(ticketForSlide(10, 100)).toBe("€[10-100]m");
    expect(ticketForSlide(2.5, null)).toBe("€2.5m+");
    expect(ticketForSlide(null, 20)).toBe("up to €20m");
    expect(ticketForSlide(null, null)).toBeNull();
  });
});

const inv = (extra: Partial<Investment>): Investment => ({
  company_name: "Tethys",
  entry_year: 2026,
  country: null,
  description_short: null,
  description_short_by_ai: false,
  description: null,
  source_url: "https://x",
  sector: null,
  sector_by_ai: false,
  ...extra,
});

describe("investment lines", () => {
  it("prefers the AI summary and keeps its flag", () => {
    const i = inv({ description_short: "Designer of systems", description_short_by_ai: true, description: "Long text" });
    expect(investmentText(i)).toEqual({ text: "Designer of systems", byAi: true });
    expect(investmentLine(i)).toBe("Tethys (2026) - Designer of systems");
  });
  it("falls back to the published text, cut with an ellipsis", () => {
    const i = inv({ description: "a".repeat(200), entry_year: null });
    const { text, byAi } = investmentText(i, 10);
    expect([text, byAi]).toEqual(["aaaaaaaaaa…", false]);
    expect(investmentLine(inv({ entry_year: null }))).toBe("Tethys");
  });
});

describe("selectionCsv", () => {
  it("exports the selected funds with origin, star and investments", () => {
    const s = toggle(initialSelection(data), "fund-x", "starred");
    const lines = selectionCsv(selectedRows(data, s)).split("\r\n");
    expect(lines[0].startsWith("﻿Fund;Strategy;Origin;Interest expressed")).toBe(true);
    expect(lines[1]).toBe("Fund a;Strategy a;Ranking;;1;90;High;;;;;;;");
    expect(lines[2]).toBe("Excluded Partners;X Fund;Added manually;Yes;;;;;;;;;;");
  });

  it("exports the ticket of the tickets file with its source", () => {
    const ticket = { label: null, min_eur_m: 10, max_eur_m: 50, source_type: "web", source_url: "https://x", to_confirm: true };
    const row = { ...selectedRows(data, initialSelection(data))[0] };
    row.profile = profile({ ticket });
    const line = selectionCsv([row]).split("\r\n")[1];
    expect(line).toContain(";€[10-50]m;Web research (third-party source, to confirm);");
  });
});

describe("fundTicket", () => {
  it("uses the tickets file, never the strategy's own bounds", () => {
    const ticket = { label: "X", min_eur_m: 5, max_eur_m: 20, source_type: "base", source_url: null, to_confirm: false };
    expect(fundTicket(profile({ ticket, equity_ticket_min_eur_m: 1, equity_ticket_max_eur_m: 2 }))).toBe("€[5-20]m");
    expect(fundTicket(profile({ equity_ticket_min_eur_m: 1, equity_ticket_max_eur_m: 2 }))).toBeNull();
  });

  it("labels each source", () => {
    const base = { label: null, min_eur_m: 1, max_eur_m: 2, source_url: null, to_confirm: false };
    expect(ticketSourceLabel({ ...base, source_type: "base" })).toBe("Friedland database");
    expect(ticketSourceLabel({ ...base, source_type: "internal" })).toBe("Internal intelligence");
    expect(ticketSourceLabel({ ...base, source_type: "web" })).toBe("Web research");
    expect(ticketSourceLabel(null)).toBe("");
  });
});
