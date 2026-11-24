"""Central configuration for the ETL pipeline and warehouse."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# dataset name -> source file in the source directory
DATASETS: dict[str, str] = {
    "transactions": "transactions.csv",
    "accounts_receivable": "accounts_receivable.csv",
    "accounts_payable": "accounts_payable.csv",
    "recurring_expenses": "recurring_expenses.csv",
    "payroll": "payroll.csv",
    "revenue_assumptions": "revenue_assumptions.csv",
    "hiring_plan": "hiring_plan.csv",
}

# category -> reporting group (anything not listed is "Operating")
CATEGORY_GROUPS: dict[str, str] = {"Revenue": "Revenue", "Payroll": "People"}
DEFAULT_CATEGORY_GROUP = "Operating"


@dataclass(frozen=True)
class PipelineConfig:
    source_dir: Path = ROOT / "data" / "demo"
    db_path: Path = ROOT / "data" / "warehouse" / "cashflow.db"
    archive_dir: Path = ROOT / "data" / "archive"
    starting_cash: float = 250000.0
    as_of_date: str | None = None  # defaults to the latest transaction date

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Build a config from environment variables, falling back to defaults."""
        base = cls()
        return cls(
            source_dir=Path(os.getenv("CASHFLOW_SOURCE_DIR", base.source_dir)),
            db_path=Path(os.getenv("CASHFLOW_DB", base.db_path)),
            archive_dir=Path(os.getenv("CASHFLOW_ARCHIVE_DIR", base.archive_dir)),
            starting_cash=float(os.getenv("CASHFLOW_STARTING_CASH", base.starting_cash)),
            as_of_date=os.getenv("CASHFLOW_AS_OF_DATE") or None,
        )
