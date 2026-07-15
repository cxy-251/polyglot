"""111｜``sqlite3.Row``、自定义 row factory 与 TEXT 解码。

默认查询行是 tuple。``sqlite3.Row`` 在很小开销下增加 index、slice 与大小写不敏感的
column-name access；自定义 ``row_factory(cursor, tuple)`` 可以输出 dict/namedtuple。
``text_factory`` 只控制 SQLite TEXT 的 bytes 到 Python 表示，BLOB 始终保持 bytes。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sqlite3.default-row-tuple python.sqlite3.Row
# polyglot-covers: python.sqlite3.Row.index python.sqlite3.Row.slice python.sqlite3.Row.iteration
# polyglot-covers: python.sqlite3.Row.named-access python.sqlite3.Row.case-insensitive
# polyglot-covers: python.sqlite3.Row.keys python.sqlite3.Row.equality
# polyglot-covers: python.sqlite3.connection-row-factory python.sqlite3.cursor-row-factory
# polyglot-covers: python.sqlite3.row-factory-snapshot python.sqlite3.custom-row-factory
# polyglot-covers: python.sqlite3.dict-row python.sqlite3.namedtuple-row
# polyglot-covers: python.sqlite3.text-factory python.sqlite3.text-as-bytes
# polyglot-covers: python.sqlite3.custom-text-decoding python.sqlite3.BLOB-unaffected




import sqlite3
from collections import namedtuple
import pytest
import datetime
import queue
import threading
import time

def test_rows_are_plain_tuples_by_default():
    """row_factory=None 时结果保持最简单、最低开销的 tuple。"""

    connection = sqlite3.connect(":memory:")
    try:
        row = connection.execute("SELECT 'Earth' AS name, 6378 AS radius").fetchone()

        assert row == ("Earth", 6378)
        assert type(row) is tuple
        assert connection.row_factory is None
    finally:
        connection.close()

def test_row_supports_index_slice_iteration_and_length():
    """Row 保留 sequence protocol，现有 tuple-oriented code 通常无需改写。"""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute("SELECT 1 AS a, 2 AS b, 3 AS c").fetchone()

        assert len(row) == 3
        assert row[0] == 1
        assert row[-1] == 3
        assert row[1:] == (2, 3)
        assert tuple(row) == (1, 2, 3)
    finally:
        connection.close()


def test_row_named_access_is_case_insensitive_and_keys_keep_query_spelling():
    """lookup 忽略 column name 大小写，keys() 则保留 SQL result 的原始名称与顺序。"""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            'SELECT "Python" AS Language, 1991 AS FirstYear'
        ).fetchone()

        assert row["Language"] == "Python"
        assert row["language"] == "Python"
        assert row["FIRSTYEAR"] == 1991
        assert row.keys() == ["Language", "FirstYear"]
    finally:
        connection.close()


def test_unknown_row_column_raises_index_error_not_key_error():
    """Row 是 sequence/mapping hybrid；缺失 name 的具体异常是 IndexError。"""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute("SELECT 1 AS present").fetchone()

        with pytest.raises(IndexError):
            _ = row["missing"]
    finally:
        connection.close()


def test_row_equality_includes_both_column_names_and_values():
    """值相同但 alias 不同的 Row 不相等，避免丢失 result schema 差异。"""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        first = connection.execute("SELECT 1 AS value").fetchone()
        same = connection.execute("SELECT 1 AS value").fetchone()
        renamed = connection.execute("SELECT 1 AS other").fetchone()
        changed = connection.execute("SELECT 2 AS value").fetchone()

        assert first == same
        assert first != renamed
        assert first != changed
    finally:
        connection.close()


def test_connection_row_factory_only_affects_cursors_created_after_assignment():
    """Cursor 在创建时 snapshot connection factory；之后修改不会追溯现有 cursor。"""

    connection = sqlite3.connect(":memory:")
    try:
        old_cursor = connection.cursor()
        connection.row_factory = sqlite3.Row
        new_cursor = connection.cursor()

        old_row = old_cursor.execute("SELECT 1 AS value").fetchone()
        new_row = new_cursor.execute("SELECT 1 AS value").fetchone()

        assert type(old_row) is tuple
        assert isinstance(new_row, sqlite3.Row)
    finally:
        connection.close()


def test_cursor_factory_override_does_not_change_parent_connection():
    """单个 cursor 可覆盖 row_factory，适合局部查询而不影响 connection 其他消费者。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.cursor()
        cursor.row_factory = sqlite3.Row

        local_row = cursor.execute("SELECT 1 AS value").fetchone()
        default_row = connection.execute("SELECT 2 AS value").fetchone()

        assert isinstance(local_row, sqlite3.Row)
        assert type(default_row) is tuple
        assert connection.row_factory is None
    finally:
        connection.close()


def test_custom_dict_factory_uses_cursor_description():
    """factory 的 row 参数只有 values；column names 要从当前 cursor.description 组合。"""

    def dict_factory(cursor, row):
        names = [column[0] for column in cursor.description]
        return dict(zip(names, row))

    connection = sqlite3.connect(":memory:")
    connection.row_factory = dict_factory
    try:
        row = connection.execute("SELECT 'Ada' AS name, 1815 AS born").fetchone()

        assert row == {"name": "Ada", "born": 1815}
    finally:
        connection.close()


def test_custom_namedtuple_factory_supports_index_and_attribute_access():
    """namedtuple recipe 同时保留 unpack/index 与可读 attribute；生产代码可缓存生成的 class。"""

    def namedtuple_factory(cursor, row):
        fields = [column[0] for column in cursor.description]
        row_type = namedtuple("ResultRow", fields)
        return row_type._make(row)

    connection = sqlite3.connect(":memory:")
    connection.row_factory = namedtuple_factory
    try:
        row = connection.execute("SELECT 1 AS left, 2 AS right").fetchone()

        assert row == (1, 2)
        assert row[0] == 1
        assert row.right == 2
    finally:
        connection.close()


def test_text_factory_defaults_to_str_and_can_return_raw_bytes():
    """TEXT 默认按 UTF-8 decode 为 str；设为 bytes 可把解码决策推迟给调用者。"""

    connection = sqlite3.connect(":memory:")
    try:
        assert connection.text_factory is str
        assert connection.execute("SELECT ?", ("中文",)).fetchone() == ("中文",)

        connection.text_factory = bytes
        assert connection.execute("SELECT ?", ("中文",)).fetchone() == (
            "中文".encode("utf-8"),
        )
    finally:
        connection.close()


def test_custom_text_factory_receives_bytes_for_every_text_value():
    """自定义 callable 可集中实现 legacy encoding、normalization 或包装类型。"""

    seen = []

    def tagged_text(raw):
        seen.append(raw)
        return {"decoded": raw.decode("utf-8")}

    connection = sqlite3.connect(":memory:")
    connection.text_factory = tagged_text
    try:
        row = connection.execute("SELECT 'first', 'second'").fetchone()

        assert row == ({"decoded": "first"}, {"decoded": "second"})
        assert seen == [b"first", b"second"]
    finally:
        connection.close()


def test_text_factory_does_not_transform_blob_values():
    """TEXT 与 BLOB 由 SQLite storage class 区分；同样的 bytes 内容不会误走 text factory。"""

    connection = sqlite3.connect(":memory:")
    connection.text_factory = lambda raw: ("text", raw)
    try:
        row = connection.execute("SELECT ?, ?", ("payload", b"payload")).fetchone()

        assert row == (("text", b"payload"), b"payload")
        assert type(row[1]) is bytes
    finally:
        connection.close()


# 112｜``sqlite3.Connection`` 的 SQL function、aggregate 与执行回调。
#
# Connection 可把 Python callable 暴露为 scalar function、aggregate、collation，也能通过
# authorizer、progress handler 和 trace callback 观察或限制执行。回调运行在 SQLite 执行
# 路径内，返回值/异常规则各不相同；案例只用内存数据，不加载真实动态扩展。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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


# 113｜``sqlite3`` SQL dump、online backup、URI 与连接锁等待。
#
# ``iterdump`` 产生可读 SQL，适合迁移/审阅；``backup`` 直接复制数据库 pages，并可在源库
# 仍被访问时工作。``uri=True`` 才能使用 mode=ro/rw、named shared memory 等 SQLite URI
# 参数。锁等待案例用 ``timeout=0`` 立即失败，不引入 sleep 或时间敏感断言。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.sqlite3.iterdump python.sqlite3.sql-dump
# polyglot-covers: python.sqlite3.dump-restore python.sqlite3.executescript-restore
# polyglot-covers: python.sqlite3.backup python.sqlite3.backup-memory
# polyglot-covers: python.sqlite3.backup-progress python.sqlite3.backup-pages
# polyglot-covers: python.sqlite3.backup-attached-database python.sqlite3.backup-name
# polyglot-covers: python.sqlite3.uri python.sqlite3.uri-read-only python.sqlite3.uri-rw
# polyglot-covers: python.sqlite3.shared-memory-uri python.sqlite3.uri-lifetime
# polyglot-covers: python.sqlite3.timeout python.sqlite3.database-lock
# polyglot-covers: python.sqlite3.OperationalError python.sqlite3.no-sleep




def _populated_connection():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE language(name TEXT, year INTEGER)")
    connection.executemany(
        "INSERT INTO language VALUES (?, ?)",
        [("Python", 1991), ("Go", 2009), ("Rust", 2010)],
    )
    connection.commit()
    return connection


def test_iterdump_emits_transactional_sql_source():
    """dump 是 SQL statement iterator，不是 bytes snapshot；通常逐行写入文本文件。"""

    connection = _populated_connection()
    try:
        lines = list(connection.iterdump())

        assert lines[0] == "BEGIN TRANSACTION;"
        assert lines[-1] == "COMMIT;"
        assert any(line.startswith("CREATE TABLE language") for line in lines)
        assert sum(line.startswith("INSERT INTO \"language\"") for line in lines) == 3
    finally:
        connection.close()


def test_iterdump_output_can_restore_schema_and_data():
    """用 executescript 消费 dump，可把内存库迁移到另一个独立 connection。"""

    source = _populated_connection()
    target = sqlite3.connect(":memory:")
    try:
        script = "\n".join(source.iterdump())
        target.executescript(script)

        rows = target.execute(
            "SELECT name, year FROM language ORDER BY year"
        ).fetchall()
        assert rows == [("Python", 1991), ("Go", 2009), ("Rust", 2010)]
    finally:
        target.close()
        source.close()


def test_backup_copies_an_in_memory_database_to_another_connection():
    """backup target 是已打开 Connection；返回 None，schema 与 records 一起复制。"""

    source = _populated_connection()
    target = sqlite3.connect(":memory:")
    try:
        returned = source.backup(target)

        assert returned is None
        assert target.execute(
            "SELECT name FROM language ORDER BY year"
        ).fetchall() == [("Python",), ("Go",), ("Rust",)]
    finally:
        target.close()
        source.close()


def test_backup_progress_reports_integer_page_counts():
    """pages 控制每个 step 的规模；最后 callback 的 remaining 为零。"""

    source = sqlite3.connect(":memory:")
    target = sqlite3.connect(":memory:")
    reports = []
    try:
        source.execute("CREATE TABLE payload(value BLOB)")
        source.executemany(
            "INSERT INTO payload VALUES (?)",
            [(b"x" * 2048,) for _ in range(20)],
        )
        source.commit()

        source.backup(
            target,
            pages=1,
            progress=lambda status, remaining, total: reports.append(
                (status, remaining, total)
            ),
            sleep=0,
        )

        assert reports
        assert all(all(isinstance(value, int) for value in report) for report in reports)
        assert reports[-1][1] == 0
        assert reports[-1][2] >= 1
        assert target.execute("SELECT count(*) FROM payload").fetchone() == (20,)
    finally:
        target.close()
        source.close()


def test_backup_can_select_an_attached_source_database(tmp_path):
    """name 不限 main/temp，也可指定 ATTACH 的 schema；target 收到它作为自己的 main。"""

    attached_path = tmp_path / "archive.sqlite"
    source = sqlite3.connect(":memory:")
    target = sqlite3.connect(":memory:")
    try:
        source.execute("ATTACH DATABASE ? AS archive", (str(attached_path),))
        source.execute("CREATE TABLE archive.event(value)")
        source.execute("INSERT INTO archive.event VALUES ('copied')")
        source.commit()

        source.backup(target, name="archive")

        assert target.execute("SELECT * FROM event").fetchall() == [("copied",)]
    finally:
        target.close()
        source.close()


def test_backup_rejects_an_unknown_source_database_name():
    """name 是 SQLite schema name，不是输出文件名；未知名称属于 OperationalError。"""

    source = sqlite3.connect(":memory:")
    target = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.OperationalError):
            source.backup(target, name="missing_schema")
    finally:
        target.close()
        source.close()


def test_uri_read_only_mode_allows_queries_and_rejects_writes(tmp_path):
    """mode=ro 防止意外 mutation；必须同时传 uri=True 才解析 query parameters。"""

    path = tmp_path / "readonly.sqlite"
    writer = sqlite3.connect(path)
    writer.execute("CREATE TABLE item(value)")
    writer.execute("INSERT INTO item VALUES ('kept')")
    writer.commit()
    writer.close()

    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        assert connection.execute("SELECT * FROM item").fetchall() == [("kept",)]
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO item VALUES ('blocked')")
    finally:
        connection.close()


def test_uri_rw_mode_refuses_to_create_a_missing_database(tmp_path):
    """普通 connect 会创建文件；mode=rw 适合把路径拼写错误变成立即失败。"""

    path = tmp_path / "missing.sqlite"

    with pytest.raises(sqlite3.OperationalError):
        sqlite3.connect(f"{path.as_uri()}?mode=rw", uri=True)

    assert path.exists() is False


def test_named_shared_memory_uri_is_visible_between_live_connections():
    """相同 URI 的 shared cache 共享内存库；普通 ``:memory:`` 不共享。"""

    uri = "file:polyglot_113_shared?mode=memory&cache=shared"
    first = sqlite3.connect(uri, uri=True)
    second = sqlite3.connect(uri, uri=True)
    try:
        first.execute("CREATE TABLE item(value)")
        first.execute("INSERT INTO item VALUES (28)")
        first.commit()

        assert second.execute("SELECT * FROM item").fetchall() == [(28,)]
    finally:
        second.close()
        first.close()


def test_shared_memory_database_lives_until_the_last_connection_closes():
    """named memory URI 不是持久文件；所有连接关闭后，再同名连接得到全新空库。"""

    uri = "file:polyglot_113_lifetime?mode=memory&cache=shared"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("CREATE TABLE transient(value)")
    connection.close()

    reopened = sqlite3.connect(uri, uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            reopened.execute("SELECT * FROM transient")
    finally:
        reopened.close()


def test_zero_timeout_reports_a_write_lock_without_sleeping(tmp_path):
    """timeout 是等待锁的上限；设零可在测试/非阻塞流程中立即得到 OperationalError。"""

    path = tmp_path / "locked.sqlite"
    first = sqlite3.connect(path)
    second = sqlite3.connect(path, timeout=0)
    try:
        first.execute("CREATE TABLE item(value)")
        first.commit()
        first.execute("BEGIN EXCLUSIVE")
        first.execute("INSERT INTO item VALUES ('pending')")

        with pytest.raises(sqlite3.OperationalError, match="locked"):
            second.execute("INSERT INTO item VALUES ('blocked')")
    finally:
        first.rollback()
        second.close()
        first.close()


# 114｜``sqlite3`` DB-API 常量、异常层级、自定义 factory 与线程边界。
#
# 模块同时暴露 Python wrapper version 与链接的 SQLite runtime version，两者不要混淆。
# DB-API ``threadsafety=1`` 表示可共享模块但默认不能跨线程使用同一 connection；确需共享时
# 可传 ``check_same_thread=False``，但写操作的序列化责任转移给调用者。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.sqlite3.apilevel python.sqlite3.paramstyle
# polyglot-covers: python.sqlite3.threadsafety python.sqlite3.module-version
# polyglot-covers: python.sqlite3.sqlite-version python.sqlite3.version-info
# polyglot-covers: python.sqlite3.exception-hierarchy python.sqlite3.Error
# polyglot-covers: python.sqlite3.OperationalError python.sqlite3.IntegrityError
# polyglot-covers: python.sqlite3.ProgrammingError python.sqlite3.Warning
# polyglot-covers: python.sqlite3.connection-factory python.sqlite3.Connection-subclass
# polyglot-covers: python.sqlite3.cursor-factory python.sqlite3.Cursor-subclass
# polyglot-covers: python.sqlite3.check-same-thread python.sqlite3.cross-thread-error
# polyglot-covers: python.sqlite3.cross-thread-opt-out python.sqlite3.user-serialization
# polyglot-covers: python.sqlite3.compile-options python.sqlite3.SQLITE-THREADSAFE
# polyglot-covers: python.sqlite3.Date python.sqlite3.Time python.sqlite3.Timestamp
# polyglot-covers: python.sqlite3.FromTicks python.sqlite3.Binary python.sqlite3.BLOB-adapter
# polyglot-covers: python.sqlite3.interrupt python.sqlite3.cross-thread-interrupt




class TrackingConnection(sqlite3.Connection):
    def execute(self, sql, parameters=(), /):
        self.last_sql = sql
        return super().execute(sql, parameters)


class TrackingCursor(sqlite3.Cursor):
    def execute(self, sql, parameters=(), /):
        self.last_sql = sql
        return super().execute(sql, parameters)


def test_required_db_api_constants_describe_the_supported_contract():
    """paramstyle 声明 qmark；sqlite3 额外支持 named，但不因此改变规范常量。"""

    assert sqlite3.apilevel == "2.0"
    assert sqlite3.paramstyle == "qmark"
    assert sqlite3.threadsafety == 1


def test_wrapper_and_runtime_versions_have_string_and_tuple_forms():
    """version 属于 Python module，sqlite_version 属于动态链接 library。"""

    assert isinstance(sqlite3.version, str)
    assert isinstance(sqlite3.version_info, tuple)
    assert all(isinstance(part, int) for part in sqlite3.version_info)

    assert isinstance(sqlite3.sqlite_version, str)
    assert isinstance(sqlite3.sqlite_version_info, tuple)
    assert all(isinstance(part, int) for part in sqlite3.sqlite_version_info)
    assert sqlite3.sqlite_version.startswith(
        ".".join(str(part) for part in sqlite3.sqlite_version_info[:2])
    )


def test_db_api_date_time_constructors_are_standard_datetime_types():
    """DB-API constructor names 是 datetime classes 的 aliases，不是 sqlite3 私有包装。"""

    assert sqlite3.Date is datetime.date
    assert sqlite3.Time is datetime.time
    assert sqlite3.Timestamp is datetime.datetime
    assert sqlite3.Date(2024, 2, 29) == datetime.date(2024, 2, 29)
    assert sqlite3.Time(12, 30, 45) == datetime.time(12, 30, 45)
    assert sqlite3.Timestamp(2024, 1, 2, 3, 4, 5) == datetime.datetime(
        2024, 1, 2, 3, 4, 5
    )


def test_from_ticks_constructors_follow_local_time_not_utc():
    """FromTicks 委托 time.localtime；结果会受进程 timezone 影响，不是 UTC conversion。"""

    ticks = 1_700_000_000
    parts = time.localtime(ticks)

    assert sqlite3.DateFromTicks(ticks) == datetime.date(*parts[:3])
    assert sqlite3.TimeFromTicks(ticks) == datetime.time(*parts[3:6])
    assert sqlite3.TimestampFromTicks(ticks) == datetime.datetime(*parts[:6])


def test_binary_wraps_a_buffer_and_binds_it_as_blob():
    """Binary 在 3.10 是 memoryview alias；binding 时内容进入 BLOB，读取返回 bytes。"""

    wrapped = sqlite3.Binary(bytearray(b"\x00\xff"))
    connection = sqlite3.connect(":memory:")
    try:
        restored, storage_class = connection.execute(
            "SELECT ?, typeof(?)", (wrapped, wrapped)
        ).fetchone()

        assert isinstance(wrapped, memoryview)
        assert wrapped.tobytes() == b"\x00\xff"
        assert restored == b"\x00\xff"
        assert storage_class == "blob"
    finally:
        connection.close()


def test_db_api_exception_hierarchy_supports_broad_or_precise_catches():
    """Warning 独立于 Error；database subclasses 最终都可由 sqlite3.Error 捕获。"""

    assert issubclass(sqlite3.Warning, Exception)
    assert not issubclass(sqlite3.Warning, sqlite3.Error)
    assert issubclass(sqlite3.InterfaceError, sqlite3.Error)
    assert issubclass(sqlite3.DatabaseError, sqlite3.Error)

    for error_type in (
        sqlite3.DataError,
        sqlite3.OperationalError,
        sqlite3.IntegrityError,
        sqlite3.InternalError,
        sqlite3.ProgrammingError,
        sqlite3.NotSupportedError,
    ):
        assert issubclass(error_type, sqlite3.DatabaseError)


def test_sql_operation_failure_raises_operational_error():
    """缺失 table 是数据库当前状态/操作问题，不是 constraint 或 Python API 形状错误。"""

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            connection.execute("SELECT * FROM missing")
    finally:
        connection.close()


def test_relational_constraint_failure_raises_integrity_error():
    """UNIQUE/FOREIGN KEY 等 relational integrity 失败使用 IntegrityError。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE account(name TEXT UNIQUE)")
        connection.execute("INSERT INTO account VALUES ('alice')")

        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            connection.execute("INSERT INTO account VALUES ('alice')")
    finally:
        connection.close()


def test_error_base_class_can_catch_different_database_failures():
    """边界层可捕获 Error 统一 cleanup，业务层通常应继续区分具体 subclass。"""

    connection = sqlite3.connect(":memory:")
    try:
        for sql in ("SELECT * FROM missing", "THIS IS INVALID SQL"):
            with pytest.raises(sqlite3.Error):
                connection.execute(sql)
    finally:
        connection.close()


def test_connect_factory_constructs_a_connection_subclass():
    """factory 接管实例类型，同时保留底层初始化；适合 instrumentation 或统一策略。"""

    connection = sqlite3.connect(":memory:", factory=TrackingConnection)
    try:
        cursor = connection.execute("SELECT ?", (42,))

        assert isinstance(connection, TrackingConnection)
        assert connection.last_sql == "SELECT ?"
        assert cursor.fetchone() == (42,)
    finally:
        connection.close()


def test_cursor_factory_constructs_a_cursor_subclass():
    """Connection.cursor(factory=...) 只影响该 cursor，不替换 connection shortcut 行为。"""

    connection = sqlite3.connect(":memory:")
    try:
        cursor = connection.cursor(factory=TrackingCursor)
        returned = cursor.execute("SELECT ?", (7,))

        assert isinstance(cursor, TrackingCursor)
        assert returned is cursor
        assert cursor.last_sql == "SELECT ?"
        assert cursor.fetchone() == (7,)
    finally:
        connection.close()


def test_default_connection_rejects_use_from_another_thread():
    """check_same_thread=True 记录 creator thread；跨线程使用得到 ProgrammingError。"""

    connection = sqlite3.connect(":memory:")
    outcomes = queue.Queue()

    def use_connection():
        try:
            connection.execute("SELECT 1")
        except Exception as error:
            outcomes.put(error)
        else:
            outcomes.put("unexpected success")

    worker = threading.Thread(target=use_connection)
    worker.start()
    worker.join()
    try:
        error = outcomes.get_nowait()
        assert isinstance(error, sqlite3.ProgrammingError)
        assert "thread" in str(error).lower()
    finally:
        connection.close()


def test_check_same_thread_false_allows_serial_cross_thread_access():
    """opt-out 仅移除 Python guard；此例串行读，真实并发写仍须应用自行加锁。"""

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("CREATE TABLE item(value)")
    connection.execute("INSERT INTO item VALUES (42)")
    connection.commit()
    outcomes = queue.Queue()

    def read_connection():
        outcomes.put(connection.execute("SELECT * FROM item").fetchall())

    worker = threading.Thread(target=read_connection)
    worker.start()
    worker.join()
    try:
        assert outcomes.get_nowait() == [(42,)]
    finally:
        connection.close()


def test_interrupt_aborts_an_active_query_from_another_thread():
    """interrupt 是少数明确跨线程调用的 API；Event 协调代替不稳定的 sleep。"""

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    entered_callback = threading.Event()
    release_callback = threading.Event()
    outcomes = queue.Queue()

    def blocking_function(value):
        entered_callback.set()
        release_callback.wait(timeout=2)
        return value

    def run_query():
        try:
            outcomes.put(connection.execute("SELECT py_block(1)").fetchone())
        except Exception as error:
            outcomes.put(error)

    connection.create_function("py_block", 1, blocking_function)
    worker = threading.Thread(target=run_query)
    worker.start()
    try:
        assert entered_callback.wait(timeout=2) is True
        assert connection.interrupt() is None
    finally:
        release_callback.set()
        worker.join(timeout=2)

    try:
        assert worker.is_alive() is False
        error = outcomes.get_nowait()
        assert isinstance(error, sqlite3.OperationalError)
        assert "interrupt" in str(error).lower()
    finally:
        connection.close()


def test_runtime_compile_options_report_sqlite_threadsafe_mode():
    """DB-API level 与 SQLITE_THREADSAFE 数字含义不同；compile option 才描述底层构建。"""

    connection = sqlite3.connect(":memory:")
    try:
        options = connection.execute(
            "SELECT compile_options FROM pragma_compile_options "
            "WHERE compile_options LIKE 'THREADSAFE=%'"
        ).fetchall()

        assert len(options) == 1
        name, value = options[0][0].split("=", 1)
        assert name == "THREADSAFE"
        assert value in {"0", "1", "2"}
    finally:
        connection.close()
