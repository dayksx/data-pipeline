# Airflow orchestration

Airflow schedules the full **ingest → transform → analysis** Spark pipeline on the standalone cluster. SQL analysis remains a manual step (see [project README](../README.md)).

## DAG: `dags/medallion_pipeline.py`

| Setting | Value | Reason |
|---------|-------|--------|
| `dag_id` | `sales_medallion_pipeline` | Medallion pipeline for Online Retail |
| `schedule` | `@daily` | Exercise requires a daily run |
| `catchup` | `False` | Avoid backfilling past dates on first enable |

### Tasks

```text
ingest_retails_csv  →  transform_clean_data  →  analyze_sales_data
```

| Task | Spark job | Notes |
|------|-----------|--------|
| `ingest_retails_csv` | `/opt/pipeline/spark/jobs/ingest.py` | CSV → bronze Parquet |
| `transform_clean_data` | `/opt/pipeline/spark/jobs/transform.py` | Cleaning, PII hash, silver Parquet + `public.sales_clean` |
| `analyze_sales_data` | `/opt/pipeline/spark/jobs/analysis.py` | Gold metrics → Parquet + Postgres (`total_revenue`, `top_products`, `monthly_sales`, `monthly_stats`) |

All tasks use **`SparkSubmitOperator`** with connection `spark_default` (`spark://spark-master:7077` from `docker-compose.yml`).

`transform_clean_data` and `analyze_sales_data` also need:

- `--packages org.postgresql:postgresql:42.7.3` (set via `packages` on the operator)

Spark jobs default to `POSTGRES_HOST=postgres` and database `pipeline`; no extra `spark.driverEnv` is required when running inside Docker. For manual `spark-submit` from the host, use the `--conf spark.driverEnv` / `spark.executorEnv` flags documented in the main README.

### Out of scope for the DAG

- **SQL** (`postgres/queries/analysis.sql`): run after `sales_clean` exists, outside Airflow (main README, step 3).

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
├── Dockerfile                    # Airflow 2.9.2 + Java 17
├── dags/
│   └── medallion_pipeline.py     # DAG sales_medallion_pipeline
├── logs/                         # Task logs (mounted volume)
└── plugins/                      # Optional operators/hooks
```

## Run

1. Start the stack: `docker compose up -d` (see main README).
2. Open http://localhost:8088 (`admin` / `admin`).
3. Enable **`sales_medallion_pipeline`**, then **Trigger DAG** (or wait for `@daily`).

Task logs: Airflow UI → DAG → task instance → Log, or files under `airflow/logs/`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `up_for_retry` on `ingest_retails_csv` | Real Spark failure, then Airflow retries (expected) | Open task **Log**; see error at the bottom |
| `Unable to clear output directory` | Parquet under `data/` owned by another uid (often 1001 from older Spark images) | Reset: `docker exec -u root pipeline-spark-master rm -rf /opt/pipeline/data/bronze /opt/pipeline/data/silver /opt/pipeline/data/gold`, then **Clear** + **Trigger**. Spark and Airflow both use uid **50000** (`docker-compose.yml`) |

`up_for_retry` with a 5-minute wait is normal after a failure — not a freeze. The task will retry up to 2 times, then turn **failed** if the underlying error persists.
