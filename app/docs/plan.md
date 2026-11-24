# Implementation plan

Deadline: 1 December 2026, 23:59 (submission on `main`); presentation 2 December. Phase 1 = the database (the
owner, with the assistant); then hand-over on GitHub to a teammate for phase 2 = matching and ranked output.
Both phases are delivered by the deadline. The day-by-day schedule and the split of roles between the six
members are still to plan.

## Slices

| # | Slice | Acceptance criteria | Skills | Status |
|---|---|---|---|---|
| 1 | Walking skeleton: `npm run create-app`, `npm run setup`, page shows "Backend status: OK", `npm run verify` passes | – | product-interview | done |
| 2 | Normalized investor CSV import: startup loader, relationship and amount validation, and standalone scoring adapter | DQ2, DQ3 and import checks | manage-data, test-and-check | implemented |
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
| 14 | Phase 2 design: matching method, inputs, weights, explanation; update product.md (F6), acceptance.md (criteria and hand-worked score examples) | F6 | product-interview (update), plan-architecture | todo |
| 15+ | Phase 2 build: score logic with tests, API endpoint, input form and ranked results screen (slices defined in step 14) | F6 | build-feature, test-and-check | todo |

## Progress log

| Date | Slice | What changed | Checks run and results (command, exit code) | Open problems |
|---|---|---|---|---|
| 2026-11-17 | – | Product interview; drafts of the four documents | `npm ci` (exit 0); `npm run setup` in template mode: Node 26.13.0, Python 3.12.4 found (exit 0) | documents not yet agreed |
| 2026-11-18 | 1 | Documents agreed (2026-11-17); `npm run create-app`; `npm run setup`; Next.js 16.4.2 -> 16.4.6 after `next build` refused the vulnerable version | `npm run verify`: first run 1 step failed (frontend build, security refusal); after the update all 8 steps passed (exit 0); Playwright screenshots at 1366 and 390 px looked at by the assistant: "Backend status: OK" | `npm audit` still lists dev-only tooling findings (minimatch, picomatch), not shipped in the app |
| 2026-11-24 | 2 | Loaded the 112-fund / 153-strategy import at startup and added a scoring adapter and fund-level longlist helper | Core validator passed; `npm run verify` passed (10 backend tests, 7 frontend tests and 2 health-page browser checks at 1366 and 390 px); all 153 strategies accepted by the separate scoring model | Source coverage, legacy vocabulary alignment and scoring/API wiring remain open |

| 2026-11-24 | 2 review | Code, test and security reviews found two sector projection defects. Preserved generalist preferences and projected explicit exclusions as unknown. | Both regressions reproduced before the fix; `npm run verify` then passed all 8 stages (12 backend tests, 7 frontend tests, 2 Chromium smoke checks). The separate scoring checkout passed 132 tests. | Include the existing local-data ignore rule in the PR. Source redistribution rights and production eligibility remain open. |

| 2026-11-24 | 2 publication | Prepared the clean investor snapshot from the main baseline. Preserved the original universe and financial criteria except unsupported Infocession bounds. Separated research leads, retained sourced paraphrases, and corrected ReBest attribution. | Dataset validator and unittest passed; `npm run verify` passed all eight stages with 15 backend tests, seven frontend tests and two browser checks; all 153 strategies validated against the separate scoring model | Original branch remains separate. Scoring production wiring and source publication decisions remain open. |

## Known problems and open questions

- Course sheet (`final_project.pdf`) received 2026-11-18: business plan PDF (8-12 pages) and slides must also be
  in the repository by the deadline; individual contribution is graded only from each member's own commits, pull
  requests and reviews.
- Phase 2 matching method not decided (keywords rejected; NAF codes one option).
- Paid sources (CFNews, Capital Finance) are not readable by the assistant: deals will have gaps.
- Terms of use to check per source site before collecting.
- Each member must contribute code: the split of slices between members is still to plan.
