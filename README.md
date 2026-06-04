# Online Retail Data Pipeline

End-to-end data pipeline using **PostgreSQL**, a **Spark** standalone cluster, and **Airflow**, deployed with Docker Compose. Source dataset: `data/retails.csv`.

## Architecture

### Logical data model

The source data follows a retail sales model: customers place transactions (invoices), and each transaction contains one or more product lines.

![Logical data model](docs/image.png)

| Entity | Attributes in the diagram | How it appears in `retails.csv` |
|--------|---------------------------|----------------------------------|
| **Customer** | `CustomerId`, `Country` | `CustomerID`, `Country` on each row |
| **Transaction** | `InvoiceNo`, `InvoiceDate` | `InvoiceNo`, `InvoiceDate` on each row |
| **Product** | `StockCode`, `Description`, `Unit price` | `StockCode`, `Description`, `UnitPrice` on each row |
| **Transaction_Product** | `Quantity`, `Unit price`, `Revenue` | `Quantity`, `UnitPrice`, `Revenue` on each row |

**Is this diagram correct?** Yes, as a **logical model** for the Online Retail dataset. The CSV is a **denormalized export**: one row equals one **Transaction_Product** line, with customer, invoice, and product attributes repeated on the same row. The pipeline does not create four separate PostgreSQL tables; after cleaning, everything is stored at line-item level in `public.sales_clean` (silver layer), which matches the associative entity in the diagram.

**Cardinality in the diagram:**
- A customer can initiate zero or many transactions (`0..*`).
- A transaction contains one or many product lines (`1..*`).
- A product can appear on zero or many transaction lines (`0..*`).

This matches the exercise data: many lines per invoice, many products, and many customers.

### Technical stack

```text
retails.csv  →  ingest (bronze)  →  transform (silver + sales_clean)
                                              ↓
                                    analysis (gold + Postgres tables)
                                              ↓
                              postgres/queries/analysis.sql (SQL)

Orchestration (optional): Airflow DAG → Spark jobs on standalone cluster
Infrastructure: Docker Compose (Postgres, Spark master/worker, Airflow)
```

More detail on Spark jobs: [`spark/README.md`](spark/README.md).

## Prerequisites

- Docker Engine and Docker Compose v2
- Approximately 8 GB of available RAM
- `data/retails.csv` present in the repository

## 1. Build and start the stack

From the project root, run:

```bash
docker compose build
docker compose up -d
```

**On the first run:**

- **Postgres** executes scripts in `postgres/init/` (including creation of the `airflow` metadata database).
- **`airflow-init`** runs once (`airflow db migrate` and admin user creation), then exits.
- The other services remain active: Postgres, Spark master and worker, Airflow webserver and scheduler.

Verify that Postgres is healthy and that `airflow-init` has completed successfully:

```bash
docker compose ps
```

| Service | URL / access |
|---------|----------------|
| Airflow UI | http://localhost:8088 (`admin` / `admin`) |
| Spark UI | http://localhost:8080 |
| PostgreSQL | `localhost:5432` (`postgres` / `postgres`, database `pipeline`) |

## 2. Run the pipeline (Spark)

Submit jobs from the `pipeline-spark-master` container. The repository is mounted at `/opt/pipeline` inside the containers.

**Ingest** (CSV to bronze Parquet):

```bash
docker exec pipeline-spark-master spark-submit \
  --master spark://spark-master:7077 \
  --name ingest-retails \
  /opt/pipeline/spark/jobs/ingest.py
```

**Transform** (data cleaning, PII hashing, silver Parquet and `public.sales_clean`):

```bash
docker exec pipeline-spark-master spark-submit \
  --master spark://spark-master:7077 \
  --name transform-clean-data \
  --packages org.postgresql:postgresql:42.7.3 \
  --conf spark.driverEnv.POSTGRES_HOST=postgres \
  --conf spark.driverEnv.POSTGRES_DB=pipeline \
  --conf spark.driverEnv.POSTGRES_USER=postgres \
  --conf spark.driverEnv.POSTGRES_PASSWORD=postgres \
  --conf spark.executorEnv.POSTGRES_HOST=postgres \
  --conf spark.executorEnv.POSTGRES_DB=pipeline \
  --conf spark.executorEnv.POSTGRES_USER=postgres \
  --conf spark.executorEnv.POSTGRES_PASSWORD=postgres \
  /opt/pipeline/spark/jobs/transform.py
```

**Analysis** (`spark/jobs/analysis.py`, PySpark questions from the exercise):

```bash
docker exec pipeline-spark-master spark-submit \
  --master spark://spark-master:7077 \
  --name analysis-retails \
  --packages org.postgresql:postgresql:42.7.3 \
  --conf spark.driverEnv.POSTGRES_HOST=postgres \
  --conf spark.driverEnv.POSTGRES_DB=pipeline \
  --conf spark.driverEnv.POSTGRES_USER=postgres \
  --conf spark.driverEnv.POSTGRES_PASSWORD=postgres \
  --conf spark.executorEnv.POSTGRES_HOST=postgres \
  --conf spark.executorEnv.POSTGRES_DB=pipeline \
  --conf spark.executorEnv.POSTGRES_USER=postgres \
  --conf spark.executorEnv.POSTGRES_PASSWORD=postgres \
  /opt/pipeline/spark/jobs/analysis.py
```

The analysis job addresses the three PySpark requirements:

| Exercise question | Implementation | Postgres table | Driver logs |
|-------------------|----------------|----------------|-------------|
| **What is the total revenue generated in the dataset?** | `sum(revenue)` | `public.total_revenue` | Result printed at job completion |
| **Which are the top 10 most popular products based on the quantity sold?** | Group by product, order by `total_quantity`, `limit(10)` | `public.top_products` | Top 10 displayed with `.show(10)` |
| **What is the monthly revenue trend? Provide insights into any noticeable patterns or anomalies.** | Monthly revenue and summary statistics | `public.monthly_sales`, `public.monthly_stats` | Monthly breakdown and aggregate stats |

**Required execution order:** ingest → transform → analysis.

## 3. Run SQL analysis

Execute after `transform` has populated `sales_clean`:

```bash
docker exec -i pipeline-postgres psql -U postgres -d pipeline < postgres/queries/analysis.sql
```

## 4. Validate the results

**Verify the cleaned dataset** (loaded by `transform.py`):

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT COUNT(*) AS sales_clean_rows FROM public.sales_clean;"
```

**PySpark exercise answers** (available after `analysis.py`):

**What is the total revenue generated in the dataset?**

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT * FROM public.total_revenue;"
```

**Which are the top 10 most popular products based on the quantity sold?**

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT * FROM public.top_products ORDER BY total_quantity DESC;"
```

**What is the monthly revenue trend? Provide insights into any noticeable patterns or anomalies.**

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT TO_CHAR(sale_month, 'YYYY-MM') AS month,
          invoices_count, revenue, items_sold
   FROM public.monthly_sales
   ORDER BY sale_month;"
```

Note: `sale_month` is stored as a timestamp by Spark. `TO_CHAR` is used here for readable output only.

**Insights** (based on cleaned data from Jan 2010 to Dec 2011, consistent with `analysis.py`):

**Patterns**
- The time series shows **two distinct phases**: low revenue in **Jan–Nov 2010** (approximately £4k–£17k per month, few invoices), followed by a **stable high-volume phase** from **Dec 2010** onward (approximately £840k–£980k per month, around 100 invoices per month).
- Throughout **2011**, monthly revenue remains within a **narrow range** with stable invoice counts, consistent with **recurring B2B wholesale** activity rather than strong retail seasonality.
- Revenue **increases gradually during 2011**, reaching a peak in **August 2011** (approximately £981k), followed by moderate fluctuations until the end of the dataset.
- In peak months, approximately **100 invoices** account for roughly **35,000 line items** (about 350 lines per invoice), which is typical of B2B order patterns.

**Anomalies**
- **December 2010** shows a major step change: revenue increases from approximately **£6k (November)** to **£848k (December)** (roughly 140×), with invoice volume rising from single digits to about 100. Early 2010 should be treated as a **ramp-up period**, not comparable to 2011 operating levels.
- **December 2011** appears weak (approximately £252k), but the source file **ends on 11 December 2011**. This month is **incomplete** and should not be interpreted as a business decline.
- **May 2010** records the lowest monthly revenue (approximately £4.4k, 5 invoices), likely due to **limited data coverage** at the beginning of the extract.
- The **standard deviation** is close to the **mean** monthly revenue because of early low values and the December 2010 discontinuity. The **median** (approximately £547k) better represents a typical month once the ramp-up period is excluded.

**Summary statistics** (also available in `public.monthly_stats` and in the analysis job logs):

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT * FROM public.monthly_stats;"
```

Reference values: total cleaned revenue approximately **£10.98M** over **24 months**; peak month **August 2011**; lowest month **May 2010**.

**Expected output directories on the host:**

- `data/bronze/retails_raw/`: raw Parquet files
- `data/silver/retails_clean/`: cleaned Parquet files
- `data/gold/retails_analysis/`: analytical Parquet outputs

## 5. Airflow (orchestration)

After completing step 1, the Airflow UI is available. To schedule **ingest → transform**, add a DAG under `airflow/dags/` (for example `etl_pipeline.py` using `SparkSubmitOperator` with the same job paths and Spark/Postgres configuration as in step 2). Then:

1. Open http://localhost:8088 and sign in with `admin` / `admin`.
2. Enable the DAG.
3. Use **Trigger DAG** for a manual execution, or wait for the `@daily` schedule.

The scheduler is already configured to depend on Spark and Postgres. No additional initialization is required beyond `docker compose up -d`.

## Reset the environment

Stop all services and remove the Postgres volume (this clears business data and Airflow metadata):

```bash
docker compose down -v
```

Then repeat from **step 1**. The `airflow-init` service will run again on the next `docker compose up`.

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `ClassNotFoundException: org.postgresql.Driver` | Include `--packages org.postgresql:postgresql:42.7.3` for transform and analysis jobs |
| JDBC connection refused from Spark | Set host to `postgres` (not `localhost`) using `spark.driverEnv` and `spark.executorEnv` |
| Permission errors on `airflow/logs` (SELinux) | Volume mounts use the `:z` flag; ensure the directory exists: `mkdir -p airflow/logs` |
| `airflow-init` already completed | Expected on restart; the admin user is recreated only after `docker compose down -v` |
