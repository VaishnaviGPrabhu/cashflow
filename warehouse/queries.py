"""Run the named SQL queries in analytics_queries.sql.

    python -m warehouse.queries                 # run every query
    python -m warehouse.queries top_vendors_by_spend
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

QUERY_FILE = Path(__file__).with_name("analytics_queries.sql")


def load_queries(path: Path = QUERY_FILE) -> dict[str, str]:
    text = path.read_text()
    parts = re.split(r"^-- name:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    # parts = [preamble, name1, body1, name2, body2, ...]
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run_query(con: sqlite3.Connection, name: str) -> tuple[list[str], list[tuple]]:
    cur = con.execute(load_queries()[name])
    return [c[0] for c in cur.description], cur.fetchall()


def _print(name: str, cols: list[str], rows: list[tuple]) -> None:
    print(f"\n== {name} ({len(rows)} rows)")
    print(" | ".join(cols))
    for row in rows:
        print(" | ".join(str(v) for v in row))


def main() -> None:
    from pipeline.config import PipelineConfig

    db = PipelineConfig.from_env().db_path
    if not Path(db).exists():
        sys.exit(f"No warehouse at {db}. Run: python -m pipeline.run_pipeline")
    con = sqlite3.connect(db)
    names = sys.argv[1:] or list(load_queries())
    for name in names:
        _print(name, *run_query(con, name))


if __name__ == "__main__":
    main()
