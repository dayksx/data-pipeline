# Airflow orchestration

Airflow schedules the **ingest → transform** Spark pipeline on the standalone cluster. SQL and gold-layer analysis remain manual steps (see [project README](../README.md)).

## DAG: `dags/etl_pipeline.py`

| Setting | Value | Reason |
|---------|-------|--------|
| `dag_id` | `online_retail_pipeline` | Matches the Online Retail exercise |
| `schedule` | `@daily` | Exercise requires a daily run |
| `catchup` | `False` | Avoid backfilling past dates on first enable |
| `default_args` | `retries=2`, `retry_delay=5 min` | Handles transient Spark or DB failures |

### Tasks

```text
ingest_retails_csv  →  transform_clean_data
```

| Task | Spark job | Notes |
|------|-----------|--------|
| `ingest_retails_csv` | `/opt/pipeline/spark/jobs/ingest.py` | CSV → bronze Parquet |
| `transform_clean_data` | `/opt/pipeline/spark/jobs/transform.py` | Cleaning, PII hash, silver + `sales_clean` |

Both tasks use **`SparkSubmitOperator`** with connection `spark_default` (`spark://spark-master:7077` from `docker-compose.yml`).

`transform_clean_data` also needs:

- `--packages org.postgresql:postgresql:42.7.3`
- `spark.driverEnv` / `spark.executorEnv` for `POSTGRES_HOST=postgres` (and DB credentials)

Same parameters as the manual `spark-submit` commands in the main README.

### Out of scope for the DAG (by design)

- **`analysis.py`**: not required for the daily ingest/transform orchestration in the exercise; run manually or add a third task if needed.
- **SQL** (`postgres/queries/analysis.sql`): run after `sales_clean` exists, outside Airflow.

## Design choices

| Choice | Why |
|--------|-----|
| **SparkSubmitOperator** | Submits PySpark jobs to the existing Docker Spark cluster; no duplicate compute inside Airflow workers |
| **Jobs on `/opt/pipeline`** | Repo root is mounted in Airflow and Spark containers; one path for scripts and data |
| **LocalExecutor** | Single-machine exercise stack; scheduler runs tasks in-process without a Celery/Kubernetes setup |
| **Custom image** (`airflow/Dockerfile`) | OpenJDK 17 required for `spark-submit` from Airflow tasks |
| **Postgres DB `airflow`** | Metadata only; business data stays in DB `pipeline` |
| **`airflow-init` service** | One-shot DB migration and `admin` user before webserver/scheduler start |
| **Scheduler depends on Spark worker** | Reduces failures when the first DAG run starts before the cluster is up |

## Layout

```text
airflow/
├── Dockerfile          # Airflow 2.9.2 + Java 17
├── dags/
│   └── etl_pipeline.py # DAG definition (add or enable in repo)
├── logs/               # Task logs (mounted volume)
└── plugins/            # Optional operators/hooks
```

## Run

1. Start the stack: `docker compose up -d` (see main README).
2. Place or verify `dags/etl_pipeline.py`.
3. Open http://localhost:8088 (`admin` / `admin`).
4. Enable **`online_retail_pipeline`**, then **Trigger DAG** (or wait for `@daily`).

Task logs: Airflow UI → DAG → task instance → Log, or files under `airflow/logs/`.
