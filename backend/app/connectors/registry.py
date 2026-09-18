from app.connectors.cockroachdb import CockroachDBConnector
# from app.connectors.postgres_connector import PostgresConnector
# from app.connectors.mysql_connector import MySQLConnector
# from app.connectors.mongodb_connector import MongoDBConnector

CONNECTOR_REGISTRY = {
    "cockroachdb": CockroachDBConnector,
    # "postgresql": PostgresConnector,
    # "mysql": MySQLConnector,
    # "mongodb": MongoDBConnector,
}


def get_connector(connector_type: str, config: dict):
    connector_cls = CONNECTOR_REGISTRY.get(connector_type)
    if not connector_cls:
        raise ValueError(f"Unsupported connector type: {connector_type}")
    return connector_cls(config)