import logging
from typing import Any

from utils.get_db import get_db_connection

logger = logging.getLogger(__name__)


def get_table(source: Any, database: str, schema: str, **kwargs: Any) -> list[str]:
    """
    Extract table names for a given database and schema.

    :param source: Connection config dict, Connector instance, or DB connection.
    :param database: Target database name.
    :param schema: Target schema name.
    :return: List of table names.
    """
    logger.info("Starting table extraction task for database: '%s', schema: '%s'...", database, schema)
    try:
        # Case 1: Connector object
        if hasattr(source, "get_tables"):
            tables = source.get_tables(database, schema)
        # Case 2: Config dictionary
        elif isinstance(source, dict):
            conn = get_db_connection(source, database=database)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                        (schema,),
                    )
                    tables = [row[0] for row in cur.fetchall()]
            finally:
                conn.close()
        # Case 3: Raw DB-API connection object
        elif hasattr(source, "cursor"):
            with source.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                    (schema,),
                )
                tables = [row[0] for row in cur.fetchall()]
        else:
            raise TypeError(f"Unsupported source type for get_table: {type(source)}")

        logger.info(
            "Successfully retrieved %d table(s) for '%s.%s': %s",
            len(tables),
            database,
            schema,
            tables,
        )
        return tables

    except Exception as e:
        logger.exception("Failed during table extraction for '%s.%s': %s", database, schema, str(e))
        raise


get_tables = get_table
