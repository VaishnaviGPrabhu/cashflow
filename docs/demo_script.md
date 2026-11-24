# 20-minute showcase
## 30-second intro
“I built AI CashFlow Copilot, a synthetic finance workflow that answers cash, burn, runway, scenario and risk questions. The model interprets results, while deterministic Python tools remain the source of truth.”
## Live demo
Overview → Forecast → Risk Review → AI Analyst: “What is our current runway?” → “What happens if I hire two engineers next month?” → Evaluation.
## Architecture
Data → validation → deterministic calculations → tools → AI interpretation → evaluation → human review.
## Skill
The skill standardizes retrieval, calculation, labels, traceability and failure handling.
## MCP
Optional FastMCP server exposes governed tools; no QuickBooks/Xero integration is claimed.
## Failure
Show the 7.2-month plausible error, then the 6.8493-month deterministic result and regression test.
## Business impact
Measure analyst time, review time, error/rework and adoption in a production pilot rather than inventing metrics.

## Data engineering demo (5 minutes)
1. `python -m pipeline.run_pipeline` - show the run summary and the data-quality checks.
2. Run it again - show the row counts do not change (idempotent load).
3. Append a bad row to `data/demo/transactions.csv` - show it is rejected with a reason in `etl_rejects`.
4. `python -m warehouse.queries top_vendors_by_spend` and `monthly_cashflow_running_balance` - explain the window functions.
5. `uvicorn api:app --reload` - open `/dashboard`, then `/docs` for the REST endpoints.
6. Show `docs/data_engineering.md` (architecture and star schema) and the Power BI dashboard once you have built it.
