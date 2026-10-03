"""Loader for EIA-860M monthly generator inventory workbooks.

Each workbook has one sheet per inventory (Operating, Planned, Retired,
Canceled or Postponed, plus Puerto Rico variants). Every sheet has a title in
row 0 ("Inventory of ... as of August 2026"), headers in row 2, and a blank row
plus a long NOTES row at the bottom.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

MAIN_SHEETS = ["Operating", "Planned", "Retired", "Canceled or Postponed"]
PR_SHEETS = ["Operating_PR", "Planned_PR", "Retired_PR"]

# Planned-generator status codes in their natural progression toward operation.
PLANNED_STATUS_ORDER = ["P", "L", "T", "U", "V", "TS"]
PLANNED_STATUS_LABELS = {
    "P": "Planned, approvals not initiated",
    "L": "Approvals pending",
    "T": "Approvals received",
    "U": "Under construction, <=50%",
    "V": "Under construction, >50%",
    "TS": "Construction complete, not in operation",
}

_TITLE_RE = re.compile(r"as of (\w+ \d{4})")


def _snake(name: str) -> str:
    name = re.sub(r"\(([^)]*)\)", r"\1", name)  # "Capacity (MW)" -> "Capacity MW"
    return re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


def inventory_month(path: str | Path, sheet: str = "Planned") -> pd.Timestamp:
    """Parse the inventory month from a sheet's title row."""
    title = pd.read_excel(path, sheet_name=sheet, header=None, nrows=1).iat[0, 0]
    match = _TITLE_RE.search(str(title))
    if not match:
        raise ValueError(f"Could not parse inventory month from title: {title!r}")
    return pd.to_datetime(match.group(1), format="%B %Y")


def _month_date(year: pd.Series, month: pd.Series) -> pd.Series:
    parts = pd.DataFrame({"year": year, "month": month, "day": 1})
    return pd.to_datetime(parts, errors="coerce")


def read_sheet(path: str | Path, sheet: str, inv_month: pd.Timestamp | None = None) -> pd.DataFrame:
    """Read one inventory sheet into a cleaned DataFrame.

    - drops the footer (blank + NOTES rows)
    - snake_cases column names and drops map-link columns
    - builds planned_date / operating_date / planned_retirement_date
    - splits status into status_code and status_label
    - tags rows with inventory_month and sheet
    """
    df = pd.read_excel(path, sheet_name=sheet, header=2)
    df = df.dropna(subset=["Plant ID"]).drop(columns=["Google Map", "Bing Map"], errors="ignore")
    df.columns = [_snake(c) for c in df.columns]

    for col in ["entity_id", "plant_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["generator_id"] = df["generator_id"].astype(str).str.strip()

    date_cols = {
        "planned_date": ("planned_operation_year", "planned_operation_month"),
        "operating_date": ("operating_year", "operating_month"),
        "planned_retirement_date": ("planned_retirement_year", "planned_retirement_month"),
        "retirement_date": ("retirement_year", "retirement_month"),
    }
    for new, (y, m) in date_cols.items():
        if y in df.columns and m in df.columns:
            df[new] = _month_date(df[y], df[m])

    if "status" in df.columns:
        codes = df["status"].astype(str).str.extract(r"^\((\w+)\)\s*(.*)$")
        df["status_code"] = codes[0]
        df["status_label"] = codes[1]

    df["sheet"] = sheet
    df["inventory_month"] = inv_month if inv_month is not None else inventory_month(path, sheet)
    return df.reset_index(drop=True)


def load_workbook(path: str | Path, include_pr: bool = False) -> dict[str, pd.DataFrame]:
    """Load the main inventory sheets (optionally Puerto Rico too) keyed by sheet name."""
    inv = inventory_month(path)
    sheets = MAIN_SHEETS + (PR_SHEETS if include_pr else [])
    return {s: read_sheet(path, s, inv) for s in sheets}
