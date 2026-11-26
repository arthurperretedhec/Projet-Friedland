// Logique pure de l'écran de screening (sans React, sans réseau), pour être testée facilement.
// Contrat de l'API : app/docs/scoring.md, « Route d'API POST /api/score ».

// --- Vocabulaire (mêmes codes que app/backend/app/logic/reference.py) -------------------------

export const DEAL_TYPES = [
  { value: "primary_lbo", label: "LBO primaire", hint: "Transmission, MBO / MBI, succession familiale" },
  { value: "secondary_lbo", label: "LBO secondaire", hint: "Sortie d'un fonds, reprise par un autre fonds" },
  { value: "build_up", label: "Build-up", hint: "Acquisition par une plateforme déjà détenue" },
  { value: "growth", label: "Capital développement", hint: "Financer la croissance, souvent minoritaire" },
  { value: "carve_out", label: "Carve-out", hint: "Cession d'une filiale ou d'une division" },
] as const;

export const SECTORS = [
  { value: "software_it", label: "Logiciel & IT" },
  { value: "healthcare", label: "Santé" },
  { value: "business_services", label: "Services aux entreprises" },
  { value: "industrials", label: "Industrie" },
  { value: "consumer_retail", label: "Consommation & distribution" },
  { value: "food_beverage", label: "Agroalimentaire & boissons" },
  { value: "financial_services", label: "Services financiers" },
  { value: "education", label: "Éducation" },
  { value: "energy_environment", label: "Énergie & environnement" },
  { value: "construction_real_estate", label: "Construction & immobilier" },
  { value: "transport_logistics", label: "Transport & logistique" },
  { value: "media_telecom", label: "Médias & télécoms" },
  { value: "agriculture", label: "Agriculture" },
] as const;

export const STAKES = [
  { value: "majority", label: "Majoritaire", hint: "Le fonds prend le contrôle" },
  { value: "minority", label: "Minoritaire", hint: "Le dirigeant garde le contrôle" },
] as const;

const DATA_FIELD_LABELS: Record<string, string> = {
  ticket_min_eur_m: "ticket minimum",
  ticket_max_eur_m: "ticket maximum",
  equity_ticket_min_eur_m: "ticket minimum",
  equity_ticket_max_eur_m: "ticket maximum",
  ev_min_eur_m: "VE minimum",
  ev_max_eur_m: "VE maximum",
  deal_types: "types d'opération",
  stake: "position",
  sectors: "secteurs",
};

const CODE_LABELS: Record<string, string> = {
  ...Object.fromEntries(DEAL_TYPES.map((d) => [d.value, d.label])),
  ...Object.fromEntries(SECTORS.map((s) => [s.value, s.label.toLowerCase()])),
  ...DATA_FIELD_LABELS,
};
const CODE_PATTERN = new RegExp(`\\b(${Object.keys(CODE_LABELS).join("|")})\\b`, "g");

/** Remplace les codes techniques (« primary_lbo », « ticket_min_eur_m »…) par leur libellé français. */
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
  if (text.trim() === "") return "Champ obligatoire";
  const value = parseAmount(text);
  if (value === null) return "Saisir un nombre en M€, par exemple 12,5";
  if (value <= 0) return "Doit être supérieur à 0";
  if (value > MAX_AMOUNT_EUR_M) return "Montant trop élevé (en M€, pas en €)";
  return undefined;
}

/** Contrôle le formulaire. Renvoie la requête prête à envoyer, ou les erreurs champ par champ. */
export function validateForm(
  values: FormValues,
): { ok: true; request: ScoreRequest } | { ok: false; errors: FieldErrors } {
  const errors: FieldErrors = {};
  if (values.companyName.trim() === "") errors.companyName = "Champ obligatoire";
  if (values.companyName.trim().length > 120) errors.companyName = "120 caractères maximum";
  if (!SECTORS.some((s) => s.value === values.sector)) errors.sector = "Choisir un secteur";
  if (!DEAL_TYPES.some((d) => d.value === values.dealType)) errors.dealType = "Choisir un type d'opération";
  if (!STAKES.some((s) => s.value === values.stake)) errors.stake = "Choisir une position";
  const evError = amountError(values.enterpriseValue);
  const ticketError = amountError(values.equityTicket);
  if (evError) errors.enterpriseValue = evError;
  if (ticketError) errors.equityTicket = ticketError;
  if (!evError && !ticketError) {
    const ev = parseAmount(values.enterpriseValue)!;
    const ticket = parseAmount(values.equityTicket)!;
    if (ticket > ev) errors.equityTicket = "Le ticket equity ne peut pas dépasser la VE";
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
  description: string | null; // texte publié par le fonds
  source_url: string;
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
  holdings_collected: boolean;
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

export const UNREACHABLE = "Le serveur ne répond pas. Est-il lancé ? Démarrer l'application avec `npm run dev`.";

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
  const message = typeof error?.message === "string" ? error.message : `Réponse inattendue du serveur (HTTP ${status}).`;
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
  1: "Tier 1 · à contacter en priorité",
  2: "Tier 2 · à qualifier",
  3: "Tier 3 · opportuniste",
};

export const CONFIDENCE_LABELS: Record<string, string> = { élevé: "Élevée", moyen: "Moyenne", faible: "Faible" };

/** « 5–20 M€ », « jusqu'à 20 M€ », « dès 5 M€ » ou « non publié ». */
export function formatRange(min: number | null, max: number | null): string {
  const n = (v: number) => v.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
  if (min !== null && max !== null) return `${n(min)}–${n(max)} M€`;
  if (max !== null) return `jusqu'à ${n(max)} M€`;
  if (min !== null) return `dès ${n(min)} M€`;
  return "non publié";
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
      !(view.hideLowConfidence && c.confidence.level === "faible") &&
      (query === "" || fold(`${c.management_company ?? ""} ${c.best_strategy_name ?? ""}`).includes(query)),
  );
  return { shown: view.limit === null ? matching : matching.slice(0, view.limit), matching: matching.length };
}

/** Raisons d'exclusion regroupées par critère (« Type d'opération : 39 »), de la plus fréquente à la moins. */
export function exclusionSummary(excluded: ExcludedStrategy[]): { criterion: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const strategy of excluded) {
    const first = strategy.exclusion_reasons[0] ?? "Raison non précisée";
    const criterion = first.split(" :")[0];
    counts.set(criterion, (counts.get(criterion) ?? 0) + 1);
  }
  return [...counts.entries()].map(([criterion, count]) => ({ criterion, count })).sort((a, b) => b.count - a.count);
}
