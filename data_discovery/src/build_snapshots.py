"""Stack every monthly EIA-860M workbook in data/raw/ into one long table.

Output (data/processed/):
    generator_snapshot.parquet  one row per generator x sheet x inventory month
    schema_by_month.csv         which source columns each month's sheets had

Usage (from data_discovery/):
    uv run python src/build_snapshots.py
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_eia860m import load_workbook  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

KEEP = [
    "inventory_month", "sheet", "entity_id", "entity_name", "plant_id", "plant_name", "plant_state",
    "county", "balancing_authority_code", "sector", "generator_id", "technology", "energy_source_code",
    "prime_mover_code", "nameplate_capacity_mw", "net_summer_capacity_mw", "capacity_mw", "status_code",
    "planned_date", "operating_date", "retirement_date", "planned_retirement_date", "latitude", "longitude",
    "source_file",
]
CATEGORICAL = ["sheet", "entity_name", "plant_name", "plant_state", "county", "balancing_authority_code",
               "sector", "technology", "energy_source_code", "prime_mover_code", "status_code", "source_file"]


def load_one(path: Path) -> tuple[pd.DataFrame, list[dict]]:
    sheets = load_workbook(path)
    schema = [{"inventory_month": df["inventory_month"].iloc[0], "sheet": name, "column": c}
              for name, df in sheets.items() for c in df.columns]
    frames = []
    for df in sheets.values():
        df = df.copy()
        # Nameplate capacity is missing from the earliest files; fall back to net summer capacity.
        nameplate = df.get("nameplate_capacity_mw", pd.Series(float("nan"), index=df.index))
        df["capacity_mw"] = pd.to_numeric(nameplate.fillna(df.get("net_summer_capacity_mw")), errors="coerce").astype(float)
        df["source_file"] = path.name
        frames.append(df.reindex(columns=KEEP))
    return pd.concat(frames, ignore_index=True), schema


def main() -> None:
    files = sorted(RAW_DIR.glob("*_generator*.xlsx"))
    if not files:
        sys.exit(f"No workbooks in {RAW_DIR}; run src/download_eia860m.py first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frames, schema = [], []
    with ProcessPoolExecutor() as pool:
        for path, (df, sch) in zip(files, pool.map(load_one, files)):
            frames.append(df)
            schema.extend(sch)
            print(f"{path.name:<32} {len(df):>7,} rows")

    snap = pd.concat(frames, ignore_index=True)
    dupes = snap.duplicated(["inventory_month", "sheet", "plant_id", "generator_id"]).sum()
    for c in CATEGORICAL:
        snap[c] = snap[c].astype("category")
    snap = snap.sort_values(["inventory_month", "sheet", "plant_id", "generator_id"]).reset_index(drop=True)
    snap.to_parquet(OUT_DIR / "generator_snapshot.parquet", index=False)
    pd.DataFrame(schema).to_csv(OUT_DIR / "schema_by_month.csv", index=False)

    months = snap["inventory_month"].nunique()
    print(f"\n{len(files)} files -> {len(snap):,} rows across {months} inventory months "
          f"({snap.inventory_month.min():%Y-%m} .. {snap.inventory_month.max():%Y-%m}); "
          f"duplicate keys: {dupes}")


if __name__ == "__main__":
    main()
