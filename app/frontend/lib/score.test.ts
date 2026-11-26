import { describe, expect, it } from "vitest";

import {
  DEFAULT_VIEW,
  EMPTY_FORM,
  exclusionSummary,
  filterCompanies,
  formatRange,
  humanize,
  interpretScore,
  parseAmount,
  type RankedCompany,
  ticketShareOfEv,
  tierOf,
  UNREACHABLE,
  validateForm,
} from "./score";

const filled = {
  ...EMPTY_FORM,
  companyName: "  PME industrielle  ",
  sector: "industrials",
  enterpriseValue: "40",
  equityTicket: "15",
};

function company(rank: number, score: number, name: string, level = "moyen"): RankedCompany {
  return {
    rank,
    fund_id: `fund-${rank}`,
    management_company: name,
    best_strategy_id: `str-${rank}`,
    best_strategy_name: `${name} Fund I`,
    score,
    criteria: [],
    confidence: { criteria_known: 7, criteria_total: 9, level, missing_data: [] },
    missing_data: [],
    warnings: [],
    other_strategies: [],
    profile: {
      website: null,
      source_url: null,
      last_fund_name: null,
      equity_ticket_min_eur_m: 5,
      equity_ticket_max_eur_m: 20,
      target_ev_min_eur_m: null,
      target_ev_max_eur_m: null,
      latest_investments_france: [],
      holdings_collected: false,
    },
  };
}

describe("parseAmount", () => {
  it("reads French and plain decimals and thousand spaces", () => {
    expect(parseAmount("12,5")).toBe(12.5);
    expect(parseAmount("12.5")).toBe(12.5);
    expect(parseAmount("1 200")).toBe(1200);
  });
  it("refuses text, negative numbers and Infinity", () => {
    expect(parseAmount("abc")).toBeNull();
    expect(parseAmount("-5")).toBeNull();
    expect(parseAmount("Infinity")).toBeNull();
    expect(parseAmount("")).toBeNull();
  });
});

describe("validateForm", () => {
  it("builds the API request with trimmed name and numbers", () => {
    const result = validateForm(filled);
    expect(result).toEqual({
      ok: true,
      request: {
        deal_type: "primary_lbo",
        sector: "industrials",
        equity_ticket_eur_m: 15,
        stake_sought: "majority",
        enterprise_value_eur_m: 40,
        company_name: "PME industrielle",
      },
    });
  });
  it("lists every missing field on an empty form", () => {
    const result = validateForm(EMPTY_FORM);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(Object.keys(result.errors).sort()).toEqual(["companyName", "enterpriseValue", "equityTicket", "sector"]);
    }
  });
  it("refuses zero, a typo in euros and a ticket above the EV", () => {
    const zero = validateForm({ ...filled, equityTicket: "0" });
    expect(zero.ok || zero.errors.equityTicket).toBe("Doit être supérieur à 0");
    const euros = validateForm({ ...filled, enterpriseValue: "40000000" });
    expect(euros.ok || euros.errors.enterpriseValue).toBe("Montant trop élevé (en M€, pas en €)");
    const above = validateForm({ ...filled, equityTicket: "50" });
    expect(above.ok || above.errors.equityTicket).toBe("Le ticket equity ne peut pas dépasser la VE");
  });
});

describe("ticketShareOfEv", () => {
  it("is 15 / 40 = 37,5 %, rounded to 38", () => {
    expect(ticketShareOfEv(filled)).toBe(38);
    expect(ticketShareOfEv(EMPTY_FORM)).toBeNull();
  });
});

describe("tierOf (proposed thresholds 80 / 60)", () => {
  it("puts the boundaries in the higher tier", () => {
    expect([100, 80, 79.9, 60, 59.9, 0].map(tierOf)).toEqual([1, 1, 2, 2, 3, 3]);
  });
});

describe("formatRange", () => {
  it("covers both, one or no bound", () => {
    expect(formatRange(5, 20)).toBe("5–20 M€");
    expect(formatRange(null, 60)).toBe("jusqu'à 60 M€");
    expect(formatRange(2.5, null)).toBe("dès 2,5 M€");
    expect(formatRange(null, null)).toBe("non publié");
  });
});

describe("humanize", () => {
  it("replaces engine codes by French labels, whole words only", () => {
    expect(humanize("Le fonds accepte les opérations primary_lbo.")).toBe("Le fonds accepte les opérations LBO primaire.");
    expect(humanize("Donnée manquante (ticket_min_eur_m)")).toBe("Donnée manquante (ticket minimum)");
    expect(humanize("Secteur industrials ciblé")).toBe("Secteur industrie ciblé");
    expect(humanize("buyout_industrials_x")).toBe("buyout_industrials_x");
  });
});

describe("filterCompanies", () => {
  const list = [company(1, 95, "Alpha"), company(2, 70, "Bêta", "faible"), company(3, 40, "Gamma")];
  it("keeps the engine order and ranks", () => {
    expect(filterCompanies(list, DEFAULT_VIEW).shown.map((c) => c.rank)).toEqual([1, 2, 3]);
  });
  it("filters by tier, confidence, accent-insensitive search and limit", () => {
    expect(filterCompanies(list, { ...DEFAULT_VIEW, minTier: 2 }).shown.map((c) => c.rank)).toEqual([1, 2]);
    expect(filterCompanies(list, { ...DEFAULT_VIEW, hideLowConfidence: true }).shown.map((c) => c.rank)).toEqual([1, 3]);
    expect(filterCompanies(list, { ...DEFAULT_VIEW, search: "beta" }).shown.map((c) => c.rank)).toEqual([2]);
    expect(filterCompanies(list, { ...DEFAULT_VIEW, limit: 1 })).toMatchObject({ matching: 3 });
  });
});

describe("exclusionSummary", () => {
  it("counts the first reason by criterion, most frequent first", () => {
    const excluded = [
      { strategy_id: "a", fund_id: "f", strategy_name: null, management_company: null, exclusion_reasons: ["Position recherchée : x"] },
      { strategy_id: "b", fund_id: "f", strategy_name: null, management_company: null, exclusion_reasons: ["Type d'opération : y"] },
      { strategy_id: "c", fund_id: "f", strategy_name: null, management_company: null, exclusion_reasons: ["Type d'opération : z"] },
    ];
    expect(exclusionSummary(excluded)).toEqual([
      { criterion: "Type d'opération", count: 2 },
      { criterion: "Position recherchée", count: 1 },
    ]);
  });
});

describe("interpretScore", () => {
  it("returns the data on 200", () => {
    const body = { companies: [], counts: {} };
    expect(interpretScore(200, body)).toEqual({ kind: "ok", data: body });
  });
  it("passes the French validation details through on 422", () => {
    const body = { error: { code: "invalid_request", message: "Requête invalide", details: [{ field: "sector", message: "secteur inconnu" }] } };
    expect(interpretScore(422, body)).toEqual({ kind: "error", message: "Requête invalide", details: [{ field: "sector", message: "secteur inconnu" }] });
  });
  it("says the server is down on a network error or a 500 from the proxy", () => {
    expect(interpretScore(null, null)).toMatchObject({ message: UNREACHABLE });
    expect(interpretScore(500, null)).toMatchObject({ message: UNREACHABLE });
  });
});
