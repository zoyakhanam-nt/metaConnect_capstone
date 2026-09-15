import psycopg2

from app.connectors.base import BaseConnector


class CockroachDBConnector(BaseConnector):
    def _connect(self, database: str | None = None):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=database or self.database,
            user=self.username,
            password=self.password,
            sslmode="disable",   # use verify-full + sslrootcert for CockroachDB Cloud
            connect_timeout=5,
        )

    def test_connection(self) -> bool:
        conn = self._connect()
        conn.close()
        return True

    def get_databases(self) -> list[str]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT datname FROM pg_database "
                    "WHERE datname NOT IN ('system', 'postgres', 'defaultdb')"
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_schemas(self, database: str) -> list[str]:
        conn = self._connect(database)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name NOT IN "
                    "('pg_catalog', 'information_schema', 'crdb_internal', 'pg_extension')"
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_tables(self, database: str, schema: str) -> list[str]:
        conn = self._connect(database)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                    (schema,),
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_columns(self, database: str, schema: str, table: str) -> list[dict]:
        conn = self._connect(database)
        try:
            with conn.cursor() as cur:
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
                return [
                    {
                        "name": row[0],
                        "data_type": row[1],
                        "is_nullable": row[2] == "YES",
                        "is_primary_key": row[3],
                    }
                    for row in cur.fetchall()
                ]
        finally:
            conn.close()


def get_connector(connection_type: str, **kwargs) -> BaseConnector:
    if connection_type == "cockroachdb":
        return CockroachDBConnector(**kwargs)
    raise ValueError(f"Unsupported connection type: {connection_type}")