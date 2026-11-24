# Acceptance criteria

## Main user journey

| Id | Feature | Given | When | Then | Status |
|---|---|---|---|---|---|
| AC1 | F1 | the data files with 100 strategies | the banker opens the home page | the table lists 100 rows and the cards show "100 strategies" and the counts per segment (target 35 / 40 / 25) | open |
| AC2 | F1 | the data files | the banker selects segment "mid" and sector "healthcare" | only mid-cap strategies whose `sectors` include `healthcare` are listed, and the count card shows their number | open |
| AC3 | F1 | the data files | the banker types a name that matches nothing (e.g. `zzzz`) | the page shows "No strategy matches these filters" and a "Clear filters" button | open |
| AC4 | F2 | a strategy with deals and portfolio rows | the banker clicks its row | the detail page shows its criteria, `other_criteria` verbatim, last fund, partner name, and the tables of its deals and portfolio companies | open |
| AC5 | F2 | an unknown id in the URL (`/strategies/does-not-exist`) | the page loads | it shows "Strategy not found" and a link back to the list; no stack trace | open |
| AC6 | F3 | any strategy | the detail page is open | each block shows a working source link and its `collected_on` date; an empty field shows "not published", never 0 | open |
| AC7 | F4 | a strategy row without `source_url` or `collected_on` | `npm run verify` runs | the data check fails and names the file, the row id and the missing field | open |
| AC9 | F5 | segment "mid" selected | the banker clicks "Export CSV" | a file `strategies-<date>.csv` downloads with exactly the rows shown, the source columns included, and accents displayed correctly in Excel | open |
| AC8 | F4 | a row with `ticket_min_eur_m` > `ticket_max_eur_m`, or a value outside the reference lists | `npm run verify` runs | the data check fails and names the row and the rule broken | open |

## Data quality rules (checked by automated tests on the real CSV files)

| Id | Rule | Status |
|---|---|---|
| DQ1 | every row has `source_url` (http/https) and `collected_on` (valid date, not in the future) | open |
| DQ2 | `strategy_id` and `deal_id` are unique; every `strategy_id` in `deals.csv` and `portfolio.csv` exists in `strategies.csv` | passed on import |
| DQ3 | when both are present: `ticket_min ≤ ticket_max`, `ev_min ≤ ev_max`; all amounts > 0 | passed on import |
| DQ4 | `segment`, `stake`, `deal_types`, `sectors`, `deal_type`, `direction` only use reference-list values | open |
| DQ5 | `last_fund_year` between 2018 and the current year (selection rule) | open |
| DQ6 | `deal_date` within the last 3 years before `collected_on` | open |
| DQ7 | `segment` agrees with the segment rule (CALC1) when the EV range is present | open |
| DQ8 | NAF codes, when present, match the format `NN.NNL` (e.g. `62.01Z`) | open |
| DQ9 | no column holds an email address or phone number | open |

## Investor import checks

- The startup integration test loads 112 funds, 153 strategies, 8 buckets and 10 sectors and checks
  original IDs and names, bucket membership, subsectors, source-preserved exclusions and null bounds.
- Negative cases cover orphaned sector links, inconsistent membership and fund links, zero amounts and
  reversed ranges. Buyer-list tests confirm that excluded strategies cannot displace an eligible strategy
  and the first eligible result per fund survives in the supplied ranking order. Adapter regressions
  cover generalist sector preferences and explicit exclusions.
- Publication checks cover research lead separation, null bounds for withheld directory figures,
  attributed paraphrases, deal-specific sources, and Dangel's fund-level vehicle attribution.
  Verbatim quote fields are intentionally blank. Four public deal dates remain unknown, and older
  historical deals are retained with their original dates. Source-by-source permission and
  factual verification are separate from this structural check.

## Screens (how each was checked)

| Id | Screen / state | Expected | Test | Browser check | Looked at by |
|---|---|---|---|---|---|
| V1 | strategies list, 1366 px | cards on one line, table readable | – | Playwright smoke | pending |
| V2 | strategies list, 390 px | cards stack, table scrolls inside its box, no sideways page scroll | – | Playwright smoke | pending |
| V3 | strategy detail, 1366 px and 390 px | blocks stack, source links visible | – | Playwright | pending |

## Calculations (known answers)

Segment rule: midpoint = (`ev_min_eur_m` + `ev_max_eur_m`) ÷ 2; small if midpoint < 50, mid if 50 ≤ midpoint ≤ 500,
large if midpoint > 500.

| Id | Number | Inputs (example) | Hand working | Expected result | Tolerance | Status |
|---|---|---|---|---|---|---|
| CALC1 | segment | EV 20 to 150 (EUR m) | (20 + 150) ÷ 2 = 170 ÷ 2 = 85; 50 ≤ 85 ≤ 500 | mid | exact | open |
| CALC2 | segment, boundary | EV 10 to 90 | (10 + 90) ÷ 2 = 50; 50 is not < 50 | mid | exact | open |
| CALC3 | segment, only one bound published | EV min 300, max empty | no midpoint | segment taken from the fund's own published wording, with quote; if none, left empty and listed as a gap in the data README | – | open |
| CALC4 | segment, EV range missing | no EV range | no midpoint | same as CALC3 | – | open |
| CALC5 | count cards | 3 test rows: small, mid, mid | 1 small, 2 mid, 0 large; total 1 + 2 + 0 = 3 | total 3, small 1, mid 2, large 0 | exact | open |

## Edge cases and errors

| Id | Situation | Expected behaviour | Status |
|---|---|---|---|
| E1 | backend not running | list page shows "Could not load data. Is the backend running?" and a "Try again" button | open |
| E2 | a value is not published | shown as "not published", never 0 or a guess | open |
| E3 | a CSV file is missing or has a wrong header | backend refuses to start with a message naming the file and the column; `npm run verify` fails | open |
| E4 | a strategy has no deals or no portfolio rows | the block shows "No deal recorded in the base" / "No portfolio company recorded" | open |
