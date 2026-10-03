# Data Discovery

Exploratory analysis of EIA-860M monthly generator inventories, the raw material for `generator_snapshot`. See the repo-level `README.md` for the project goal.

## Layout

```
data_discovery/
  pyproject.toml              # uv environment (pandas, openpyxl, matplotlib, seaborn, jupyterlab)
  src/load_eia860m.py         # loader: one workbook -> cleaned DataFrames per sheet
  01_eda_august_2026.ipynb    # first-pass EDA of the August 2026 snapshot
  data/raw/                   # EIA workbooks (gitignored; download yourself)
```

## Setup

```bash
cd data_discovery
uv sync                       # creates .venv with all dependencies
uv run jupyter lab            # open the notebook
```

Re-run the notebook headless:

```bash
uv run jupyter nbconvert --to notebook --execute --inplace 01_eda_august_2026.ipynb
```

## Getting the data

1. Go to https://www.eia.gov/electricity/data/eia860m/. The current month is linked at the top, and past months are under *Archives*.
2. Download the monthly generator inventory workbook (e.g. `august_generator2026.xlsx`) into `data/raw/`.
3. Free download, no API key, about 10–15 MB each. Raw files are **not committed**.

## Workbook structure (EIA-860M)

| Sheet | Contents | Key date fields |
| --- | --- | --- |
| Operating | Generators in service (status OP/SB/OS/OA) | Operating month/year, planned retirement |
| Planned | Generators not yet operating (status P/L/T/U/V/TS) | **Planned** operation month/year (current value only) |
| Retired | Retired generators | Operating + retirement month/year |
| Canceled or Postponed | Canceled / indefinitely postponed projects | *None* |
| `*_PR` | Puerto Rico versions of the above | same |

Quirks the loader handles: the title is in row 0 (it carries the inventory month), headers are in row 2, and each sheet ends with a blank row plus a NOTES row. Generators under 1 MW at a facility are excluded by EIA.

## Loader usage

```python
import sys; sys.path.insert(0, "src")
from load_eia860m import load_workbook

sheets = load_workbook("data/raw/august_generator2026.xlsx")   # dict of DataFrames
planned = sheets["Planned"]   # adds planned_date, status_code, inventory_month, snake_case columns
```

`inventory_month` is stamped on every row, so several monthly workbooks can be concatenated directly into a prototype `generator_snapshot`.
