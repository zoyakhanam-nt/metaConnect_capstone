import logging
from typing import Any

from utils.get_db import get_db_connection

logger = logging.getLogger(__name__)


def get_schema(source: Any, database: str, **kwargs: Any) -> list[str]:
    """
    Extract schemas for a specific database.

    :param source: Connection config dict, Connector instance, or DB connection.
    :param database: Target database name.
    :return: List of schema names.
    """
    logger.info("Starting schema extraction task for database: '%s'...", database)
    try:
        # Case 1: Connector object
        if hasattr(source, "get_schemas"):
            schemas = source.get_schemas(database)
        # Case 2: Config dictionary
        elif isinstance(source, dict):
            conn = get_db_connection(source, database=database)
            try:
                with conn.cursor() as cur:
                    conn_type = (source.get("connection_type") or "cockroachdb").lower()
                    if conn_type in ("cockroachdb", "postgres", "postgresql"):
                        cur.execute(
                            "SELECT schema_name FROM information_schema.schemata "
                            "WHERE schema_name NOT IN "
                            "('pg_catalog', 'information_schema', 'crdb_internal', 'pg_extension')"
                        )
                        schemas = [row[0] for row in cur.fetchall()]
                    elif conn_type == "mysql":
                        schemas = [database]
                    else:
                        raise ValueError(f"Unsupported connection type: {conn_type}")
            finally:
                conn.close()
        # Case 3: Raw DB-API connection object
        elif hasattr(source, "cursor"):
            with source.cursor() as cur:
                cur.execute(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name NOT IN "
                    "('pg_catalog', 'information_schema', 'crdb_internal', 'pg_extension')"
                )
                schemas = [row[0] for row in cur.fetchall()]
        else:
            raise TypeError(f"Unsupported source type for get_schema: {type(source)}")

        logger.info(
            "Successfully retrieved %d schema(s) for database '%s': %s",
            len(schemas),
            database,
            schemas,
        )
        return schemas

    except Exception as e:
        logger.exception("Failed during schema extraction for database '%s': %s", database, str(e))
        raise


get_schemas = get_schema
