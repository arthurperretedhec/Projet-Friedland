// Sélection des fonds pour le PowerPoint et contenu du bandeau (logique pure, testée).
// Le banquier coche / décoche les fonds classés, peut ajouter un fonds écarté par les filtres et
// marquer ceux qui ont exprimé un intérêt (étoile, comme sur les slides).

import {
  CONFIDENCE_LABELS,
  type ExcludedCompany,
  type FundProfile,
  type Investment,
  type RankedCompany,
  type ScoreResponse,
  tierOf,
} from "./score";

export type FundChoice = { included: boolean; starred: boolean };
export type Selection = Record<string, FundChoice>; // clé : fund_id

/** Par défaut : Tier 1 coché (une longlist de discussion materials), le reste décoché. */
export function initialSelection(data: ScoreResponse): Selection {
  const selection: Selection = {};
  for (const c of data.companies) selection[c.fund_id] = { included: tierOf(c.score) === 1, starred: false };
  for (const e of data.excluded_companies) selection[e.fund_id] = { included: false, starred: false };
  return selection;
}

export function toggle(selection: Selection, fundId: string, key: keyof FundChoice): Selection {
  const current = selection[fundId] ?? { included: false, starred: false };
  const next = { ...current, [key]: !current[key] };
  // Marquer un intérêt sélectionne le fonds : il ira dans le PowerPoint.
  if (key === "starred" && next.starred) next.included = true;
  return { ...selection, [fundId]: next };
}

export function setIncluded(selection: Selection, fundIds: string[], included: boolean): Selection {
  const next = { ...selection };
  for (const id of fundIds) next[id] = { ...(next[id] ?? { starred: false }), included };
  return next;
}

/** Une ligne du futur bandeau PowerPoint, que le fonds vienne du classement ou d'un ajout manuel. */
export type BannerRow = {
  fundId: string;
  fundName: string;
  strategyName: string | null;
  origin: "ranked" | "added";
  rank: number | null;
  score: number | null;
  confidence: string | null;
  starred: boolean;
  profile: FundProfile;
};

export function rowFromRanked(c: RankedCompany, starred = false): BannerRow {
  return {
    fundId: c.fund_id,
    fundName: c.management_company ?? c.fund_id,
    strategyName: c.best_strategy_name,
    origin: "ranked",
    rank: c.rank,
    score: c.score,
    confidence: CONFIDENCE_LABELS[c.confidence.level] ?? c.confidence.level,
    starred,
    profile: c.profile,
  };
}

export function rowFromExcluded(e: ExcludedCompany, starred = false): BannerRow {
  return {
    fundId: e.fund_id,
    fundName: e.management_company ?? e.fund_id,
    strategyName: e.strategies[0]?.strategy_name ?? null,
    origin: "added",
    rank: null,
    score: null,
    confidence: null,
    starred,
    profile: e.profile,
  };
}

/** Fonds retenus pour le PowerPoint : d'abord le classement (ordre du moteur), puis les ajouts. */
export function selectedRows(data: ScoreResponse, selection: Selection): BannerRow[] {
  const ranked = data.companies
    .filter((c) => selection[c.fund_id]?.included)
    .map((c) => rowFromRanked(c, !!selection[c.fund_id]?.starred));
  const added = data.excluded_companies
    .filter((e) => selection[e.fund_id]?.included)
    .map((e) => rowFromExcluded(e, !!selection[e.fund_id]?.starred));
  return [...ranked, ...added];
}

// --- Contenu du bandeau (format des slides) ---------------------------------------------------

const n = (v: number) => v.toLocaleString("en-GB", { maximumFractionDigits: 1 });

/** Ticket au format des slides : « €[10-100]m », « €10m+ », « up to €20m », sinon null. */
export function ticketForSlide(min: number | null, max: number | null): string | null {
  if (min !== null && max !== null) return `€[${n(min)}-${n(max)}]m`;
  if (min !== null) return `€${n(min)}m+`;
  if (max !== null) return `up to €${n(max)}m`;
  return null;
}

/** Texte d'une participation : le résumé IA s'il existe, sinon le début du texte publié. */
export function investmentText(inv: Investment, max = 110): { text: string | null; byAi: boolean } {
  if (inv.description_short) return { text: inv.description_short, byAi: inv.description_short_by_ai };
  if (!inv.description) return { text: null, byAi: false };
  const clean = inv.description.replace(/…$/, "");
  return { text: clean.length > max ? `${clean.slice(0, max).trimEnd()}…` : inv.description, byAi: false };
}

/** « Tethys (2026) - Designer and manufacturer of … » ; l'année manque si le site ne la publie pas. */
export function investmentLine(inv: Investment): string {
  const { text } = investmentText(inv);
  const head = inv.entry_year ? `${inv.company_name} (${inv.entry_year})` : inv.company_name;
  return text ? `${head} - ${text}` : head;
}

// --- Export CSV de la sélection (Excel français : BOM, « ; ») --------------------------------

function cell(value: string | number | null): string {
  const text = value === null ? "" : typeof value === "number" ? String(value).replace(".", ",") : value;
  return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function selectionCsv(rows: BannerRow[]): string {
  const header = [
    "Fonds",
    "Stratégie",
    "Origine",
    "Intérêt exprimé",
    "Rang",
    "Score /100",
    "Confiance",
    "Dernier fonds",
    "Ticket",
    "Participations dans le secteur de la cible",
    "Dernières participations en France (descriptions résumées par l'IA quand indiqué)",
    "Site",
    "Source des critères",
  ];
  const lines = rows.map((r) => [
    r.fundName,
    r.strategyName,
    r.origin === "ranked" ? "Classement" : "Ajout manuel",
    r.starred ? "Oui" : "",
    r.rank,
    r.score,
    r.confidence,
    r.profile.last_fund_name,
    ticketForSlide(r.profile.equity_ticket_min_eur_m, r.profile.equity_ticket_max_eur_m),
    r.profile.sector_investments.map(investmentLine).join(" | "),
    r.profile.latest_investments_france.map(investmentLine).join(" | "),
    r.profile.website,
    r.profile.source_url,
  ]);
  return "﻿" + [header, ...lines].map((l) => l.map(cell).join(";")).join("\r\n") + "\r\n";
}
