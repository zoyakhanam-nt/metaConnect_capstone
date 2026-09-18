import logging

from sqlalchemy.orm import Session

from app.connectors.cockroachdb import get_connector
from app.core.crypto import decrypt_password, decrypt_value
from app.models.connection import Connection
from app.models.metadata import ColumnMetadata, DatabaseMetadata, SchemaMetadata, TableMetadata

logger = logging.getLogger(__name__)


def run_ingestion(db: Session, connection: Connection) -> None:
    logger.info("Starting ingestion for connection_id=%s", connection.id)

    connector = get_connector(
        connection.connection_type,
        host=decrypt_value(connection.host),
        port=int(decrypt_value(connection.port)),
        database=connection.database,
        username=connection.username,
        password=decrypt_value(connection.password),
    )

    try:
        db.query(DatabaseMetadata).filter(DatabaseMetadata.connection_id == connection.id).delete()
        db.commit()

        for db_name in connector.get_databases():
            db_row = DatabaseMetadata(connection_id=connection.id, name=db_name)
            db.add(db_row)
            db.flush()

            for schema_name in connector.get_schemas(db_name):
                schema_row = SchemaMetadata(database_id=db_row.id, name=schema_name)
                db.add(schema_row)
                db.flush()

                for table_name in connector.get_tables(db_name, schema_name):
                    table_row = TableMetadata(schema_id=schema_row.id, name=table_name)
                    db.add(table_row)
                    db.flush()

                    for col in connector.get_columns(db_name, schema_name, table_name):
                        db.add(
                            ColumnMetadata(
                                table_id=table_row.id,
                                name=col["name"],
                                data_type=col["data_type"],
                                is_primary_key=col["is_primary_key"],
                                is_nullable=col["is_nullable"],
                            )
                        )

        db.commit()
        logger.info("Ingestion succeeded for connection_id=%s", connection.id)
    except Exception:
        logger.exception("Ingestion failed for connection_id=%s", connection.id)
        raise
