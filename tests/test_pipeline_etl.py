import shutil
import sqlite3

from core.calculations import calculate_runway, current_cash, monthly_burn
from core.data_loader import load_demo_data
from pipeline.config import PipelineConfig
from pipeline.run_pipeline import DataQualityError, ETLPipeline
from pipeline.transform import SchemaError

DEMO = PipelineConfig().source_dir


def _config(tmp_path, source=None, db="wh.db"):
    return PipelineConfig(source_dir=source or DEMO, db_path=tmp_path / db, archive_dir=tmp_path / "archive")


def _copy_source(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(DEMO, src)
    return src


def _scalar(db, sql, params=()):
    con = sqlite3.connect(db)
    try:
        return con.execute(sql, params).fetchone()[0]
    finally:
        con.close()


def test_full_load_row_counts(tmp_path):
    cfg = _config(tmp_path)
    summary = ETLPipeline(cfg).run()
    assert summary.status == "SUCCESS" and summary.rows_rejected == 0
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 41
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_receivables") == 2
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_payroll") == 4
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM dim_counterparty") >= 8
    assert not any(not r.passed for r in summary.dq_results if r.severity == "HIGH")


def test_rerun_is_idempotent(tmp_path):
    cfg = _config(tmp_path)
    ETLPipeline(cfg).run()
    ETLPipeline(cfg).run()
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 41
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM etl_run_log WHERE status='SUCCESS'") == 2
    assert _scalar(cfg.db_path, "SELECT COUNT(DISTINCT first_run_id) FROM fact_transactions") == 1


def test_new_transactions_are_appended_incrementally(tmp_path):
    src = _copy_source(tmp_path)
    cfg = _config(tmp_path, src)
    first = ETLPipeline(cfg).run()
    with open(src / "transactions.csv", "a") as fh:
        fh.write("2026-11-04,inflow,Revenue,Beta Systems,63000\n")
    second = ETLPipeline(cfg).run()
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 42
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions WHERE first_run_id=?", (first.run_id,)) == 41
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions WHERE first_run_id=?", (second.run_id,)) == 1


def test_invalid_rows_are_rejected_with_reason(tmp_path):
    src = _copy_source(tmp_path)
    with open(src / "transactions.csv", "a") as fh:
        fh.write("not-a-date,outflow,Software,DevTools,100\n")
        fh.write("2026-11-05,outflow,Software,DevTools,-50\n")
        fh.write("2026-11-06,sideways,Software,DevTools,10\n")
    cfg = _config(tmp_path, src)
    summary = ETLPipeline(cfg).run()
    assert summary.rows_rejected == 3
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 41
    reasons = _scalar(cfg.db_path, "SELECT GROUP_CONCAT(reason, ' | ') FROM etl_rejects")
    assert "invalid date" in reasons and "negative value" in reasons and "unexpected value" in reasons


def test_identical_rows_are_both_kept_and_flagged(tmp_path):
    src = _copy_source(tmp_path)
    with open(src / "transactions.csv", "a") as fh:
        fh.write("2026-10-23,outflow,Office,NewOfficeVendor,12000\n")  # exact copy of an existing row
    cfg = _config(tmp_path, src)
    summary = ETLPipeline(cfg).run()
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 42
    repeat = [r for r in summary.dq_results if r.check == "repeated_transaction_rows"][0]
    assert not repeat.passed
    ETLPipeline(cfg).run()  # re-running must not create a third copy
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 42


def test_missing_column_fails_run_and_keeps_existing_data(tmp_path):
    src = _copy_source(tmp_path)
    cfg = _config(tmp_path, src)
    ETLPipeline(cfg).run()
    (src / "transactions.csv").write_text("date,type,category,amount\n2026-11-01,inflow,Revenue,10\n")
    try:
        ETLPipeline(cfg).run()
        raise AssertionError("expected SchemaError")
    except SchemaError:
        pass
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 41
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM etl_run_log WHERE status='FAILED'") == 1
    assert "vendor" in _scalar(cfg.db_path, "SELECT message FROM etl_run_log WHERE status='FAILED'")


def test_empty_source_blocks_the_load(tmp_path):
    src = _copy_source(tmp_path)
    (src / "payroll.csv").write_text("employee_id,role,start_date,monthly_salary\n")
    cfg = _config(tmp_path, src)
    try:
        ETLPipeline(cfg).run()
        raise AssertionError("expected DataQualityError")
    except DataQualityError:
        pass
    assert _scalar(cfg.db_path, "SELECT COUNT(*) FROM fact_transactions") == 0


def test_raw_files_are_archived_per_run(tmp_path):
    cfg = _config(tmp_path)
    summary = ETLPipeline(cfg).run()
    assert len(summary.archive_locations) == 7
    assert (cfg.archive_dir / summary.run_id / "transactions.csv").exists()


def test_foreign_keys_are_consistent(tmp_path):
    cfg = _config(tmp_path)
    ETLPipeline(cfg).run()
    con = sqlite3.connect(cfg.db_path)
    con.execute("PRAGMA foreign_keys = ON")
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.close()


def test_sql_runway_matches_python_calculations(tmp_path):
    cfg = _config(tmp_path)
    ETLPipeline(cfg).run()
    data = load_demo_data()
    cash = current_cash(data["transactions"])
    burn = monthly_burn(data["recurring_expenses"], data["payroll"], data["transactions"])
    con = sqlite3.connect(cfg.db_path)
    sql_cash, sql_burn, sql_runway = con.execute("SELECT * FROM vw_runway").fetchone()
    con.close()
    assert sql_cash == cash and sql_burn == burn
    assert abs(sql_runway - calculate_runway(cash, burn)) < 0.001
