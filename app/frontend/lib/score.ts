// Logique pure de l'écran de screening (sans React, sans réseau), pour être testée facilement.
// Contrat de l'API : app/docs/scoring.md, « Route d'API POST /api/score ».

// --- Vocabulaire (mêmes codes que app/backend/app/logic/reference.py) -------------------------

export const DEAL_TYPES = [
  { value: "primary_lbo", label: "Primary LBO", hint: "Transfer, MBO / MBI, family succession" },
  { value: "secondary_lbo", label: "Secondary LBO", hint: "A fund exits, another fund buys in" },
  { value: "build_up", label: "Build-up", hint: "Acquisition by a platform already held" },
  { value: "growth", label: "Growth capital", hint: "Funding growth, often a minority stake" },
  { value: "carve_out", label: "Carve-out", hint: "Sale of a subsidiary or a division" },
] as const;

export const SECTORS = [
  { value: "software_it", label: "Software & IT" },
  { value: "healthcare", label: "Healthcare" },
  { value: "business_services", label: "Business services" },
  { value: "industrials", label: "Industrials" },
  { value: "consumer_retail", label: "Consumer & retail" },
  { value: "food_beverage", label: "Food & beverage" },
  { value: "financial_services", label: "Financial services" },
  { value: "education", label: "Education" },
  { value: "energy_environment", label: "Energy & environment" },
  { value: "construction_real_estate", label: "Construction & real estate" },
  { value: "transport_logistics", label: "Transport & logistics" },
  { value: "media_telecom", label: "Media & telecom" },
  { value: "agriculture", label: "Agriculture" },
] as const;

/** Libellé anglais du secteur pour l'en-tête du bandeau (« Investments in Food & beverage sector »). */
export const SECTOR_EN: Record<string, string> = {
  software_it: "Software & IT",
  healthcare: "Healthcare",
  business_services: "Business services",
  industrials: "Industrials",
  consumer_retail: "Consumer & retail",
  food_beverage: "Food & beverage",
  financial_services: "Financial services",
  education: "Education",
  energy_environment: "Energy & environment",
  construction_real_estate: "Construction & real estate",
  transport_logistics: "Transport & logistics",
  media_telecom: "Media & telecom",
  agriculture: "Agriculture",
};

/** Libellé court du secteur pour l'en-tête du bandeau (« Investments in F&B »). */
export const SECTOR_SHORT: Record<string, string> = {
  software_it: "Software & IT",
  healthcare: "Healthcare",
  business_services: "Business services",
  industrials: "Industrials",
  consumer_retail: "Consumer",
  food_beverage: "F&B",
  financial_services: "Financial services",
  education: "Education",
  energy_environment: "Energy",
  construction_real_estate: "Construction",
  transport_logistics: "Transport",
  media_telecom: "Media & telecom",
  agriculture: "Agriculture",
};

export const STAKES = [
  { value: "majority", label: "Majority", hint: "The fund takes control" },
  { value: "minority", label: "Minority", hint: "Management keeps control" },
] as const;

const DATA_FIELD_LABELS: Record<string, string> = {
  ticket_min_eur_m: "minimum ticket",
  ticket_max_eur_m: "maximum ticket",
  equity_ticket_min_eur_m: "minimum ticket",
  equity_ticket_max_eur_m: "maximum ticket",
  ev_min_eur_m: "minimum EV",
  ev_max_eur_m: "maximum EV",
  deal_types: "deal types",
  stake: "stake",
  sectors: "sectors",
};

const CODE_LABELS: Record<string, string> = {
  ...Object.fromEntries(DEAL_TYPES.map((d) => [d.value, d.label])),
  ...Object.fromEntries(SECTORS.map((s) => [s.value, s.label.toLowerCase()])),
  ...DATA_FIELD_LABELS,
};
const CODE_PATTERN = new RegExp(`\\b(${Object.keys(CODE_LABELS).join("|")})\\b`, "g");

/** Remplace les codes techniques (« primary_lbo », « ticket_min_eur_m »…) par leur libellé. */
export function humanize(text: string): string {
  return text.replace(CODE_PATTERN, (code) => CODE_LABELS[code] ?? code);
}

export function labelOf(list: readonly { value: string; label: string }[], value: string): string {
  return list.find((item) => item.value === value)?.label ?? value;
}

// --- Formulaire -------------------------------------------------------------------------------

export type FormValues = {
  companyName: string;
  website: string;
  sector: string;
  dealType: string;
  stake: string;
  enterpriseValue: string; // texte saisi, « 40 » ou « 40,5 »
  equityTicket: string;
};

export const EMPTY_FORM: FormValues = {
  companyName: "",
  website: "",
  sector: "",
  dealType: "primary_lbo",
  stake: "majority",
  enterpriseValue: "",
  equityTicket: "",
};

export type ScoreRequest = {
  deal_type: string;
  sector: string;
  equity_ticket_eur_m: number;
  stake_sought: string;
  enterprise_value_eur_m: number;
  company_name?: string;
};

export type FieldErrors = Partial<Record<keyof FormValues, string>>;

const MAX_AMOUNT_EUR_M = 100_000; // garde-fou : 100 Md€ ; au-delà, c'est une faute de frappe

/** Lit un montant en M€ saisi à la française (« 12,5 », « 1 200 »). null si ce n'est pas un nombre. */
export function parseAmount(text: string): number | null {
  const cleaned = text.replace(/[\s  ]/g, "").replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(cleaned)) return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

function amountError(text: string): string | undefined {
  if (text.trim() === "") return "Required";
  const value = parseAmount(text);
  if (value === null) return "Enter an amount in €m, e.g. 12.5";
  if (value <= 0) return "Must be greater than 0";
  if (value > MAX_AMOUNT_EUR_M) return "Amount too high (in €m, not €)";
  return undefined;
}

/** Contrôle le formulaire. Renvoie la requête prête à envoyer, ou les erreurs champ par champ. */
export function validateForm(
  values: FormValues,
): { ok: true; request: ScoreRequest } | { ok: false; errors: FieldErrors } {
  const errors: FieldErrors = {};
  if (values.companyName.trim() === "") errors.companyName = "Required";
  if (values.companyName.trim().length > 120) errors.companyName = "120 characters maximum";
  if (!SECTORS.some((s) => s.value === values.sector)) errors.sector = "Choose a sector";
  if (!DEAL_TYPES.some((d) => d.value === values.dealType)) errors.dealType = "Choose a deal type";
  if (!STAKES.some((s) => s.value === values.stake)) errors.stake = "Choose a stake";
  const evError = amountError(values.enterpriseValue);
  const ticketError = amountError(values.equityTicket);
  if (evError) errors.enterpriseValue = evError;
  if (ticketError) errors.equityTicket = ticketError;
  if (!evError && !ticketError) {
    const ev = parseAmount(values.enterpriseValue)!;
    const ticket = parseAmount(values.equityTicket)!;
    if (ticket > ev) errors.equityTicket = "The equity ticket cannot exceed the EV";
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return {
    ok: true,
    request: {
      deal_type: values.dealType,
      sector: values.sector,
      equity_ticket_eur_m: parseAmount(values.equityTicket)!,
      stake_sought: values.stake,
      enterprise_value_eur_m: parseAmount(values.enterpriseValue)!,
      company_name: values.companyName.trim(),
    },
  };
}

/** Part du ticket dans la VE, en %, arrondie à l'unité ; null si un des montants manque. */
export function ticketShareOfEv(values: FormValues): number | null {
  const ev = parseAmount(values.enterpriseValue);
  const ticket = parseAmount(values.equityTicket);
  if (ev === null || ticket === null || ev <= 0) return null;
  return Math.round((ticket / ev) * 100);
}

// --- Réponse ----------------------------------------------------------------------------------

export type Criterion = {
  id: string;
  label: string;
  kind: "eliminatory" | "graded";
  status: string;
  status_label: string;
  points: number | null;
  max_points: number | null;
  explanation: string;
};

export type Investment = {
  company_name: string;
  entry_year: number | null;
  country: string | null; // null = pays non publié par le fonds
  description_short: string | null; // résumé IA au format des slides
  description_short_by_ai: boolean;
  description: string | null; // texte publié par le fonds (ou par la société)
  source_url: string;
  sector: string | null; // code de la base (FOOD_AGRI…)
  sector_by_ai: boolean; // secteur classé par l'IA, pas publié
};

export type FundProfile = {
  website: string | null;
  source_url: string | null;
  last_fund_name: string | null;
  equity_ticket_min_eur_m: number | null;
  equity_ticket_max_eur_m: number | null;
  target_ev_min_eur_m: number | null;
  target_ev_max_eur_m: number | null;
  latest_investments_france: Investment[];
  sector_investments: Investment[];
  holdings_collected: boolean;
  logo_url?: string | null;
  logo_white?: boolean; // logo blanc : affiché en noir
  logo_verified?: boolean; // annuaire France Invest (sinon site du fonds, non vérifié)
};

export type RankedCompany = {
  rank: number;
  fund_id: string;
  management_company: string | null;
  best_strategy_id: string;
  best_strategy_name: string | null;
  score: number;
  criteria: Criterion[];
  confidence: { criteria_known: number; criteria_total: number; level: string; missing_data: string[] };
  missing_data: string[];
  warnings: string[];
  other_strategies: {
    strategy_id: string;
    strategy_name: string | null;
    rank: number | null;
    score: number;
    excluded: boolean;
    exclusion_reasons: string[];
  }[];
  profile: FundProfile;
};

export type ExcludedStrategy = {
  strategy_id: string;
  fund_id: string;
  strategy_name: string | null;
  management_company: string | null;
  exclusion_reasons: string[];
};

export type ScoreResponse = {
  company_name: string;
  analysis_date: string;
  config_version: string;
  message: string | null;
  counts: {
    strategies_total: number;
    strategies_ranked: number;
    strategies_excluded: number;
    companies_ranked: number;
  };
  companies: RankedCompany[];
  excluded: ExcludedStrategy[];
  excluded_companies: ExcludedCompany[];
};

export type ExcludedCompany = {
  fund_id: string;
  management_company: string | null;
  strategies: ExcludedStrategy[];
  profile: FundProfile;
};

export const UNREACHABLE = "The server is not responding. Is it running? Start the app with `npm run dev`.";

/** Transforme la réponse HTTP de POST /api/score en résultat ou en message d'erreur affichable. */
export function interpretScore(
  status: number | null,
  body: unknown,
): { kind: "ok"; data: ScoreResponse } | { kind: "error"; message: string; details: { field: string; message: string }[] } {
  if (status === null || status >= 500) return { kind: "error", message: UNREACHABLE, details: [] };
  if (status === 200 && typeof body === "object" && body !== null && Array.isArray((body as ScoreResponse).companies)) {
    return { kind: "ok", data: body as ScoreResponse };
  }
  const error = (body as { error?: { message?: unknown; details?: unknown } } | null)?.error;
  const details = Array.isArray(error?.details) ? (error.details as { field: string; message: string }[]) : [];
  const message = typeof error?.message === "string" ? error.message : `Unexpected server response (HTTP ${status}).`;
  return { kind: "error", message, details };
}

// --- Lecture du classement --------------------------------------------------------------------

// Tiers : seuils PROPOSÉS (Alexandre, 2026-11-26), à valider par le groupe. Un seul endroit à modifier.
export const TIER_THRESHOLDS = { tier1: 80, tier2: 60 } as const;

export type Tier = 1 | 2 | 3;

export function tierOf(score: number): Tier {
  if (score >= TIER_THRESHOLDS.tier1) return 1;
  if (score >= TIER_THRESHOLDS.tier2) return 2;
  return 3;
}

export const TIER_LABELS: Record<Tier, string> = {
  1: "Tier 1 · contact first",
  2: "Tier 2 · to qualify",
  3: "Tier 3 · opportunistic",
};

export const CONFIDENCE_LABELS: Record<string, string> = { high: "High", medium: "Medium", low: "Low" };

/** « €5–20m », « up to €20m », « from €5m » ou « not published ». */
export function formatRange(min: number | null, max: number | null): string {
  const n = (v: number) => v.toLocaleString("en-GB", { maximumFractionDigits: 1 });
  if (min !== null && max !== null) return `€${n(min)}–${n(max)}m`;
  if (max !== null) return `up to €${n(max)}m`;
  if (min !== null) return `from €${n(min)}m`;
  return "not published";
}

export type ViewOptions = {
  search: string;
  minTier: Tier; // 3 = tous, 2 = tiers 1 et 2, 1 = tier 1 seul
  hideLowConfidence: boolean;
  limit: number | null; // null = tous
};

export const DEFAULT_VIEW: ViewOptions = { search: "", minTier: 3, hideLowConfidence: false, limit: 25 };

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

/** Applique les options d'affichage au classement (sans changer les rangs calculés par le moteur). */
export function filterCompanies(
  companies: RankedCompany[],
  view: ViewOptions,
): { shown: RankedCompany[]; matching: number } {
  const query = fold(view.search.trim());
  const matching = companies.filter(
    (c) =>
      tierOf(c.score) <= view.minTier &&
      !(view.hideLowConfidence && c.confidence.level === "low") &&
      (query === "" || fold(`${c.management_company ?? ""} ${c.best_strategy_name ?? ""}`).includes(query)),
  );
  return { shown: view.limit === null ? matching : matching.slice(0, view.limit), matching: matching.length };
}

/** Raisons d'exclusion regroupées par critère (« Type d'opération : 39 »), de la plus fréquente à la moins. */
export function exclusionSummary(excluded: ExcludedStrategy[]): { criterion: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const strategy of excluded) {
    const first = strategy.exclusion_reasons[0] ?? "Reason not given";
    const criterion = first.split(":")[0];
    counts.set(criterion, (counts.get(criterion) ?? 0) + 1);
  }
  return [...counts.entries()].map(([criterion, count]) => ({ criterion, count })).sort((a, b) => b.count - a.count);
}
