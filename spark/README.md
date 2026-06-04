# Spark jobs

PySpark jobs for the Online Retail pipeline, organized using a **bronze → silver → gold** data lake structure. Results are also persisted in PostgreSQL for SQL-based analysis and orchestration via Airflow.

## Job overview

| Job | File | Input | Output |
|-----|------|-------|--------|
| Ingest | `ingest.py` | `data/retails.csv` | `data/bronze/retails_raw/` (Parquet) |
| Transform | `transform.py` | Bronze Parquet | `data/silver/retails_clean/` (Parquet) and `public.sales_clean` (PostgreSQL) |
| Analysis | `analysis.py` | Silver Parquet | `data/gold/retails_analysis/*/` (Parquet) and PostgreSQL tables |
| Test | `test.py` | CSV (connectivity check only) | Console output only; not part of the production pipeline |

**Execution order:** `ingest.py` → `transform.py` → `analysis.py`

Docker execution commands are documented in the [project README](../README.md).

---

## `ingest.py`: raw data ingestion (bronze layer)

**Objective:** Load the source CSV into the data lake with minimal transformation. Business rules are not applied at this stage.

**Processing steps:**
- Read `retails.csv` with header row and inferred schema
- Trim leading and trailing whitespace on string columns
- Add metadata columns: `ingested_at` (timestamp) and `source_file`
- Write output as Parquet using `mode("overwrite")`

**Design decisions:**
- Bronze layer preserves original column names (`InvoiceNo`, `CustomerID`, etc.) to allow reprocessing from source
- Data quality rules and PII handling are deferred to `transform.py` (clear separation between ingestion and transformation)
- Session timezone is set to UTC to ensure consistent timestamp handling

---

## `transform.py`: data cleaning and loading (silver layer)

**Objective:** Apply data quality rules, anonymize personally identifiable information (PII), and load the dataset used for downstream SQL and analytical processing.

**Processing steps:**
- Read bronze-layer Parquet files
- Standardize column names to `snake_case`
- Enforce appropriate data types (dates, numeric values, strings)
- Apply filtering rules:
  - Exclude invoices starting with `C` (cancellations)
  - Remove rows with null values on required fields
  - Exclude `quantity <= 0` and negative unit prices
  - Exclude test country `Utopia`
- Replace `CustomerID` with `customer_id_hash` (SHA-256 with salt)
- Remove duplicates based on `(invoice_no, stock_code, invoice_date, quantity)`
- Compute `revenue = round(quantity * unit_price, 2)`; the source `Revenue` column is not used (`revenue_source` is dropped)
- Derive `sale_date` and `sale_month` for aggregation purposes
- Write results to silver Parquet and to `public.sales_clean` via JDBC

**Design decisions:**
- **PII protection:** only `customer_id_hash` is persisted; the original `customer_id` is never stored in silver or PostgreSQL
- Hash salt is provided via `PII_HASH_SALT` (default `"secret"`; must be changed in production environments)
- **Dual persistence (Parquet and PostgreSQL):** Parquet supports efficient Spark processing; PostgreSQL supports SQL analysis and reporting
- Database connection parameters are read from environment variables (`POSTGRES_HOST`, default `localhost`; use `postgres` within Docker)

---

## `analysis.py`: analytical outputs (gold layer)

**Objective:** Compute the metrics required by the PySpark exercise and publish the results.

**Processing steps:**
- Read silver-layer Parquet (equivalent to `sales_clean`, without JDBC access)
- Generate four result datasets:
  1. **`total_revenue`:** sum of `revenue` across all cleaned records
  2. **`top_products`:** top 10 products ranked by **quantity sold** (not revenue)
  3. **`monthly_sales`:** monthly revenue, invoice count, and units sold
  4. **`monthly_stats`:** descriptive statistics on monthly revenue (average, median, min, max, standard deviation)
- Write results to driver logs for inspection
- Persist outputs under `data/gold/retails_analysis/<table>/` and in `public.<table>` in PostgreSQL

**Design decisions:**
- Silver Parquet is used as input rather than JDBC, keeping analysis as a dedicated Spark processing step
- Product ranking follows the exercise requirement (`total_quantity` descending)
- The additional `monthly_stats` table supports interpretation of revenue trends; complementary SQL analysis is defined in `postgres/queries/analysis.sql`

---

## Shared configuration

| Variable | Default | Used by |
|----------|---------|---------|
| `PIPELINE_ROOT` | `/opt/pipeline` | All jobs (file paths) |
| `POSTGRES_HOST` | `localhost` | Transform, analysis |
| `POSTGRES_DB` | `pipeline` | Transform, analysis |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `postgres` | Transform, analysis |
| `PII_HASH_SALT` | `secret` | Transform |

For JDBC-enabled jobs running in Docker, PostgreSQL connection settings must be passed to both the driver and executors (see main README).

**Spark configuration:** all jobs set `spark.sql.session.timeZone = UTC` and log level `WARN`.

**JDBC dependency:** transform and analysis require `--packages org.postgresql:postgresql:42.7.3` at submission time.

---

## `test.py`

Utility script to verify that Spark can read the source CSV. It is not used in production or in Airflow orchestration.
