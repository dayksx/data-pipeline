# AI Insights Agent

LangGraph agent that answers natural-language questions about the retail pipeline
warehouse in PostgreSQL.

The agent does not read raw files directly. It uses a semantic layer (YAML) and
read-only SQL tools against `sales_clean` and gold tables produced by Spark.

## What is inside

- `src/insights_agent/` — CLI, LangGraph graph, config, semantic loader, SQL tools
- `semantic/` — dataset card and predefined gold KPIs (`metrics.yaml`)
- `tests/` — pytest guardrails (SQL validation, tools, semantic loader)
- `pyproject.toml` — package metadata and dependencies

## Prerequisites

- Python **3.11–3.13** (3.14 is not supported by this package yet)
- Pipeline running with PostgreSQL available (`POSTGRES_HOST=localhost` when running Python on the host)
- Warehouse tables from Spark jobs: `sales_clean`, `total_revenue`, `top_products`, `monthly_sales`, `monthly_stats`
- An LLM API key

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

## How it works

1. The CLI sends a `HumanMessage` to a LangGraph workflow (`agent` → `tools` → `answer`).
2. The LLM chooses tools: semantic layer, predefined gold KPIs, or validated read-only SQL.
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
