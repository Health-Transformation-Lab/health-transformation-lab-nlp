"""Reports for the Health Transformation Lab benches (spec 029), served by FastAPI to a React front end.

    settings  every setting, declared once, checked at start
    sources   where the rows come from: a Databricks SQL warehouse, or the committed snapshot (DuckDB)
    benches   the bench registry: PerioBench, then OralHealthBench, then AccessBench, and each one's reports
    reports   one module per report: its SQL on the gold tables and the payload the front end draws
    main      the FastAPI app: /api/... and the built front end
"""
