"""Pipeline orchestrator.   Run:  python -m pipeline.run_pipeline

extract -> archive raw files -> transform -> pre-load checks -> load (one transaction)
        -> post-load reconciliation -> COMMIT  (or ROLLBACK and log the failure)
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import DATASETS, PipelineConfig
from .extract import Extractor
from .load import WarehouseLoader
from .quality import DataQualityChecker, DQResult
from .storage import ArchiveStore, archive_from_env
from .transform import Transformer

log = logging.getLogger("cashflow.etl")


class DataQualityError(Exception):
    """A HIGH-severity data-quality check failed; nothing was loaded."""


@dataclass
class RunSummary:
    run_id: str
    status: str
    rows_extracted: int = 0
    rows_loaded: int = 0
    rows_rejected: int = 0
    as_of_date: str = ""
    archive_locations: list[str] = field(default_factory=list)
    dq_results: list[DQResult] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ETLPipeline:
    def __init__(self, config: PipelineConfig | None = None, archive: ArchiveStore | None = None):
        self.config = config or PipelineConfig.from_env()
        self.archive = archive or archive_from_env(self.config.archive_dir)
        self.loader = WarehouseLoader(self.config)
        self.checker = DataQualityChecker()

    def run(self) -> RunSummary:
        run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}Z-{uuid.uuid4().hex[:6]}"
        summary = RunSummary(run_id, "RUNNING")
        con = self.loader.connect()
        in_txn = False
        try:
            self.loader.prepare(con, DATASETS)
            con.execute("INSERT INTO etl_run_log (run_id, started_at, status) VALUES (?, ?, 'RUNNING')", (run_id, _now()))

            extracted = Extractor(self.config.source_dir).extract()
            summary.rows_extracted = sum(d.row_count for d in extracted.values())
            summary.archive_locations = self.archive.save(run_id, [d.path for d in extracted.values()])

            result = Transformer().transform(extracted)
            summary.rows_rejected = len(result.rejects)
            summary.rows_loaded = sum(len(df) for df in result.clean.values())
            summary.dq_results = self.checker.pre_load(extracted, result)
            if self.checker.blocking(summary.dq_results):
                raise DataQualityError("; ".join(f"{r.dataset}/{r.check}: {r.details}"
                                                 for r in self.checker.blocking(summary.dq_results)))

            con.execute("BEGIN")
            in_txn = True
            summary.as_of_date = self.loader.load(con, run_id, extracted, result)
            summary.dq_results += self.checker.post_load(con, extracted, result, run_id)
            if self.checker.blocking(summary.dq_results):
                raise DataQualityError("; ".join(f"{r.dataset}/{r.check}: {r.details}"
                                                 for r in self.checker.blocking(summary.dq_results)))
            self._write_audit(con, run_id, summary, result.rejects)
            con.execute("UPDATE etl_run_log SET status='SUCCESS', finished_at=?, rows_extracted=?, rows_loaded=?, "
                        "rows_rejected=? WHERE run_id=?",
                        (_now(), summary.rows_extracted, summary.rows_loaded, summary.rows_rejected, run_id))
            con.execute("COMMIT")
            in_txn = False
            self.loader.create_views(con)
            summary.status = "SUCCESS"
            log.info("run %s succeeded: %d loaded, %d rejected", run_id, summary.rows_loaded, summary.rows_rejected)
            return summary
        except Exception as exc:
            if in_txn:
                con.execute("ROLLBACK")  # warehouse stays exactly as it was before this run
            self._record_failure(con, run_id, summary, exc)
            log.error("run %s failed: %s", run_id, exc)
            raise
        finally:
            con.close()

    @staticmethod
    def _write_audit(con: sqlite3.Connection, run_id: str, summary: RunSummary, rejects) -> None:
        con.executemany("INSERT INTO dq_results (run_id, check_name, dataset, severity, passed, details) VALUES (?,?,?,?,?,?)",
                        [(run_id, r.check, r.dataset, r.severity, int(r.passed), r.details) for r in summary.dq_results])
        con.executemany("INSERT INTO etl_rejects (run_id, dataset, reason, raw_record) VALUES (?,?,?,?)",
                        [(run_id, r.dataset, r.reason, r.raw_record) for r in rejects])

    def _record_failure(self, con: sqlite3.Connection, run_id: str, summary: RunSummary, exc: Exception) -> None:
        try:
            con.execute("BEGIN")
            con.execute("INSERT OR IGNORE INTO etl_run_log (run_id, started_at, status) VALUES (?, ?, 'RUNNING')", (run_id, _now()))
            con.execute("UPDATE etl_run_log SET status='FAILED', finished_at=?, rows_extracted=?, message=? WHERE run_id=?",
                        (_now(), summary.rows_extracted, f"{type(exc).__name__}: {exc}"[:500], run_id))
            con.executemany("INSERT INTO dq_results (run_id, check_name, dataset, severity, passed, details) VALUES (?,?,?,?,?,?)",
                            [(run_id, r.check, r.dataset, r.severity, int(r.passed), r.details) for r in summary.dq_results])
            con.execute("COMMIT")
        except sqlite3.Error:
            log.exception("could not write failure record for %s", run_id)
        summary.status = "FAILED"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CashFlow ETL pipeline.")
    parser.add_argument("--source", help="folder with the source CSV files")
    parser.add_argument("--db", help="SQLite warehouse path")
    args = parser.parse_args()
    base = PipelineConfig.from_env()
    config = PipelineConfig(source_dir=args.source or base.source_dir, db_path=args.db or base.db_path,
                            archive_dir=base.archive_dir, starting_cash=base.starting_cash, as_of_date=base.as_of_date)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = ETLPipeline(config).run()
    print(f"Run {s.run_id}: {s.status}")
    print(f"  extracted={s.rows_extracted} loaded={s.rows_loaded} rejected={s.rows_rejected} as_of={s.as_of_date}")
    for r in s.dq_results:
        print(f"  [{'PASS' if r.passed else 'FAIL'}] {r.severity:<6} {r.dataset}/{r.check}: {r.details}")


if __name__ == "__main__":
    main()
