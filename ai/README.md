# AI Insights Agent

LangGraph agent that answers natural-language questions about the retail pipeline
warehouse in PostgreSQL.

The agent does not read raw files directly. It uses three complementary sources:

| Source | Role | Example question |
|--------|------|------------------|
| **`semantic/*.yaml`** | Schema, grain, column definitions | « What does `sale_month` mean? » |
| **SQL (Postgres)** | Live KPIs and ad-hoc analytics | « What is total revenue? » |
| **RAG (`rag/docs/` + pgvector)** | Qualitative analysis reports | « Why did revenue jump in Dec 2010? » |

Numbers must come from SQL. RAG provides context and interpretation from indexed markdown reports stored in `public.rag_chunks`.

## What is inside

- `src/insights_agent/` — CLI, LangGraph graph, config, semantic loader, SQL tools
- `semantic/` — dataset card and predefined gold KPIs (`metrics.yaml`)
- `rag/docs/` — analysis reports corpus (see [`rag/README.md`](rag/README.md))
- `tests/` — pytest guardrails (SQL validation, tools, semantic loader)
- `pyproject.toml` — package metadata and dependencies

## Prerequisites

- Python **3.11–3.13** (3.14 is not supported by this package yet)
- Pipeline running with PostgreSQL available (`POSTGRES_HOST=localhost` when running Python on the host)
- Warehouse tables from Spark jobs: `sales_clean`, `total_revenue`, `top_products`, `monthly_sales`, `monthly_stats`
- Postgres with **pgvector** (`pgvector/pgvector:pg16` in root `docker-compose.yml`) and table `public.rag_chunks` (created by `postgres/init/create_pgvector_db.sql` on first boot)
- An LLM API key (chat + embeddings for RAG indexing)

## Setup

From this directory:

```bash
cd ai
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy env vars and set your API key:

```bash
cp .env.example .env
# edit .env — at minimum LLM_API_KEY
```

Use `POSTGRES_HOST=localhost` when Postgres runs via Docker Compose on the host.
Use `POSTGRES_HOST=postgres` only when the agent itself runs inside the Compose network.

After a reboot, activate the venv again in each new terminal (`source .venv/bin/activate`).
You do not need to re-run `pip install` unless dependencies change.

## Usage

Single question:

```bash
insights ask "What is the total revenue?"
```

Show tool calls and SQL:

```bash
insights ask "Top 10 products by quantity" --verbose
```

Machine-readable output:

```bash
insights ask "Monthly revenue trend" --json
```

Interactive chat (conversation memory within the session):

```bash
insights chat
```

Type `exit`, `quit`, or `q` to leave. Chat uses a dedicated LangGraph thread
(`chat_session`); one-shot `ask` uses `ask_session` so it does not mix with chat history.

### RAG (vector store)

Index the analysis reports into Postgres (`insights index` — see [`rag/README.md`](rag/README.md)):

```bash
insights index
```

Verify chunks in pgvector:

```bash
docker exec -it pipeline-postgres psql -U postgres -d pipeline -c \
  "SELECT source, section, LEFT(content, 50) FROM rag_chunks LIMIT 5;"
```

Then ask qualitative questions:

```bash
insights ask "Why is December 2011 revenue low?" --verbose
```

## How it works

1. The CLI sends a `HumanMessage` to a LangGraph workflow (`agent` → `tools` → `answer`).
2. The LLM chooses tools: semantic layer, predefined gold KPIs, validated read-only SQL, or RAG search over `rag_chunks`.
3. SQL is parsed and restricted to allowed tables; Postgres errors are returned as JSON so the agent can retry.
4. With tools, the `answer` node summarizes tool output only; without tools, the agent reply is returned directly.
5. A `MemorySaver` checkpointer keeps message history per `thread_id` (used by `insights chat`).

Numbers in answers should come from SQL results, not from model guesses.

## Tests

```bash
cd ai
source .venv/bin/activate
pytest -q
```
