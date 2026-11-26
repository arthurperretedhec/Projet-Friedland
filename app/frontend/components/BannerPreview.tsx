"use client";

import { useState } from "react";

import { type Investment, SECTOR_SHORT } from "@/lib/score";
import { type BannerRow, investmentText, ticketForSlide } from "@/lib/selection";

// Mise en page des slides « Financial partners » des discussion materials (Difagri, slides 75-79) :
// en-têtes bleu clair arrondis de même hauteur, cadre navy arrondi pour le fonds, cadre gris clair
// pour les investissements, puces carrées. Pas de source ni de lien sur la slide.
const LEFT = "grid grid-cols-[178fr_108fr_102fr_137fr] gap-[10px]";
const RIGHT = "grid grid-cols-2 gap-[10px]";
const OUTER = "grid grid-cols-[525fr_898fr] gap-[10px]";
const MAX_PER_COLUMN = 3;

const INK = "#12416b"; // bleu marine des slides
const HEAD_BG = "#d4edff";

/** Logo du fonds (collecte du 2026-11-26) ; à défaut, ou si l'image ne charge pas, son nom. */
function Logo({ name, url, white }: { name: string; url?: string | null; white?: boolean }) {
  const [failed, setFailed] = useState(false);
  const short = name.replace(/\b(SAS|SA|SCA|S\.A\.)\b/g, "").replace(/\s+/g, " ").trim();
  if (url && !failed)
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={short}
        onError={() => setFailed(true)}
        className="max-h-[56px] max-w-[150px] object-contain"
        style={white ? { filter: "brightness(0)" } : undefined}
      />
    );
  return <span className="text-[15px] leading-tight font-bold text-[#222]">{short}</span>;
}

function Head({ children }: { children: React.ReactNode }) {
  return (
    <div className="slide-r flex h-[34px] items-center justify-center px-2 text-center text-[12.5px] font-bold whitespace-nowrap" style={{ background: HEAD_BG, color: INK }}>
      {children}
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
            <span>
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

/** Une ligne du bandeau, telle qu'elle sortira dans le PowerPoint. */
export function BannerPreview({ row, sector }: { row: BannerRow; sector: string }) {
  const p = row.profile;
  const ticket = ticketForSlide(p.equity_ticket_min_eur_m, p.equity_ticket_max_eur_m);
  const empty = p.holdings_collected ? "No investment identified" : "Portefeuille pas encore collecté";
  const sectorShort = SECTOR_SHORT[sector] ?? sector;
  return (
    <figure aria-label="Aperçu du bandeau PowerPoint" className="slide scroll-thin overflow-x-auto bg-white p-4" style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
      <div className="min-w-[820px]">
        <div className={OUTER}>
          <div className={LEFT}>
            <Head>Fund name</Head>
            <Head>Amount</Head>
            <Head>Vintage</Head>
            <Head>Ticket size</Head>
          </div>
          <div className={RIGHT}>
            <Head>
              Investments in{" "}<u>{sectorShort}</u>
            </Head>
            <Head>
              Latest investments in{" "}<u>France</u>
            </Head>
          </div>
        </div>

        <div className={`${OUTER} mt-[10px]`}>
          <div className={`slide-r ${LEFT} min-h-[118px] items-center border bg-white`} style={{ borderColor: INK }}>
            <div className="relative flex items-center justify-center px-2 text-center">
              <Logo key={p.logo_url ?? row.fundId} name={row.fundName} url={p.logo_url} white={p.logo_white} />
              {row.starred && (
                <span aria-label="Intérêt exprimé" className="absolute -top-5 left-1/2 -translate-x-1/2 text-lg text-[#7b2d6e]">
                  ★
                </span>
              )}
            </div>
            <div className="text-center text-[12px] text-[#222]">
              <span className="font-bold underline" style={{ color: INK }}>
                n.d.
              </span>
              {p.last_fund_name && (
                <>
                  <br />
                  {p.last_fund_name}
                </>
              )}
            </div>
            <div className="text-center text-[12px] text-[#222]">n.d.</div>
            <div className="text-center text-[12px] font-bold" style={{ color: INK }}>
              {ticket ?? "n.d."}
            </div>
          </div>
          <div className={`slide-r ${RIGHT} min-h-[118px] items-center border bg-[#f7f7f7] px-3 py-2`} style={{ borderColor: INK }}>
            <div data-testid="banner-sector">
              <Bullets items={p.sector_investments} empty={empty} />
            </div>
            <div data-testid="banner-france">
              <Bullets items={p.latest_investments_france} empty={empty} />
            </div>
          </div>
        </div>
      </div>
    </figure>
  );
}
