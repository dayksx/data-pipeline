import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
SPARK_PACKAGES = "org.postgresql:postgresql:42.7.3"

# Transient failures (Spark master not ready, JDBC timeout) are retried automatically.
# Downstream tasks do not run until upstream succeeds (task chain below).
default_args = {
    "owner": "pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}


with DAG(
    dag_id="sales_medallion_pipeline",
    start_date=datetime(2026, 6, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    tags=["retails", "spark", "medallion"],
) as dag: 
    ingest = SparkSubmitOperator(
        task_id="ingest_retails_csv",
        name="ingest-retails-csv",
        application=f"{BASE}/spark/jobs/ingest.py",
        conn_id="spark_default",
        verbose=True,
    )
    transform = SparkSubmitOperator(
        task_id="transform_clean_data",
        name="transform-clean-data",
        application=f"{BASE}/spark/jobs/transform.py",
        conn_id="spark_default",
        verbose=True,
        packages=SPARK_PACKAGES,
    )
    analysis = SparkSubmitOperator(
        task_id="analyze_sales_data",
        name="analyze-sales-data",
        application=f"{BASE}/spark/jobs/analysis.py",
        conn_id="spark_default",
        verbose=True,
        packages=SPARK_PACKAGES,
    )

    trigger_rag = TriggerDagRunOperator(
        task_id="trigger_rag_index",
        trigger_dag_id="rag_index_pipeline",
        wait_for_completion=False,
    )

    ingest >> transform >> analysis >> trigger_rag
