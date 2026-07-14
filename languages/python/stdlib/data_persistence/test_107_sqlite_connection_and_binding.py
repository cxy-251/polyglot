"""107｜``sqlite3`` 连接、原生类型、CRUD 与参数绑定。

SQLite 是无独立服务进程的磁盘/内存数据库；``sqlite3`` 实现 DB-API 2.0。SQL 结构由
程序给出，数据必须通过 qmark 或 named placeholder 绑定，不能用字符串拼接。默认只转换
SQLite 的 NULL/INTEGER/REAL/TEXT/BLOB 五种存储类，自定义类型留给后续适配案例。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sqlite3.connect python.sqlite3.memory python.sqlite3.path-like
# polyglot-covers: python.sqlite3.Connection python.sqlite3.Cursor python.sqlite3.close
# polyglot-covers: python.sqlite3.execute-shortcut python.sqlite3.cursor-iterator
# polyglot-covers: python.sqlite3.create-table python.sqlite3.insert python.sqlite3.select
# polyglot-covers: python.sqlite3.update python.sqlite3.delete python.sqlite3.order-by
# polyglot-covers: python.sqlite3.NULL python.sqlite3.INTEGER python.sqlite3.REAL
# polyglot-covers: python.sqlite3.TEXT python.sqlite3.BLOB python.sqlite3.native-types
# polyglot-covers: python.sqlite3.qmark-placeholder python.sqlite3.named-placeholder
# polyglot-covers: python.sqlite3.binding-count python.sqlite3.named-extra-ignored
# polyglot-covers: python.sqlite3.sql-injection python.sqlite3.complete-statement
# polyglot-covers: python.sqlite3.ProgrammingError python.sqlite3.default-tuples

import sqlite3

import pytest


def test_memory_connection_creates_a_private_transient_database():
    """每个普通 ``:memory:`` connection 都有自己的数据库，close 后内容消失。"""

    first = sqlite3.connect(":memory:")
    second = sqlite3.connect(":memory:")
    try:
        first.execute("CREATE TABLE note(body TEXT)")
        first.execute("INSERT INTO note VALUES (?)", ("private",))

        assert first.execute("SELECT body FROM note").fetchone() == ("private",)
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            second.execute("SELECT body FROM note")
    finally:
        first.close()
        second.close()


def test_connect_accepts_path_like_objects_and_creates_a_file(tmp_path):
    """3.7 起 database 可直接传 PathLike；无需在业务层提前转字符串。"""

    path = tmp_path / "records.sqlite"
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE item(value)")
        connection.commit()
    finally:
        connection.close()

    assert path.is_file()


def test_connection_shortcut_returns_a_cursor_with_default_tuple_rows():
    """Connection.execute 会隐式新建 Cursor，但 fetch 仍发生在返回的 cursor 上。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.execute("SELECT 40 + 2 AS answer")

        assert isinstance(cursor, sqlite3.Cursor)
        assert cursor.connection is connection
        assert cursor.fetchone() == (42,)
        assert cursor.fetchone() is None
    finally:
        connection.close()


def test_basic_crud_workflow_uses_explicit_ordering():
    """没有 ORDER BY 时 row 顺序不是契约；可查阅案例应把期望顺序写进 SQL。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE task(id INTEGER PRIMARY KEY, title, done)")
        connection.executemany(
            "INSERT INTO task(title, done) VALUES (?, ?)",
            [("read", False), ("write", False), ("review", True)],
        )
        connection.execute("UPDATE task SET done = ? WHERE title = ?", (True, "write"))
        connection.execute("DELETE FROM task WHERE title = ?", ("read",))

        rows = connection.execute(
            "SELECT title, done FROM task ORDER BY title"
        ).fetchall()

        assert rows == [("review", 1), ("write", 1)]
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("value", "sql_type", "python_type"),
    [
        (None, "null", type(None)),
        (42, "integer", int),
        (3.5, "real", float),
        ("中文", "text", str),
        (b"\x00\xff", "blob", bytes),
    ],
)
def test_native_python_values_map_to_five_sqlite_storage_classes(
    value,
    sql_type,
    python_type,
):
    """列声明不决定这里的实际 storage class；``typeof`` 可观察 SQLite 动态类型。"""

    connection = sqlite3.connect(":memory:")
    try:
        restored, actual_type = connection.execute(
            "SELECT ?, typeof(?)", (value, value)
        ).fetchone()

        assert restored == value
        assert type(restored) is python_type
        assert actual_type == sql_type
    finally:
        connection.close()


def test_qmark_placeholders_bind_a_sequence_in_position_order():
    """qmark 数量必须与 sequence 长度相同；单值也要写成 ``(value,)``。"""

    connection = sqlite3.connect(":memory:")
    try:
        row = connection.execute(
            "SELECT ? AS language, ? AS year", ("Python", 1991)
        ).fetchone()

        assert row == ("Python", 1991)
    finally:
        connection.close()


def test_named_placeholders_bind_a_mapping_and_ignore_extra_keys():
    """named mapping 必须包含全部引用名，但多出的项目按 DB-API 契约被忽略。"""

    connection = sqlite3.connect(":memory:")
    try:
        parameters = {"name": "Python", "year": 1991, "unused": "ignored"}
        row = connection.execute(
            "SELECT :name, :year", parameters
        ).fetchone()

        assert row == ("Python", 1991)
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("sql", "parameters"),
    [
        ("SELECT ?, ?", (1,)),
        ("SELECT ?", (1, 2)),
        ("SELECT :required", {}),
    ],
)
def test_missing_or_extra_positional_bindings_raise_programming_error(
    sql,
    parameters,
):
    """绑定形状是 programmer error；不要等数据库操作后再猜是哪一个值缺失。"""

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute(sql, parameters)
    finally:
        connection.close()


def test_binding_treats_sql_metacharacters_as_plain_data():
    """placeholder 不只是转义 quote：它把 SQL code 与 value 分开，阻止注入改变结构。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE account(name, role)")
        connection.executemany(
            "INSERT INTO account VALUES (?, ?)",
            [("alice", "admin"), ("bob", "reader")],
        )
        hostile = "' OR TRUE; --"

        rows = connection.execute(
            "SELECT name FROM account WHERE name = ?", (hostile,)
        ).fetchall()

        assert rows == []
        assert connection.execute("SELECT count(*) FROM account").fetchone() == (2,)
    finally:
        connection.close()


def test_complete_statement_only_checks_lexical_completeness():
    """该 helper 不验证 table、column 或 SQL grammar，只判断 quote 闭合且以分号结束。"""

    assert sqlite3.complete_statement("SELECT value FROM item;") is True
    assert sqlite3.complete_statement("SELECT value FROM item") is False
    assert sqlite3.complete_statement("THIS IS NOT VALID SQL;") is True
    assert sqlite3.complete_statement("SELECT 'unterminated;") is False


def test_operations_on_a_closed_connection_raise_programming_error():
    """close 后对象不会自动重连；继续使用属于 API lifecycle 错误。"""

    connection = sqlite3.connect(":memory:")
    connection.close()

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
