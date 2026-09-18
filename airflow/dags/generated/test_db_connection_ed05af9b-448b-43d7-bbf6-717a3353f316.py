
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


CONNECTION_ID = "ed05af9b-448b-43d7-bbf6-717a3353f316"


def run_ingestion(**context):
    import requests

    backend_url = os.getenv("BACKEND_URL", "http://api:8000")
    internal_api_key = os.getenv("INTERNAL_API_KEY")
    if not internal_api_key:
        raise RuntimeError("INTERNAL_API_KEY is missing in the environment for the ingestion DAG.")
    headers = {"X-Internal-Api-Key": internal_api_key}

    conf = context["dag_run"].conf or {}
    run_id = conf.get("run_id")

    if run_id:
        # manually triggered from the API — a run row already exists, just execute it
        url = f"{backend_url}/api/internal/ingestion-runs/{run_id}/execute"
    else:
        # fired automatically by the schedule — no run exists yet, create + execute in one call
        url = f"{backend_url}/api/internal/connections/{CONNECTION_ID}/scheduled-ingest"

    resp = requests.post(url, headers=headers, timeout=300)
    resp.raise_for_status()


with DAG(
    dag_id="test_db_connection_ed05af9b-448b-43d7-bbf6-717a3353f316",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=False,
) as dag:

    ingest_task = PythonOperator(
        task_id="run_ingestion",
        python_callable=run_ingestion,
    )
