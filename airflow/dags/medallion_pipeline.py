import os
from datetime import datetime
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")

from airflow import DAG

with DAG(
    dag_id="medallion_pipeline",
    start_date=datetime(2026, 6, 1),
    schedule=None,
    catchup=False,
    tags=["retails", "spark", "medallion"],
) as dag: 
    ingest = SparkSubmitOperator(
        task_id="ingest_retails_csv",
        application=f"{BASE}/spark/jobs/ingest.py",
        conn_id="spark_default",
        verbose=True,

    )