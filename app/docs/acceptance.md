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
| DQ2 | `strategy_id` and `deal_id` are unique; every `strategy_id` in `deals.csv` and `portfolio.csv` exists in `strategies.csv` | open |
| DQ3 | when both are present: `ticket_min ≤ ticket_max`, `ev_min ≤ ev_max`; all amounts > 0 | open |
| DQ4 | `segment`, `stake`, `deal_types`, `sectors`, `deal_type`, `direction` only use reference-list values | open |
| DQ5 | `last_fund_year` between 2018 and the current year (selection rule) | open |
| DQ6 | `deal_date` within the last 3 years before `collected_on` | open |
| DQ7 | `segment` agrees with the segment rule (CALC1) when the EV range is present | open |
| DQ8 | NAF codes, when present, match the format `NN.NNL` (e.g. `62.01Z`) | open |
| DQ9 | no column holds an email address or phone number | open |

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

## Scoring (F6, known answers)

Rules, weights and thresholds: `app/docs/scoring.md` (agreed by Arthur Perret on 2026-11-20, to be
submitted to the group). Weights: sector 35, enterprise value fit 35, fund size 20, investment period
10. Synthetic operation A: `primary_lbo`, equity ticket 15, EV 60 (EUR m), `software_it`, majority,
analysis date 2026-11-20. Fund data is fictitious (`app/backend/tests/fixtures/synthetic_scoring_data.py`).

| Id | Fund (synthetic) | Hand working | Expected score | Tolerance | Test | Status |
|---|---|---|---|---|---|---|
| SC1 | Bravo: primary_lbo + build_up, ticket 5–20, EV 20–100, stake both, `generalist`, last fund 100 in 2021 | kept (5 ≤ 15 ≤ 20, both); sector generalist 35 × 0.5 = 17.5; EV 20 ≤ 60 ≤ 100 → 35; 15 / 100 = 15 % → 20 × 0.5 = 10; 2026 − 2021 = 5 years → 10 × 0.5 = 5; 17.5 + 35 + 10 + 5 | 67.5 | exact | `test_hand_case_1_bravo_for_operation_a_is_67_5` | passing |
| SC2 | Foxtrot: primary_lbo, ticket 10–15, EV 70–150, stake both, `industrials`, last fund 75 in 2019 | kept (ticket = maximum 15 is accepted); sector 0; EV 60 < 70 but 0.75 × 70 = 52.5 ≤ 60 → 35 × 0.5 = 17.5; 15 / 75 = 20 % → 20 × 0.5 = 10; 2026 − 2019 = 7 years → 0; 0 + 17.5 + 10 + 0 | 27.5 | exact | `test_hand_case_2_foxtrot_for_operation_a_is_27_5` | passing |
| SC3 | Alpha with EV range 80.4–200 (other fields as Alpha: primary_lbo, ticket 5–20, majority, `software_it`, last fund 200 in 2023); operation A with EV 60.3 | kept; sector 35; EV 60.3 < 80.4 but 0.75 × 80.4 = 60.3 exactly (bound included) → 35 × 0.5 = 17.5; 15 / 200 = 7.5 % → 20; 2026 − 2023 = 3 years → 10; 35 + 17.5 + 20 + 10. Decimal boundary: without the tolerance the computer gives 60.300000000000004 and the fund would get 0 | 82.5 | exact | `test_full_score_with_a_decimal_near_boundary` | passing |
| SC4 | Bravo (SC1) with a modified configuration: sector weight 33 with generalist ratio 0.25, EV weight 37 (fund size 20, period 10) | sector 33 × 0.25 = 8.25; EV 37 × 1 = 37; fund size 20 × 0.5 = 10; period 10 × 0.5 = 5; total 8.25 + 37 + 10 + 5 = 60.25, rounded to 0.1 half up | 60.3 (not 60.2) | exact | `test_total_is_rounded_half_up` | passing |

## Edge cases and errors

| Id | Situation | Expected behaviour | Status |
|---|---|---|---|
| E1 | backend not running | list page shows "Could not load data. Is the backend running?" and a "Try again" button | open |
| E2 | a value is not published | shown as "not published", never 0 or a guess | open |
| E3 | a CSV file is missing or has a wrong header | backend refuses to start with a message naming the file and the column; `npm run verify` fails | open |
| E4 | a strategy has no deals or no portfolio rows | the block shows "No deal recorded in the base" / "No portfolio company recorded" | open |
