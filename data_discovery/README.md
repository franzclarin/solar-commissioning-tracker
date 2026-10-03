# Data Discovery

Exploratory analysis of the full EIA-860M monthly generator inventory archive (Mar 2015 – present), stacked into a prototype `generator_snapshot`. See the repo-level `README.md` for the project goal.

## Layout

```
data_discovery/
  pyproject.toml               # uv environment
  src/download_eia860m.py      # fetch every monthly workbook into data/raw/
  src/load_eia860m.py          # loader: one workbook -> cleaned DataFrames per sheet
  src/build_snapshots.py       # stack all workbooks -> data/processed/generator_snapshot.parquet
  EDA.ipynb                    # EDA: raw data, archive overview, latest snapshot, history
  data/raw/                    # EIA workbooks (gitignored)
  data/processed/              # stacked parquet + schema log (gitignored)
```

## Setup

```bash
cd data_discovery
uv sync                                   # creates .venv with all dependencies
uv run python src/download_eia860m.py     # ~135 files, ~1.15 GB; skips files already present
uv run python src/build_snapshots.py      # ~1 min -> data/processed/ (4.3 M rows, ~90 MB parquet)
uv run jupyter lab                        # open EDA.ipynb
```

To run the notebook in VS Code / Cursor / another Jupyter front end, register the venv as a kernel once:

```bash
uv run python -m ipykernel install --user --name solar-data-discovery --display-name "Python (solar data_discovery)"
```

Then pick **Python (solar data_discovery)** as the kernel. In VS Code you can also choose the interpreter `data_discovery/.venv/bin/python`. Run with the working directory set to `data_discovery/` (the default when the notebook is opened from there), because the notebook uses relative paths (`src/`, `data/`).

Re-run the notebook headless:

```bash
uv run jupyter nbconvert --to notebook --execute --inplace EDA.ipynb
```

To refresh with a newly published month, re-run the download script (it only fetches new files), then `build_snapshots.py`.

## The data

- Source: https://www.eia.gov/electricity/data/eia860m/ (free, no API key).
- Archive URL pattern: `.../eia860m/archive/xls/{month}_generator{year}.xlsx`. The current month lives at `.../eia860m/xls/`.
- Coverage: March 2015, then every month from July 2015 on. April–June 2015 were never published. New months appear about 3–4 weeks after month-end.
- Archived files may include EIA revisions, so they are not guaranteed to match exactly what was published in that month.

## Workbook structure (EIA-860M)

| Sheet | Contents | Key date fields |
| --- | --- | --- |
| Operating | Generators in service (status OP/SB/OS/OA) | Operating month/year, planned retirement |
| Planned | Generators not yet operating (status P/L/T/U/V/TS) | **Planned** operation month/year (current value only) |
| Retired | Retired generators | Operating + retirement month/year |
| Canceled or Postponed | Canceled / indefinitely postponed projects (sheet named `Canceled` in early files) | *None* |
| `*_PR` | Puerto Rico versions of the above (from 2018) | same |

Quirks the loader handles:
- The title row carries the inventory month (there is no date column).
- The header is on row 1 in 2015 files and row 2 later.
- Footer NOTES rows.
- Renamed columns.
- A dozen old retired nuclear units with blank Plant IDs.

Early files lack nameplate MW (until Apr 2016), county and coordinates (until Dec 2015), and balancing authority (until Jul 2016). `capacity_mw` in the stacked table is nameplate where available, otherwise net summer. Generators under 1 MW at a facility are excluded by EIA.

## Loader usage

```python
import sys; sys.path.insert(0, "src")
import pandas as pd
from load_eia860m import load_workbook

sheets = load_workbook("data/raw/august_generator2026.xlsx")       # one month: dict of DataFrames
snap = pd.read_parquet("data/processed/generator_snapshot.parquet")  # all months, one row per generator x sheet x month
```

## Holdout discipline

Analyses of *outcomes* (did promised MW arrive?) in `EDA.ipynb` only use cohorts up to `DEV_COHORT_END = 2021-12`. 2022 is the validation year and 2023–2024 the locked test set (see `CLAUDE.md`).
