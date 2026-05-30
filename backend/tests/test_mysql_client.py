from app.db.mysql import MySQLClient, MySQLConfig, get_mysql_dsn


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.lastrowid = 42

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> dict[str, object]:
        return {"id": 1, "object_id": "MET_123"}

    def fetchall(self) -> list[dict[str, object]]:
        return [{"id": 1}, {"id": 2}]


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_mysql_config_parses_pymysql_dsn() -> None:
    config = MySQLConfig.from_dsn(
        "mysql+pymysql://seitem:secret@mysql6.sqlpub.com:3311/seitem?charset=utf8mb4"
    )

    assert config.host == "mysql6.sqlpub.com"
    assert config.port == 3311
    assert config.user == "seitem"
    assert config.password == "secret"
    assert config.database == "seitem"
    assert config.charset == "utf8mb4"


def test_get_mysql_dsn_prefers_environment(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MYSQL_DSN=mysql+pymysql://file:pw@localhost/db\n")
    monkeypatch.setenv("MYSQL_DSN", "mysql+pymysql://env:pw@localhost/db")

    assert get_mysql_dsn([env_file]) == "mysql+pymysql://env:pw@localhost/db"


def test_get_mysql_dsn_reads_env_file_when_environment_missing(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PROJECT_NAME=Knowledge QA Subsystem\n"
        "MYSQL_DSN=mysql+pymysql://file:pw@localhost:3307/seitem\n"
    )
    monkeypatch.delenv("MYSQL_DSN", raising=False)

    assert get_mysql_dsn([env_file]) == "mysql+pymysql://file:pw@localhost:3307/seitem"


def test_mysql_client_fetch_and_execute_use_connection_factory() -> None:
    connections: list[FakeConnection] = []

    def factory(config: MySQLConfig) -> FakeConnection:
        connections.append(FakeConnection())
        return connections[-1]

    client = MySQLClient(
        MySQLConfig(
            host="localhost",
            port=3306,
            user="user",
            password="password",
            database="db",
        ),
        connection_factory=factory,
    )

    one = client.fetch_one("select * from artifacts where object_id=%s", ("MET_123",))
    many = client.fetch_all("select * from artifacts")
    inserted_id = client.execute("insert into qa_log(question) values(%s)", ("问题",))

    assert one == {"id": 1, "object_id": "MET_123"}
    assert many == [{"id": 1}, {"id": 2}]
    assert inserted_id == 42
    assert connections[0].cursor_instance.executed == [
        ("select * from artifacts where object_id=%s", ("MET_123",))
    ]
    assert connections[1].cursor_instance.executed == [("select * from artifacts", None)]
    assert connections[2].cursor_instance.executed == [
        ("insert into qa_log(question) values(%s)", ("问题",))
    ]
    assert connections[2].commits == 1
    assert all(connection.closed for connection in connections)
