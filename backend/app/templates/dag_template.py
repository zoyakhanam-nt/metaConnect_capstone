def generate_dag(
    dag_id: str,
    connection_id: str,
    connection_name: str | None = None,
    schedule_cron: str | None = None,
) -> str:
    schedule_repr = f'"{schedule_cron}"' if schedule_cron else "None"

    return f'''import os
import logging
from datetime import datetime
import requests

from airflow import DAG
from airflow.operators.python import PythonOperator

from utils.get_db import get_db
from utils.get_schema import get_schema
from utils.get_table import get_table
from utils.get_column import get_column
from utils.extract_metadata import extract_metadata

logger = logging.getLogger("airflow.task")

CONNECTION_ID = "{connection_id}"


def _get_backend_auth():
    backend_url = os.getenv("BACKEND_URL", "http://api:8000")
    internal_api_key = os.getenv("INTERNAL_API_KEY")
    if not internal_api_key:
        raise RuntimeError("INTERNAL_API_KEY is missing in the environment for the ingestion DAG.")
    headers = {{"X-Internal-Api-Key": internal_api_key, "Content-Type": "application/json"}}
    return backend_url, headers


def task_get_databases(**context):
    logger.info("Starting db task for connection %s...", CONNECTION_ID)
    backend_url, headers = _get_backend_auth()

    # 1. Fetch decrypted connection configuration from backend
    config_url = f"{{backend_url}}/api/internal/connections/{{CONNECTION_ID}}/config"
    resp = requests.get(config_url, headers=headers, timeout=30)
    resp.raise_for_status()
    config = resp.json()

    # 2. Determine or register run_id
    conf = context.get("dag_run").conf or {{}}
    run_id = conf.get("run_id")
    if not run_id:
        start_url = f"{{backend_url}}/api/internal/connections/{{CONNECTION_ID}}/start-run"
        start_payload = {{
            "dag_id": context.get("dag").dag_id,
            "dag_run_id": context.get("dag_run").run_id,
        }}
        start_resp = requests.post(start_url, json=start_payload, headers=headers, timeout=30)
        start_resp.raise_for_status()
        run_id = start_resp.json().get("run_id")

    # 3. Call get_db from utils
    conn_type = config.get("connection_type", "cockroachdb")
    logger.info("Executing database extraction using connection type: '%s'", conn_type)
    databases = get_db(config)

    return {{
        "config": config,
        "run_id": run_id,
        "databases": databases,
    }}


def task_get_schemas(**context):
    logger.info("Starting schema task for connection %s...", CONNECTION_ID)
    ti = context["ti"]
    upstream_data = ti.xcom_pull(task_ids="get_db_task")
    if not upstream_data:
        raise RuntimeError("Missing upstream database data from get_db_task")

    config = upstream_data["config"]
    run_id = upstream_data["run_id"]
    databases = upstream_data["databases"]

    schemas_by_db = {{}}
    for db_name in databases:
        schemas_by_db[db_name] = get_schema(config, db_name)

    return {{
        "config": config,
        "run_id": run_id,
        "databases": databases,
        "schemas_by_db": schemas_by_db,
    }}


def task_get_tables(**context):
    logger.info("Starting table task for connection %s...", CONNECTION_ID)
    ti = context["ti"]
    upstream_data = ti.xcom_pull(task_ids="get_schema_task")
    if not upstream_data:
        raise RuntimeError("Missing upstream schema data from get_schema_task")

    config = upstream_data["config"]
    run_id = upstream_data["run_id"]
    databases = upstream_data["databases"]
    schemas_by_db = upstream_data["schemas_by_db"]

    tables_by_schema = {{}}
    for db_name, schemas in schemas_by_db.items():
        tables_by_schema[db_name] = {{}}
        for schema_name in schemas:
            tables_by_schema[db_name][schema_name] = get_table(config, db_name, schema_name)

    return {{
        "config": config,
        "run_id": run_id,
        "databases": databases,
        "schemas_by_db": schemas_by_db,
        "tables_by_schema": tables_by_schema,
    }}


def task_get_columns(**context):
    logger.info("Starting column task for connection %s...", CONNECTION_ID)
    ti = context["ti"]
    upstream_data = ti.xcom_pull(task_ids="get_table_task")
    if not upstream_data:
        raise RuntimeError("Missing upstream table data from get_table_task")

    config = upstream_data["config"]
    run_id = upstream_data["run_id"]
    databases = upstream_data["databases"]
    schemas_by_db = upstream_data["schemas_by_db"]
    tables_by_schema = upstream_data["tables_by_schema"]

    columns_by_table = {{}}
    for db_name, schemas_dict in tables_by_schema.items():
        columns_by_table[db_name] = {{}}
        for schema_name, tables in schemas_dict.items():
            columns_by_table[db_name][schema_name] = {{}}
            for table_name in tables:
                columns_by_table[db_name][schema_name][table_name] = get_column(
                    config, db_name, schema_name, table_name
                )

    return {{
        "config": config,
        "run_id": run_id,
        "databases": databases,
        "schemas_by_db": schemas_by_db,
        "tables_by_schema": tables_by_schema,
        "columns_by_table": columns_by_table,
    }}


def task_extract_metadata(**context):
    logger.info("Starting extract metadata task for connection %s...", CONNECTION_ID)
    ti = context["ti"]
    upstream_data = ti.xcom_pull(task_ids="get_column_task")
    if not upstream_data:
        raise RuntimeError("Missing upstream column data from get_column_task")

    config = upstream_data["config"]
    run_id = upstream_data["run_id"]

    metadata_tree = extract_metadata(
        source=config,
        databases=upstream_data["databases"],
        schemas_by_db=upstream_data["schemas_by_db"],
        tables_by_schema=upstream_data["tables_by_schema"],
        columns_by_table=upstream_data["columns_by_table"],
    )

    backend_url, headers = _get_backend_auth()
    save_url = f"{{backend_url}}/api/internal/connections/{{CONNECTION_ID}}/metadata"
    save_payload = {{
        "run_id": run_id,
        "status": "success",
        "metadata": metadata_tree,
    }}
    logger.info("Posting extracted metadata to backend (%s)...", save_url)
    resp = requests.post(save_url, json=save_payload, headers=headers, timeout=120)
    resp.raise_for_status()
    logger.info("Successfully extracted and persisted metadata for connection %s.", CONNECTION_ID)


def handle_task_failure(context):
    exc = context.get("exception")
    logger.error("Ingestion task failed for connection %s: %s", CONNECTION_ID, exc)
    try:
        backend_url, headers = _get_backend_auth()
        conf = context.get("dag_run").conf or {{}}
        run_id = conf.get("run_id")
        save_url = f"{{backend_url}}/api/internal/connections/{{CONNECTION_ID}}/metadata"
        payload = {{
            "run_id": run_id,
            "status": "failed",
            "error_message": str(exc),
            "metadata": [],
        }}
        requests.post(save_url, json=payload, headers=headers, timeout=30)
    except Exception as e:
        logger.warning("Could not report failure status to backend: %s", e)


default_args = {{
    "owner": "metaconnect",
    "depends_on_past": False,
    "on_failure_callback": handle_task_failure,
}}

with DAG(
    dag_id="{dag_id}",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule={schedule_repr},
    catchup=False,
    is_paused_upon_creation=False,
) as dag:

    t_get_db = PythonOperator(
        task_id="get_db_task",
        python_callable=task_get_databases,
    )

    t_get_schema = PythonOperator(
        task_id="get_schema_task",
        python_callable=task_get_schemas,
    )

    t_get_table = PythonOperator(
        task_id="get_table_task",
        python_callable=task_get_tables,
    )

    t_get_column = PythonOperator(
        task_id="get_column_task",
        python_callable=task_get_columns,
    )

    t_extract_metadata = PythonOperator(
        task_id="extract_metadata_task",
        python_callable=task_extract_metadata,
    )

    t_get_db >> t_get_schema >> t_get_table >> t_get_column >> t_extract_metadata
'''