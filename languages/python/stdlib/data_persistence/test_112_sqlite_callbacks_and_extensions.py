"""112｜``sqlite3.Connection`` 的 SQL function、aggregate 与执行回调。

Connection 可把 Python callable 暴露为 scalar function、aggregate、collation，也能通过
authorizer、progress handler 和 trace callback 观察或限制执行。回调运行在 SQLite 执行
路径内，返回值/异常规则各不相同；案例只用内存数据，不加载真实动态扩展。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sqlite3.create-function python.sqlite3.scalar-function
# polyglot-covers: python.sqlite3.variadic-function python.sqlite3.deterministic-function
# polyglot-covers: python.sqlite3.remove-function python.sqlite3.callback-native-result
# polyglot-covers: python.sqlite3.create-aggregate python.sqlite3.aggregate-step
# polyglot-covers: python.sqlite3.aggregate-finalize python.sqlite3.empty-aggregate
# polyglot-covers: python.sqlite3.create-collation python.sqlite3.remove-collation
# polyglot-covers: python.sqlite3.set-authorizer python.sqlite3.SQLITE-DENY
# polyglot-covers: python.sqlite3.SQLITE-IGNORE python.sqlite3.authorizer-arguments
# polyglot-covers: python.sqlite3.set-progress-handler python.sqlite3.abort-query
# polyglot-covers: python.sqlite3.set-trace-callback python.sqlite3.trace-implicit-sql
# polyglot-covers: python.sqlite3.enable-callback-tracebacks
# polyglot-covers: python.sqlite3.enable-load-extension python.sqlite3.platform-capability
# polyglot-covers: python.sqlite3.load-extension python.sqlite3.missing-extension

import sqlite3

import pytest


def test_scalar_function_receives_sql_values_and_returns_native_value():
    """narg 固定 SQL arity；参数/返回值都应落在 SQLite 原生类型集合。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.create_function("py_double", 1, lambda value: value * 2)

        assert connection.execute("SELECT py_double(?)", (21,)).fetchone() == (42,)
    finally:
        connection.close()


def test_minus_one_narg_registers_a_variadic_function():
    """narg=-1 把不同 SQL argument count 都路由到同一个 ``*args`` callable。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.create_function("py_join", -1, lambda *parts: "|".join(parts))

        assert connection.execute("SELECT py_join('a')").fetchone() == ("a",)
        assert connection.execute("SELECT py_join('a', 'b', 'c')").fetchone() == (
            "a|b|c",
        )
    finally:
        connection.close()


def test_deterministic_flag_depends_on_linked_sqlite_version():
    """deterministic 是 SQLite 3.8.3 能力；旧 runtime 应得到 NotSupportedError。"""

    connection = sqlite3.connect(":memory:")
    try:
        if sqlite3.sqlite_version_info < (3, 8, 3):
            with pytest.raises(sqlite3.NotSupportedError):
                connection.create_function(
                    "py_identity", 1, lambda value: value, deterministic=True
                )
        else:
            returned = connection.create_function(
                "py_identity", 1, lambda value: value, deterministic=True
            )
            assert returned is None
            assert connection.execute("SELECT py_identity(7)").fetchone() == (7,)
    finally:
        connection.close()


def test_registering_none_removes_a_scalar_function():
    """同 name/arity 传 None 是 removal API；之后 SQL resolution 失败。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.create_function("temporary_fn", 1, lambda value: value)
        assert connection.execute("SELECT temporary_fn(1)").fetchone() == (1,)

        connection.create_function("temporary_fn", 1, None)
        with pytest.raises(sqlite3.OperationalError, match="function"):
            connection.execute("SELECT temporary_fn(1)").fetchone()
    finally:
        connection.close()


def test_aggregate_class_gets_one_step_per_row_then_finalize():
    """SQLite 为每个 group 构造 aggregate instance，依次 step，最后只取 finalize 结果。"""

    events = []

    class Product:
        def __init__(self):
            self.value = 1
            events.append("init")

        def step(self, value):
            self.value *= value
            events.append(("step", value))

        def finalize(self):
            events.append("finalize")
            return self.value

    connection = sqlite3.connect(":memory:")
    try:
        connection.create_aggregate("py_product", 1, Product)
        result = connection.execute(
            "SELECT py_product(value) FROM "
            "(SELECT 2 AS value UNION ALL SELECT 3 UNION ALL SELECT 4)"
        ).fetchone()

        assert result == (24,)
        assert events == [
            "init",
            ("step", 2),
            ("step", 3),
            ("step", 4),
            "finalize",
        ]
    finally:
        connection.close()


def test_aggregate_over_no_rows_returns_null_without_constructing_class():
    """空 input 不创建 aggregate object，也不调用 finalize；SQL aggregate result 是 NULL。"""

    constructed = []

    class NeverConstructed:
        def __init__(self):
            constructed.append(True)

        def step(self, value):
            raise AssertionError("empty input must not call step")

        def finalize(self):
            return "not reached"

    connection = sqlite3.connect(":memory:")
    try:
        connection.create_aggregate("empty_aggregate", 1, NeverConstructed)
        result = connection.execute(
            "SELECT empty_aggregate(value) FROM "
            "(SELECT 1 AS value WHERE FALSE)"
        ).fetchone()

        assert result == (None,)
        assert constructed == []
    finally:
        connection.close()


def test_custom_collation_controls_order_and_none_removes_it():
    """collation 返回负/零/正决定 TEXT 排序；None 删除 connection-local 注册。"""

    def reverse(left, right):
        return (right > left) - (right < left)

    connection = sqlite3.connect(":memory:")
    try:
        connection.create_collation("reverse_text", reverse)
        connection.execute("CREATE TABLE word(value)")
        connection.executemany(
            "INSERT INTO word VALUES (?)", [("alpha",), ("charlie",), ("bravo",)]
        )

        rows = connection.execute(
            "SELECT value FROM word ORDER BY value COLLATE reverse_text"
        ).fetchall()
        assert rows == [("charlie",), ("bravo",), ("alpha",)]

        connection.create_collation("reverse_text", None)
        with pytest.raises(sqlite3.OperationalError, match="collation"):
            connection.execute(
                "SELECT value FROM word ORDER BY value COLLATE reverse_text"
            ).fetchall()
    finally:
        connection.close()


def test_authorizer_can_deny_an_operation_before_it_changes_data():
    """返回 SQLITE_DENY 中止 statement；callback 参数指出 action/table/column 来源。"""

    calls = []

    def authorizer(action, first, second, database, trigger):
        calls.append((action, first, second, database, trigger))
        if action == sqlite3.SQLITE_DELETE and first == "item":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE item(value)")
        connection.execute("INSERT INTO item VALUES ('kept')")
        connection.set_authorizer(authorizer)

        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("DELETE FROM item")

        connection.set_authorizer(None)
        assert connection.execute("SELECT * FROM item").fetchall() == [("kept",)]
        assert any(call[0] == sqlite3.SQLITE_DELETE for call in calls)
    finally:
        connection.close()


def test_authorizer_ignore_replaces_a_column_read_with_null():
    """对 SQLITE_READ 返回 IGNORE 不终止 query，而把敏感 column 替换为 SQL NULL。"""

    def hide_secret(action, table, column, database, trigger):
        if action == sqlite3.SQLITE_READ and table == "account" and column == "secret":
            return sqlite3.SQLITE_IGNORE
        return sqlite3.SQLITE_OK

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE account(name, secret)")
        connection.execute("INSERT INTO account VALUES ('alice', 'token')")
        connection.set_authorizer(hide_secret)

        assert connection.execute(
            "SELECT name, secret FROM account"
        ).fetchone() == ("alice", None)
    finally:
        connection.close()


def test_progress_handler_can_abort_a_query_and_then_be_removed():
    """handler 每 n 个 VM instructions 被调用；非零返回值以 OperationalError 中断。"""

    calls = []

    def cancel():
        calls.append("called")
        return 1

    connection = sqlite3.connect(":memory:")
    try:
        connection.set_progress_handler(cancel, 1)
        with pytest.raises(sqlite3.OperationalError, match="interrupted"):
            connection.execute(
                "WITH RECURSIVE count(x) AS ("
                "VALUES(1) UNION ALL SELECT x + 1 FROM count WHERE x < 1000"
                ") SELECT sum(x) FROM count"
            ).fetchone()

        assert calls
        connection.set_progress_handler(None, 0)
        assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        connection.close()


def test_trace_callback_observes_implicit_transaction_sql_and_can_be_disabled():
    """trace 不限于显式 execute：默认 DML 触发的 BEGIN 也会出现，return value 被忽略。"""

    statements = []
    connection = sqlite3.connect(":memory:")
    try:
        connection.set_trace_callback(lambda sql: statements.append(sql) or "ignored")
        connection.execute("CREATE TABLE item(value)")
        connection.execute("INSERT INTO item VALUES (1)")

        normalized = [statement.upper() for statement in statements]
        assert any(statement.startswith("CREATE TABLE") for statement in normalized)
        assert any(statement.startswith("BEGIN") for statement in normalized)
        assert any(statement.startswith("INSERT") for statement in normalized)

        connection.set_trace_callback(None)
        count_before = len(statements)
        connection.execute("SELECT * FROM item").fetchall()
        assert len(statements) == count_before
    finally:
        connection.close()


def test_callback_traceback_debug_switch_is_a_process_wide_side_effect_api():
    """该开关控制 callback exception 是否打印到 stderr；调用本身返回 None。"""

    try:
        assert sqlite3.enable_callback_tracebacks(True) is None
    finally:
        sqlite3.enable_callback_tracebacks(False)


def test_loadable_extension_switch_is_an_optional_build_capability():
    """某些平台未编译 extension support；两种结果都是文档允许的构建能力。"""

    connection = sqlite3.connect(":memory:")
    try:
        method = getattr(connection, "enable_load_extension", None)
        if method is None:
            pytest.skip("当前 Python 构建未暴露 loadable-extension API")
        try:
            returned = method(False)
        except (sqlite3.OperationalError, sqlite3.NotSupportedError) as error:
            assert "extension" in str(error).lower()
        else:
            assert returned is None
    finally:
        connection.close()


def test_load_extension_reports_a_missing_library_when_capability_exists(tmp_path):
    """案例只探测不存在的隔离路径；不依赖或加载主机上的真实 shared library。"""

    connection = sqlite3.connect(":memory:")
    enable = getattr(connection, "enable_load_extension", None)
    load = getattr(connection, "load_extension", None)
    try:
        if enable is None or load is None:
            pytest.skip("当前 Python 构建未暴露 loadable-extension API")
        try:
            enable(True)
        except (sqlite3.OperationalError, sqlite3.NotSupportedError):
            pytest.skip("当前 SQLite runtime 未启用 loadable-extension support")

        with pytest.raises(sqlite3.OperationalError):
            load(str(tmp_path / "definitely-missing-extension"))
    finally:
        if enable is not None:
            try:
                enable(False)
            except (sqlite3.OperationalError, sqlite3.NotSupportedError):
                pass
        connection.close()
