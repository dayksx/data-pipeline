# RAG — corpus and vector store

Qualitative analysis reports indexed in **pgvector** for the insights agent. Each `.md` file is a standalone report retrieved via vector similarity search, alongside the YAML semantic layer and SQL warehouse.

## Corpus (`docs/`)

| File | Topic | Typical questions |
|------|-------|-------------------|
| `01-monthly-revenue-trends.md` | Monthly trends, Dec 2010 / Dec 2011 anomalies | "Why did revenue jump in December 2010?" |
| `02-product-performance.md` | Top products, volume vs revenue | "What are the bestsellers?" |
| `03-geographic-distribution.md` | Country mix, Australia focus | "Which country earns the most?" |
| `04-b2b-behavior.md` | Large baskets, wholesale profile | "Is this B2B or B2C?" |
| `05-data-quality-cleaning.md` | Exclusions, cleaning impact | "Why is Utopia filtered out?" |

Figures in the reports were computed from `data/retails.csv` using the same rules as `spark/jobs/transform.py`. **Live KPIs** should still come from SQL (`run_gold_query` / `run_sql_readonly`), not from RAG alone.

## Vector database (pgvector)

RAG chunks live in the **same Postgres instance** as the medallion warehouse (`pipeline` database). No separate vector DB service.

| Item | Value |
|------|-------|
| Docker image | `pgvector/pgvector:pg16` (root `docker-compose.yml`) |
| Init script | `postgres/init/create_pgvector_db.sql` |
| Extension | `vector` (pgvector) |
| Table | `public.rag_chunks` |
| Embedding model | `text-embedding-3-small` (1536 dimensions) |

### Table schema

```sql
CREATE TABLE public.rag_chunks (
    id          SERIAL PRIMARY KEY,
    chunk_id    TEXT NOT NULL UNIQUE,   -- stable hash: source + section
    source      TEXT NOT NULL,          -- e.g. 01-monthly-revenue-trends.md
    section     TEXT NOT NULL,          -- ## heading
    content     TEXT NOT NULL,          -- chunk text returned to the agent
    embedding   vector(1536) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

`content` and metadata are stored **with** the embedding so retrieval returns text the LLM can use — not just similarity scores.

### Verify on first boot

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c "\dx vector"
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c "\d public.rag_chunks"
```

The table is empty until you run the index job (see **Usage** below).

> **Note:** Plain `postgres:16` does not include the `vector` extension. Use `pgvector/pgvector:pg16` or init will fail and Postgres stays unhealthy.

## Layout

```text
ai/rag/
├── README.md
├── docs/                    # markdown corpus (5 analysis reports)
├── .warehouse_state.json    # fingerprint — skip regen if SQL unchanged
└── jobs/
    ├── chunking.py          # docs/ → chunks (helper)
    ├── generate_reports.py  # SQL → rewrite docs/ when warehouse changes
    └── index.py             # batch job: chunks → embed → rag_chunks (+ __main__)
```

## Usage

### Regenerate reports from SQL (daily check)

After Spark `analysis` has loaded gold tables, refresh the markdown corpus if the warehouse changed:

```bash
cd ai && source .venv/bin/activate

# Check only — no writes
python rag/jobs/generate_reports.py --check-only

# Regenerate 5 .md files when fingerprint changed
python rag/jobs/generate_reports.py

# Force rewrite even if SQL unchanged
python rag/jobs/generate_reports.py --force
```

Fingerprint uses `sales_clean` row count, total revenue, date range, and gold table counts.  
If `updated: true`, run `python rag/jobs/index.py` to re-embed.

**Cron example** (daily at 06:00, after Airflow DAG):

```bash
0 6 * * * cd /path/to/ai && .venv/bin/python rag/jobs/generate_reports.py | grep -q '"updated": true' && .venv/bin/python rag/jobs/index.py
```

### Index (manual)

After `docker compose up -d`, `LLM_API_KEY` in `ai/.env`, and `pip install -e ".[dev]"` from `ai/`:

```bash
cd ai
source .venv/bin/activate
python rag/jobs/index.py
```

Expected output:

```json
{
  "indexed": 38,
  "sources": ["01-monthly-revenue-trends.md", "..."]
}
```

Verify in Postgres:

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT COUNT(*) FROM rag_chunks;"
```

### Prod — Airflow

DAG `sales_medallion_pipeline`: `ingest` → `transform` → `analysis` → **`index_rag_docs`**.

Set Airflow Variable `LLM_API_KEY`. Task runs `python /opt/pipeline/ai/rag/jobs/index.py` inside the Compose network (`POSTGRES_HOST=postgres`).

See [`local/RAG-TUTORIAL.md`](../../local/RAG-TUTORIAL.md) Phase 6 for full setup.

**Query** (via `search_analyses` tool in the agent):

```bash
insights ask "Why is December 2011 revenue low?" --verbose
```

**Inspect index:**

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT COUNT(*) FROM rag_chunks;"

docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT source, section FROM rag_chunks ORDER BY source, id;"
```

## Three sources — when to use what

| Question type | Tool / source |
|---------------|---------------|
| Column meaning, schema | `get_semantic_layer` (YAML) |
| Numbers, aggregates, filters | `run_gold_query` / `run_sql_readonly` (SQL) |
| Why / patterns / anomalies / B2B context | `search_analyses` (RAG) |

### Batch vs runtime

| Layer | Path | How to run |
|-------|------|------------|
| **Batch** | `ai/rag/jobs/index.py` | `python rag/jobs/index.py` or Airflow `index_rag_docs` |
| **Runtime** | `ai/src/insights_agent/tools.py` | `search_rag` + `@tool search_analyses` |
