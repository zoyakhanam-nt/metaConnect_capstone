import time
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

    def ensure_dag(self, connection_id: str, schedule_cron: str | None = None) -> str:
        dag_id = f"ingest_connection_{connection_id}"
        dag_content = generate_dag(dag_id=dag_id, connection_id=connection_id, schedule_cron=schedule_cron)

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

    def deploy_and_trigger(self, connection_id: str, run_id: str, schedule_cron: str | None = None) -> tuple[str, str]:
        dag_id = self.ensure_dag(connection_id, schedule_cron)
        dag_run_id = self.trigger_dag(dag_id, conf={"run_id": run_id})
        return dag_id, dag_run_id

    def register_schedule(self, connection_id: str, schedule_cron: str | None) -> str:
        return self.ensure_dag(connection_id, schedule_cron)

    def fetch_task_logs(self, dag_id: str, dag_run_id: str, task_id: str = "run_ingestion", try_number: int = 1) -> str:
        from urllib.parse import quote

        encoded_run_id = quote(dag_run_id, safe="")
        url = f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{encoded_run_id}/taskInstances/{task_id}/logs/{try_number}"
        resp = requests.get(url, auth=self.airflow_auth, headers={"Accept": "text/plain"})
        resp.raise_for_status()
        return resp.text