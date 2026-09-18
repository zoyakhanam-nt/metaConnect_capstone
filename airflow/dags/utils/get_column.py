import logging
from typing import Any

from utils.get_db import get_db_connection

logger = logging.getLogger(__name__)


def get_column(source: Any, database: str, schema: str, table: str, **kwargs: Any) -> list[dict[str, Any]]:
    """
    Extract column metadata for a given table.

    :param source: Connection config dict, Connector instance, or DB connection.
    :param database: Target database name.
    :param schema: Target schema name.
    :param table: Target table name.
    :return: List of column metadata dictionaries.
    """
    logger.info("Starting column extraction task for '%s.%s.%s'...", database, schema, table)
    try:
        # Case 1: Connector object
        if hasattr(source, "get_columns"):
            columns = source.get_columns(database, schema, table)
        # Case 2: Config dictionary
        elif isinstance(source, dict):
            conn = get_db_connection(source, database=database)
            try:
                with conn.cursor() as cur:
                    conn_type = (source.get("connection_type") or "cockroachdb").lower()
                    if conn_type in ("cockroachdb", "postgres", "postgresql"):
                        cur.execute(
                            """
                            SELECT c.column_name, c.data_type, c.is_nullable,
                                   EXISTS (
                                       SELECT 1 FROM information_schema.key_column_usage k
                                       JOIN information_schema.table_constraints t
                                         ON k.constraint_name = t.constraint_name
                                        AND k.table_schema = t.table_schema
                                       WHERE t.constraint_type = 'PRIMARY KEY'
                                         AND k.table_schema = c.table_schema
                                         AND k.table_name = c.table_name
                                         AND k.column_name = c.column_name
                                   ) AS is_primary_key
                            FROM information_schema.columns c
                            WHERE c.table_schema = %s AND c.table_name = %s
                            ORDER BY c.ordinal_position
                            """,
                            (schema, table),
                        )
                        columns = [
                            {
                                "name": row[0],
                                "data_type": row[1],
                                "is_nullable": row[2] == "YES",
                                "is_primary_key": bool(row[3]),
                            }
                            for row in cur.fetchall()
                        ]
                    elif conn_type == "mysql":
                        cur.execute(
                            """
                            SELECT column_name, data_type, is_nullable, column_key
                            FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = %s
                            ORDER BY ordinal_position
                            """,
                            (schema, table),
                        )
                        columns = [
                            {
                                "name": row[0],
                                "data_type": row[1],
                                "is_nullable": row[2] == "YES",
                                "is_primary_key": row[3] == "PRI",
                            }
                            for row in cur.fetchall()
                        ]
                    else:
                        raise ValueError(f"Unsupported connection type: {conn_type}")
            finally:
                conn.close()
        # Case 3: Raw DB-API connection object
        elif hasattr(source, "cursor"):
            with source.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.column_name, c.data_type, c.is_nullable,
                           EXISTS (
                               SELECT 1 FROM information_schema.key_column_usage k
                               JOIN information_schema.table_constraints t
                                 ON k.constraint_name = t.constraint_name
                                AND k.table_schema = t.table_schema
                               WHERE t.constraint_type = 'PRIMARY KEY'
                                 AND k.table_schema = c.table_schema
                                 AND k.table_name = c.table_name
                                 AND k.column_name = c.column_name
                           ) AS is_primary_key
                    FROM information_schema.columns c
                    WHERE c.table_schema = %s AND c.table_name = %s
                    ORDER BY c.ordinal_position
                    """,
                    (schema, table),
                )
                columns = [
                    {
                        "name": row[0],
                        "data_type": row[1],
                        "is_nullable": row[2] == "YES",
                        "is_primary_key": bool(row[3]),
                    }
                    for row in cur.fetchall()
                ]
        else:
            raise TypeError(f"Unsupported source type for get_column: {type(source)}")

        logger.info(
            "Successfully retrieved %d column(s) for '%s.%s.%s'",
            len(columns),
            database,
            schema,
            table,
        )
        return columns

    except Exception as e:
        logger.exception("Failed during column extraction for '%s.%s.%s': %s", database, schema, table, str(e))
        raise


get_columns = get_column
