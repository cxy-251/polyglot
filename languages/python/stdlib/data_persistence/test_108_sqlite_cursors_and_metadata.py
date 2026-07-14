"""108｜``sqlite3.Cursor`` 批处理、结果消费与 DB-API 元数据。

Cursor 既是语句执行器，也是查询结果的 iterator。``execute`` 只接受一条 statement，
``executemany`` 针对 DML 重复绑定，``executescript`` 才负责脚本。``description``、
``lastrowid`` 与 ``rowcount`` 各有不同更新时间，不能把它们当成统一的结果摘要。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sqlite3.Cursor.execute python.sqlite3.single-statement
# polyglot-covers: python.sqlite3.Cursor.executemany python.sqlite3.parameter-iterable
# polyglot-covers: python.sqlite3.Cursor.executescript python.sqlite3.sql-script
# polyglot-covers: python.sqlite3.fetchone python.sqlite3.fetchmany python.sqlite3.fetchall
# polyglot-covers: python.sqlite3.arraysize python.sqlite3.cursor-iteration
# polyglot-covers: python.sqlite3.description python.sqlite3.description-seven-tuple
# polyglot-covers: python.sqlite3.lastrowid python.sqlite3.rowcount
# polyglot-covers: python.sqlite3.total_changes python.sqlite3.cursor-connection
# polyglot-covers: python.sqlite3.setinputsizes python.sqlite3.setoutputsize
# polyglot-covers: python.sqlite3.Cursor.close python.sqlite3.closed-cursor

import sqlite3

import pytest


def _connection_with_numbers():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE number(value INTEGER)")
    connection.executemany(
        "INSERT INTO number VALUES (?)",
        [(1,), (2,), (3,), (4,), (5,)],
    )
    return connection


def test_execute_accepts_one_statement_not_a_script():
    """多 statement 必须显式选择 executescript；execute 不会只执行第一条后静默忽略。"""

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.Warning):
            connection.execute("CREATE TABLE a(x); CREATE TABLE b(y)")
    finally:
        connection.close()


def test_executemany_consumes_any_iterable_of_parameter_sequences():
    """parameters 不必预先 materialize 成 list；generator 适合逐批产生输入。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE square(value, squared)")
        parameters = ((value, value * value) for value in range(4))

        cursor = connection.executemany(
            "INSERT INTO square VALUES (?, ?)", parameters
        )

        assert cursor.rowcount == 4
        assert connection.execute(
            "SELECT * FROM square ORDER BY value"
        ).fetchall() == [(0, 0), (1, 1), (2, 4), (3, 9)]
    finally:
        connection.close()


def test_executemany_rejects_non_dml_statements():
    """3.10 的 executemany 只用于 INSERT/UPDATE/DELETE/REPLACE，不是重复 SELECT。"""

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.executemany("SELECT ?", [(1,), (2,)])
    finally:
        connection.close()


def test_executescript_runs_multiple_statements_and_returns_a_cursor():
    """script 是 str 而非参数化 API；动态 value 仍应交给 execute 的 placeholder。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.executescript(
            """
            CREATE TABLE language(name, year);
            INSERT INTO language VALUES ('Python', 1991);
            INSERT INTO language VALUES ('Go', 2009);
            """
        )

        assert isinstance(cursor, sqlite3.Cursor)
        assert cursor.connection is connection
        assert connection.execute(
            "SELECT * FROM language ORDER BY year"
        ).fetchall() == [("Python", 1991), ("Go", 2009)]
    finally:
        connection.close()


def test_fetch_methods_consume_one_shared_result_position():
    """fetchone/fetchmany/fetchall 不是独立查询；每次都从当前 cursor position 继续。"""

    connection = _connection_with_numbers()
    try:
        cursor = connection.execute("SELECT value FROM number ORDER BY value")

        assert cursor.fetchone() == (1,)
        assert cursor.fetchmany(2) == [(2,), (3,)]
        assert cursor.fetchall() == [(4,), (5,)]
        assert cursor.fetchone() is None
        assert cursor.fetchmany(2) == []
        assert cursor.fetchall() == []
    finally:
        connection.close()


def test_fetchmany_uses_arraysize_when_size_is_omitted():
    """arraysize 默认 1 且可写；稳定批处理应保持相同 size，避免性能抖动。"""

    connection = _connection_with_numbers()
    try:
        cursor = connection.execute("SELECT value FROM number ORDER BY value")
        assert cursor.arraysize == 1

        cursor.arraysize = 2
        assert cursor.fetchmany() == [(1,), (2,)]
        assert cursor.fetchmany() == [(3,), (4,)]
        assert cursor.fetchmany() == [(5,)]
    finally:
        connection.close()


def test_cursor_iteration_streams_remaining_rows():
    """Cursor 实现 iterator protocol；迭代从当前 position 开始而非重新执行 SQL。"""

    connection = _connection_with_numbers()
    try:
        cursor = connection.execute("SELECT value FROM number ORDER BY value")
        assert cursor.fetchone() == (1,)

        assert list(cursor) == [(2,), (3,), (4,), (5,)]
        assert list(cursor) == []
    finally:
        connection.close()


def test_description_contains_names_and_six_none_fields_even_without_rows():
    """description 描述 result columns，不取决于 SELECT 是否匹配到 record。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.execute(
            "SELECT 1 AS answer, 'x' AS label WHERE FALSE"
        )

        assert cursor.fetchall() == []
        assert [column[0] for column in cursor.description] == ["answer", "label"]
        assert all(len(column) == 7 for column in cursor.description)
        assert all(column[1:] == (None,) * 6 for column in cursor.description)
    finally:
        connection.close()


def test_lastrowid_only_tracks_successful_single_execute_inserts():
    """executemany 不更新 lastrowid；它保留该 cursor 之前单条 INSERT 得到的值。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.cursor()
        assert cursor.lastrowid is None
        cursor.execute("CREATE TABLE item(id INTEGER PRIMARY KEY, value)")
        cursor.execute("INSERT INTO item(value) VALUES (?)", ("first",))
        first_id = cursor.lastrowid

        cursor.executemany(
            "INSERT INTO item(value) VALUES (?)",
            [("second",), ("third",)],
        )

        assert first_id == 1
        assert cursor.lastrowid == first_id
    finally:
        connection.close()


def test_rowcount_and_total_changes_measure_different_scopes():
    """rowcount 属于最近 DML，total_changes 累计整个 connection 生命周期的修改。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE item(value)")
        inserted = connection.executemany(
            "INSERT INTO item VALUES (?)", [(1,), (2,), (3,)]
        )
        updated = connection.execute("UPDATE item SET value = value * 10")
        selected = connection.execute("SELECT * FROM item")

        assert inserted.rowcount == 3
        assert updated.rowcount == 3
        assert selected.rowcount == -1
        assert connection.total_changes == 6
    finally:
        connection.close()


def test_db_api_size_hint_methods_are_intentional_no_ops():
    """为兼容 DB-API 而存在的 size methods 在 sqlite3 不分配资源，也不改变结果。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.cursor()

        assert cursor.setinputsizes([int, str]) is None
        assert cursor.setoutputsize(1024) is None
        assert cursor.setoutputsize(128, 0) is None
    finally:
        connection.close()


def test_closed_cursor_rejects_future_operations_but_connection_survives():
    """cursor.close 只结束该 result context，不会级联关闭 parent connection。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.cursor()
        cursor.close()

        with pytest.raises(sqlite3.ProgrammingError):
            cursor.execute("SELECT 1")
        assert connection.execute("SELECT 2").fetchone() == (2,)
    finally:
        connection.close()
