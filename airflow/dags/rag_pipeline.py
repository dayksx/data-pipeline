"""RAG batch DAG — refresh markdown reports + pgvector index.

Triggered automatically by sales_medallion_pipeline after Spark analysis,
or manually from the Airflow UI.
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")

# Write reports under data/rag/docs (world-writable like bronze/) — not ai/rag/docs (host-owned)
RAG_DOCS = f"{BASE}/data/rag/docs"

AI_ENV = {
    "PYTHONPATH": f"{BASE}/ai/src:{BASE}/ai/rag/jobs",
    "RAG_DOCS_DIR": RAG_DOCS,
    "POSTGRES_HOST": "postgres",
    "POSTGRES_DB": "pipeline",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "LLM_API_KEY": "{{ var.value.get('LLM_API_KEY', '') }}",
}

RAG_SETUP = f"mkdir -p {RAG_DOCS}"

default_args = {
    "owner": "pipeline",
    "retries": 1,
    "retry_delay": timedelta(seconds=20),
}

with DAG(
    dag_id="rag_index_pipeline",
    start_date=datetime(2026, 6, 1),
    schedule=None,  # triggered by medallion DAG (or manual)
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    tags=["retails", "rag", "insights"],
) as dag:
    generate_reports = BashOperator(
        task_id="generate_rag_reports",
        bash_command=f"{RAG_SETUP} && cd {BASE}/ai && python rag/jobs/generate_reports.py",
        env=AI_ENV,
    )

    index_rag = BashOperator(
        task_id="index_rag_docs",
        bash_command=f"{RAG_SETUP} && cd {BASE}/ai && python rag/jobs/index.py",
        env=AI_ENV,
    )

    generate_reports >> index_rag
