import json
from datetime import datetime
from unittest.mock import patch

import psycopg
import pytest

from insights_agent.tools import (
    TOOLS,
    _dumps,
    get_semantic_layer,
    run_gold_query,
    run_sql_readonly,
)


def test_tools_exported() -> None:
    names = {tool.name for tool in TOOLS}
    assert names == {"get_semantic_layer", "run_gold_query", "run_sql_readonly"}


def test_get_semantic_layer_returns_dataset_context() -> None:
    text = get_semantic_layer.invoke({})
    assert "online_retail" in text
    assert "customer_id_hash" in text


def test_run_gold_query_unknown_metric() -> None:
    payload = json.loads(run_gold_query.invoke({"metric_id": "not_a_metric"}))
    assert "error" in payload
    assert "total_revenue" in payload["available"]


def test_run_sql_readonly_rejects_drop() -> None:
    payload = json.loads(run_sql_readonly.invoke({"query": "DROP TABLE sales_clean"}))
    assert payload["error"] == "validation_failed"
    assert payload["errors"]


def test_run_sql_readonly_query_failed_returns_json_not_raise() -> None:
    with patch("insights_agent.tools.run_query", side_effect=psycopg.errors.UndefinedColumn("column x does not exist")):
        payload = json.loads(
            run_sql_readonly.invoke({"query": "SELECT country FROM public.sales_clean LIMIT 1"})
        )
    assert payload["error"] == "query_failed"
    assert "column x does not exist" in payload["message"]
    assert payload["sql"]


def test_dumps_serializes_datetime() -> None:
    payload = json.loads(_dumps({"ts": datetime(2011, 1, 1, 12, 0, 0)}))
    assert payload["ts"] == "2011-01-01T12:00:00"
