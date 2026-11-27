"use client";

import { useState } from "react";

import { type Investment, SECTOR_SHORT } from "@/lib/score";
import { type BannerRow, investmentText, ticketForSlide } from "@/lib/selection";

// Layout of the "Financial partners" slides of the discussion materials: rounded light-blue headers of
// equal height, rounded navy frame for the fund part, light-grey frame for the investments, square bullets.
// No source or link on the slide.
//
// One grid of six columns (slide proportions) is shared by the header row and the body row: each body
// frame is a subgrid spanning its columns, so every value sits exactly under its header box.
export const BANNER_COLUMNS = "178fr 108fr 102fr 137fr 449fr 449fr";
const GAP = 10;
const MAX_PER_COLUMN = 3;

const INK = "#12416b"; // slide navy
const HEAD_BG = "#d4edff";

/** Fund logo; falls back to the fund name when there is none or the image does not load. */
function Logo({ name, url, white }: { name: string; url?: string | null; white?: boolean }) {
  const [failed, setFailed] = useState(false);
  const short = name.replace(/\b(SAS|SA|SCA|S\.A\.)\b/g, "").replace(/\s+/g, " ").trim();
  if (url && !failed)
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={short}
        data-testid="banner-logo"
        onError={() => setFailed(true)}
        className="block h-auto max-h-[48px] w-auto max-w-full object-contain"
        style={white ? { filter: "brightness(0)" } : undefined}
      />
    );
  return <span className="block text-[13px] leading-tight font-bold break-words text-[#222]">{short}</span>;
}

function Head({ children }: { children: React.ReactNode }) {
  return (
    <div className="slide-r flex h-[34px] min-w-0 items-center justify-center px-2 text-center text-[12.5px] font-bold whitespace-nowrap" style={{ background: HEAD_BG, color: INK }}>
      <span>{children}</span>
    </div>
  );
}

function Bullets({ items, empty }: { items: Investment[]; empty: string }) {
  if (items.length === 0)
    return (
      <ul className="text-[11.5px] leading-[1.3]">
        <li className="flex gap-1.5">
          <span style={{ color: INK }}>▪</span>
          <span>{empty}</span>
        </li>
      </ul>
    );
  return (
    <ul className="space-y-1 text-[11.5px] leading-[1.3] text-[#222]">
      {items.slice(0, MAX_PER_COLUMN).map((inv) => {
        const { text } = investmentText(inv);
        return (
          <li key={inv.company_name} className="flex gap-1.5">
            <span style={{ color: INK }}>▪</span>
            <span className="min-w-0">
              <span className="font-bold underline" style={{ color: INK }}>
                {inv.company_name}
              </span>
              {inv.entry_year ? <span style={{ color: INK }}> ({inv.entry_year})</span> : null}
              {text ? ` - ${text}` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

const CELL = "min-w-0 px-2 text-center text-[12px]";

/** One banner row, as it will come out in the PowerPoint. */
export function BannerPreview({ row, sector }: { row: BannerRow; sector: string }) {
  const p = row.profile;
  const ticket = ticketForSlide(p.equity_ticket_min_eur_m, p.equity_ticket_max_eur_m);
  const empty = p.holdings_collected ? "No investment identified" : "Portfolio not yet collected";
  const sectorShort = SECTOR_SHORT[sector] ?? sector;
  return (
    <figure aria-label="PowerPoint banner preview" className="slide scroll-thin overflow-x-auto bg-white p-4" style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
      <div data-testid="banner-grid" className="grid min-w-[820px]" style={{ gridTemplateColumns: BANNER_COLUMNS, columnGap: GAP, rowGap: GAP }}>
        <Head>Fund name</Head>
        <Head>Amount</Head>
        <Head>Vintage</Head>
        <Head>Ticket size</Head>
        <Head>
          Investments in <u>{sectorShort}</u>
        </Head>
        <Head>
          Latest investments in <u>France</u>
        </Head>

        <div data-testid="banner-fund" className="slide-r col-span-4 grid min-h-[118px] grid-cols-subgrid items-center border bg-white py-2" style={{ borderColor: INK }}>
          <div className="relative flex min-w-0 items-center justify-center px-2">
            <Logo key={p.logo_url ?? row.fundId} name={row.fundName} url={p.logo_url} white={p.logo_white} />
            {row.starred && (
              <span aria-label="Interest expressed" className="absolute -top-5 left-1/2 -translate-x-1/2 text-lg text-[#7b2d6e]">
                ★
              </span>
            )}
          </div>
          <div className={`${CELL} text-[#222]`}>
            <span className="font-bold underline" style={{ color: INK }}>
              n.d.
            </span>
            {p.last_fund_name && <span className="block break-words">{p.last_fund_name}</span>}
          </div>
          <div className={`${CELL} text-[#222]`}>n.d.</div>
          <div className={`${CELL} font-bold`} style={{ color: INK }}>
            {ticket ?? "n.d."}
          </div>
        </div>
        <div className="slide-r col-span-2 grid min-h-[118px] grid-cols-subgrid items-center border bg-[#f7f7f7] py-2" style={{ borderColor: INK }}>
          <div data-testid="banner-sector" className="min-w-0 px-2">
            <Bullets items={p.sector_investments} empty={empty} />
          </div>
          <div data-testid="banner-france" className="min-w-0 px-2">
            <Bullets items={p.latest_investments_france} empty={empty} />
          </div>
        </div>
      </div>
    </figure>
  );
}
