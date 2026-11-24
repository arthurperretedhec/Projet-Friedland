# Implementation plan

Deadline: 1 December 2026, 23:59 (submission on `main`); presentation 2 December. Phase 1 = the database (the
owner, with the assistant); then hand-over on GitHub to a teammate for phase 2 = matching and ranked output.
Both phases are delivered by the deadline. The day-by-day schedule and the split of roles between the six
members are still to plan.

## Slices

| # | Slice | Acceptance criteria | Skills | Status |
|---|---|---|---|---|
| 1 | Walking skeleton: `npm run create-app`, `npm run setup`, page shows "Backend status: OK", `npm run verify` passes | – | product-interview | done |
| 2 | Data format: empty CSV files with headers, reference lists, loader and data-quality tests (written first, on small test fixtures), data `README.md` (method, sources, GDPR note) | AC7, AC8, DQ1–DQ9, CALC1–CALC4 | manage-data, test-and-check | todo |
| 3 | Collection batch 1: 20 strategies (small cap), with source quotes | DQ1–DQ7 | – | todo |
| 4 | Collection batch 2: 20 strategies (small and mid cap) | DQ1–DQ7 | – | todo |
| 5 | Collection batch 3: 20 strategies (mid cap) | DQ1–DQ7 | – | todo |
| 6 | Collection batch 4: 20 strategies (mid and large cap) | DQ1–DQ7 | – | todo |
| 7 | Collection batch 5: 20 strategies (large cap); check the 35 / 40 / 25 split | DQ1–DQ7, AC1 | – | todo |
| 8 | Deals (last 3 years) and portfolio companies for the 100 strategies | DQ2, DQ6 | – | todo |
| 9 | Optional: NAF codes for deal targets and portfolio companies via the public API, only if phase 2 needs them | DQ8 | integrate-api | optional |
| 10 | API: `/api/strategies`, `/api/strategies/{id}`, `/api/reference` | CALC5, E3 | build-feature | todo |
| 11 | Strategies list screen with cards, search, filters and CSV export | AC1–AC3, AC9, E1, V1, V2 | build-feature, design-interface | todo |
| 12 | Strategy detail screen with sources | AC4–AC6, E2, E4, V3 | build-feature, design-interface | todo |
| – | Team verification of every row (`verified_by`, `verified_on`), in parallel with slices 4–12 | – | – | todo |
| 13 | Hand-over: README section "how to continue" (setup, data files, checks), push, pull request reviewed by a teammate | – | write-docs, git-collaboration | todo |
| 14 | Phase 2 design: matching method, inputs, weights, explanation; update product.md (F6), acceptance.md (criteria and hand-worked score examples) | F6 | product-interview (update), plan-architecture | in progress: score rules proposed in `scoring.md` (Arthur, 2026-11-20), group agreement pending |
| 15+ | Phase 2 build: score logic with tests, API endpoint, input form and ranked results screen (slices defined in step 14) | F6 | build-feature, test-and-check | in progress: score engine with tests on `arthur/scoring-engine`; API endpoint, input form and results screen todo |

## Progress log

| Date | Slice | What changed | Checks run and results (command, exit code) | Open problems |
|---|---|---|---|---|
| 2026-11-17 | – | Product interview; drafts of the four documents | `npm ci` (exit 0); `npm run setup` in template mode: Node 26.13.0, Python 3.12.4 found (exit 0) | documents not yet agreed |
| 2026-11-18 | 1 | Documents agreed (2026-11-17); `npm run create-app`; `npm run setup`; Next.js 16.4.2 -> 16.4.6 after `next build` refused the vulnerable version | `npm run verify`: first run 1 step failed (frontend build, security refusal); after the update all 8 steps passed (exit 0); Playwright screenshots at 1366 and 390 px looked at by the assistant: "Backend status: OK" | `npm audit` still lists dev-only tooling findings (minimatch, picomatch), not shipped in the app |
| 2026-11-20 | 15+ | Score engine (branch `arthur/scoring-engine`, Arthur Perret): configurable module `app/backend/app/logic/scoring/` (4 eliminatory + 4 graded criteria, weights 35/35/20/10 in `config.py`), synthetic test data, `app/docs/scoring.md`, SC1–SC2 in acceptance.md. No API route or screen yet | backend pytest: 86 passed (84 score + 2 health); ruff: all checks passed; `npm run verify`: 8/8 steps passed (exit 0) | criteria and weights to be agreed by the group; fund and operation formats to check with Simon/Alexandre and Constantin; reference lists copied from architecture.md until `reference.py` exists |
| 2026-11-20 | 15+ | Review of the score engine (`review-changes`: code-reviewer, test-reviewer, 2 rounds). Round 1: 0 blocker, 1 major (float error at exact G2/G3 boundaries, verified), 9 minor. Fixed: the major (tolerance comparisons), half-up rounding, one EV bound listed in `missing_data` with a warning (Arthur's decision), config checks, implausible fund year refused (1980–2100), code robustness, formatting, docs (plan, product F6, architecture decision row, scoring.md). 43 new tests in `test_scoring_review_fixes.py`; existing tests unchanged. Deferred: reference lists (slice 2). Round 2: 0 blocker, 0 major, minors listed below | backend pytest: 129 passed, then 132 after the round-2 minors; ruff check and format: clean; `npm run verify`: 8/8 steps passed (exit 0); SC1 67.5 and SC2 27.5 unchanged | see "Known problems" |

## Known problems and open questions

- Course sheet (`final_project.pdf`) received 2026-11-18: business plan PDF (8-12 pages) and slides must also be
  in the repository by the deadline; individual contribution is graded only from each member's own commits, pull
  requests and reviews.
- Phase 2 matching method: proposed in `app/docs/scoring.md` (2026-11-20): sector matched by
  reference-list category (no keywords, NAF not used), eliminatory deal type / ticket / stake, graded
  sector / EV / fund size / investment period. To be agreed by the group.
- Paid sources (CFNews, Capital Finance) are not readable by the assistant: deals will have gaps.
- Terms of use to check per source site before collecting.
- Each member must contribute code: the split of slices between members is still to plan.

Score engine review findings still open (2026-11-20):

| Finding | Severity | Status | Why still open | Decided by | Next step |
|---|---|---|---|---|---|
| code-reviewer R1 #10: reference lists copied in `scoring/config.py` | minor | verified | deferred to slice 2 (`reference.py` does not exist yet) | Arthur, 2026-11-20 | import from `app/logic/reference.py` in slice 2 |
| code-reviewer R2 #2: both EV bounds missing counted as one `missing_data` entry (`"ev_min_eur_m, ev_max_eur_m"`) | minor | verified | accepted: the EV criterion is what is missing; documented in scoring.md; existing tests unchanged | Arthur, 2026-11-20 | none |
| code-reviewer R2 #4: architecture.md decision log not in date order | minor | verified | cosmetic; the 2026-11-17 row was already out of order | Arthur, 2026-11-20 (not in scope) | reorder when the group edits the log |

Fixed after round 2 (2026-11-20, approved by Arthur): rounding from already-rounded points documented
in scoring.md (R2 code #3); new test row 2.25 / 22.4 → partial, comments of three control rows
corrected, tighter `match` (R2 tests #1, #2, #5); SC3 (82.5) and SC4 (60.3) added to acceptance.md
(R2 tests #3); warning when the fund year is after the analysis date, with tests (R2 tests #4).
pytest 132 passed.
