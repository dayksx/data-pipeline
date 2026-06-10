import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
import sqlglot
from langchain_core.tools import tool
from psycopg.rows import dict_row
from sqlglot import exp

from insights_agent.config import ALLOWED_TABLES, get_settings
from insights_agent.semantic_loader import build_semantic_context, get_metric, load_metrics

from langchain_openai import OpenAIEmbeddings

def _json_safe(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def _dumps(data: Any) -> str:
    return json.dumps(_json_safe(data))


def run_query(sql: str) -> dict[str, Any]:
    """Execute one SQL statement and return rows as list of dicts."""
    settings = get_settings()
    max_rows = settings.sql_max_rows

    with psycopg.connect(settings.postgres_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = '{settings.sql_timeout_seconds}s'")
            cur.execute(sql)
            rows = cur.fetchmany(max_rows + 1)

        truncated = len(rows) > max_rows

        if truncated:
            rows = rows[:max_rows]

        columns = list(rows[0].keys()) if rows else []

        return {
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }



@dataclass
class SqlValidation:
    ok: bool
    sql: str | None
    errors: list[str]

def validate_sql(query: str) -> SqlValidation:
    errors: list[str] = []
    q = query.strip().rstrip(";")

    if not q:
        return SqlValidation(False, None, ["Empty query"])

    if ";" in q:
        return SqlValidation(False, None, ["Only one SQL statement allowed"])

    try:
        parsed = sqlglot.parse_one(q, read="postgres")

    except sqlglot.errors.ParseError as e:
            return SqlValidation(False, None, [f"Parse error: {e}"])

    if not isinstance(parsed, (exp.Select, exp.Union)):
        return SqlValidation(False, None, ["Only SELECT / UNION queries allowed"])

    for table in parsed.find_all(exp.Table):
        name = (table.name).lower()
        if name not in ALLOWED_TABLES:
            errors.append(f"Table not allowed: {name}")

    if errors: 
        return SqlValidation(False, None, errors)

    settings = get_settings()

    if parsed.args.get("limit") is None or parsed.args.get("limit") > settings.sql_max_rows:
        parsed = parsed.limit(settings.sql_max_rows)

    safe_sql = parsed.sql(dialect="postgres")
    return SqlValidation(True, safe_sql, [])
    

def search_rag(query: str, top_k: int) -> dict:

    settings = get_settings()
    # Embed the query to get a vector
    embedder = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.llm_api_key)
    query_vector = embedder.embed_query(query)

    with psycopg.connect(settings.postgres_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                # score = 1 - cosinus distance
                """
                SELECT source, section, content, 1 - (embedding <=> %s::vector) AS score
                FROM public.rag_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vector, query_vector, top_k),
            )
            rows = cur.fetchall()

    if not rows:
        return {"error": "index_empty", "hint": "Run RAG pipeline to populate the index"}

    return {"chunks": rows, "query": query}

# Agentic Tools
    
@tool
def get_semantic_layer() -> str:
    """Dataset grain, columns, time range, known anomalies (from dataset_card.yaml)."""
    return build_semantic_context()

@tool
def run_gold_query(metric_id: str) -> str:
    """Predefined KPI. IDs: total_revenue, top_products_by_quantity, monthly_revenue_trend."""
    try:
        spec = get_metric(metric_id)
    except KeyError as e:
        return json.dumps({
            "error": str(e),
            "available": sorted(load_metrics()),
        })
    try:
        result = run_query(spec["sql"])

    except psycopg.Error as exc:
        return _dumps({
            "error": "query_failed",
            "message": str(exc).strip(),
            "sql": spec["sql"],
        })

    return _dumps({
        "metric_id": metric_id,
        "description": spec.get("description", ""),
        **result,
    })

@tool
def run_sql_readonly(query: str) -> str:
    """Run one PostgreSQL SELECT on sales_clean or gold tables. Invalid SQL is rejected."""
    validation = validate_sql(query)
    if not validation.ok:
        return json.dumps({
            "error": "validation_failed",
            "errors": validation.errors,
            "sql": query,
        })

    try:
        result = run_query(validation.sql)

    except psycopg.Error as exc:
        # Fail closed on validate_sql; graceful on execution so the LLM can retry.
        return _dumps({
            "error": "query_failed",
            "message": str(exc).strip(),
            "sql": validation.sql,
        })

    return _dumps(result)

@tool
def search_analyses(query: str) -> str:
    """Search qualitative analysis reports (anomalies, patterns, B2B context, data quality).
    Use for WHY/HOW questions, not for live KPI numbers — use run_gold_query or run_sql_readonly for metrics."""

    config = get_settings()

    return _dumps(search_rag(query, config.rag_top_k))

TOOLS = [get_semantic_layer, run_gold_query, run_sql_readonly, search_analyses]

