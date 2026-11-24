"""Export the star schema to CSV files that Power BI Desktop can import.

    python -m powerbi.export          # writes powerbi/export/*.csv
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

from pipeline.config import PipelineConfig

OUT_DIR = Path(__file__).resolve().parent / "export"
TABLES = ["dim_date", "dim_counterparty", "dim_category", "fact_transactions", "fact_receivables",
          "fact_payables", "fact_revenue_plan", "fact_hiring_plan", "vw_monthly_cashflow", "vw_vendor_spend"]


def export(db_path: Path, out_dir: Path = OUT_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    written = []
    for table in TABLES:
        cur = con.execute(f"SELECT * FROM {table}")
        path = out_dir / f"{table}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([c[0] for c in cur.description])
            writer.writerows(cur.fetchall())
        written.append(path)
    con.close()
    return written


if __name__ == "__main__":
    db = PipelineConfig.from_env().db_path
    if not Path(db).exists():
        sys.exit(f"No warehouse at {db}. Run: python -m pipeline.run_pipeline")
    for p in export(db):
        print("wrote", p)
