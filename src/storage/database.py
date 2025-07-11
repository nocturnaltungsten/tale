"""Database connection manager for tale storage."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from .schema import create_all_tables


class Database:
    """Database connection manager."""

    def __init__(self, db_path: str | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to database file. Defaults to ~/.tale/tale.db
        """
        if db_path is None:
            db_path = "~/.tale/tale.db"

        self.db_path = Path(db_path).expanduser()
        self._persistent_conn = None

        # Handle in-memory databases specially
        if str(self.db_path) == ":memory:":
            # For in-memory databases, maintain a persistent connection
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database with schema
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Initialize database schema."""
        with self.get_connection() as conn:
            for table_sql in create_all_tables():
                conn.execute(table_sql)
            conn.commit()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection context manager.

        Yields:
            sqlite3.Connection: Database connection with row factory
        """
        if self._persistent_conn is not None:
            # For in-memory databases, use persistent connection
            yield self._persistent_conn
        else:
            # For file databases, create new connection
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def execute_sql(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute SQL statement and return cursor.

        Args:
            sql: SQL statement to execute
            params: Parameters for SQL statement

        Returns:
            sqlite3.Cursor: Result cursor
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Execute SQL and fetch one row.

        Args:
            sql: SQL statement to execute
            params: Parameters for SQL statement

        Returns:
            Optional[sqlite3.Row]: Single row result or None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cast(sqlite3.Row | None, cursor.fetchone())

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute SQL and fetch all rows.

        Args:
            sql: SQL statement to execute
            params: Parameters for SQL statement

        Returns:
            list[sqlite3.Row]: All matching rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()


def init_database(db_path: str | None = None) -> Database:
    """Initialize database singleton.

    Args:
        db_path: Path to database file

    Returns:
        Database: Database instance
    """
    return Database(db_path)
