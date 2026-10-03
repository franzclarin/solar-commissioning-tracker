"""Loader for EIA-860M monthly generator inventory workbooks.

Each workbook has one sheet per inventory (Operating, Planned, Retired,
Canceled [or Postponed], plus Puerto Rico variants from 2018). Every sheet has a
title in row 0 ("Inventory of ... as of August 2026"), a header row (row 1 in
early files, row 2 later), and footer NOTES rows. Column names drift over the
years; COLUMN_ALIASES maps old names onto the current ones.
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

# snake_cased historical column name -> current snake_cased name
COLUMN_ALIASES = {
    "sector_name": "sector",
    "nameplate_capacity_mw_": "nameplate_capacity_mw",
    "net_summer_capacity_mw_": "net_summer_capacity_mw",
    "net_winter_capacity_mw_": "net_winter_capacity_mw",
    "status_code": "status",
}

_TITLE_RE = re.compile(r"as of (\w+)\s+(\d{4})")
READ_KW = {"engine": "calamine"}


def _snake(name: str) -> str:
    name = re.sub(r"\(([^)]*)\)", r"\1", str(name))  # "Capacity (MW)" -> "Capacity MW"
    return re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


def resolve_sheet(available: list[str], canonical: str) -> str | None:
    """Find the workbook's sheet for a canonical name ('Canceled' in 2015 files, etc.)."""
    if canonical in available:
        return canonical
    if canonical.startswith("Canceled"):
        return next((s for s in available if s.lower().startswith("cancel")), None)
    return next((s for s in available if s.strip().lower() == canonical.lower()), None)


def _parse_title(title: str) -> pd.Timestamp:
    match = _TITLE_RE.search(str(title))
    if not match:
        raise ValueError(f"Could not parse inventory month from title: {title!r}")
    return pd.to_datetime(f"{match.group(1)} {match.group(2)}", format="%B %Y")


def inventory_month(path: str | Path, sheet: str = "Planned") -> pd.Timestamp:
    """Parse the inventory month from a sheet's title row."""
    title = pd.read_excel(path, sheet_name=sheet, header=None, nrows=1, **READ_KW).iat[0, 0]
    return _parse_title(title)


def _month_date(year: pd.Series, month: pd.Series) -> pd.Series:
    parts = pd.DataFrame({
        "year": pd.to_numeric(year, errors="coerce"),
        "month": pd.to_numeric(month, errors="coerce"),
        "day": 1,
    })
    return pd.to_datetime(parts, errors="coerce")


def _frame_from_raw(raw: pd.DataFrame) -> pd.DataFrame:
    """Locate the header row (the one containing 'Plant ID') and build the table."""
    head = raw.head(10).astype(str).apply(lambda r: r.str.strip())
    hdr = next(i for i in range(len(head)) if (head.iloc[i] == "Plant ID").any())
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [_snake(c) for c in raw.iloc[hdr]]
    df = df.loc[:, [c for c in df.columns if c and c != "nan"]]
    return df.rename(columns=COLUMN_ALIASES)


def read_sheet(path: str | Path, sheet: str, inv_month: pd.Timestamp | None = None,
               canonical: str | None = None) -> pd.DataFrame:
    """Read one inventory sheet into a cleaned DataFrame.

    - finds the header row, drops footer rows (no numeric plant_id)
    - snake_cases column names (with historical aliases) and drops map-link columns
    - builds planned_date / operating_date / planned_retirement_date / retirement_date
    - splits status into status_code and status_label
    - tags rows with inventory_month and the canonical sheet name
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None, **READ_KW)
    if inv_month is None:
        inv_month = _parse_title(raw.iat[0, 0])
    df = _frame_from_raw(raw).drop(columns=["google_map", "bing_map"], errors="ignore")

    df["plant_id"] = pd.to_numeric(df["plant_id"], errors="coerce").astype("Int64")
    df = df[df["plant_id"].notna()]
    df["entity_id"] = pd.to_numeric(df["entity_id"], errors="coerce").astype("Int64")
    df["generator_id"] = df["generator_id"].astype(str).str.strip()
    df["entity_name"] = df["entity_name"].astype(str).str.strip()

    numeric = [c for c in df.columns if c.endswith(("_mw", "_mwh", "_year", "_month")) or c in ("latitude", "longitude")]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")

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
        codes = df["status"].astype(str).str.strip().str.extract(r"^\(?(\w+)\)?\s*(.*)$")
        df["status_code"] = codes[0]
        df["status_label"] = codes[1].replace("", pd.NA)

    df["sheet"] = canonical or sheet
    df["inventory_month"] = inv_month
    return df.reset_index(drop=True)


def load_workbook(path: str | Path, include_pr: bool = False) -> dict[str, pd.DataFrame]:
    """Load the main inventory sheets (optionally Puerto Rico too) keyed by canonical sheet name.

    Sheets missing from older files (e.g. Retired before 2017) are skipped.
    """
    available = pd.ExcelFile(path, **READ_KW).sheet_names
    out = {}
    inv = None
    for canonical in MAIN_SHEETS + (PR_SHEETS if include_pr else []):
        actual = resolve_sheet(available, canonical)
        if actual is None:
            continue
        out[canonical] = read_sheet(path, actual, inv, canonical)
        inv = out[canonical]["inventory_month"].iloc[0]
    return out
