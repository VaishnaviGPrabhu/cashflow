from fastapi.testclient import TestClient

import api
from pipeline.config import PipelineConfig
from pipeline.run_pipeline import ETLPipeline


def test_warehouse_endpoints_return_data(tmp_path, monkeypatch):
    cfg = PipelineConfig(db_path=tmp_path / "wh.db", archive_dir=tmp_path / "archive")
    ETLPipeline(cfg).run()
    monkeypatch.setenv("CASHFLOW_DB", str(cfg.db_path))
    client = TestClient(api.app)
    assert client.get("/warehouse/runway").json()["current_cash"] == 215700.0
    assert len(client.get("/warehouse/monthly-cashflow").json()) == 10
    assert client.get("/warehouse/vendors?limit=2").json()[0]["vendor"] == "NovaTech Payroll"
    assert client.get("/pipeline/status").json()["last_run"]["status"] == "SUCCESS"
    assert client.get("/dashboard").status_code == 200


def test_warehouse_endpoint_reports_503_before_first_run(tmp_path, monkeypatch):
    monkeypatch.setenv("CASHFLOW_DB", str(tmp_path / "missing.db"))
    response = TestClient(api.app).get("/warehouse/runway")
    assert response.status_code == 503 and "pipeline" in response.json()["detail"]
