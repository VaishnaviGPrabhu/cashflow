import sqlite3

from pipeline.config import PipelineConfig
from pipeline.run_pipeline import ETLPipeline
from warehouse.queries import load_queries, run_query


def _warehouse(tmp_path):
    cfg = PipelineConfig(db_path=tmp_path / "wh.db", archive_dir=tmp_path / "archive")
    ETLPipeline(cfg).run()
    return sqlite3.connect(cfg.db_path)


def test_every_named_query_runs_and_returns_rows(tmp_path):
    con = _warehouse(tmp_path)
    names = list(load_queries())
    assert len(names) >= 10
    for name in names:
        cols, rows = run_query(con, name)
        assert cols and rows, name


def test_running_balance_ends_at_current_cash(tmp_path):
    con = _warehouse(tmp_path)
    _, rows = run_query(con, "monthly_cashflow_running_balance")
    assert rows[-1][0] == "2026-10" and rows[-1][3] == 215700.0


def test_revenue_growth_first_month_is_null(tmp_path):
    con = _warehouse(tmp_path)
    _, rows = run_query(con, "revenue_month_over_month")
    assert rows[0][2] is None and rows[1][2] == 4000.0


def test_top_vendor_is_payroll_and_shares_sum_to_100(tmp_path):
    con = _warehouse(tmp_path)
    _, rows = run_query(con, "top_vendors_by_spend")
    assert rows[0][0] == "NovaTech Payroll"
    assert abs(sum(r[3] for r in rows) - 100) < 0.1


def test_spike_detection_finds_the_devtools_october_charge(tmp_path):
    con = _warehouse(tmp_path)
    _, rows = run_query(con, "unusual_transactions")
    assert [(r[1], r[3]) for r in rows] == [("DevTools", 18500.0)]


def test_aging_buckets_add_up_to_open_receivables(tmp_path):
    con = _warehouse(tmp_path)
    _, rows = run_query(con, "receivables_aging_summary")
    assert sum(r[2] for r in rows) == 40000.0


def test_powerbi_export_writes_one_csv_per_table(tmp_path):
    from powerbi.export import TABLES, export

    cfg = PipelineConfig(db_path=tmp_path / "wh.db", archive_dir=tmp_path / "archive")
    ETLPipeline(cfg).run()
    written = export(cfg.db_path, tmp_path / "pbi")
    assert len(written) == len(TABLES)
    header = (tmp_path / "pbi" / "fact_transactions.csv").read_text().splitlines()[0]
    assert header.startswith("transaction_key,row_hash,date_key")
