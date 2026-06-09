# RAG — corpus and vector store

Qualitative analysis reports indexed in **pgvector** for the insights agent. Each `.md` file is a standalone report retrieved via vector similarity search, alongside the YAML semantic layer and SQL warehouse.

## Corpus (`docs/`)

| File | Topic | Typical questions |
|------|-------|-------------------|
| `01-tendances-revenus-mensuels.md` | Monthly trends, Dec 2010 / Dec 2011 anomalies | « Why did revenue jump in December 2010? » |
| `02-performance-produits.md` | Top products, volume vs revenue | « What are the bestsellers? » |
| `03-repartition-geographique.md` | Country mix, Australia focus | « Which country earns the most? » |
| `04-comportement-b2b.md` | Large baskets, wholesale profile | « Is this B2B or B2C? » |
| `05-qualite-donnees-nettoyage.md` | Exclusions, cleaning impact | « Why is Utopia filtered out? » |

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
    source      TEXT NOT NULL,          -- e.g. 01-tendances-revenus-mensuels.md
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

The table is empty until you run `insights index`.

> **Note:** Plain `postgres:16` does not include the `vector` extension. Use `pgvector/pgvector:pg16` or init will fail and Postgres stays unhealthy.

## Layout

```text
ai/rag/
├── README.md           # this file
├── docs/               # markdown corpus (chunked by ## sections)
└── jobs/               # batch pipeline (like spark/jobs/)
    ├── chunking.py     # docs/ → chunks
    └── index.py        # chunks → embed → rag_chunks (CLI + Airflow entry point)

ai/src/insights_agent/rag/
└── retriever.py        # runtime: similarity search for the agent tool

postgres/init/
└── create_pgvector_db.sql

airflow/dags/medallion_pipeline.py
└── index_rag_docs      # task after analyze_sales_data
```

## Usage

### Dev — manual index

After `docker compose up -d` and `LLM_API_KEY` in `ai/.env`:

```bash
cd ai && source .venv/bin/activate
pip install -e ".[dev]"
insights index
# or: python rag/jobs/index.py
```

### Prod — Airflow

DAG `sales_medallion_pipeline`: `ingest` → `transform` → `analysis` → **`index_rag_docs`**.

Set Airflow Variable `LLM_API_KEY`. Task runs `python /opt/pipeline/ai/rag/jobs/index.py` inside the Compose network (`POSTGRES_HOST=postgres`).

See [`local/RAG-TUTORIAL.md`](../../local/RAG-TUTORIAL.md) Phase 6 for full setup.

**Query** (once `search_analyses` tool is wired in the agent):

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

## Batch vs runtime

| Layer | Path | Trigger |
|-------|------|---------|
| **Batch** | `ai/rag/jobs/` | Airflow `index_rag_docs`, or `insights index` in dev |
| **Runtime** | `insights_agent/rag/retriever.py` | Agent tool `search_analyses` on each question |

Same pattern as `spark/jobs/` (batch warehouse) vs insights agent (interactive queries).

## Next steps

1. Implement `rag/jobs/chunking.py` and `rag/jobs/index.py`
2. Implement `insights_agent/rag/retriever.py` + `search_analyses` in `tools.py`
3. Wire `insights index` CLI and Airflow task `index_rag_docs`
