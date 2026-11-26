"use client";

import { useState } from "react";

import { FundDrawer } from "@/components/FundDrawer";
import {
  CONFIDENCE_LABELS,
  DEFAULT_VIEW,
  exclusionSummary,
  filterCompanies,
  humanize,
  type ScoreResponse,
  TIER_LABELS,
  TIER_THRESHOLDS,
  type Tier,
  tierOf,
  type ViewOptions,
} from "@/lib/score";
import {
  initialSelection,
  rowFromExcluded,
  rowFromRanked,
  type Selection,
  selectedRows,
  selectionCsv,
  setIncluded,
  ticketForSlide,
  toggle,
} from "@/lib/selection";

const control =
  "border-0 border-b border-[var(--border-strong)] bg-[var(--border-light)] px-2.5 py-1.5 text-sm focus-visible:outline-2 focus-visible:outline-[var(--focus)]";

const TIER_TONE: Record<Tier, string> = {
  1: "bg-[var(--accent)] text-white",
  2: "border border-[var(--accent)] text-[var(--accent)]",
  3: "bg-[var(--surface-2)] text-[var(--muted)]",
};

function TierBadge({ score }: { score: number }) {
  const tier = tierOf(score);
  return (
    <span title={TIER_LABELS[tier]} className={`inline-block rounded-sm px-1.5 py-0.5 text-[10px] font-bold tracking-wide ${TIER_TONE[tier]}`}>
      T{tier}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 text-right font-semibold tabular-nums">{score.toLocaleString("fr-FR")}</span>
      <div className="hidden h-1 w-14 rounded bg-[var(--border)] sm:block" aria-hidden="true">
        <div className="h-1 rounded bg-[var(--accent)]" style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
      </div>
    </div>
  );
}

function Star({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={label}
      title="Intérêt exprimé"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`text-base leading-none focus-visible:outline-2 focus-visible:outline-[var(--focus)] ${on ? "text-[var(--gold)]" : "text-[var(--border-strong)] hover:text-[var(--muted)]"}`}
    >
      ★
    </button>
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

export function RankingResults({ data, website = "", sector }: { data: ScoreResponse; website?: string; sector: string }) {
  const [view, setView] = useState<ViewOptions>(DEFAULT_VIEW);
  const [selection, setSelection] = useState<Selection>(() => initialSelection(data));
  const [open, setOpen] = useState<string | null>(null);
  const { shown, matching } = filterCompanies(data.companies, view);
  const chosen = selectedRows(data, selection);
  const added = chosen.filter((r) => r.origin === "added").length;
  const starred = chosen.filter((r) => r.starred).length;
  const tierCounts = ([1, 2, 3] as Tier[]).map((t) => data.companies.filter((c) => tierOf(c.score) === t).length);
  const exclusions = exclusionSummary(data.excluded);
  const set = (patch: Partial<ViewOptions>) => setView({ ...view, ...patch });
  const allShownIncluded = shown.length > 0 && shown.every((c) => selection[c.fund_id]?.included);

  const openCompany = data.companies.find((c) => c.fund_id === open);
  const openExcluded = data.excluded_companies.find((e) => e.fund_id === open);
  const openRow = openCompany ? rowFromRanked(openCompany) : openExcluded ? rowFromExcluded(openExcluded) : null;

  return (
    <section aria-labelledby="results-heading" className="flex flex-col gap-4" data-testid="results">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label-caps">Acquéreurs financiers potentiels</p>
          <h2 id="results-heading" className="display-light rule-blue mt-1 text-4xl">
            {data.company_name}
          </h2>
          <p className="mt-3 text-xs text-[var(--muted)]">
            {website && (
              <>
                <a href={/^https?:\/\//i.test(website) ? website : `https://${website}`} target="_blank" rel="noreferrer noopener" className="link-cta normal-case">
                  {website}
                </a>
                {" · "}
              </>
            )}
            Analyse du {new Date(data.analysis_date).toLocaleDateString("fr-FR")} · grille {data.config_version}
          </p>
        </div>
      </header>

      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          ["Sociétés compatibles", data.counts.companies_ranked],
          ["Tier 1", tierCounts[0]],
          ["Tier 2", tierCounts[1]],
          ["Stratégies écartées", `${data.counts.strategies_excluded} / ${data.counts.strategies_total}`],
        ].map(([label, value]) => (
          <div key={label} className="bracket flex flex-col-reverse px-5 py-4">
            <dt className="label-caps mt-1">{label}</dt>
            <dd className="text-[40px] leading-none font-normal text-[var(--heading)] tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      {/* Barre de sélection pour le PowerPoint */}
      <div
        data-testid="selection-bar"
        className="on-dark sticky top-0 z-20 flex flex-wrap items-center gap-3 bg-[var(--navy)] px-5 py-3 text-sm text-white"
      >
        <span aria-live="polite">
          <span className="text-lg font-semibold tabular-nums">{chosen.length}</span> fonds sélectionnés pour le PowerPoint
          {added > 0 && <span className="text-white/75"> · dont {added} ajouté{added > 1 ? "s" : ""} manuellement</span>}
          {starred > 0 && <span className="text-white/90"> · ★ {starred} intérêt{starred > 1 ? "s" : ""} exprimé{starred > 1 ? "s" : ""}</span>}
        </span>
        <div role="group" aria-label="Sélection rapide" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          <span className="text-white/70">Cocher :</span>
          {([1, 2, 3] as Tier[]).map((t) => {
            const ids = data.companies.filter((c) => tierOf(c.score) === t).map((c) => c.fund_id);
            const all = ids.length > 0 && ids.every((id) => selection[id]?.included);
            return (
              <button
                key={t}
                type="button"
                aria-pressed={all}
                disabled={ids.length === 0}
                onClick={() => setSelection(setIncluded(selection, ids, !all))}
                className={`link-cta !text-white disabled:opacity-40 ${all ? "" : "opacity-70"}`}
                title={all ? `Décocher les ${ids.length} fonds Tier ${t}` : `Cocher les ${ids.length} fonds Tier ${t}`}
              >
                {all ? "✓ " : ""}Tier {t} ({ids.length})
              </button>
            );
          })}
          <button type="button" onClick={() => setSelection(setIncluded(selection, data.companies.map((c) => c.fund_id), true))} className="link-cta !text-white">
            Tout
          </button>
          <button
            type="button"
            onClick={() => setSelection(setIncluded(selection, [...data.companies, ...data.excluded_companies].map((c) => c.fund_id), false))}
            className="link-cta !text-white"
          >
            Rien
          </button>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-5">
          <button type="button" onClick={() => setSelection(initialSelection(data))} className="link-cta !text-white">
            Réinitialiser (Tier 1)
          </button>
          <button
            type="button"
            disabled={chosen.length === 0}
            onClick={() => download(`selection-${data.company_name.replace(/[^\p{L}\p{N}]+/gu, "-")}.csv`, selectionCsv(chosen))}
            className="btn-primary bracket !py-2.5"
          >
            Exporter la sélection (CSV)
          </button>
        </div>
      </div>

      {data.message && (
        <p role="status" className="border-l-4 border-[var(--warn)] bg-[var(--surface-2)] px-3 py-2">
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
              className={`${control} w-full sm:w-56`}
            />
            <select aria-label="Tiers affichés" value={view.minTier} onChange={(e) => set({ minTier: Number(e.target.value) as Tier })} className={control}>
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
            <label className="flex items-center gap-1.5 text-[var(--muted)]">
              <input type="checkbox" checked={view.hideLowConfidence} onChange={(e) => set({ hideLowConfidence: e.target.checked })} className="accent-[var(--accent)]" />
              Masquer la confiance faible
            </label>
            <span className="ml-auto text-xs text-[var(--muted)]" aria-live="polite">
              {shown.length} affichés sur {matching}
            </span>
          </div>

          <div className="scroll-thin overflow-x-auto border-t-2 border-[var(--accent)]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--surface-2)] text-[var(--foreground)]">
                <tr className="label-caps">
                  <th scope="col" className="w-9 px-3 py-2">
                    <input
                      type="checkbox"
                      aria-label="Cocher ou décocher tous les fonds affichés"
                      checked={allShownIncluded}
                      onChange={() => setSelection(setIncluded(selection, shown.map((c) => c.fund_id), !allShownIncluded))}
                      className="h-4 w-4 accent-[var(--accent)]"
                    />
                  </th>
                  <th scope="col" className="w-7 px-1 py-2">
                    <span className="sr-only">Intérêt exprimé</span>★
                  </th>
                  <th scope="col" className="px-2 py-2 font-semibold">#</th>
                  <th scope="col" className="px-2 py-2 font-semibold">Tier</th>
                  <th scope="col" className="px-2 py-2 font-semibold">Société de gestion · stratégie</th>
                  <th scope="col" className="px-2 py-2 font-semibold">Score</th>
                  <th scope="col" className="hidden px-2 py-2 font-semibold md:table-cell">Ticket</th>
                  <th scope="col" className="hidden px-2 py-2 font-semibold lg:table-cell">Confiance</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((c, i) => {
                  const choice = selection[c.fund_id] ?? { included: false, starred: false };
                  return (
                    <tr
                      key={c.fund_id}
                      data-testid="ranking-row"
                      onClick={() => setOpen(c.fund_id)}
                      className={`cursor-pointer border-t border-[var(--border)] align-middle hover:bg-[var(--accent-soft)] ${i % 2 ? "bg-[#fafbfd]" : "bg-white"} ${choice.included ? "" : "opacity-55"}`}
                    >
                      <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          aria-label={`Inclure ${c.management_company ?? c.fund_id} dans le PowerPoint`}
                          checked={choice.included}
                          onChange={() => setSelection(toggle(selection, c.fund_id, "included"))}
                          className="h-4 w-4 accent-[var(--accent)]"
                        />
                      </td>
                      <td className="px-1 py-2">
                        <Star on={choice.starred} label={`Intérêt exprimé par ${c.management_company ?? c.fund_id}`} onClick={() => setSelection(toggle(selection, c.fund_id, "starred"))} />
                      </td>
                      <td className="px-2 py-2 tabular-nums text-[var(--muted)]">{c.rank}</td>
                      <td className="px-2 py-2">
                        <TierBadge score={c.score} />
                      </td>
                      <td className="px-2 py-2">
                        <button type="button" className="text-left focus-visible:outline-2 focus-visible:outline-[var(--focus)]" onClick={() => setOpen(c.fund_id)}>
                          <span className="font-medium text-[var(--heading)]">{c.management_company ?? c.fund_id}</span>
                          <span className="block text-xs text-[var(--muted)]">
                            {c.best_strategy_name}
                            {c.other_strategies.length > 0 && ` · +${c.other_strategies.length}`}
                          </span>
                        </button>
                      </td>
                      <td className="px-2 py-2">
                        <ScoreBar score={c.score} />
                      </td>
                      <td className="hidden px-2 py-2 text-xs tabular-nums md:table-cell">
                        {ticketForSlide(c.profile.equity_ticket_min_eur_m, c.profile.equity_ticket_max_eur_m) ?? <span className="text-[var(--muted)]">n.d.</span>}
                      </td>
                      <td className="hidden px-2 py-2 text-xs lg:table-cell">
                        {CONFIDENCE_LABELS[c.confidence.level] ?? c.confidence.level}
                        {c.warnings.length > 0 && <span className="ml-1 text-[var(--warn)]">· {c.warnings.length} à vérifier</span>}
                      </td>
                    </tr>
                  );
                })}
                {shown.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-center text-[var(--muted)]">
                      Aucun fonds ne correspond à ces options d&apos;affichage.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[var(--muted)]">
            Cliquez sur un fonds pour l&apos;aperçu du bandeau. Tier 1 : score ≥ {TIER_THRESHOLDS.tier1} · Tier 2 : {TIER_THRESHOLDS.tier2}–
            {TIER_THRESHOLDS.tier1 - 1} · Tier 3 : moins de {TIER_THRESHOLDS.tier2}. Une donnée manquante n&apos;écarte jamais un fonds.
          </p>
        </>
      )}

      {data.excluded_companies.length > 0 && (
        <details className="bg-[var(--surface-2)] text-sm" data-testid="excluded-companies">
          <summary className="cursor-pointer px-4 py-3">
            <span className="font-medium">{data.excluded_companies.length} sociétés de gestion écartées par les filtres</span>
            <span className="text-[var(--muted)]"> · vous pouvez en ajouter une à la sélection</span>
            <span className="block text-xs text-[var(--muted)]">
              Stratégies écartées : {exclusions.map((e) => `${e.criterion} (${e.count})`).join(", ")}
            </span>
          </summary>
          <ul className="scroll-thin max-h-96 overflow-y-auto border-t border-[var(--border)]">
            {data.excluded_companies.map((e) => {
              const choice = selection[e.fund_id] ?? { included: false, starred: false };
              return (
                <li key={e.fund_id} className="flex items-start gap-3 border-b border-[var(--border)] px-4 py-2">
                  <input
                    type="checkbox"
                    aria-label={`Ajouter ${e.management_company ?? e.fund_id} à la sélection`}
                    checked={choice.included}
                    onChange={() => setSelection(toggle(selection, e.fund_id, "included"))}
                    className="mt-1 h-4 w-4 accent-[var(--accent)]"
                  />
                  <Star on={choice.starred} label={`Intérêt exprimé par ${e.management_company ?? e.fund_id}`} onClick={() => setSelection(toggle(selection, e.fund_id, "starred"))} />
                  <button type="button" onClick={() => setOpen(e.fund_id)} className="text-left focus-visible:outline-2 focus-visible:outline-[var(--focus)]">
                    <span className="font-medium text-[var(--heading)]">{e.management_company ?? e.fund_id}</span>
                    <span className="block text-xs text-[var(--muted)]">{humanize(e.strategies[0]?.exclusion_reasons[0] ?? "")}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </details>
      )}

      {openRow && (
        <FundDrawer
          row={openRow}
          sector={sector}
          company={openCompany}
          excluded={openExcluded}
          choice={selection[openRow.fundId] ?? { included: false, starred: false }}
          onToggle={(key) => setSelection(toggle(selection, openRow.fundId, key))}
          onClose={() => setOpen(null)}
        />
      )}
    </section>
  );
}
