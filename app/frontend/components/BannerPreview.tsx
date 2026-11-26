import { investmentText, ticketForSlide, type BannerRow } from "@/lib/selection";

/** Monogramme en attendant les logos (collecte à faire) : initiales du nom de la société de gestion. */
function Monogram({ name }: { name: string }) {
  const initials = name
    .replace(/\b(SAS|SA|SCA|Gestion|Partners|Capital|Group|Groupe)\b/gi, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  const letters = (initials.length > 1 ? initials.map((w) => w[0]) : (initials[0] ?? "").slice(0, 2).split(""))
    .join("")
    .toUpperCase();
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded border border-[#c9d3e3] bg-white text-sm font-bold tracking-wide text-[var(--slide-ink)]">
      {letters || "?"}
    </div>
  );
}

function Head({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={`rounded-md bg-[var(--slide-head)] px-2 py-1.5 text-center text-[11px] font-semibold text-[var(--slide-ink)] ${wide ? "" : ""}`}>
      {children}
    </div>
  );
}

const ND = <span className="text-[var(--slide-muted)] italic">n.d.</span>;

/** Une ligne du bandeau « Financial partners » des discussion materials, telle qu'elle sortira. */
export function BannerPreview({ row }: { row: BannerRow }) {
  const p = row.profile;
  const ticket = ticketForSlide(p.equity_ticket_min_eur_m, p.equity_ticket_max_eur_m);
  const investments = p.latest_investments_france;
  const anyAi = investments.some((i) => investmentText(i).byAi);
  return (
    <figure aria-label="Aperçu du bandeau PowerPoint" className="scroll-thin overflow-x-auto rounded-lg bg-[var(--slide-bg)] p-3 text-[var(--slide-ink)] shadow-lg ring-1 ring-black/10">
      <div className="min-w-[640px]">
      <div className="grid grid-cols-[minmax(92px,1.1fr)_0.8fr_0.7fr_0.8fr_2.6fr] gap-1.5">
        <Head>Fund name</Head>
        <Head>Amount</Head>
        <Head>Vintage</Head>
        <Head>Ticket size</Head>
        <Head>
          Latest investments in <u>France</u>
        </Head>
      </div>
      <div className="mt-1.5 grid grid-cols-[minmax(92px,1.1fr)_0.8fr_0.7fr_0.8fr_2.6fr] items-center gap-1.5 rounded-md border border-[#d6dde8] bg-[#f7f9fc] py-2 text-[11px]">
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
        <ul className="space-y-1 pr-2">
          {investments.length === 0 && (
            <li className="text-[var(--slide-muted)]">
              • {p.holdings_collected ? "No investment identified" : "Portefeuille pas encore collecté pour ce fonds"}
            </li>
          )}
          {investments.map((inv) => {
            const { text } = investmentText(inv);
            return (
              <li key={inv.company_name} className="leading-snug">
                •{" "}
                <a href={inv.source_url} target="_blank" rel="noreferrer noopener" className="font-semibold text-[var(--slide-link)] underline">
                  {inv.company_name}
                </a>
                {inv.entry_year ? ` (${inv.entry_year})` : ""}
                {text ? ` - ${text}` : ""}
                {inv.country === null && <span className="ml-1 text-[9px] text-[var(--slide-muted)]">[pays non publié]</span>}
              </li>
            );
          })}
        </ul>
      </div>
      </div>
      <figcaption className="mt-2 flex flex-wrap gap-x-3 text-[10px] text-[var(--slide-muted)]">
        <span>Source : public information (sites des fonds)</span>
        {anyAi && <span>Descriptions résumées par l&apos;IA à partir du site du fonds</span>}
        <span>n.d. = non disponible dans la base · logo à collecter</span>
      </figcaption>
    </figure>
  );
}
