from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True, slots=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"

    @classmethod
    def from_dsn(cls, dsn: str) -> "MySQLConfig":
        parsed = urlparse(dsn)
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise ValueError("MYSQL_DSN must use mysql or mysql+pymysql scheme.")
        if not parsed.hostname or not parsed.username or not parsed.path.strip("/"):
            raise ValueError("MYSQL_DSN must include host, username, and database.")

        query = parse_qs(parsed.query)
        charset = query.get("charset", ["utf8mb4"])[0] or "utf8mb4"
        return cls(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=unquote(parsed.username),
            password=unquote(parsed.password or ""),
            database=unquote(parsed.path.lstrip("/")),
            charset=charset,
        )


ConnectionFactory = Callable[[MySQLConfig], Any]


def get_mysql_dsn(env_file_paths: list[Path] | None = None) -> str | None:
    env_value = os.getenv("MYSQL_DSN")
    if env_value:
        return env_value

    paths = env_file_paths or [
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
    ]
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "MYSQL_DSN":
                return _unquote_env_value(value.strip())
    return None


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _pymysql_connection_factory(config: MySQLConfig) -> Any:
    import pymysql
    from pymysql.cursors import DictCursor

    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset=config.charset,
        cursorclass=DictCursor,
        autocommit=False,
    )


class MySQLClient:
    def __init__(
        self,
        config: MySQLConfig,
        connection_factory: ConnectionFactory = _pymysql_connection_factory,
    ) -> None:
        self._config = config
        self._connection_factory = connection_factory

    def fetch_one(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, Any] | None:
        connection = self._connection_factory(self._config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        finally:
            connection.close()

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, Any]]:
        connection = self._connection_factory(self._config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        finally:
            connection.close()

    def execute(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> int:
        connection = self._connection_factory(self._config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                connection.commit()
                return int(getattr(cursor, "lastrowid", 0) or 0)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
