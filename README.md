# AI CashFlow Copilot
AI-assisted cash-flow forecasting, runway analysis, scenario planning, anomaly review and finance workflow demonstration for fictional NovaTech Labs.
> Prototype for financial analysis and workflow demonstration. Outputs are decision-support drafts and require review by a qualified finance professional.
## Stack
Python 3.11+, SQLite and SQL, Pandas, NumPy, FastAPI, JavaScript (vanilla), Streamlit, Plotly, pytest, python-dotenv, Anthropic SDK. Optional: AWS S3 (boto3), Power BI.
## Architecture
Data → Validation → Deterministic calculations → Tools → AI interpretation → Evaluation → Human review.
## Data engineering layer
An ETL pipeline loads the CSV data into a SQLite **star schema** (dimensions, facts, reporting views), with
data-quality checks, a raw-file archive, an audit log, SQL analytics queries, a REST API and a JavaScript web page.
See [docs/data_engineering.md](docs/data_engineering.md).

```bash
python -m pipeline.run_pipeline        # build the warehouse (data/warehouse/cashflow.db)
python -m warehouse.queries            # run the 11 SQL analytics queries
uvicorn api:app --reload               # then open http://127.0.0.1:8000/dashboard
python -m powerbi.export               # CSVs for Power BI (see powerbi/README.md)
```

## Install
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```
Windows activation: `.venv\Scripts\activate`
## Run
```bash
streamlit run app/streamlit_app.py
```
## Tests
```bash
pytest -q
python -m evaluations.evaluation_runner
```
## Optional Claude
Set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in `.env`. If absent, deterministic demo mode remains available.
## Optional API
`uvicorn api:app --reload`
## Optional MCP
Install a compatible MCP Python package and run `python -m mcp_server.server`. The app does not require MCP.
## Security
No hardcoded credentials. `.env` is ignored. Demo data is synthetic.
## Limitations
No real accounting integrations, authentication, ledger reconciliation, production audit controls, or automated financial decisions.
## Demo
Start at Overview, then Forecast → Risk Review → AI Analyst → Scenarios → Evaluation → show `skills/cash_flow_forecast/SKILL.md` and `docs/failure_analysis.md`.
