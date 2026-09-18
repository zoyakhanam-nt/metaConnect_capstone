def generate_dag(
    dag_id: str,
    connection_id: str,
    connection_name: str | None = None,
    schedule_cron: str | None = None,
) -> str:
    schedule_repr = f'"{schedule_cron}"' if schedule_cron else "None"

    return f'''from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from utils.run_ingestion import run_metadata_ingestion


with DAG(
    dag_id="{dag_id}",
    start_date=datetime(2024, 1, 1),
    schedule={schedule_repr},
    catchup=False,
    is_paused_upon_creation=False,
) as dag:
    ingest_metadata = PythonOperator(
        task_id="ingest_metadata",
        python_callable=run_metadata_ingestion,
        op_kwargs={{"connection_id": "{connection_id}"}},
    )
'''
