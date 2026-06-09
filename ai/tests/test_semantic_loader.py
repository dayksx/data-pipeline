import pytest

from insights_agent.semantic_loader import build_semantic_context, get_metric, load_metrics


def test_load_metrics_contains_gold_kpis() -> None:
    metrics = load_metrics()
    assert "total_revenue" in metrics
    assert "top_products_by_quantity" in metrics
    assert "monthly_revenue_trend" in metrics


def test_get_metric_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown metric_id"):
        get_metric("does_not_exist")


def test_build_semantic_context_mentions_sql_notes() -> None:
    text = build_semantic_context()
    assert "SQL note:" in text
    assert "customer_id_hash" in text
    assert "run_gold_query" in text
