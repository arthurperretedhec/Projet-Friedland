# AI usage

How AI tools were used in this project. The assistant adds entries as the work happens; the owner (student, team or
instructor) reviews them and completes the summary before hand-in.

## Summary (complete before hand-in)

- **Tools:** <e.g. Claude Code (model shown by `/model`), Cline with <model>, any chat assistant>
- **What AI did:** <code, tests, debugging, design proposals, documents>
- **What we decided ourselves:** <product scope, stack choice, acceptance criteria, ...>
- **How we checked AI output:** <tests, `npm run verify`, reviewer agents, hand checks of numbers, trying the app>
- **One example where the AI was wrong or misleading, and how we caught it:** <...>

## Log

| Date | Who asked | What the AI contributed | How it was checked | Accepted / changed / rejected |
|---|---|---|---|---|
| 2026-11-03 | owner (instructor) | Claude Code (Opus 5.5) built the App Creator toolkit (rules, skills, agents, launchers, scaffold, docs) via recorded steps in `runs/` ([index](runs/INDEX.md)) | toolkit checks (`npm run check-toolkit`, `npm run verify`) and reviews, per step record | accepted or changed per step, as recorded in `runs/` |
| 2026-11-03 | owner (instructor) | B16: Claude Code (Opus 5.5) repaired the B15a/B15b review findings: verify and demo no longer pass the root `.env` to child processes; dispatcher error/timeout handling, wider redaction (credentials, home paths) with counts and a redacted-text hash in RESULT.json, refusal to send prompts containing credentials; PowerShell/cmd hints; client guide size cap, overall timeout and port check; CI actions pinned to SHAs. Caught its own mistakes along the way: a home-path pattern that would have rewritten a quoted regex, and over-long lines in the guide code | throwaway tests under `.cache/` (redaction, dispatcher failure/timeout/success paths with a fake `claude`, launcher helpers), the guide's 11 example tests + ruff, `npm run check-toolkit`, full `npm run verify` exit 0 | pending owner review |
| 2026-11-17 | Constantin Sorel | Claude Code (Opus 5.5) ran the product interview and drafted `app/docs/product.md`, `architecture.md`, `acceptance.md`, `plan.md` from the owner's answers | owner read the summary and the drafts and corrected them before agreeing | changed, then accepted |
| 2026-11-17 | Constantin Sorel | AI mistake caught: the assistant first proposed keyword matching for sector proximity, then wrote in the drafts that phase 2 matching "will rely on NAF codes" although the owner had not decided it | owner rejected keyword matching (a car maker and a car-wrapping shop share keywords but not a value-chain position) and pointed out that NAF was not agreed; drafts corrected to "method not decided, NAF one option" | rejected / corrected |
| 2026-11-18 | Constantin Sorel | AI mistake caught: the assistant understood "database first, matching later" as "matching out of the MVP" and wrote it under "Explicitly not in the MVP" in the agreed `product.md` | owner clarified that both phases are delivered by 1 December; `product.md` and `plan.md` corrected (F6 added, slices 13-15 added) | corrected |
| 2026-11-18 | Constantin Sorel | Claude Code created the walking skeleton (`npm run create-app`, `npm run setup`), diagnosed the failing frontend build (Next.js 16.4.2 refused for a known vulnerability, confirmed with `npm audit`) and updated Next.js to 16.4.6 | `npm run verify` exit 0 (8/8 steps); screenshots at 1366 and 390 px looked at | accepted by the owner |
