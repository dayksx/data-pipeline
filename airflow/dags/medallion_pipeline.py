from datetime import datetime

from airflow import DAG

with DAG(
    dag_id="medallion_pipeline",
    start_date=datetime(2026, 6, 1),
    schedule=None,
    catchup=False,
    tags=["retails", "spark", "medallion"],
) as dag: 
    pass