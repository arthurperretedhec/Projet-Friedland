# Product: Friedland Buyer Screening

Status: agreed on 2026-11-17

## Problem and customers

- **Customer:** an M&A banker (analyst or associate) at an investment bank or advisory boutique running a
  sell-side mandate for a French company.
- **Problem today:** the list of potential financial buyers (private equity funds) is built by hand from the
  team's memory, fund websites and press (CFNews, Capital Finance). It takes hours, relevant funds are missed, and
  fund criteria (ticket size, target EV, sectors) are scattered across dozens of websites.
- **Success looks like:** the banker finds, in a few minutes, the French PE strategies whose published criteria fit
  the company for sale, ranked, with the explanation of each score and the source of every figure one click away.

## Phases (both delivered by 1 December 2026)

- **Phase 1 (first): the database.** 100 French PE strategies, their recent deals and current portfolio, every
  row sourced, browsable in the app. Built by the owner with the assistant, pushed to GitHub, then handed over
  to a teammate who continues with phase 2.
- **Phase 2 (second): matching and ranked output.** The banker describes the company for sale (activity
  description and other inputs to define) and gets a ranked list of strategies with the explanation of each
  score. Method, inputs, weights and rules are designed after the database exists. Known constraint: plain
  keyword matching on activity descriptions is rejected (it matches unrelated value-chain positions, e.g. a car
  maker and a car-wrapping shop). NAF codes are one option under consideration, not a decision.

## Main user journey (phase 1; the phase 2 journey is written when matching is designed)

1. The banker opens the app and sees the list of strategies and how many are in the base (by segment).
2. They filter by segment (small / mid / large), sector, stake (majority / minority) and deal type, or search by
   name.
3. They open a strategy and see its criteria, last fund, partner, recent deals and portfolio, each with its
   source link and collection date.
4. They take away a first longlist of funds to contact, with sources they can quote.

## Screens and visuals

Look: a table of figures with a detail page. Used on a phone: no (laptop first, must stay readable at 390 px).
Theme: kit default (dark default, light follows the system). Density: compact.
Visual references: none.

| Screen | Purpose | The user sees first | Cards / charts / tables | The user can | States |
|---|---|---|---|---|---|
| Strategies list | browse the base | two cards: "Strategies in base" (count) and "By segment" (small / mid / large counts); the table | table: management company, strategy, segment, equity ticket (EUR m), target EV (EUR m), stake, sectors, last fund (year, EUR m) | search by name, filter by segment, sector, stake, deal type; open a row; export the filtered list (CSV) | loading / "no strategy matches these filters" / "could not load data, is the backend running?" |
| Strategy detail | check one strategy | name, management company, segment, criteria | criteria block (incl. "other criteria" verbatim), last fund, partner name, tables of deals and portfolio companies; each block with source link, collected-on date, verified or not | open source links, go back to the list | loading / "strategy not found" / missing value shown as "not published" |

Agreed visuals: table only, plus the two count cards (by the owner's choice: option A).

## MVP features (must have)

| Id | Feature (what the user can do) | Why the customer needs it | Criteria |
|---|---|---|---|
| F1 | Browse the 100 strategies in a table with search and filters | replaces visiting dozens of fund websites | AC1, AC2, AC3 |
| F2 | Open a strategy and see its criteria, last fund, partner, deals and portfolio | the banker needs the detail to judge fit | AC4, AC5 |
| F3 | See the source and collection date of every figure | figures must be quotable and checkable; nothing invented | AC6 |
| F4 | The data is checked automatically (required fields, ranges, allowed values) every time `npm run verify` runs | a wrong figure in front of a client or jury is costly | AC7, AC8 |
| F5 | Export the filtered list to a CSV file that opens in Excel | the banker works on the longlist in Excel | AC9 |
| F6 | Describe the company for sale and get a ranked list of strategies with the explanation of each score (phase 2; method to design after the database) | this is the problem the product solves: who is likely to bid | score rules: `app/docs/scoring.md` (proposed 2026-11-20, group agreement pending); SC1, SC2 |

## Explicitly not in the MVP

- Strategic (industrial) buyers: the tool targets financial buyers only.
- Funds without activity in France: scope is France only.
- Automatic data refresh or scraping: data is collected and checked by hand, respecting site terms.
- Data from PitchBook, Capital IQ, Mergermarket (licence terms); manual cross-checks only.
- User accounts: single-user tool run locally.
- PDF export: CSV export (F5) is enough for the banker's work in Excel.
- Public online hosting: the demo runs on a laptop.
- Partner contact details (email, phone, LinkedIn): personal data not needed.

## Data and calculations

| Data | Source | Freshness | Offline demo data (fixtures) | Licence / terms checked? |
|---|---|---|---|---|
| Strategies (criteria, last fund, partner name) | fund websites, press releases, France Invest directory, AMF GECO | collected Nov 2026, date on every row | the CSV files themselves (the app never calls the web at runtime) | per source, before collecting [to confirm per site] |
| Deals (last 3 years) | fund websites, press releases, free press articles | collected Nov 2026 | same | same |
| Portfolio companies | fund websites ("portfolio" pages) | collected Nov 2026 | same | same |
| NAF codes of deal targets and portfolio companies (optional columns, kept in case the matching uses them) | `recherche-entreprises.api.gouv.fr` (free public API, no key) | collected once, date recorded | stored in the CSV files | [to confirm] |

| Number the app shows | Formula | Units | Source of inputs | Known-answer example |
|---|---|---|---|---|
| Segment of a strategy | from the target EV range midpoint: < 50 small, 50–500 mid, > 500 large | EUR m | `ev_min_eur_m`, `ev_max_eur_m` | CALC1–CALC4 |
| Counts on the list cards | number of strategies (in total, per segment) after filters | count | `strategies.csv` | CALC5 |

## Capabilities

| Capability | Needed? | Notes |
|---|---|---|
| Accounts / sign-in | no | single user, local |
| Per-user saved data | no | |
| File uploads | no | |
| Payments | no | |
| Background jobs / scheduled refresh | no | data collected by hand |
| Works offline (`npm run demo`) | yes | all data is in CSV files |
| Must be online for others | no | demo on a laptop |

## Team and constraints

- Mode: interactive; the owner (Constantin Sorel) approves each step.
- Experience: six finance students, first app for all members.
- Time available: until 1 December 2026 (submission and live demo); 14 days from 17 November.
- Budget: 0.
- Rules to respect: course "Programming and AI for Corporate Finance" (EDHEC Nice): real and free data, every
  member contributes code, AI use disclosed in `AI-USAGE.md`. The official project sheet (PDF) has not been seen
  [to confirm when available]. Data rules: no invented data, a source on every row, site terms and robots.txt
  respected, GDPR minimal approach (public professional data only).
