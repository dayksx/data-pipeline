import os
from datetime import datetime
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
SPARK_PACKAGES = "org.postgresql:postgresql:42.7.3"


with DAG(
    dag_id="sales_medallion_pipeline",
    start_date=datetime(2026, 6, 1),
    schedule=None,
    catchup=False,
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

    ingest >> transform >> analysis
