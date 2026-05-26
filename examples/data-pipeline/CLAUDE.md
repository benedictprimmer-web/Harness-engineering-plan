# Acme Analytics Pipeline

## Project

A dbt + Airflow data pipeline that transforms raw IoT sensor telemetry from the operational database into analytics-ready tables in the Acme data warehouse (Snowflake). Runs daily in production; supports ad-hoc backfill runs. Downstream consumers include the BI dashboards (Metabase) and the alert rule evaluation service.

## Stack

- **Runtime**: Python 3.11, managed with `uv`
- **Transformation**: dbt-core 1.8 + dbt-snowflake adapter
- **Orchestration**: Apache Airflow 2.9 (deployed on Astronomer)
- **Warehouse**: Snowflake (prod), DuckDB (local dev/testing)
- **Testing**: pytest + dbt tests (schema tests, custom data tests)
- **Linting**: Ruff, sqlfluff (for SQL in dbt models)

## Commands

```bash
uv sync                         # install Python deps
dbt deps                        # install dbt packages
dbt debug                       # verify connection
dbt compile                     # compile models (no execution)
dbt run                         # run all models against dev target
dbt run --select +my_model      # run a model and its upstream deps
dbt test                        # run all dbt tests
dbt test --select my_model      # test a specific model
dbt docs generate && dbt docs serve   # generate + view docs
sqlfluff lint models/           # lint SQL files
uv run pytest                   # run Python unit tests
```

## Architecture

```
dbt/
  models/
    staging/          ← 1:1 with source tables, light cleaning only
      _sources.yml    ← source definitions (raw tables in Snowflake)
      stg_*.sql       ← staging models (prefix: stg_)
    intermediate/     ← joins and business logic, not exposed to BI
      int_*.sql       ← intermediate models (prefix: int_)
    marts/            ← final analytics tables, exposed to BI tools
      core/           ← entity-level facts and dimensions
      finance/        ← revenue and billing metrics
      operations/     ← device and alert metrics
  tests/              ← custom data tests (singular tests)
  macros/             ← reusable SQL macros
  seeds/              ← static reference data (CSV → table)
  snapshots/          ← SCD type 2 snapshots
  dbt_project.yml     ← project config, model materializations
  profiles.yml        ← connection profiles (NOT committed — see below)
airflow/
  dags/               ← Airflow DAG definitions
  plugins/            ← custom Airflow operators/hooks
tests/                ← pytest tests for Python code in airflow/
```

## Conventions

- **Model naming**: `stg_` prefix for staging, `int_` prefix for intermediate, no prefix for marts
- **Materialization defaults**: staging = view, intermediate = ephemeral, marts = table (configured in `dbt_project.yml`)
- **One model per file**: each `.sql` file defines exactly one model
- **Sources defined in `_sources.yml`**: never reference raw tables directly in models — always go through `{{ source() }}`
- **Refs not hard-coded names**: always use `{{ ref('model_name') }}` to reference other models
- **Column descriptions in YAML**: every mart model must have column descriptions in its `.yml` schema file
- **No SELECT \***: always list columns explicitly in models
- **Idempotent DAGs**: all Airflow DAGs must be safe to re-run for the same execution date

## Environment

`profiles.yml` is **not committed** (it contains credentials). Each developer maintains their own at `~/.dbt/profiles.yml`.

For local dev, use the `dev` profile target which points to:
- Your personal Snowflake dev schema: `DEV_<YOUR_NAME>` (e.g., `DEV_ALICE`)
- Or local DuckDB: `dbt run --profiles-dir .dbt-local` (uses `dbt-local/profiles.yml.example`)

Required environment variables:
- `SNOWFLAKE_ACCOUNT` — get from 1Password → "Snowflake Dev Credentials"
- `SNOWFLAKE_USER` / `SNOWFLAKE_PASSWORD` — same
- `SNOWFLAKE_ROLE` — typically `TRANSFORMER` for dev, `TRANSFORMER_PROD` in CI
- `AIRFLOW__CORE__SQL_ALCHEMY_CONN` — Airflow metadata DB (only needed for Airflow DAG testing)

## Gotchas

- **Dev target only for dbt run**: always run against `--target dev` (default). Never run `dbt run --target prod` locally — production runs only happen in CI/CD.
- **Full refresh is destructive**: `dbt run --full-refresh` drops and recreates tables. Never run with `--target prod` without a change window approved by the data team.
- **`profiles.yml` must NOT be committed**: it's in `.gitignore`. If you see it in `git status`, do not stage it.
- **DuckDB for unit testing**: most dbt model logic can be tested locally with DuckDB without Snowflake access. Use `--profiles-dir .dbt-local` for this.
- **Airflow DAG bag parse errors**: Airflow imports all files in `dags/` — a syntax error in any `.py` file breaks the whole DAG bag. Always run `python dags/my_dag.py` to check for import errors before committing.
- **`dbt deps` after pulling**: if `packages.yml` changed, run `dbt deps` to update installed packages. Missing packages cause cryptic compilation errors.
- **Snowflake zero-copy cloning**: the prod schema is cloned daily into `PROD_CLONE` for ad-hoc queries. Query `PROD_CLONE` for analytics work — not `PROD` directly.
