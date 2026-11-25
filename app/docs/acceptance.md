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
| DQ4 | `segment`, `stake`, `deal_types`, `sectors`, `deal_type`, `direction` only use reference-list values | partly covered (2026-11-25): every `deal_types`, `stake`, sector code, `sector_scope` and `polarity` value of the snapshot has a translation in `reference.py` (`test_every_value_of_the_base_has_a_translation`, `test_sector_scope_and_polarity_values_are_all_known`); `segment` and `direction` not covered |
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

## Scoring (F6, known answers)

**Two configurations.** Criteria v2 are the default since 2026-11-25 (section "Criteria v2" below). The v1 cases (SC1–SC7 with weights 35/35/20/10) are kept: the v1 rules still exist in the code and their tests now run with `SCORING_CONFIG_V1`; their expected values are unchanged.

### Criteria v1 (2026-11-20, `SCORING_CONFIG_V1`)

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

Real funds (`app/backend/data/strategies.csv`, snapshot of 2026-11-24, checked 2026-11-25), current criteria (35/35/20/10). Operation LBO small: `primary_lbo`, ticket 15, EV 40 (EUR m), `industrials`, majority, 2026-11-25. Operation build-up mid: `build_up`, ticket 40, EV 150, `business_services`, majority, 2026-11-25.

| Id | Real strategy (CSV values) | Hand working | Expected score | Tolerance | Test | Status |
|---|---|---|---|---|---|---|
| SC5 | `str-abenex-industries-90`, LBO small: deal_types `buyout;growth`, stake `majority;controlling_minority`, sector `INDUSTRIALS` (themes), ticket 5–20, EV min empty, EV max 60; source abenex.com (first closing) | kept: buyout covers primary LBO, 5 ≤ 15 ≤ 20, stake both; sector 35; EV 40 ≤ 60 (one bound) 35; fund size missing 20 × 0.5 = 10; fund year missing 10 × 0.5 = 5; 35 + 35 + 10 + 5 | 85 | exact | `test_real_fund_1_abenex_industries_for_lbo_small_is_85` | passing |
| SC6 | `str-argos-midmarket`, build-up mid: deal_types `buyout;build_up`, stake `majority`, sectors `BUSINESS_SERVICES;INDUSTRIALS` (generalist plus preferences), tickets empty, EV 50–250; source argos.fund | kept: build_up covered, tickets missing (not excluded, 2 warnings), majority; sector 35; 50 ≤ 150 ≤ 250 35; 10; 5; 35 + 35 + 10 + 5 | 85 | exact | `test_real_fund_2_argos_midmarket_for_buildup_mid_is_85` | passing |
| SC7 | `str-antin-flagship`, LBO small: deal_types `infrastructure_equity` (non-PE), ticket min 400, stake empty | excluded: no PE deal type (E1) and 15 < 400 (E2); score 0 | excluded, 0 | exact | `test_real_fund_3_antin_flagship_is_excluded_from_lbo_small` | passing |

### Criteria v2 (default since 2026-11-25, `SCORING_CONFIG`)

Weights: sector 40, fund type 25, lead capacity 15, geography 10, transaction speciality 10; EV, fund size and
fund age disabled. Eliminatory criteria unchanged. Tie-break: fewer missing data, then source quality
(`classification_basis`: SOURCE_DESCRIPTION > INTERPRETED_DESCRIPTION > BROAD_MAPPING > HISTORICAL_DIRECTORY_LABEL),
then `strategy_id`. Confidence: missing data over the 9 active criteria (eliminatory included): 0–1 high, 2–3 medium, 4+ low. Synthetic operation A and funds as above, with the v2 columns added to the fixtures on
2026-11-25 (`app/backend/tests/fixtures/synthetic_scoring_data.py`). Real operations as in SC5–SC7.

| Id | Case | v1 value | Hand working (v2) | v2 value | Test | Status |
|---|---|---|---|---|---|---|
| SC1 | Bravo, operation A: generalist; GROWTH_EQUITY with BUYOUT secondary; CONTROL_NOT_VERIFIED; Europe; `thematic_sector_focus` | 67.5 | sector 40 × 0.5 = 20; fund type BUYOUT secondary 25 × 0.5 = 12.5; lead 15 × 0.5 = 7.5; Europe 10 × 0.5 = 5; no `transmission` 0; 20 + 12.5 + 7.5 + 5 + 0 | 45 | `test_sc1_v2_bravo_is_45` | passing |
| SC2 | Foxtrot, operation A: `industrials`; SPECIAL_SITUATIONS; CONTROL_NOT_VERIFIED; Nouvelle_Aquitaine; `carve_out` | 27.5 | 0 + 0 + 7.5 + French region 5 + 0 | 12.5 | `test_sc2_v2_foxtrot_is_12_5` | passing |
| SC3 | Alpha with EV 80.4–200, operation A with EV 60.3 | 82.5 | EV no longer scored; 40 + 25 + 15 + France 10 + `transmission` 10 | 100 | `test_sc3_v2_decimal_ev_no_longer_counts_and_alpha_is_100` | passing |
| SC4 | Half-up rounding with a modified v1 configuration | 60.3 | rounding mechanism, unchanged in v2 (same `_round`); kept as a v1 configuration test | – | `test_total_is_rounded_half_up` (v1) | passing |
| SC5 | `str-abenex-industries-90`, LBO small (strategies.csv line 2): BUYOUT; CONTROL_POSSIBLE; France;Italy;Benelux; `thematic_sector_focus` | 85 | `industrials` 40 + BUYOUT 25 + CONTROL_POSSIBLE 15 + France 10 + no `transmission` 0; confidence 9/9 (0 missing) high | 90 | `test_sc5_v2_abenex_industries_for_lbo_small_is_90` | passing |
| SC6 | `str-argos-midmarket`, build-up mid (line 46): BUYOUT; CONTROL_POSSIBLE; France;...;Europe; `buy_and_build`; tickets empty | 85 | 40 + 25 + 15 + 10 + `buy_and_build` 10; confidence 7/9 (2 tickets missing) medium | 100 | `test_sc6_v2_argos_midmarket_for_buildup_mid_is_100` | passing |
| SC7 | `str-antin-flagship`, LBO small | excluded | unchanged: E1 (non-PE) and E2 (15 < 400) | excluded | `test_sc7_v2_antin_flagship_still_excluded` | passing |
| SC8 | `str-aldebaran-transform`, LBO small: `family_succession` now covers primary LBO; SPECIAL_SITUATIONS with BUYOUT secondary; CONTROL_POSSIBLE; France; no `transmission` | excluded (E1) before 2026-11-25; 67.5 under `SCORING_CONFIG_V1` since then, because the `family_succession` translation is shared by both configurations (sector 35 + EV both bounds missing 17.5 + 10 + 5) | 40 + 12.5 + 15 + 10 + 0 | 77.5 | `test_aldebaran_now_eligible_thanks_to_family_succession` | passing |

## Edge cases and errors

| Id | Situation | Expected behaviour | Status |
|---|---|---|---|
| E1 | backend not running | list page shows "Could not load data. Is the backend running?" and a "Try again" button | open |
| E2 | a value is not published | shown as "not published", never 0 or a guess | open |
| E3 | a CSV file is missing or has a wrong header | backend refuses to start with a message naming the file and the column; `npm run verify` fails | open |
| E4 | a strategy has no deals or no portfolio rows | the block shows "No deal recorded in the base" / "No portfolio company recorded" | open |
