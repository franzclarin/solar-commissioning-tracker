# CLAUDE.md

Guidance for Claude Code when working in this repository. See `README.md` for the full project description.

## Project

Longitudinal tracker of planned U.S. utility-scale solar generators across EIA-860M monthly inventories (July 2015 onward). Goal: test whether construction status and repeated planned-date pushes improve 3–6 month forecasts of commissioned MW versus the published schedule and a status-only baseline, initially for a small verified set of NextEra Energy / AES projects.

No code exists yet. Current phase: weekend pilot — trace one frozen state/solar cohort.

## Core tables

- `generator_snapshot` — plant × generator × inventory month, as published. Never mutate raw values; record the source file and inventory month.
- `generator_transition` — explained changes between consecutive snapshots (status, planned date, MW, renumbering, cancellation, disappearance).
- `ownership_evidence` — dated operator / owner / JV / public-parent links with source and confidence.

## Rules to follow

- **Identity and outcome definitions come before modeling.** Don't silently match renumbered or vanished generators; flag them for adjudication.
- **A missing row is not a cancellation.** Disappearances need explicit adjudication and a recorded reason.
- **Operator ≠ owner.** Keep ownership uncertainty visible; never infer economic exposure from operator identity alone.
- **No look-ahead.** Features for a forecast at inventory month *t* may only use snapshots published at or before *t*. Keep inventory-vintage backtests separate from verified-publication-date tests, since EIA revises preliminary data.
- **Cohort splits are fixed:** develop 2018–2021, validate 2022, locked test 2023–2024. Do not touch the locked set during development.
- Unfinished projects are censored; cancellation is a separate outcome (competing risk).
- Prefer simple models (discrete-time survival / logistic). Report capacity-weighted absolute error, calibration, and cohort/year block-bootstrap intervals against all baselines.
- Abandon company attribution if >10% of pilot MW has unresolved identity or ownership; fall back to state/technology analysis.

## Data sources

- EIA-860M monthly: https://www.eia.gov/electricity/data/eia860m/
- EIA-860 annual (ownership): https://www.eia.gov/electricity/data/eia860/
- Dated SEC filings for the parent crosswalk.
- Raw downloads are free (no API key), ~10 MB per monthly workbook. Do not commit raw workbooks to git.

## Deliverables

Two-page memo, one expected-vs-realized MW chart, a 20-project evidence ledger, and code that reproduces one cohort and refreshes its transitions.
