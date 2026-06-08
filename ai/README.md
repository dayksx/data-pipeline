# AI Insights Agent

This directory contains a small LangGraph agent that answers questions about the
retail data pipeline warehouse in PostgreSQL.

The agent does not read raw files directly. It uses a semantic layer and
read-only SQL tools to query the cleaned and gold tables produced by the Spark
pipeline.

## What is inside

- `src/insights_agent/` - Python package for the CLI, LangGraph graph, config,
  semantic loader, and SQL tools.
- `semantic/` - YAML files that describe the dataset, metrics, tables, and
  known caveats.
- `ARCHITECTURE.md` - design notes and the reasoning behind the agent.
- `TUTORIAL.md` - step-by-step build guide.
- `pyproject.toml` - package metadata and dependencies.

## Prerequisites

- Python 3.11+
- The main data pipeline running with PostgreSQL available
- The warehouse tables created by the Spark jobs:
  - `sales_clean`
  - `total_revenue`
  - `top_products`
  - `monthly_sales`
  - `monthly_stats`
- An LLM API key

## Setup

From this directory:

```bash
cd ai
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create an `.env` file in `ai/`:

```env
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pipeline
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Adjust the PostgreSQL values if your local setup uses different credentials or
ports.

## Usage

Ask a question with the `insights` CLI:

```bash
insights ask "What is the total revenue?"
```

Show the tool calls and SQL used by the agent:

```bash
insights ask "What are the top 10 products by revenue?" --verbose
```

## How it works

1. The CLI sends the user question to the LangGraph workflow.
2. The LLM decides whether it needs the semantic layer or a SQL query.
3. SQL is validated so only one read-only query can run against allowed tables.
4. The final answer is generated from tool results only.

This keeps the agent auditable: numbers in the answer should come from SQL
results, not from model guesses.

## More Detail

Read `ARCHITECTURE.md` for the design overview and `TUTORIAL.md` for a full
walkthrough of how the agent is built.
