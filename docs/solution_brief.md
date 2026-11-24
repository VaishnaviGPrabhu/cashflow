# AI CashFlow Copilot — Solution Brief
## Executive summary
A synthetic finance workflow for cash visibility, runway, scenario planning and risk review.
## User problem
Finance teams repeatedly combine cash, AR/AP, recurring spend, payroll and assumptions to answer liquidity questions.
## Target user
Founders, FP&A analysts and finance managers.
## Workflow
Question → evidence → validation → deterministic calculation → risk checks → AI interpretation → traceability → human review.
## Architecture
Streamlit → finance tools → deterministic core. Optional Claude interprets verified context. Optional MCP exposes the same tools.
## Skill
The Cash Flow Forecast Skill defines workflow, rules, failure handling and human-review requirements.
## Evaluation
10 golden cases and 5 trap cases.
## Trade-offs
Deterministic arithmetic; explicit assumptions; human-in-the-loop decisions.
## Business impact
No fabricated hours-saved claim. Production impact should be measured against a baseline.
## Security
Synthetic data, environment variables for secrets, no credentials in prompts/source.
## Future
Authenticated app → governed connector/MCP gateway → finance systems → calculation service → model gateway → evaluation/observability → human approvals.
