# Fund holdings collection: handoff (batch 2 not finished)

Status on 2026-11-27 (Alexandre Robin, with Claude). Batch 1 (10 funds, 174 holdings) is merged (PR #8).
Batch 2 was researched but **nothing from batch 2 is in `app/backend/data/portfolio_extended.csv` yet**.
This note says what is left and how to finish it.

## How a batch is done

1. For each fund, open its portfolio page (URLs below) and keep only the companies **still held**
   (leave out exits / "realised" / "cédée").
2. Add one row per company to `app/backend/data/portfolio_extended.csv` (same columns as the existing rows):
   `fund_id`, `management_company` exactly as in `data/funds.csv`, `company_name`, `entry_year`, `country`,
   `company_description` (text published by the fund), `description_short` (one English line written for the
   slide, then `description_short_by = ai_summary`), `sector` (one of the codes below, then
   `sector_by = ai_classified`), `sector_published` (the fund's own label, if any), `source_url`,
   `status = held`, `instrument = equity`, `collected_on`.
3. Rules:
   - `country`: only if the fund publishes it, otherwise the region, otherwise blank. Blank means
     "not published" and the company **can appear under "Latest in France"**, so prefer a region when known.
   - Never add a company whose name is on the owner's confidential list (ask Alexandre).
4. Add the new `fund_id`s to the `collected` list in
   `app/backend/tests/test_portfolio_extended.py::test_shipped_file_loads_and_every_ai_summary_is_flagged`.
5. Run the checks (backend `pytest` + `ruff check`, frontend `vitest`, `eslint`, `tsc`, Playwright), restart
   `npm run dev` (the backend reads the CSV at start-up), look at a few banners, update `plan.md` and
   `AI-USAGE.md`, commit, one PR per batch.

Sector codes: `TECH_SOFTWARE`, `HEALTHCARE`, `BUSINESS_SERVICES`, `INDUSTRIALS`, `CONSUMER`, `FOOD_AGRI`,
`FINANCIAL_SERVICES`, `ENERGY_ENV`, `INFRA_TRANSPORT`, `REAL_ESTATE_HOSPITALITY` (building works and real estate
go here: the app's "Construction & real estate" maps to it).

## Batch 2: what is left

### Data found, rows still to write (step 2 above)

| fund_id | Fund | Held | Where the data is | Notes |
|---|---|---|---|---|
| fund-016 | AREV Partners | 4 | https://arevpartners.com/fr/investissements/ (one page per company: date, description) | NexInlife 2026, Laboratoire Ysonut 2024, Groupe Pinard 2024, Komposite 2024; all France. Mozaik was sold in Nov 2026: leave out. |
| fund-022 | B & Capital | 12 | https://b-and-capital.com/en/investments/ ("Held" block: name, year, sector, activity) | EDS Emballage 2026 … Galaed 2020. Country not published. |
| fund-021 | Azulis Capital | 12 | https://www.azuliscapital.fr/participations/ (one page per company: acquisition date, country, sector, status) | All "Actif", mostly France. |
| fund-019 | Artemis | 11 | https://www.groupeartemis.com/en/our-investments | Family holding (Kering, Christie's, Ponant, CAA…). Entry years are in the texts, not in a field. |
| fund-020 | Astorg | 35 | https://www.astorg.com/our-portfolio (click "Load more" until the end; each page says IN PORTFOLIO + "YYYY ENTRY INTO PORTFOLIO" + head office) | 77 companies in total, 36 in portfolio; Normec appears twice (keep one). |
| fund-025 | BTP Capital Investissement | 33 | https://www.btpki.fr/nos-participations (each "Voir plus" opens a pop-up: sector, entry year, French département, description) | All France. Building works → `REAL_ESTATE_HOSPITALITY`; materials makers → `INDUSTRIALS`; software (Keepeo, Teamoty, Atline) → `TECH_SOFTWARE`. |
| fund-041 | Ekkio Capital | 17 | https://ekkio.com/investissements, filter "Entreprise en portefeuille" (17 companies); one page per company | Do **not** trust the pages alone: Ivalis and Paris Experience Group have no exit date but are not in the filter. |
| fund-035 | Chevrillon & Associés | 7 | https://www.groupechevrillon.com/investissements/ ("Participations actuelles") | No years on the list. One current holding is on the confidential list: leave it out (8 listed, 7 to add). |

### Data still to fetch

| fund_id | Fund | Where | What is missing |
|---|---|---|---|
| fund-044 | EMZ Partners | https://emzpartners.com/portfolio/ | 47 companies marked "Portfolio" with an activity; entry year and country are on each company page (`emzpartners.com/emz/<name>/`), not fetched yet. Without them the rows have no year. |
| fund-034 | Chequers Capital | https://www.chequerscapital.com/portefeuille/ | 19 companies with sector, year and country on the list; a one-line description is on each company page (`/projetsportefeuilles/<name>/`), not fetched yet. |

### Funds checked and skipped (no usable list on the website)

Access Capital Partners (names hidden), Alba Infra (infrastructure assets, not companies), Argos and Adaxtra
(sites down or empty), BlackFin (logos only), Capital Croissance (only 11 of its companies have a page, not the
latest ones), Capital Grand Est (logos only), Elaia (12 featured start-ups only), Cathay (page in Chinese, no
list), Aquiti (names hidden). They need another source (press, CFNews, annual reports) or can stay empty.

## After batch 2

The other funds with a website are still to do, in `fund_id` order from fund-045 (and fund-024 Bpifrance, fund-026 Butler,
fund-028 to fund-033, fund-036 to fund-040 that were not looked at in detail).
