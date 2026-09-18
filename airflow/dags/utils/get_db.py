import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    import psycopg2
except ImportError:
    psycopg2 = None


def get_db_connection(config: dict[str, Any], database: str | None = None) -> Any:
    """
    Establish a connection based on config dictionary.
    Supports CockroachDB, PostgreSQL, MySQL, and extensible connection types.
    """
    conn_type = (config.get("connection_type") or "cockroachdb").lower()
    db_name = database or config.get("database") or "defaultdb"

    if conn_type in ("cockroachdb", "postgres", "postgresql"):
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed in this environment.")

        ca_bundle = None
        for p in [
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
            "/etc/ssl/ca-bundle.pem",
        ]:
            if os.path.exists(p):
                ca_bundle = p
                break

        kwargs: dict[str, Any] = {
            "host": config.get("host"),
            "port": int(config.get("port", 26257 if conn_type == "cockroachdb" else 5432)),
            "dbname": db_name,
            "user": config.get("username"),
            "password": config.get("password"),
            "connect_timeout": 15,
        }
        if conn_type == "cockroachdb":
            kwargs["sslmode"] = config.get("sslmode", "verify-full")
            if ca_bundle:
                kwargs["sslrootcert"] = ca_bundle
        else:
            kwargs["sslmode"] = config.get("sslmode", "prefer")

        return psycopg2.connect(**kwargs)

    elif conn_type == "mysql":
        try:
            import pymysql
            return pymysql.connect(
                host=config.get("host"),
                port=int(config.get("port", 3306)),
                user=config.get("username"),
                password=config.get("password"),
                database=db_name,
                connect_timeout=15,
            )
        except ImportError:
            try:
                import mysql.connector
                return mysql.connector.connect(
                    host=config.get("host"),
                    port=int(config.get("port", 3306)),
                    user=config.get("username"),
                    password=config.get("password"),
                    database=db_name,
                    connection_timeout=15,
                )
            except ImportError:
                raise RuntimeError("Neither 'pymysql' nor 'mysql-connector-python' is installed.")
    else:
        raise ValueError(f"Unsupported connection type: '{conn_type}'")


def get_db(source: Any, **kwargs: Any) -> list[str]:
    """
    Extract databases from the given connection config or connector.

    :param source: Connection config dict, Connector instance, or DB connection.
    :return: List of database names.
    """
    logger.info("Starting database extraction task...")
    try:
        # Case 1: Connector object with get_databases method
        if hasattr(source, "get_databases"):
            databases = source.get_databases()
        # Case 2: Config dictionary
        elif isinstance(source, dict):
            conn = get_db_connection(source)
            try:
                with conn.cursor() as cur:
                    conn_type = (source.get("connection_type") or "cockroachdb").lower()
                    if conn_type in ("cockroachdb", "postgres", "postgresql"):
                        cur.execute(
                            "SELECT datname FROM pg_database "
                            "WHERE datname NOT IN ('system', 'postgres') "
                            "AND datistemplate = false;"
                        )
                        databases = [row[0] for row in cur.fetchall()]
                    elif conn_type == "mysql":
                        cur.execute("SHOW DATABASES;")
                        excluded = {"information_schema", "mysql", "performance_schema", "sys"}
                        databases = [row[0] for row in cur.fetchall() if row[0] not in excluded]
                    else:
                        raise ValueError(f"Unsupported connection type: {conn_type}")
            finally:
                conn.close()
        # Case 3: Raw DB-API connection object
        elif hasattr(source, "cursor"):
            with source.cursor() as cur:
                cur.execute(
                    "SELECT datname FROM pg_database "
                    "WHERE datname NOT IN ('system', 'postgres') "
                    "AND datistemplate = false;"
                )
                databases = [row[0] for row in cur.fetchall()]
        else:
            raise TypeError(f"Unsupported source type for get_db: {type(source)}")

        logger.info("Successfully retrieved %d database(s): %s", len(databases), databases)
        return databases

    except Exception as e:
        logger.exception("Failed during database extraction: %s", str(e))
        raise


get_databases = get_db
