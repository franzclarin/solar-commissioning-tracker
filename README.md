# solar-commissioning-tracker

**Renewable commissioning: which promised megawatts actually arrive?**

Track planned U.S. utility-scale solar generators through successive EIA inventories, separating genuine delays from database corrections. The goal is to support a decision to **trust, investigate, or discount** an apparent near-term capacity ramp.

## Question and hypothesis

For renewable developers (initially a small, verified set associated with **NextEra Energy** or **AES**): do construction status and repeated planned-date pushes improve estimates of MW entering operation over the next **3–6 months**?

- Delayed operation can defer generation and economic contribution, conditional on ownership and contracts.
- **Refutation:** predictive usefulness is rejected if these features fail to beat the published schedule or a status-only baseline.
- Commissioned MW alone does not establish earnings exposure.

## Data

| Source | Use |
| --- | --- |
| [EIA-860M monthly archives](https://www.eia.gov/electricity/data/eia860m/) | Generator snapshots (from July 2015): plant/generator/entity IDs, geography, technology, MW, status, planned and actual operating dates |
| [EIA-860 annual files](https://www.eia.gov/electricity/data/eia860/) | Ownership schedules |
| SEC filings (dated) | Limited parent-company crosswalk |

Unit of analysis: **plant × generator × inventory month**. Downloads are free and require no key (~10 MB per monthly workbook).

**Known gaps**
- EIA preliminary estimates are revised later; exact original release dates and preservation of every historical file version are unverified.
- Operator identity is not evidence of economic ownership.
- **Largest gap:** dated ownership and genuinely historical (point-in-time) availability.

## Data model

- `generator_snapshot` — one row per generator per inventory month, as published.
- `generator_transition` — explained month-to-month changes: status moves, date pushes, MW changes, renumbering, cancellations, disappearances (an absent row requires adjudication).
- `ownership_evidence` — operator vs. owner vs. joint venture vs. public parent at the relevant date, with uncertainty kept visible.

## Methods

Simple discrete-time survival or logistic models; unfinished projects are censored and cancellation is treated as a separate outcome. The hard decisions are identity and outcome definitions, not model choice.

## Evaluation

- **Splits:** develop on 2018–2021 cohorts, validate on 2022, lock 2023–2024 (where follow-up is complete).
- **Baselines:** published schedule; historical state/technology completion rates; status-only forecast.
- **Target:** ≥10% lower capacity-weighted absolute error for six-month commissioned MW, with calibration and cohort/year block-bootstrap intervals.
- **Ablations:** date pushes, status, ownership weights.
- **Manual audit:** trace 40 projects (including disappearances); reserve another 20.
- Separate inventory-vintage backtests from verified-publication-date tests. Shared developers and policy shocks limit independence.

## Differentiation

[EIA's solar-delay analysis](https://www.eia.gov/todayinenergy/detail.php?id=62003) already measures schedule slippage, and [PUDL](https://github.com/catalyst-cooperative/pudl) provides reproducible EIA integration. This project adds frozen entry cohorts, explained transitions, capacity-weighted calibration, and bounded company exposure — making a capacity ramp *assessable* rather than merely chartable. Novelty confidence: medium.

## Deliverables

1. Two-page memo.
2. One expected-vs-realized MW chart.
3. 20-project evidence ledger.
4. Code that reproduces one cohort and refreshes its transitions. (Dashboard optional.)

## Scope and failure conditions

- **Weekend pilot (12 h):** 2 h inspecting three workbooks and identities; 4 h parsing one state/solar cohort; 3 h adjudicating changes; 3 h chart and memo. Proves longitudinal feasibility, not forecasting skill.
- **Deeper study:** 8–10 weeks, 50–80 hours.
- **First check:** can a frozen cohort be traced?
- **Abandon company attribution** if >10% of pilot MW has unresolved identity or ownership; fall back to a state/technology study.
- A failed prediction still yields a useful schedule-reliability tracker.

> **Hardest reviewer question:** "Which investment conclusion changes when these generators slip, and how much economic exposure did you verify?"
