# Interview preparation

## Data engineering questions about this project
1. **Walk me through the pipeline.** Extract CSVs, archive the raw files, transform and validate, load staging,
   build dimensions and facts in one transaction, reconcile, then commit. Reporting views sit on top.
2. **Why a star schema?** Facts hold measurable events, dimensions hold the descriptive context. It keeps
   queries simple and is the shape BI tools like Power BI expect.
3. **How do you stop duplicate loads?** A row hash (content + occurrence number) with a UNIQUE constraint and
   an upsert, so re-running the same file changes nothing.
4. **What happens if a load fails halfway?** The transaction rolls back, the warehouse keeps its previous
   state, and `etl_run_log` records the failure and message.
5. **What is the difference between staging and the warehouse?** Staging is an untouched text copy of the
   latest extract; the warehouse tables are typed, constrained and modelled.
6. **ETL vs ELT?** Here the cleaning happens in Python before loading (ETL), and the reporting logic is done
   in SQL views (the ELT style). Explain which one you would pick at larger scale and why.
7. **How do you know the data is right?** Reconciliation checks (row counts, amount totals, foreign keys),
   and a test that the SQL runway equals the Python runway.
8. **Which SQL features did you use?** Joins, GROUP BY, window functions (running total, LAG, RANK, moving
   average), CTEs, correlated subqueries, conditional aggregation.
9. **How would you scale this?** Managed warehouse (Redshift, Snowflake, Synapse), an orchestrator for
   scheduling and retries, incremental extraction, partitioning, monitoring and alerts.
10. **What are the limits of your project?** Small synthetic data, SQLite, no scheduler, no real cloud
    deployment. Say this directly.

## Original project questions
Why deterministic arithmetic; why MCP; how to productionize; how to measure impact; what must remain human-controlled.
