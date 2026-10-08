import vertica_python

from app.connectors.base import BaseConnector

SYSTEM_SCHEMA_FILTER = "is_system_schema = false"


class VerticaConnector(BaseConnector):
    """Vertica metadata connector (Database -> Schema -> Table -> Column).

    A Vertica connection is scoped to a single database, so get_databases()
    returns just the one the connection is attached to.
    """

    def _connect(self, database: str | None = None):
        return vertica_python.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password or "",
            database=database or self.database,
            connection_timeout=15,
            autocommit=True,
        )

    def _query(self, sql: str, params: tuple | None = None, database: str | None = None) -> list:
        conn = self._connect(database)
        try:
            cur = conn.cursor()
            cur.execute(sql, params or ())
            return cur.fetchall()
        finally:
            conn.close()

    def test_connection(self) -> bool:
        self._query("SELECT 1")
        return True

    def get_databases(self) -> list[str]:
        return [row[0] for row in self._query("SELECT current_database()")]

    def get_schemas(self, database: str) -> list[str]:
        rows = self._query(
            f"SELECT schema_name FROM v_catalog.schemata "
            f"WHERE {SYSTEM_SCHEMA_FILTER} ORDER BY schema_name",
            database=database,
        )
        return [row[0] for row in rows]

    def get_tables(self, database: str, schema: str) -> list[str]:
        rows = self._query(
            "SELECT table_name FROM v_catalog.tables "
            "WHERE table_schema = %s AND is_system_table = false "
            "AND is_temp_table = false ORDER BY table_name",
            (schema,),
            database=database,
        )
        return [row[0] for row in rows]

    def get_columns(self, database: str, schema: str, table: str) -> list[dict]:
        rows = self._query(
            """
            SELECT c.column_name, c.data_type, c.is_nullable,
                   (pk.column_name IS NOT NULL) AS is_primary_key
            FROM v_catalog.columns c
            LEFT JOIN v_catalog.primary_keys pk
                   ON pk.table_schema = c.table_schema
                  AND pk.table_name = c.table_name
                  AND pk.column_name = c.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            (schema, table),
            database=database,
        )
        return [
            {
                "name": row[0],
                "data_type": row[1],
                "is_nullable": bool(row[2]),
                "is_primary_key": bool(row[3]),
            }
            for row in rows
        ]