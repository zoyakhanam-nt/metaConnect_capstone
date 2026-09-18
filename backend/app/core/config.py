from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "deployment_service"
    db_user: str = "deployment_service"
    db_password: str = "deployment_service"
    encryption_key: str
    internal_api_key: str
    keycloak_url: str
    keycloak_realm: str
    airflow_api_url: str = "http://localhost:8080/api/v1"
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    airflow_dag_dir: str = str(ROOT_DIR / "airflow" / "dags" / "generated")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()