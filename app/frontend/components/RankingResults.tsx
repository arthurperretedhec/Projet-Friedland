"use client";

import { Fragment, useState } from "react";

import {
  CONFIDENCE_LABELS,
  DEFAULT_VIEW,
  exclusionSummary,
  filterCompanies,
  formatRange,
  humanize,
  type RankedCompany,
  type ScoreResponse,
  TIER_LABELS,
  TIER_THRESHOLDS,
  type Tier,
  tierOf,
  toCsv,
  type ViewOptions,
} from "@/lib/score";

const control =
  "rounded-md border border-[var(--border)] bg-[var(--background)] px-2.5 py-1.5 text-sm focus-visible:outline-2 focus-visible:outline-[var(--focus)]";

const TIER_TONE: Record<Tier, string> = {
  1: "border-[var(--ok)] text-[var(--ok)]",
  2: "border-[var(--warn)] text-[var(--warn)]",
  3: "border-[var(--border)] text-[var(--muted)]",
};

function TierBadge({ score }: { score: number }) {
  const tier = tierOf(score);
  return (
    <span title={TIER_LABELS[tier]} className={`inline-block rounded border px-1.5 py-0.5 text-xs font-semibold ${TIER_TONE[tier]}`}>
      T{tier}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 text-right font-semibold tabular-nums">{score.toLocaleString("fr-FR")}</span>
      <div className="hidden h-1.5 w-16 rounded bg-[var(--border)] sm:block" aria-hidden="true">
        <div className="h-1.5 rounded bg-[var(--accent)]" style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
      </div>
    </div>
  );
}

function externalUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

function CompanyDetail({ company }: { company: RankedCompany }) {
  const { profile } = company;
  return (
    <div className="grid gap-4 px-3 py-4 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <h4 className="mb-2 text-sm font-semibold">Pourquoi ce score</h4>
        <table className="w-full text-left text-xs">
          <thead className="text-[var(--muted)]">
            <tr>
              <th className="py-1 pr-2 font-medium">Critère</th>
              <th className="py-1 pr-2 font-medium">Résultat</th>
              <th className="py-1 pr-2 text-right font-medium">Points</th>
              <th className="py-1 font-medium">Explication</th>
            </tr>
          </thead>
          <tbody>
            {company.criteria.map((c) => (
              <tr key={c.id} className="border-t border-[var(--border)] align-top">
                <td className="py-1.5 pr-2 whitespace-nowrap">
                  {c.label}
                  {c.kind === "eliminatory" && <span className="ml-1 text-[var(--muted)]">(filtre)</span>}
                </td>
                <td className={`py-1.5 pr-2 whitespace-nowrap ${c.status === "missing" ? "text-[var(--warn)]" : ""}`}>
                  {c.status_label}
                </td>
                <td className="py-1.5 pr-2 text-right tabular-nums whitespace-nowrap">
                  {c.max_points === null ? "–" : `${c.points ?? 0} / ${c.max_points}`}
                </td>
                <td className="py-1.5 text-[var(--muted)]">{humanize(c.explanation)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 text-sm">
        <div>
          <h4 className="mb-1 font-semibold">Fiche publiée</h4>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-[var(--muted)]">Dernier fonds</dt>
            <dd>{profile.last_fund_name ?? "non publié"}</dd>
            <dt className="text-[var(--muted)]">Ticket equity</dt>
            <dd className="tabular-nums">{formatRange(profile.equity_ticket_min_eur_m, profile.equity_ticket_max_eur_m)}</dd>
            <dt className="text-[var(--muted)]">VE cible</dt>
            <dd className="tabular-nums">{formatRange(profile.target_ev_min_eur_m, profile.target_ev_max_eur_m)}</dd>
          </dl>
          <div className="mt-2 flex flex-wrap gap-3 text-xs">
            {profile.website && (
              <a href={externalUrl(profile.website)} target="_blank" rel="noreferrer noopener" className="underline">
                Site du fonds
              </a>
            )}
            {profile.source_url && (
              <a href={externalUrl(profile.source_url)} target="_blank" rel="noreferrer noopener" className="underline">
                Source des critères
              </a>
            )}
          </div>
        </div>
        {company.warnings.length > 0 && (
          <div>
            <h4 className="mb-1 font-semibold text-[var(--warn)]">À vérifier avant contact</h4>
            <ul className="list-disc pl-4 text-xs">
              {company.warnings.map((w) => (
                <li key={w}>{humanize(w)}</li>
              ))}
            </ul>
          </div>
        )}
        {company.other_strategies.length > 0 && (
          <div>
            <h4 className="mb-1 font-semibold">Autres stratégies de la société</h4>
            <ul className="text-xs">
              {company.other_strategies.map((o) => (
                <li key={o.strategy_id}>
                  {o.strategy_name ?? o.strategy_id} :{" "}
                  {o.excluded ? (
                    <span className="text-[var(--muted)]">écartée ({humanize(o.exclusion_reasons[0] ?? "")})</span>
                  ) : (
                    <span className="tabular-nums">{o.score.toLocaleString("fr-FR")} / 100</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function download(filename: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function RankingResults({ data, website }: { data: ScoreResponse; website: string }) {
  const [view, setView] = useState<ViewOptions>(DEFAULT_VIEW);
  const [open, setOpen] = useState<string | null>(null);
  const { shown, matching } = filterCompanies(data.companies, view);
  const tierCounts = ([1, 2, 3] as Tier[]).map((t) => data.companies.filter((c) => tierOf(c.score) === t).length);
  const exclusions = exclusionSummary(data.excluded);
  const set = (patch: Partial<ViewOptions>) => setView({ ...view, ...patch });

  return (
    <section aria-labelledby="results-heading" className="flex flex-col gap-4" data-testid="results">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="results-heading" className="text-xl font-semibold">
            Acquéreurs financiers potentiels · {data.company_name}
          </h2>
          <p className="text-sm text-[var(--muted)]">
            {website && (
              <>
                <a href={externalUrl(website)} target="_blank" rel="noreferrer noopener" className="underline">
                  {website}
                </a>
                {" · "}
              </>
            )}
            Analyse du {new Date(data.analysis_date).toLocaleDateString("fr-FR")} · grille {data.config_version}
          </p>
        </div>
        <button
          type="button"
          onClick={() => download(`acquereurs-${data.company_name.replace(/[^\p{L}\p{N}]+/gu, "-")}.csv`, toCsv(shown))}
          disabled={shown.length === 0}
          className={`${control} font-medium hover:bg-[var(--border)] disabled:opacity-50`}
        >
          Exporter la liste (CSV)
        </button>
      </header>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Sociétés de gestion compatibles", data.counts.companies_ranked],
          ["Tier 1", tierCounts[0]],
          ["Tier 2", tierCounts[1]],
          ["Stratégies écartées", `${data.counts.strategies_excluded} / ${data.counts.strategies_total}`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
            <dt className="text-xs text-[var(--muted)]">{label}</dt>
            <dd className="text-2xl font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      {data.message && (
        <p role="status" className="rounded-md border-l-4 border-[var(--warn)] bg-[var(--surface)] px-3 py-2">
          {data.message}
        </p>
      )}

      {data.companies.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Options d'affichage">
            <input
              type="search"
              aria-label="Rechercher une société de gestion"
              placeholder="Rechercher un fonds…"
              value={view.search}
              onChange={(e) => set({ search: e.target.value })}
              className={`${control} w-full sm:w-52`}
            />
            <select
              aria-label="Tiers affichés"
              value={view.minTier}
              onChange={(e) => set({ minTier: Number(e.target.value) as Tier })}
              className={control}
            >
              <option value={3}>Tous les tiers</option>
              <option value={2}>Tiers 1 et 2</option>
              <option value={1}>Tier 1 seulement</option>
            </select>
            <select
              aria-label="Nombre de fonds affichés"
              value={view.limit ?? "all"}
              onChange={(e) => set({ limit: e.target.value === "all" ? null : Number(e.target.value) })}
              className={control}
            >
              <option value={10}>Top 10</option>
              <option value={25}>Top 25</option>
              <option value={50}>Top 50</option>
              <option value="all">Tous</option>
            </select>
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={view.hideLowConfidence}
                onChange={(e) => set({ hideLowConfidence: e.target.checked })}
              />
              Masquer la confiance faible
            </label>
            <span className="ml-auto text-xs text-[var(--muted)]" aria-live="polite">
              {shown.length} affichés sur {matching}
            </span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--surface)] text-xs text-[var(--muted)]">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">#</th>
                  <th scope="col" className="px-3 py-2 font-medium">Tier</th>
                  <th scope="col" className="px-3 py-2 font-medium">Société de gestion · meilleure stratégie</th>
                  <th scope="col" className="px-3 py-2 font-medium">Score</th>
                  <th scope="col" className="hidden px-3 py-2 font-medium md:table-cell">Ticket publié</th>
                  <th scope="col" className="hidden px-3 py-2 font-medium sm:table-cell">Confiance</th>
                  <th scope="col" className="px-3 py-2 font-medium"><span className="sr-only">Détail</span></th>
                </tr>
              </thead>
              <tbody>
                {shown.map((c) => {
                  const isOpen = open === c.fund_id;
                  return (
                    <Fragment key={c.fund_id}>
                      <tr className="border-t border-[var(--border)] align-top hover:bg-[var(--surface)]" data-testid="ranking-row">
                        <td className="px-3 py-2 tabular-nums text-[var(--muted)]">{c.rank}</td>
                        <td className="px-3 py-2"><TierBadge score={c.score} /></td>
                        <td className="px-3 py-2">
                          <div className="font-medium">{c.management_company ?? c.fund_id}</div>
                          <div className="text-xs text-[var(--muted)]">
                            {c.best_strategy_name}
                            {c.other_strategies.length > 0 && ` · +${c.other_strategies.length} stratégie(s)`}
                          </div>
                        </td>
                        <td className="px-3 py-2"><ScoreBar score={c.score} /></td>
                        <td className="hidden px-3 py-2 text-xs tabular-nums md:table-cell">
                          {formatRange(c.profile.equity_ticket_min_eur_m, c.profile.equity_ticket_max_eur_m)}
                        </td>
                        <td className="hidden px-3 py-2 text-xs sm:table-cell">
                          {CONFIDENCE_LABELS[c.confidence.level] ?? c.confidence.level}
                          {c.warnings.length > 0 && (
                            <span className="ml-1 text-[var(--warn)]" title={c.warnings.map(humanize).join("\n")}>
                              · {c.warnings.length} à vérifier
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button
                            type="button"
                            aria-expanded={isOpen}
                            aria-controls={`detail-${c.fund_id}`}
                            onClick={() => setOpen(isOpen ? null : c.fund_id)}
                            className="rounded px-2 py-0.5 text-xs underline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
                          >
                            {isOpen ? "Masquer" : "Détail"}
                          </button>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr id={`detail-${c.fund_id}`} className="bg-[var(--surface)]">
                          <td colSpan={7}><CompanyDetail company={c} /></td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
                {shown.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center text-[var(--muted)]">
                      Aucun fonds ne correspond à ces options d&apos;affichage.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[var(--muted)]">
            Tier 1 : score ≥ {TIER_THRESHOLDS.tier1} · Tier 2 : {TIER_THRESHOLDS.tier2}–{TIER_THRESHOLDS.tier1 - 1} · Tier 3 :
            moins de {TIER_THRESHOLDS.tier2}. Une donnée manquante n&apos;écarte jamais un fonds : elle baisse la confiance et
            figure dans « à vérifier ».
          </p>
        </>
      )}

      {data.excluded.length > 0 && (
        <details className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-sm">
          <summary className="cursor-pointer font-medium">
            {data.counts.strategies_excluded} stratégies écartées par les filtres :{" "}
            {exclusions.map((e) => `${e.criterion} (${e.count})`).join(", ")}
          </summary>
          <ul className="mt-2 max-h-80 overflow-y-auto text-xs">
            {data.excluded.map((e) => (
              <li key={e.strategy_id} className="border-t border-[var(--border)] py-1.5">
                <span className="font-medium">{e.management_company ?? "?"}</span> · {e.strategy_name ?? e.strategy_id} :{" "}
                <span className="text-[var(--muted)]">{e.exclusion_reasons.map(humanize).join(" ; ")}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
