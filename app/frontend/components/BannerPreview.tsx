import type { Investment } from "@/lib/score";
import { type BannerRow, investmentText, ticketForSlide } from "@/lib/selection";

const COLUMNS = "grid-cols-[minmax(96px,1fr)_0.8fr_0.6fr_0.75fr_2fr_2fr]";
const MAX_PER_COLUMN = 3;

/** Monogramme en attendant les logos (collecte à faire) : deux lettres du nom de la société de gestion. */
function Monogram({ name }: { name: string }) {
  const words = name
    .replace(/\b(SAS|SA|SCA|Gestion|Partners|Capital|Group|Groupe)\b/gi, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  const letters = (words.length > 1 ? words.map((w) => w[0]) : (words[0] ?? "").slice(0, 2).split("")).join("").toUpperCase();
  return (
    <div className="flex h-12 w-12 items-center justify-center border border-[#c9d3e3] bg-white text-sm font-bold tracking-wide text-[var(--slide-ink)]">
      {letters || "?"}
    </div>
  );
}

function Head({ children }: { children: React.ReactNode }) {
  return <div className="bg-[var(--slide-head)] px-2 py-1.5 text-center text-[11px] font-semibold text-[var(--slide-ink)]">{children}</div>;
}

const ND = <span className="text-[var(--slide-muted)] italic">n.d.</span>;

function InvestmentList({ items, empty }: { items: Investment[]; empty: string }) {
  if (items.length === 0) return <p className="text-[var(--slide-muted)]">• {empty}</p>;
  return (
    <ul className="space-y-1">
      {items.slice(0, MAX_PER_COLUMN).map((inv) => {
        const { text } = investmentText(inv);
        return (
          <li key={inv.company_name} className="leading-snug">
            •{" "}
            <a href={inv.source_url} target="_blank" rel="noreferrer noopener" className="font-semibold text-[var(--slide-link)] underline">
              {inv.company_name}
            </a>
            {inv.entry_year ? ` (${inv.entry_year})` : ""}
            {text ? ` - ${text}` : ""}
          </li>
        );
      })}
    </ul>
  );
}

/** Une ligne du bandeau « Financial partners » des discussion materials, telle qu'elle sortira. */
export function BannerPreview({ row, sectorLabel }: { row: BannerRow; sectorLabel: string }) {
  const p = row.profile;
  const ticket = ticketForSlide(p.equity_ticket_min_eur_m, p.equity_ticket_max_eur_m);
  const shown = [...p.sector_investments.slice(0, MAX_PER_COLUMN), ...p.latest_investments_france.slice(0, MAX_PER_COLUMN)];
  const anyAiText = shown.some((i) => investmentText(i).byAi);
  const anyAiSector = p.sector_investments.some((i) => i.sector_by_ai);
  const noData = p.holdings_collected ? "No investment identified" : "Portefeuille pas encore collecté";
  return (
    <figure aria-label="Aperçu du bandeau PowerPoint" className="scroll-thin overflow-x-auto border border-[var(--border)] bg-[var(--slide-bg)] p-3 text-[var(--slide-ink)]">
      <div className="min-w-[760px]">
        <div className={`grid ${COLUMNS} gap-1.5`}>
          <Head>Fund name</Head>
          <Head>Amount</Head>
          <Head>Vintage</Head>
          <Head>Ticket size</Head>
          <Head>
            Investments in <u>{sectorLabel}</u> sector
          </Head>
          <Head>
            Latest investments in <u>France</u>
          </Head>
        </div>
        <div className={`mt-1.5 grid ${COLUMNS} items-center gap-1.5 border border-[#d6dde8] bg-[#f7f9fc] py-2 text-[11px]`}>
          <div className="flex flex-col items-center gap-1 px-1 text-center">
            <div className="relative">
              <Monogram name={row.fundName} />
              {row.starred && (
                <span aria-label="Intérêt exprimé" className="absolute -top-2 -right-2 text-base text-[#7b2d6e]">
                  ★
                </span>
              )}
            </div>
            <span className="text-[10px] leading-tight font-semibold">{row.fundName}</span>
          </div>
          <div className="text-center font-semibold text-[var(--slide-link)]">
            {p.last_fund_name ? (
              <span className="font-normal text-[var(--slide-ink)]">
                <span className="text-[var(--slide-muted)] italic">montant n.d.</span>
                <br />
                {p.last_fund_name}
              </span>
            ) : (
              ND
            )}
          </div>
          <div className="text-center">{ND}</div>
          <div className="text-center font-semibold text-[var(--slide-link)]">{ticket ?? ND}</div>
          <div className="pr-2" data-testid="banner-sector">
            <InvestmentList items={p.sector_investments} empty={noData} />
          </div>
          <div className="pr-2" data-testid="banner-france">
            <InvestmentList items={p.latest_investments_france} empty={noData} />
          </div>
        </div>
        <figcaption className="mt-2 flex flex-wrap gap-x-3 text-[10px] text-[var(--slide-muted)]">
          <span>Source : public information (sites des fonds et des sociétés)</span>
          {anyAiText && <span>Descriptions résumées par l&apos;IA</span>}
          {anyAiSector && <span>Secteur de certaines participations classé par l&apos;IA</span>}
          <span>n.d. = non disponible dans la base · logo à collecter</span>
        </figcaption>
      </div>
    </figure>
  );
}
