"""Load static semantic layer YAML for the insights agent."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from insights_agent.config import get_settings


def _semantic_dir() -> Path:
    path = get_settings().semantic_dir
    if not path.is_dir():
        raise FileNotFoundError(f"Semantic directory not found: {path}")
    return path


def _read_yaml(filename: str) -> dict[str, Any]:
    path = _semantic_dir() / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing semantic file: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}, got {type(data).__name__}")
    return data


@lru_cache
def load_dataset_card() -> dict[str, Any]:
    return _read_yaml("dataset_card.yaml")


@lru_cache
def load_metrics() -> dict[str, dict[str, Any]]:
    data = _read_yaml("metrics.yaml")
    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("metrics.yaml must contain a non-empty 'metrics' mapping")
    return metrics


def get_metric(metric_id: str) -> dict[str, Any]:
    metrics = load_metrics()
    if metric_id not in metrics:
        available = ", ".join(sorted(metrics))
        raise KeyError(f"Unknown metric_id '{metric_id}'. Available: {available}")
    return metrics[metric_id]


def _format_columns(table_spec: dict[str, Any]) -> str:
    columns = table_spec.get("columns", [])
    parts: list[str] = []
    for col in columns:
        if isinstance(col, dict) and "name" in col:
            desc = col.get("description", "")
            parts.append(f"{col['name']} ({col.get('type', '?')})" + (f": {desc}" if desc else ""))
    return "; ".join(parts) if parts else "(no column metadata)"


def build_semantic_context() -> str:
    """Build a compact text block for the LLM (tool get_semantic_layer / SQL generation)."""
    card = load_dataset_card()
    lines: list[str] = [
        f"Dataset: {card.get('dataset', 'unknown')}",
        f"Description: {card.get('description', '')}",
        f"Grain: {card.get('grain', '')}",
        f"Currency: {card.get('currency', '')}",
    ]

    time_range = card.get("time_range") or {}
    if time_range:
        start = time_range.get("start", "?")
        end = time_range.get("end", "?")
        note = time_range.get("note", "")
        lines.append(f"Time range: {start} to {end}" + (f" ({note})" if note else ""))

    tables: dict[str, Any] = card.get("tables") or {}
    for name, spec in tables.items():
        layer = spec.get("layer", "")
        desc = spec.get("description", "")
        header = f"Table {name}"
        if layer:
            header += f" [{layer}]"
        lines.append(f"{header}: {desc}")
        if spec.get("columns"):
            lines.append(f"  Columns: {_format_columns(spec)}")

    for anomaly in card.get("known_anomalies") or []:
        if isinstance(anomaly, dict):
            lines.append(f"Anomaly {anomaly.get('id', '?')}: {anomaly.get('summary', '')}")

    hints = card.get("agent_hints") or {}
    if hints.get("prefer_gold_for"):
        lines.append("Prefer gold tables for: " + ", ".join(hints["prefer_gold_for"]))
    if hints.get("use_sales_clean_for"):
        lines.append("Use sales_clean for: " + ", ".join(hints["use_sales_clean_for"]))
    for note in hints.get("sql_notes") or []:
        lines.append(f"SQL note: {note}")

    metrics = load_metrics()
    lines.append("Gold metrics (run_gold_query): " + ", ".join(sorted(metrics.keys())))

    return "\n".join(lines)
