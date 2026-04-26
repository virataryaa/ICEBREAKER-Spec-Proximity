import shutil
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

SRC_COT    = Path("C:/Users/virat.arya/ETG/SoftsDatabase - Documents/Database/Hardmine/ICEBREAKER/COT/Database")
SRC_ROLLEX = Path("C:/Users/virat.arya/ETG/SoftsDatabase - Documents/Database/Hardmine/ICEBREAKER/Rollex/Database")
DEST       = Path(__file__).parent.parent / "Database"
SUMMARY    = Path(__file__).parent.parent / "Automator" / "last_run.json"

COMMODITY_CONFIG = [
    ("KC",  "Arabica",      "cit"),
    ("RC",  "Robusta",      "disagg"),
    ("SB",  "Sugar",        "cit"),
    ("CC",  "Cocoa (NYC)",  "cit"),
    ("LCC", "Liffe Cocoa",  "disagg"),
    ("CT",  "Cotton",       "cit"),
]


def copy_files():
    DEST.mkdir(exist_ok=True)
    files = []
    for src in [SRC_COT / "cot_cit.parquet", SRC_COT / "cot_disagg.parquet"]:
        dst = DEST / src.name
        shutil.copy2(src, dst)
        files.append({"name": src.name, "size_kb": round(dst.stat().st_size / 1024, 1)})
    for src in SRC_ROLLEX.glob("rollex_*.parquet"):
        dst = DEST / src.name
        shutil.copy2(src, dst)
        files.append({"name": src.name, "size_kb": round(dst.stat().st_size / 1024, 1)})
    return sorted(files, key=lambda x: x["name"])


def compute_specs():
    cit    = pd.read_parquet(DEST / "cot_cit.parquet")
    disagg = pd.read_parquet(DEST / "cot_disagg.parquet")

    cit["net_spec"] = (
        (cit["Spec Long"]    - cit["Spec Short"])    +
        (cit["Index Long"]   - cit["Index Short"])   +
        (cit["Non Rep Long"] - cit["Non Rep Short"])
    )
    disagg["net_spec"] = (
        (disagg["MM Long"]      - disagg["MM Short"])      +
        (disagg["Other Long"]   - disagg["Other Short"])   +
        (disagg["Non Rep Long"] - disagg["Non Rep Short"])
    )

    results = []
    for ticker, label, source in COMMODITY_CONFIG:
        df = cit if source == "cit" else disagg
        rows = df[df["Commodity"] == ticker].sort_values("Date")
        if rows.empty:
            continue
        latest = rows.iloc[-1]
        prev   = rows.iloc[-2] if len(rows) > 1 else None
        net    = float(latest["net_spec"])
        chg    = round((net - float(prev["net_spec"])) / 1000, 1) if prev is not None else None
        results.append({
            "ticker":          ticker,
            "label":           label,
            "latest_cot_date": pd.Timestamp(latest["Date"]).strftime("%d/%m/%Y"),
            "net_spec_k":      round(net / 1000, 1),
            "wow_chg_k":       chg,   # week-on-week change in k lots
        })
    return results


def ingest():
    errors = []
    files  = []
    specs  = []

    try:
        files = copy_files()
    except Exception as e:
        errors.append(f"File copy failed: {e}")

    try:
        specs = compute_specs()
    except Exception as e:
        errors.append(f"Spec computation failed: {e}")

    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files":     files,
        "specs":     specs,
        "errors":    errors,
    }

    SUMMARY.parent.mkdir(exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2))

    print(f"[{summary['timestamp']}] Spec Proximity — Ingest complete")
    print(f"  Files:  {len(files)} parquets refreshed")
    for s in specs:
        chg_str = f"  WoW: {s['wow_chg_k']:+.1f}k" if s["wow_chg_k"] is not None else ""
        print(f"  {s['ticker']:4s}  {s['net_spec_k']:+.1f}k{chg_str}  (latest COT: {s['latest_cot_date']})")
    if errors:
        print(f"  ERRORS: {errors}")

    return summary


if __name__ == "__main__":
    ingest()
