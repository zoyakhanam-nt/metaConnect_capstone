import logging
from typing import Any

from utils.get_db import get_db
from utils.get_schema import get_schema
from utils.get_table import get_table
from utils.get_column import get_column

logger = logging.getLogger(__name__)


def extract_metadata(
    source: Any,
    databases: list[str] | None = None,
    schemas_by_db: dict[str, list[str]] | None = None,
    tables_by_schema: dict[str, dict[str, list[str]]] | None = None,
    columns_by_table: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Extracts or compiles complete hierarchical metadata (databases -> schemas -> tables -> columns).

    If partial results from individual task stages are provided, it compiles them;
    otherwise, it drives the end-to-end extraction pipeline using get_db, get_schema,
    get_table, and get_column.

    :param source: Connection config dict, Connector instance, or DB connection.
    :param databases: Optional pre-extracted list of database names.
    :param schemas_by_db: Optional pre-extracted dict mapping {database: [schemas]}.
    :param tables_by_schema: Optional pre-extracted dict mapping {database: {schema: [tables]}}.
    :param columns_by_table: Optional pre-extracted dict mapping {database: {schema: {table: [columns]}}}.
    :return: Full metadata structure as a list of database dicts.
    """
    logger.info("Starting extract metadata task...")
    try:
        if databases is None:
            databases = get_db(source)

        metadata_tree: list[dict[str, Any]] = []

        for db_name in databases:
            db_entry: dict[str, Any] = {"name": db_name, "schemas": []}

            # Resolve schemas
            schemas: list[str] | None = None
            if schemas_by_db and db_name in schemas_by_db:
                schemas = schemas_by_db[db_name]
            if schemas is None:
                schemas = get_schema(source, db_name)

            for schema_name in schemas:
                schema_entry: dict[str, Any] = {"name": schema_name, "tables": []}

                # Resolve tables
                tables: list[str] | None = None
                if (
                    tables_by_schema
                    and db_name in tables_by_schema
                    and schema_name in tables_by_schema[db_name]
                ):
                    tables = tables_by_schema[db_name][schema_name]
                if tables is None:
                    tables = get_table(source, db_name, schema_name)

                for table_name in tables:
                    # Resolve columns
                    columns: list[dict[str, Any]] | None = None
                    if (
                        columns_by_table
                        and db_name in columns_by_table
                        and schema_name in columns_by_table[db_name]
                        and table_name in columns_by_table[db_name][schema_name]
                    ):
                        columns = columns_by_table[db_name][schema_name][table_name]
                    if columns is None:
                        columns = get_column(source, db_name, schema_name, table_name)

                    table_entry: dict[str, Any] = {
                        "name": table_name,
                        "columns": columns,
                    }
                    schema_entry["tables"].append(table_entry)

                db_entry["schemas"].append(schema_entry)

            metadata_tree.append(db_entry)

        total_dbs = len(metadata_tree)
        total_schemas = sum(len(d["schemas"]) for d in metadata_tree)
        total_tables = sum(
            len(s["tables"]) for d in metadata_tree for s in d["schemas"]
        )
        total_columns = sum(
            len(t["columns"])
            for d in metadata_tree
            for s in d["schemas"]
            for t in s["tables"]
        )

        logger.info(
            "Extract metadata task finished successfully: %d databases, %d schemas, %d tables, %d columns extracted.",
            total_dbs,
            total_schemas,
            total_tables,
            total_columns,
        )
        return metadata_tree

    except Exception as e:
        logger.exception("Failed during metadata extraction task: %s", str(e))
        raise
