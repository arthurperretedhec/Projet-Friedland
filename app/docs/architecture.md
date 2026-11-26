# Architecture

Status: agreed on 2026-11-17

## Stack

- **Stack:** standard (Next.js + React + TypeScript + Tailwind CSS v4; FastAPI + pydantic; storage: CSV files;
  pytest, Vitest, Playwright). No charts in phase 1.
- **Why:** it is the course kit, so `npm run setup / dev / demo / verify` work as provided; the data work and
  later the matching are Python (the team's analysis language); CSV files open in Excel for the team's checks.
- **Alternative considered:** Streamlit (Python only, simpler). Rejected on 2026-11-17: the kit's commands,
  tests and agents are built for Next.js + FastAPI.
- **Folders** (from `app-creator.config.json`): frontend `app/frontend`, backend `app/backend`, docs `app/docs`.

## Parts of the application and their boundaries

| Part | Folder / file | Responsibility | Must not |
|---|---|---|---|
| Interface (UI) | `app/frontend/app/`, `app/frontend/components/` | list and detail screens, filters, loading/empty/error states | compute segments or counts; call third-party sites |
| Frontend helpers | `app/frontend/lib/` | API client for `/api/*`, typed responses, number formatting | business rules |
| API (routes) | `app/backend/app/main.py`, `app/backend/app/api/` | validate query parameters, call logic, return typed responses | read CSV files directly, contain rules |
| Logic | `app/backend/app/logic/` | segment rule, filtering, counts, data checks (pure functions) | read files or call the network |
| Data access | `app/backend/app/data/` | load and parse the CSV files into typed rows | contain business rules |
| Data files | `app/backend/data/` | Public investor CSV snapshot and provenance tables | be edited without updating `collected_on` and the source |
| Collection scripts | `app/backend/scripts/` | one-off helpers, e.g. NAF lookup through the public API | run when the app runs |
| Tests | `app/backend/tests/`, `app/frontend/**/*.test.ts(x)`, `app/frontend/e2e/` | logic, data checks on the real CSV files, journeys | call live services |

## API

| Method and path | Purpose | Request | Response (model) | Errors |
|---|---|---|---|---|
| `GET /api/health` | backend is up | – | `{status, app}` | – |
| `GET /api/strategies` | list with filters | `q`, `segment`, `sector`, `stake`, `deal_type` (all optional) | `{items: StrategySummary[], counts: {total, small, mid, large}}` | 422 invalid filter value |
| `GET /api/strategies/{strategy_id}` | one strategy with its deals and portfolio | path id | `StrategyDetail` | 404 `strategy_not_found` |
| `GET /api/reference` | allowed values for filters | – | `{segments, sectors, deal_types, stakes}` | – |
| `GET /api/strategies/export.csv` | CSV export of the filtered list | same filters as `/api/strategies` | `text/csv` file (UTF-8 with BOM so Excel shows accents) | 422 invalid filter value |
| `POST /api/score` | rank management companies for an operation (score engine, criteria v2) | JSON body `ScoreRequest`: `deal_type`, `sector`, `equity_ticket_eur_m`, `stake_sought`, `enterprise_value_eur_m` (required), `company_name`, `operation_id`, `analysis_date` (optional) | `ScoreResponse`: `{operation_id, company_name, analysis_date, config_version, message, counts, companies: CompanyResult[], excluded}` (details in `scoring.md`) | 422 `invalid_request` with French messages per field |

Error envelope: `{"error": {"code": "...", "message": "...", "details": ...}}`. 100 strategies: no pagination.

## Data and storage

- FastAPI loads the public CSV snapshot from `app/backend/data/` at startup via `app.data.investors`.
  It exposes a read-only in-memory catalog at `app.state.investor_data`. Imports are UTF-8 with an
  optional BOM, comma-separated, and use semicolons for multi-value cells. IDs are read as-is.
- Blank cells become `None` (JSON `null` at an API boundary). Monetary fields are positive decimals
  in EUR millions, with ordered bounds when both exist. The catalog keeps source text and URLs as supplied.
- This snapshot replaces the planned flat storage schema. The API routes above are still planned.
  Research tables `entity_aliases.csv`, `sector_dictionary.csv` and `unresolved_entities.csv` remain
  available in the import for review. Private transaction files are outside the runtime loader.

| File | Keys and application fields |
|---|---|
| `funds.csv` | Unique `fund_id`, management company name and research coverage |
| `strategies.csv` | Unique `strategy_id`, parent `fund_id`, original `strategy_name`, bucket and sector summaries, screening lane, stake and deal tags, `equity_ticket_*_eur_m`, `target_ev_*_eur_m`, `target_ebitda_min_eur_m`, fund name and source fields |
| `buckets.csv`, `strategy_buckets.csv` | Unique `bucket_id`; one primary and zero or more secondary memberships per strategy, with classification quality |
| `sectors.csv`, `strategy_sectors.csv` | Unique `sector_code`; strategy-to-sector rows retain raw tags, subsectors, polarity and mapping confidence. Several rows can describe the same code. |
| `strategy_sector_summary.csv` | Unique `strategy_id`, parent `fund_id`, sector scope and summary screening rules |
| `financial_criteria.csv`, `investment_amounts.csv` | Many rows per strategy with metric or amount type, EUR m bounds and supporting source. Unspecified investment amounts retain their own type. |
| `deals.csv`, `portfolio.csv` | Public records link to exactly one of `strategy_id` or `fund_id`. Fund-level rows can identify a `reported_vehicle` outside the tracked strategy catalog. Deals have a unique `deal_id`. The loader exposes fund-level portfolio rows through `fund_portfolio`. |
| `source_log.csv` | Unique `source_id`; strategy and deal references use IDs, portfolio references use a strategy ID or `strategy_id|company_name`, fund-level portfolio references use `fund_id|company_name`, and management-company references use the published company name. `source_paraphrase` stores editorial summaries. `evidence_status` separates `SOURCE_REFERENCE` from `RESEARCH_LEAD` at load time. References retain provenance and can require further verification. |

The snapshot has 10 normalized sector codes and 8 bucket IDs. Strategy stake and deal tags, and public
transaction role and direction values, differ from the legacy reference lists. The snapshot also omits
strategy `segment`, `last_fund_year`, `last_fund_size_eur_m`, `partner_name`, and a strategy-level
`collected_on` column. Source dates are available where supplied in `source_log.csv` and child tables.
Verification columns from the original design are absent. These gaps matter before implementing the
planned browse and detail routes.

**Scoring on the real base (2026-11-25).** The score engine reads the base through
`app.logic.scoring.real_data`: `score_operation_on_base(operation, data)` receives the base already
loaded by `load_investors` (once, at startup or in a test; logic reads no file), translates each of the
153 strategies into the engine's `Fund` model with the tables of `app/logic/reference.py`, and calls the
engine. `reference.py` is the single source of the engine's value lists (sectors, deal types, stakes)
and of the translations from the base (rules validated by Arthur on 2026-11-25, detailed in
`scoring.md`): a generic `buyout` covers both primary and secondary LBO; tags outside private equity
give the fund value `non_pe`; vague tags are ignored; generalists keep their marker; an explicit sector
exclusion stays unknown because the engine cannot express it. `app.logic.investor_scoring.scoring_input`
and its `LEGACY_*` tables are superseded and no longer used by the engine (left unchanged; Simon to
remove them or point them to `reference.py`). Subsector exclusions, bucket membership and screening
lanes stay available in the catalog for the eventual eligibility rules. After strategy scoring,
`best_strategy_per_management_company` passes the engine's best-first eligible ranking to
`buyer_longlist`. It keeps the first result for each `fund_id`, including the winning `strategy_id` and
its score explanation. The full strategy ranking remains available to callers.

**Original selection target for the 100 strategies** (agreed 2026-11-17): management company French or with a Paris office;
member of France Invest or listed in the AMF GECO database; last fund raised in 2018 or later; active in LBO or
growth investments in French companies. Target split: 35 small, 40 mid, 25 large.

### Public snapshot preparation

The release snapshot keeps source URLs and omits verbatim source excerpts. Financial facts previously
present only in quote fields are preserved as attributed paraphrases where supported by the original
record. The quotes stay blank. The two Infocession revenue ranges and six derived strategy-sector links
were withheld pending independent corroboration. The strategy IDs and historical classifications remain,
with the rows marked for historical review and the directory sources listed only as research leads.
CFNEWS profiles are also research leads. Research leads are accessible separately from source references.

The Dangel deal and portfolio record retain their original deal ID and company name. They point to
Capital Grand Est via `fund_id` and record ReBest as the reported vehicle. ReBest has no strategy ID
in this snapshot. Four public deal announcements or adviser pages have matching provenance entries.

## External services

| Service | Used for | Setting names | Offline / demo behaviour | Free tier / cost | Terms checked |
|---|---|---|---|---|---|
| `recherche-entreprises.api.gouv.fr` | NAF code of deal targets and portfolio companies, during collection only | none (no key) | not called by the app; results stored in the CSV | free | [to confirm] |

## Caching and background work

None. The app reads the CSV files at startup.

## Security and privacy

- Personal data stored: `partner_name` only (first and last name of the partner in charge, as published on the
  fund's own team page, cited). No email, phone, LinkedIn or private information. Purpose: identify who leads a
  strategy. Removal on request. The repository is public (needed for branch protection on GitHub Free), so these
  names are visible on GitHub; accepted by the owner on 2026-11-17.
- Who can see what: single user, local.
- Secrets: none needed.

## Run, test, preview (root commands)

- Python: 3.12.4 (`D:\Anaconda\python.exe` on the owner's machine, passed as `APP_PYTHON`) in `app/backend/.venv`
- Install: `npm ci` (once), then `npm run setup`
- Run: `npm run dev`, then open http://127.0.0.1:3000
- Offline demo: `npm run demo`
- Check everything: `npm run verify`

## Decision log

| Date | Decision | Reason | Basis |
|---|---|---|---|
| 2026-11-17 | Keep the course kit (Next.js + FastAPI), drop Streamlit | kit commands and tests work as provided | owner |
| 2026-11-17 | Phase 1 = database; matching designed later | data is the foundation; owner's priority | owner |
| 2026-11-17 | 100 strategies, 35 small / 40 mid / 25 large, selection rule above | realistic size, covers the market | owner |
| 2026-11-17 | The assistant collects all data; the team verifies afterwards (`verified_by`) | owner's choice; verification is recorded per row | owner |
| 2026-11-17 | Phase 2 will not rely on plain keyword matching; method still open (NAF codes one option). NAF columns kept optional in the data | keywords match unrelated value-chain positions (car maker vs car wrapping) | owner |
| 2026-11-17 | Segment rule (EV midpoint, else fund's own wording), sector list and CSV export (F5) agreed | | owner |
| 2026-11-17 | Store `partner_name` (name only); repository stays public | owner wants the contact; GitHub Free needs a public repo for branch protection | owner |
| 2026-11-17 | Add `other_criteria` (verbatim) | any published criterion is useful even if not systematic | owner |
| 2026-11-18 | Correction: matching and ranked output (F6) are in the MVP delivered by 1 December, built after the database; the database is handed over on GitHub to a teammate for phase 2 | the agreed documents had wrongly put matching under "not in the MVP" | owner |
| 2026-11-18 | Next.js and eslint-config-next 16.4.2 -> 16.4.6 in `app/frontend` (scaffold left unchanged) | 16.4.2 has a known moderate vulnerability (GHSA-mfr8-8qww-v76h, GHSA-vc7v-qv4w-wrv8) and `next build` refuses to run; 16.4.6 is the patched release of the same series | owner |
| 2026-11-20 | Score engine as a separate pure module `app/backend/app/logic/scoring/` (config, models, engine), entry point `score_operation(operation, funds)`; criteria, weights (35/35/20/10) and thresholds in `config.py`; sector matched by reference-list category; stage measured by EV, investment period approximated by `last_fund_year`; no geography criterion. Details: `scoring.md` | deterministic, configurable while the group has not agreed the criteria; reuses `strategies.csv` columns; no new library | Arthur Perret (proposal, group agreement pending) |
| 2026-11-25 | Score engine connected to the real base: `app/logic/reference.py` becomes the single source of value lists and of the translations from the base (deal types: union of covered types, `buyout` = primary + secondary LBO, non-PE tags → `non_pe`, vague tags ignored; sectors: 10 codes mapped, REAL_ESTATE_HOSPITALITY → construction_real_estate as an approximation; stakes: co-investor and reference_shareholder → minority); `app/logic/scoring/real_data.py` receives the loaded base. Criteria and weights unchanged (35/35/20/10); G3 and G4 have no data (153/153 missing) and give 15 neutral points | the base uses its own vocabulary; one shared table avoids divergent copies; logic stays free of file access | Arthur Perret (Simon's files unchanged) |
| 2026-11-25 | Criteria v2 become the engine's default configuration (`SCORING_CONFIG`; v1 kept as `SCORING_CONFIG_V1`): graded sector 40, fund type 25 (`primary_bucket`/`secondary_buckets`), lead capacity 15 (`buyer_role`), geography 10 (`geography_tags`), transaction speciality 10 (`transaction_modifiers`); EV, fund size and fund age disabled (code kept); eliminatory E1–E4 unchanged; `family_succession` covers primary LBO, `acquisition` stays vague; tie-break: missing data, then source quality (`classification_basis`), then `strategy_id`; confidence index per result; `real_data.rank_management_companies` returns one line per management company for the demo | the v1 size criteria had no or almost no data in the base (EV 22/153, fund size and year 0/153) and produced large ties | Arthur Perret (proposal D, to be agreed by the group; Simon's files unchanged) |
| 2026-11-25 | `POST /api/score` in `app/backend/app/api/score.py`: validates the operation (allowed values, positive amounts, unknown fields refused), calls the engine on the base translated once at startup (`app.state.scoring_base`), returns the ranking by management company and the excluded strategies; validation errors use the common envelope with French messages (`app/api/errors.py`, registered for the whole app) | the UI needs one call that returns everything it displays; loading once avoids translating 153 strategies per request | Arthur Perret |
| 2026-11-17 | Scope and architecture agreed (product.md, architecture.md, acceptance.md, plan.md) | documents reviewed after the product interview | owner (Constantin Sorel) |
| 2026-11-26 | Screening screen on the home page (`components/ScreeningApp.tsx`, `ScreeningForm.tsx`, `RankingResults.tsx`; pure logic in `lib/score.ts`). `POST /api/score` adds `profile` to each ranked company: published fields of its best strategy (website, source URL, last fund, ticket and EV ranges), read from the loaded base, no calculation. Display options and tiers are applied in the browser on the engine's ranking and never change ranks; tier thresholds 80 / 60 are a proposal | the banker must see the published ticket and the sources next to the score to act on the list; one call keeps the screen simple | Alexandre Robin (tiers to be agreed by the group) |
| 2026-11-26 | `app/backend/data/portfolio_extended.csv` (separate from Simon's `portfolio.csv`, unchanged), read by `app/data/portfolio_extended.py` at startup into `ScoringBase.holdings`; display only, never used by the score engine. "Latest investments in France" rule: equity only, country France or not published, newest first, else source-page order, 3 shown. Short descriptions in the slide format are AI summaries flagged in the file. Fund selection and stars live in the browser (no storage) until the PowerPoint export exists | the banner needs holdings that the base did not have; keeping a separate file avoids touching Simon's data and keeps the engine unchanged | Alexandre Robin |
| 2026-11-24 | Load the normalized investor CSV snapshot and project legacy scoring inputs separately | Preserve source IDs, relationships and financial provenance while keeping the scoring branch independent | owner import and integration request |
