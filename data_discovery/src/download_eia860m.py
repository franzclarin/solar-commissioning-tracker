"""Download EIA-860M monthly generator inventory workbooks into data/raw/.

Usage (from data_discovery/):
    uv run python src/download_eia860m.py                 # Mar 2015 .. latest available
    uv run python src/download_eia860m.py --start 2022-01 --end 2022-12

Files already present are skipped. Archived months live under /archive/xls/;
the current month lives under /xls/, so both are tried.
"""

from __future__ import annotations

import argparse
import calendar
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

BASE = "https://www.eia.gov/electricity/data/eia860m"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0 (solar-commissioning-tracker research)"}
XLSX_MAGIC = b"PK"  # xlsx is a zip; a redirect/HTML page is not


def filename(year: int, month: int) -> str:
    return f"{calendar.month_name[month].lower()}_generator{year}.xlsx"


def months(start: str, end: str) -> list[tuple[int, int]]:
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def fetch(year: int, month: int, retries: int = 3) -> str:
    name = filename(year, month)
    dest = RAW_DIR / name
    if dest.exists() and dest.stat().st_size > 0:
        return f"skip     {name}"
    for url in (f"{BASE}/archive/xls/{name}", f"{BASE}/xls/{name}"):
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
                    body = r.read()
                if not body.startswith(XLSX_MAGIC):
                    break  # redirected to an HTML page: not at this URL
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(body)
                tmp.rename(dest)
                return f"ok       {name} ({len(body) / 1e6:.1f} MB)"
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
                time.sleep(2 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(2 * (attempt + 1))
    return f"missing  {name}"


def main() -> None:
    today = date.today()
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2015-03")
    p.add_argument("--end", default=f"{today.year}-{today.month:02d}")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    targets = months(args.start, args.end)
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(fetch, y, m) for y, m in targets]
        results = [f.result() for f in as_completed(futures)]
    for line in sorted(results):
        print(line)
    print({k: sum(r.startswith(k) for r in results) for k in ("ok", "skip", "missing")})


if __name__ == "__main__":
    main()
