"use client";

import { useEffect, useRef } from "react";

import { BannerPreview } from "@/components/BannerPreview";
import { type ExcludedCompany, formatRange, humanize, type RankedCompany } from "@/lib/score";
import type { BannerRow, FundChoice } from "@/lib/selection";

type Props = {
  row: BannerRow;
  sector: string;
  company?: RankedCompany;
  excluded?: ExcludedCompany;
  choice: FundChoice;
  onToggle: (key: keyof FundChoice) => void;
  onClose: () => void;
};

function externalUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

/** Panneau latéral d'un fonds : sélection, aperçu du bandeau, détail du score et sources. */
export function FundDrawer({ row, sector, company, excluded, choice, onToggle, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const p = row.profile;

  return (
    <>
      <div className="fixed inset-0 z-30 bg-[#072535]/40" onClick={onClose} aria-hidden="true" />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        data-testid="fund-drawer"
        className="scroll-thin fade-up fixed inset-y-0 right-0 z-40 flex w-full max-w-[900px] flex-col overflow-y-auto border-l border-[var(--border-strong)] bg-[var(--surface)]"
      >
        <header className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface-2)] px-6 py-5">
          <div>
            <p className="label-caps">{row.origin === "ranked" ? `Rang ${row.rank} · score ${row.score?.toLocaleString("fr-FR")} / 100` : "Écarté par les filtres"}</p>
            <h2 id="drawer-title" className="display-light mt-1 text-3xl">
              {row.fundName}
            </h2>
            <p className="text-sm text-[var(--muted)]">{row.strategyName}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="link-cta">
            Fermer
          </button>
        </header>

        <div className="flex flex-col gap-5 p-5">
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={choice.included} onChange={() => onToggle("included")} className="h-4 w-4 accent-[var(--accent)]" />
              Inclure dans le PowerPoint
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={choice.starred} onChange={() => onToggle("starred")} className="h-4 w-4 accent-[var(--gold)]" />
              <span className="text-[var(--gold)]">★</span> Intérêt exprimé
            </label>
          </div>

          <section aria-labelledby="banner-heading">
            <h3 id="banner-heading" className="label-caps mb-2">
              Aperçu du bandeau PowerPoint
            </h3>
            <BannerPreview row={{ ...row, starred: choice.starred }} sector={sector} />
            {p.logo_url && !p.logo_verified && (
              <p className="mt-2 text-xs text-[var(--muted)]">Logo repris du site du fonds, à vérifier.</p>
            )}
            {[...p.sector_investments, ...p.latest_investments_france].some((i) => i.description_short_by_ai || i.sector_by_ai) && (
              <p className="mt-2 text-xs text-[var(--muted)]">Descriptions et secteurs des participations résumés ou classés par l&apos;IA, à relire avant envoi.</p>
            )}
          </section>

          {company && (
            <section aria-labelledby="why-heading">
              <h3 id="why-heading" className="label-caps mb-2">
                Pourquoi ce score
              </h3>
              <div className="scroll-thin overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-xs">
                <thead className="text-[var(--muted)]">
                  <tr className="border-b border-[var(--border)]">
                    <th className="py-1.5 pr-2 font-medium">Critère</th>
                    <th className="py-1.5 pr-2 font-medium">Résultat</th>
                    <th className="py-1.5 pr-2 text-right font-medium">Points</th>
                    <th className="py-1.5 font-medium">Explication</th>
                  </tr>
                </thead>
                <tbody>
                  {company.criteria.map((c) => (
                    <tr key={c.id} className="border-b border-[var(--border)] align-top">
                      <td className="py-1.5 pr-2 whitespace-nowrap">
                        {c.label}
                        {c.kind === "eliminatory" && <span className="ml-1 text-[var(--muted)]">(filtre)</span>}
                      </td>
                      <td className={`py-1.5 pr-2 whitespace-nowrap ${c.status === "missing" ? "text-[var(--warn)]" : ""}`}>{c.status_label}</td>
                      <td className="py-1.5 pr-2 text-right whitespace-nowrap tabular-nums">{c.max_points === null ? "–" : `${c.points ?? 0} / ${c.max_points}`}</td>
                      <td className="py-1.5 text-[var(--muted)]">{humanize(c.explanation)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </section>
          )}

          {excluded && (
            <section aria-labelledby="excl-heading">
              <h3 id="excl-heading" className="label-caps mb-2">
                Pourquoi ce fonds est écarté
              </h3>
              <ul className="space-y-1 text-sm">
                {excluded.strategies.map((s) => (
                  <li key={s.strategy_id}>
                    <span className="font-medium">{s.strategy_name ?? s.strategy_id}</span> :{" "}
                    <span className="text-[var(--muted)]">{s.exclusion_reasons.map(humanize).join(" ; ")}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="grid gap-5 sm:grid-cols-2">
            <section aria-labelledby="profile-heading">
              <h3 id="profile-heading" className="label-caps mb-2">
                Critères publiés
              </h3>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                <dt className="text-[var(--muted)]">Ticket equity</dt>
                <dd className="tabular-nums">{formatRange(p.equity_ticket_min_eur_m, p.equity_ticket_max_eur_m)}</dd>
                <dt className="text-[var(--muted)]">VE cible</dt>
                <dd className="tabular-nums">{formatRange(p.target_ev_min_eur_m, p.target_ev_max_eur_m)}</dd>
                <dt className="text-[var(--muted)]">Dernier fonds</dt>
                <dd>{p.last_fund_name ?? "non publié"}</dd>
              </dl>
              <div className="mt-2 flex flex-wrap gap-3 text-sm">
                {p.website && (
                  <a href={externalUrl(p.website)} target="_blank" rel="noreferrer noopener" className="link-cta">
                    Site du fonds
                  </a>
                )}
                {p.source_url && (
                  <a href={externalUrl(p.source_url)} target="_blank" rel="noreferrer noopener" className="link-cta">
                    Source des critères
                  </a>
                )}
              </div>
            </section>
            {company && (company.warnings.length > 0 || company.other_strategies.length > 0) && (
              <section aria-labelledby="check-heading">
                {company.warnings.length > 0 && (
                  <>
                    <h3 id="check-heading" className="label-caps mb-2 text-[var(--warn)]">
                      À vérifier avant contact
                    </h3>
                    <ul className="list-disc pl-4 text-sm">
                      {company.warnings.map((w) => (
                        <li key={w}>{humanize(w)}</li>
                      ))}
                    </ul>
                  </>
                )}
                {company.other_strategies.length > 0 && (
                  <>
                    <h3 className="label-caps mt-3 mb-2">Autres stratégies</h3>
                    <ul className="text-sm">
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
                  </>
                )}
              </section>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
