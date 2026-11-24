"""REST API (controller layer).

Original demo endpoints are unchanged. The /warehouse/* endpoints read the SQLite
warehouse built by `python -m pipeline.run_pipeline`; /dashboard serves the web page.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from agent.tools import FinanceTools
from core.data_loader import load_demo_data
from warehouse import repository as repo

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="AI CashFlow Copilot")
tools = FinanceTools(load_demo_data())


def _warehouse(fn, *args):
    try:
        return fn(*args)
    except repo.WarehouseNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/health")
def health():
    return {"status": "ok", "mode": "synthetic-demo"}


@app.get("/cash")
def cash():
    return tools.get_current_cash()


@app.get("/runway")
def runway():
    return tools.calculate_runway()


@app.get("/warehouse/runway")
def warehouse_runway():
    return _warehouse(repo.runway)


@app.get("/warehouse/monthly-cashflow")
def warehouse_monthly_cashflow():
    return _warehouse(repo.monthly_cashflow)


@app.get("/warehouse/vendors")
def warehouse_vendors(limit: int = Query(10, ge=1, le=100)):
    return _warehouse(repo.vendor_spend, limit)


@app.get("/warehouse/receivables-aging")
def warehouse_receivables_aging():
    return _warehouse(repo.receivables_aging)


@app.get("/warehouse/payables-due")
def warehouse_payables_due():
    return _warehouse(repo.payables_due)


@app.get("/pipeline/status")
def pipeline_status():
    return {"last_run": _warehouse(repo.last_run), "data_quality": _warehouse(repo.latest_quality_results)}


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(ROOT / "web" / "index.html")



@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/dashboard")
