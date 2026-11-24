# Power BI dashboard

The warehouse is a star schema, so it loads into Power BI Desktop without reshaping.

1. Build the warehouse: `python -m pipeline.run_pipeline`
2. Export the tables: `python -m powerbi.export` (writes `powerbi/export/*.csv`)
3. In Power BI Desktop: **Get data -> Text/CSV**, load all files in `powerbi/export/`.
4. **Model view** -> create these relationships (many-to-one, single direction):
   - `fact_transactions[date_key]` -> `dim_date[date_key]`
   - `fact_transactions[counterparty_key]` -> `dim_counterparty[counterparty_key]`
   - `fact_transactions[category_key]` -> `dim_category[category_key]`
   - `fact_receivables[due_date_key]` -> `dim_date[date_key]`, `fact_receivables[counterparty_key]` -> `dim_counterparty[counterparty_key]`
   - `fact_payables` the same way
5. Mark `dim_date` as the date table (column `full_date`).
6. Add these measures (DAX):

```
Total Inflow  = CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[direction] = "inflow" )
Total Outflow = CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[direction] = "outflow" )
Net Cash Flow = [Total Inflow] - [Total Outflow]
Outflow MoM % = DIVIDE ( [Total Outflow] - CALCULATE ( [Total Outflow], DATEADD ( dim_date[full_date], -1, MONTH ) ),
                         CALCULATE ( [Total Outflow], DATEADD ( dim_date[full_date], -1, MONTH ) ) )
Open Receivables = CALCULATE ( SUM ( fact_receivables[amount] ), fact_receivables[status] = "open" )
```

7. Suggested report page: KPI cards (Total Inflow, Total Outflow, Net Cash Flow), a line chart of
   `vw_monthly_cashflow[closing_cash]` by `year_month`, a bar chart of outflow by `dim_category[category_name]`,
   and a table of top vendors from `vw_vendor_spend`.
8. Save a screenshot to `screenshots/powerbi_dashboard.png`.

Status: the export script is tested; the Power BI report itself is **not included** in this repo. Build it
once in Power BI Desktop, then you can truthfully say you built a Power BI dashboard on this warehouse.
