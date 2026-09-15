from abc import ABC, abstractmethod


class BaseConnector(ABC):
    def __init__(self, host: str, port: int, database: str, username: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def get_databases(self) -> list[str]: ...

    @abstractmethod
    def get_schemas(self, database: str) -> list[str]: ...

    @abstractmethod
    def get_tables(self, database: str, schema: str) -> list[str]: ...

    @abstractmethod
    def get_columns(self, database: str, schema: str, table: str) -> list[dict]: ...