
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_ingestion(**context):
    import requests

    run_id = context["dag_run"].conf.get("run_id")

    if not run_id:
        raise ValueError("No run_id passed in dag_run.conf")

    backend_url = os.getenv("BACKEND_URL", "http://api:8000")

    resp = requests.post(
        f"{backend_url}/api/internal/ingestion-runs/{run_id}/execute",
        timeout=300,
    )
    resp.raise_for_status()


with DAG(
    dag_id="ingest_connection_2ca37abc-f953-4b32-93d4-484cdf4bef7c",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=False,
) as dag:

    ingest_task = PythonOperator(
        task_id="run_ingestion",
        python_callable=run_ingestion,
    )
