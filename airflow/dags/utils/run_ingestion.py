import logging
import os
from typing import Any

import requests

from utils.extract_metadata import extract_metadata

logger = logging.getLogger("airflow.task")


def _backend_auth() -> tuple[str, dict[str, str]]:
    backend_url = os.getenv("BACKEND_URL", "http://api:8000")
    internal_api_key = os.getenv("INTERNAL_API_KEY")
    if not internal_api_key:
        raise RuntimeError("INTERNAL_API_KEY is missing in the Airflow environment.")
    return backend_url, {
        "X-Internal-Api-Key": internal_api_key,
        "Content-Type": "application/json",
    }


def _load_connection_config(connection_id: str) -> tuple[str, dict[str, str], dict[str, Any]]:
    backend_url, headers = _backend_auth()
    response = requests.get(
        f"{backend_url}/api/internal/connections/{connection_id}/config",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return backend_url, headers, response.json()


def _get_run_id(connection_id: str, backend_url: str, headers: dict[str, str], context: dict[str, Any]) -> str:
    dag_run = context["dag_run"]
    conf = dag_run.conf or {}
    existing_run_id = conf.get("run_id")
    if existing_run_id:
        return str(existing_run_id)

    response = requests.post(
        f"{backend_url}/api/internal/connections/{connection_id}/start-run",
        json={"dag_id": context["dag"].dag_id, "dag_run_id": dag_run.run_id},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return str(response.json()["run_id"])


def _report_result(
    connection_id: str,
    run_id: str | None,
    status: str,
    metadata: list[dict[str, Any]],
    error_message: str | None = None,
) -> None:
    if not run_id:
        return

    backend_url, headers = _backend_auth()
    payload = {"run_id": run_id, "status": status, "metadata": metadata}
    if error_message:
        payload["error_message"] = error_message

    response = requests.post(
        f"{backend_url}/api/internal/connections/{connection_id}/metadata",
        json=payload,
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()


def run_metadata_ingestion(connection_id: str, **context: Any) -> None:
    """Run the complete metadata extraction workflow for one connection."""
    run_id = None
    try:
        backend_url, headers, config = _load_connection_config(connection_id)
        run_id = _get_run_id(connection_id, backend_url, headers, context)

        metadata = extract_metadata(config)
        _report_result(connection_id, run_id, "success", metadata)
        logger.info("Metadata ingestion succeeded for connection %s", connection_id)
    except Exception as exc:
        logger.exception("Metadata ingestion failed for connection %s", connection_id)
        try:
            _report_result(connection_id, run_id, "failed", [], str(exc))
        except Exception:
            logger.exception("Could not report ingestion failure for connection %s", connection_id)
        raise
