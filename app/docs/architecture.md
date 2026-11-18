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
| Data files | `app/backend/data/` | `strategies.csv`, `deals.csv`, `portfolio.csv`, `README.md` (sources, method) | be edited without updating `collected_on` and the source |
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

Error envelope: `{"error": {"code": "...", "message": "...", "details": ...}}`. 100 strategies: no pagination.

## Data and storage

- Storage: CSV files in `app/backend/data/`, read-only at runtime, because the data is collected by hand, small
  (about 100 strategies, a few hundred deals and portfolio rows) and must be readable in Excel. UTF-8, comma
  separator, one header row. Multi-value cells use `; ` (semicolon + space).
- Schema changes: add a column in the CSV, the loader, the checks and this table in the same change.
- Every row of every file carries: `source_url`, `other_source_urls` (optional, `; `-separated),
  `source_quote` (the exact passage(s) supporting the row), `collected_on` (YYYY-MM-DD), `verified_by`
  (team member who checked the row against the source; empty until checked), `verified_on`.
- Missing information stays empty. Never filled from memory or estimated.

| File | Fields (besides the source fields above) |
|---|---|
| `strategies.csv` | `strategy_id` (slug, unique), `management_company`, `strategy_name`, `segment` (small / mid / large), `ticket_min_eur_m`, `ticket_max_eur_m`, `ev_min_eur_m`, `ev_max_eur_m`, `ebitda_min_eur_m`, `stake` (majority / minority / both), `deal_types`, `sectors`, `geography`, `other_criteria` (verbatim text of any other published criterion), `last_fund_name`, `last_fund_size_eur_m`, `last_fund_year`, `partner_name` (first and last name only), `website` |
| `deals.csv` | `deal_id` (unique), `strategy_id` (lead strategy in our base), `target_name`, `target_naf_code`, `target_description`, `deal_date` (YYYY-MM or YYYY-MM-DD), `ev_eur_m` (only if published), `deal_type`, `role` (lead / co-investor), `co_investors` (text), `direction` (entry / exit) |
| `portfolio.csv` | `strategy_id`, `company_name`, `company_naf_code`, `company_description`, `sector`, `entry_year` |

Reference lists (in `app/backend/app/logic/reference.py`):

- `segment`: `small`, `mid`, `large`.
- `deal_types`: `primary_lbo`, `secondary_lbo`, `build_up`, `growth`, `carve_out`.
- `stake`: `majority`, `minority`, `both`.
- `sectors` (agreed 2026-11-17): `software_it`, `healthcare`, `business_services`, `industrials`, `consumer_retail`,
  `food_beverage`, `financial_services`, `education`, `energy_environment`, `construction_real_estate`,
  `transport_logistics`, `media_telecom`, `agriculture`, `generalist`.

**Selection rule for the 100 strategies** (agreed 2026-11-17): management company French or with a Paris office;
member of France Invest or listed in the AMF GECO database; last fund raised in 2018 or later; active in LBO or
growth investments in French companies. Target split: 35 small, 40 mid, 25 large.

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
| 2026-11-17 | Scope and architecture agreed (product.md, architecture.md, acceptance.md, plan.md) | documents reviewed after the product interview | owner (Constantin Sorel) |
