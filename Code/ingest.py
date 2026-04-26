import shutil
from pathlib import Path

SRC_COT    = Path("C:/Users/virat.arya/ETG/SoftsDatabase - Documents/Database/Hardmine/ICEBREAKER/COT/Database")
SRC_ROLLEX = Path("C:/Users/virat.arya/ETG/SoftsDatabase - Documents/Database/Hardmine/ICEBREAKER/Rollex/Database")
DEST       = Path(__file__).parent.parent / "Database"

def ingest():
    DEST.mkdir(exist_ok=True)
    shutil.copy2(SRC_COT / "cot_cit.parquet",    DEST / "cot_cit.parquet")
    shutil.copy2(SRC_COT / "cot_disagg.parquet", DEST / "cot_disagg.parquet")
    for f in SRC_ROLLEX.glob("rollex_*.parquet"):
        shutil.copy2(f, DEST / f.name)
    print(f"Ingested to {DEST}")

if __name__ == "__main__":
    ingest()
