import time
import re
from pathlib import Path

import requests

from app.templates.dag_template import generate_dag
from app.core.config import get_settings


class AirflowService:
    def __init__(self):
        settings = get_settings()
        self.dag_directory = Path(settings.airflow_dag_dir)
        self.dag_directory.mkdir(parents=True, exist_ok=True)

        self.airflow_api_url = settings.airflow_api_url
        self.airflow_auth = (
            settings.airflow_username,
            settings.airflow_password,
        )

    @staticmethod
    def _dag_id_for_connection(connection_name: str, connection_id: str) -> str:
        """Create a readable, unique, Airflow-safe DAG ID."""
        name = re.sub(r"[^a-zA-Z0-9]+", "_", connection_name).strip("_").lower()
        name = name or "connection"
        suffix = re.sub(r"[^a-zA-Z0-9]", "", connection_id)[:12]
        return f"{name[:220]}_{suffix}"

    def ensure_dag(
        self,
        connection_id: str,
        connection_name: str,
        schedule_cron: str | None = None,
    ) -> str:
        dag_id = self._dag_id_for_connection(connection_name, connection_id)
        dag_content = generate_dag(
            dag_id=dag_id,
            connection_id=connection_id,
            connection_name=connection_name,
            schedule_cron=schedule_cron,
        )

        dag_file = self.dag_directory / f"{dag_id}.py"
        dag_file.write_text(dag_content, encoding="utf-8")

        return dag_id

    def _wait_until_known(self, dag_id: str, attempts: int = 20, delay: float = 1.5) -> None:
        url = f"{self.airflow_api_url}/dags/{dag_id}"
        for _ in range(attempts):
            resp = requests.get(url, auth=self.airflow_auth)
            if resp.status_code == 200:
                return
            time.sleep(delay)
        raise RuntimeError(f"Airflow has not picked up DAG '{dag_id}' yet.")

    def _unpause(self, dag_id: str) -> None:
        url = f"{self.airflow_api_url}/dags/{dag_id}"
        requests.patch(url, json={"is_paused": False}, auth=self.airflow_auth)

    def trigger_dag(self, dag_id: str, conf: dict) -> str:
        self._wait_until_known(dag_id)
        self._unpause(dag_id)
        url = f"{self.airflow_api_url}/dags/{dag_id}/dagRuns"
        resp = requests.post(url, json={"conf": conf}, auth=self.airflow_auth)
        resp.raise_for_status()
        return resp.json()["dag_run_id"]

    def deploy_and_trigger(
        self,
        connection_id: str,
        connection_name: str,
        run_id: str,
        schedule_cron: str | None = None,
    ) -> tuple[str, str]:
        dag_id = self.ensure_dag(connection_id, connection_name, schedule_cron)
        dag_run_id = self.trigger_dag(dag_id, conf={"run_id": run_id})
        return dag_id, dag_run_id

    def register_schedule(
        self,
        connection_id: str,
        connection_name: str,
        schedule_cron: str | None, #optional
    ) -> str:
        return self.ensure_dag(connection_id, connection_name, schedule_cron)

    def fetch_task_logs(
        self,
        dag_id: str,
        dag_run_id: str,
        task_id: str | None = None,
        try_number: int = 1,
    ) -> str:
        from urllib.parse import quote

        encoded_run_id = quote(dag_run_id, safe="")

        # If a specific task is explicitly targeted and not the legacy single-task name
        if task_id and task_id != "run_ingestion":
            url = f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{encoded_run_id}/taskInstances/{task_id}/logs/{try_number}"
            resp = requests.get(url, auth=self.airflow_auth, headers={"Accept": "text/plain"})
            resp.raise_for_status()
            return resp.text

        # Otherwise, discover task instances in this DAG run and aggregate their logs
        ti_url = f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{encoded_run_id}/taskInstances"
        try:
            ti_resp = requests.get(ti_url, auth=self.airflow_auth)
            if ti_resp.status_code == 200:
                task_instances = ti_resp.json().get("task_instances", [])
                if task_instances:
                    # Preferred order of execution
                    order_map = {
                        "get_db_task": 1,
                        "get_schema_task": 2,
                        "get_table_task": 3,
                        "get_column_task": 4,
                        "extract_metadata_task": 5,
                    }
                    task_instances.sort(
                        key=lambda ti: order_map.get(ti.get("task_id", ""), 99)
                    )

                    combined_logs = []
                    for ti in task_instances:
                        tid = ti.get("task_id")
                        if not tid:
                            continue
                        log_url = f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{encoded_run_id}/taskInstances/{tid}/logs/{try_number}"
                        log_resp = requests.get(
                            log_url,
                            auth=self.airflow_auth,
                            headers={"Accept": "text/plain"},
                        )
                        if log_resp.status_code == 200 and log_resp.text.strip():
                            header = f"=== Task: {tid} ==="
                            combined_logs.append(f"{header}\n{log_resp.text.strip()}\n")

                    if combined_logs:
                        return "\n\n".join(combined_logs)
        except Exception:
            pass

        # Fallback to single task attempts
        for fallback_id in [task_id or "extract_metadata_task", "get_db_task", "run_ingestion"]:
            try:
                url = f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{encoded_run_id}/taskInstances/{fallback_id}/logs/{try_number}"
                resp = requests.get(url, auth=self.airflow_auth, headers={"Accept": "text/plain"})
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                continue

        return "No task logs available for this run."