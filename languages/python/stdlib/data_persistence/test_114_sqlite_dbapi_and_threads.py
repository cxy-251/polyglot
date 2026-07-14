"""114｜``sqlite3`` DB-API 常量、异常层级、自定义 factory 与线程边界。

模块同时暴露 Python wrapper version 与链接的 SQLite runtime version，两者不要混淆。
DB-API ``threadsafety=1`` 表示可共享模块但默认不能跨线程使用同一 connection；确需共享时
可传 ``check_same_thread=False``，但写操作的序列化责任转移给调用者。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import datetime
import queue
import sqlite3
import threading
import time

import pytest


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
