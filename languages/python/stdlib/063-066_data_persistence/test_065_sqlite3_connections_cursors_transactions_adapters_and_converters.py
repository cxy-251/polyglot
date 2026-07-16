"""065｜``sqlite3`` 连接、原生类型、CRUD 与参数绑定。

SQLite 是无独立服务进程的磁盘/内存数据库；``sqlite3`` 实现 DB-API 2.0。SQL 结构由
程序给出，数据必须通过 qmark 或 named placeholder 绑定，不能用字符串拼接。默认只转换
SQLite 的 NULL/INTEGER/REAL/TEXT/BLOB 五种存储类，自定义类型留给后续适配案例。

这些案例面向 Python 3.10。
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
import datetime

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


# ``sqlite3.Cursor`` 批处理、结果消费与 DB-API 元数据。
#
# Cursor 既是语句执行器，也是查询结果的 iterator。``execute`` 只接受一条 statement，
# ``executemany`` 针对 DML 重复绑定，``executescript`` 才负责脚本。``description``、
# ``lastrowid`` 与 ``rowcount`` 各有不同更新时间，不能把它们当成统一的结果摘要。
#
# 这些案例面向 Python 3.10。

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


# ``sqlite3`` 隐式事务、autocommit 与 connection context manager。
#
# Python 3.10 的 sqlite3 事务规则不同于 PEP 249 推荐：默认只在 DML 前隐式 BEGIN，
# SELECT/DDL 不会自行开启事务；``isolation_level=None`` 才把控制完全交给 SQLite
# autocommit/显式 SQL。Connection 的 with 只负责 commit/rollback，既不 BEGIN 也不 close。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.sqlite3.isolation-level python.sqlite3.deferred-default
# polyglot-covers: python.sqlite3.in-transaction python.sqlite3.implicit-begin
# polyglot-covers: python.sqlite3.DML-transaction python.sqlite3.DDL-transaction
# polyglot-covers: python.sqlite3.commit python.sqlite3.rollback python.sqlite3.no-op
# polyglot-covers: python.sqlite3.close-without-commit python.sqlite3.persistence
# polyglot-covers: python.sqlite3.connection-context python.sqlite3.context-commit
# polyglot-covers: python.sqlite3.context-rollback python.sqlite3.context-does-not-close
# polyglot-covers: python.sqlite3.autocommit python.sqlite3.explicit-begin
# polyglot-covers: python.sqlite3.executescript-implicit-commit python.sqlite3.savepoint




def test_default_isolation_level_is_an_alias_for_deferred():
    """空字符串是 3.10 的默认值，语义等价于 DEFERRED，不表示 autocommit。"""

    connection = sqlite3.connect(":memory:")
    try:
        assert connection.isolation_level == ""
        assert connection.in_transaction is False
    finally:
        connection.close()

def test_select_and_ddl_do_not_implicitly_open_a_transaction():
    """默认模式只在 INSERT/UPDATE/DELETE/REPLACE 前隐式 BEGIN。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("SELECT 1")
        assert connection.in_transaction is False

        connection.execute("CREATE TABLE item(value)")
        assert connection.in_transaction is False
    finally:
        connection.close()


def test_dml_implicitly_opens_and_commit_closes_the_transaction():
    """in_transaction 观察底层 SQLite autocommit 状态，而不是“是否用过 connection”。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE item(value)")
        connection.execute("INSERT INTO item VALUES (1)")
        assert connection.in_transaction is True

        assert connection.commit() is None
        assert connection.in_transaction is False
        assert connection.execute("SELECT * FROM item").fetchall() == [(1,)]
    finally:
        connection.close()


def test_rollback_discards_all_changes_since_implicit_begin():
    """同一事务中的多条 DML 一起撤销；rollback 不是只撤销最后一条 statement。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE item(value)")
        connection.executemany("INSERT INTO item VALUES (?)", [(1,), (2,), (3,)])
        connection.execute("UPDATE item SET value = value * 10")

        assert connection.rollback() is None
        assert connection.in_transaction is False
        assert connection.execute("SELECT * FROM item").fetchall() == []
    finally:
        connection.close()


def test_commit_and_rollback_are_no_ops_without_an_open_transaction():
    """调用者可在 cleanup 中无条件结束事务，不必先分支检查 in_transaction。"""

    connection = sqlite3.connect(":memory:")
    try:
        assert connection.in_transaction is False
        assert connection.commit() is None
        assert connection.rollback() is None
        assert connection.in_transaction is False
    finally:
        connection.close()


def test_close_does_not_implicitly_commit_pending_changes(tmp_path):
    """close 不是 commit；遗漏显式提交会静默丢失尚未提交的 DML。"""

    path = tmp_path / "close.sqlite"
    setup = sqlite3.connect(path)
    setup.execute("CREATE TABLE item(value)")
    setup.commit()
    setup.execute("INSERT INTO item VALUES ('lost')")
    setup.close()

    reopened = sqlite3.connect(path)
    try:
        assert reopened.execute("SELECT * FROM item").fetchall() == []
    finally:
        reopened.close()


def test_committed_changes_are_visible_to_a_new_connection(tmp_path):
    """同 connection 的 SELECT 可见未提交写入；新连接才可验证真正持久化。"""

    path = tmp_path / "committed.sqlite"
    writer = sqlite3.connect(path)
    writer.execute("CREATE TABLE item(value)")
    writer.execute("INSERT INTO item VALUES ('kept')")
    writer.commit()

    reader = sqlite3.connect(path)
    try:
        assert reader.execute("SELECT * FROM item").fetchall() == [("kept",)]
    finally:
        reader.close()
        writer.close()


def test_connection_context_commits_a_successful_open_transaction(tmp_path):
    """with body 的 DML 隐式 BEGIN，正常退出时 __exit__ 提交。"""

    path = tmp_path / "context-commit.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE item(value)")

    with connection:
        connection.execute("INSERT INTO item VALUES ('kept')")
        assert connection.in_transaction is True

    reader = sqlite3.connect(path)
    try:
        assert connection.in_transaction is False
        assert reader.execute("SELECT * FROM item").fetchall() == [("kept",)]
    finally:
        reader.close()
        connection.close()


def test_connection_context_rolls_back_and_propagates_body_exception():
    """异常不会被 __exit__ 吞掉；rollback 后由外层决定如何处理原异常。"""

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE item(value)")
    try:
        with pytest.raises(RuntimeError, match="abort"):
            with connection:
                connection.execute("INSERT INTO item VALUES ('lost')")
                raise RuntimeError("abort transaction")

        assert connection.in_transaction is False
        assert connection.execute("SELECT * FROM item").fetchall() == []
    finally:
        connection.close()


def test_connection_context_does_not_open_or_close_a_connection():
    """没有 DML 时 context 是 no-op；退出后同一个 connection 仍可继续查询。"""

    connection = sqlite3.connect(":memory:")
    try:
        with connection:
            assert connection.in_transaction is False
            assert connection.execute("SELECT 1").fetchone() == (1,)

        assert connection.execute("SELECT 2").fetchone() == (2,)
    finally:
        connection.close()


def test_ddl_participates_when_a_transaction_is_already_open():
    """3.6 起 sqlite3 不再在 DDL 前隐式 commit；table definition 也能随事务回滚。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE anchor(value)")
        connection.execute("INSERT INTO anchor VALUES (1)")
        connection.execute("CREATE TABLE created_inside_transaction(value)")
        connection.rollback()

        assert connection.execute("SELECT * FROM anchor").fetchall() == []
        assert connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE name = 'created_inside_transaction'"
        ).fetchone() is None
    finally:
        connection.close()


def test_none_isolation_level_leaves_simple_dml_in_autocommit_mode(tmp_path):
    """None 禁止 Python 隐式 BEGIN；每条独立 DML 由 SQLite 立即提交。"""

    path = tmp_path / "autocommit.sqlite"
    writer = sqlite3.connect(path, isolation_level=None)
    writer.execute("CREATE TABLE item(value)")
    writer.execute("INSERT INTO item VALUES ('visible')")
    assert writer.in_transaction is False

    reader = sqlite3.connect(path)
    try:
        assert reader.execute("SELECT * FROM item").fetchall() == [("visible",)]
    finally:
        reader.close()
        writer.close()


def test_autocommit_mode_still_allows_explicit_transaction_sql():
    """isolation_level=None 不等于禁止事务；BEGIN/ROLLBACK 可由应用完整控制。"""

    connection = sqlite3.connect(":memory:", isolation_level=None)
    try:
        connection.execute("CREATE TABLE item(value)")
        connection.execute("BEGIN")
        assert connection.in_transaction is True
        connection.execute("INSERT INTO item VALUES (1)")
        connection.execute("ROLLBACK")

        assert connection.in_transaction is False
        assert connection.execute("SELECT * FROM item").fetchall() == []
    finally:
        connection.close()


def test_executescript_commits_a_pending_transaction_before_the_script(tmp_path):
    """executescript 总是先 COMMIT；之后 rollback 无法撤销脚本前的 pending DML。"""

    path = tmp_path / "script-commit.sqlite"
    writer = sqlite3.connect(path)
    writer.execute("CREATE TABLE item(value)")
    writer.commit()
    writer.execute("INSERT INTO item VALUES ('before script')")

    writer.executescript("INSERT INTO item VALUES ('inside script');")
    writer.rollback()

    reader = sqlite3.connect(path)
    try:
        rows = reader.execute("SELECT value FROM item ORDER BY rowid").fetchall()
        assert rows == [("before script",), ("inside script",)]
    finally:
        reader.close()
        writer.close()


def test_savepoint_can_rollback_part_of_an_explicit_transaction():
    """SAVEPOINT 提供嵌套工作单元；ROLLBACK TO 保留外层事务及 savepoint 前写入。"""

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE item(value)")
        connection.execute("INSERT INTO item VALUES ('outer')")
        connection.execute("SAVEPOINT nested")
        connection.execute("INSERT INTO item VALUES ('discarded')")
        connection.execute("ROLLBACK TO nested")
        connection.execute("RELEASE nested")
        connection.commit()

        assert connection.execute("SELECT * FROM item").fetchall() == [("outer",)]
    finally:
        connection.close()


# ``sqlite3`` 自适配协议、注册 adapter 与 converter。
#
# SQLite 只能绑定五种原生类型。写入方向可由对象的 ``__conform__(PrepareProtocol)`` 或
# 全局注册 adapter 转换，且注册 adapter 优先；读取方向的 converter 总接收 bytes，只有
# connect 启用 PARSE_DECLTYPES/PARSE_COLNAMES 才运行。converter 注册是进程级全局状态，
# 因此案例使用本文件唯一的类型名，避免相互覆盖。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.sqlite3.PrepareProtocol python.sqlite3.__conform__
# polyglot-covers: python.sqlite3.register-adapter python.sqlite3.adapter-precedence
# polyglot-covers: python.sqlite3.adapter-native-result python.sqlite3.unsupported-type
# polyglot-covers: python.sqlite3.register-converter python.sqlite3.converter-bytes
# polyglot-covers: python.sqlite3.PARSE_DECLTYPES python.sqlite3.first-declared-word
# polyglot-covers: python.sqlite3.PARSE_COLNAMES python.sqlite3.column-name-precedence
# polyglot-covers: python.sqlite3.converter-case-insensitive python.sqlite3.NULL-conversion
# polyglot-covers: python.sqlite3.detect-types-disabled python.sqlite3.generated-field
# polyglot-covers: python.sqlite3.date-adapter python.sqlite3.timestamp-converter
# polyglot-covers: python.sqlite3.timestamp-offset-trap python.sqlite3.microsecond-truncation




class SelfAdaptingPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.seen_protocol = None

    def __conform__(self, protocol):
        self.seen_protocol = protocol
        if protocol is sqlite3.PrepareProtocol:
            return f"{self.x};{self.y}"
        return None


class RegisteredPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __conform__(self, protocol):
        return "self-adapted"


class UnsupportedValue:
    pass


def test_object_can_adapt_itself_through_prepare_protocol():
    """binding 时 sqlite3 隐式调用 __conform__，不是 Python 的 str(object) fallback。"""

    point = SelfAdaptingPoint(4, -3)
    connection = sqlite3.connect(":memory:")
    try:
        restored = connection.execute("SELECT ?", (point,)).fetchone()[0]

        assert restored == "4;-3"
        assert point.seen_protocol is sqlite3.PrepareProtocol
    finally:
        connection.close()


def test_registered_adapter_takes_precedence_over_object_conform():
    """应用注册规则覆盖 library type 自带规则，便于统一外部存储表示。"""

    sqlite3.register_adapter(
        RegisteredPoint,
        lambda point: f"registered:{point.x},{point.y}",
    )
    connection = sqlite3.connect(":memory:")
    try:
        value = connection.execute(
            "SELECT ?", (RegisteredPoint(1, 2),)
        ).fetchone()[0]

        assert value == "registered:1,2"
    finally:
        connection.close()


def test_adapter_must_return_a_natively_supported_value():
    """adapter 不能返回另一个任意对象并期待无限递归适配。"""

    class BadlyAdapted:
        pass

    sqlite3.register_adapter(BadlyAdapted, lambda value: UnsupportedValue())
    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.Error):
            connection.execute("SELECT ?", (BadlyAdapted(),))
    finally:
        connection.close()


def test_unadapted_custom_type_cannot_be_bound_implicitly():
    """sqlite3 不会 pickle 或 repr 未知对象；缺少协议/adapter 应尽早失败。"""

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(sqlite3.Error):
            connection.execute("SELECT ?", (UnsupportedValue(),))
    finally:
        connection.close()


def test_declared_type_converter_receives_bytes_and_returns_custom_value():
    """converter 输入永远是原始 bytes，即便 SQLite value 看起来像数字。"""

    inputs = []

    def convert_distance(value):
        inputs.append(value)
        return ("distance", int(value))

    sqlite3.register_converter("distance_110", convert_distance)
    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    try:
        connection.execute("CREATE TABLE route(length DISTANCE_110)")
        connection.execute("INSERT INTO route VALUES (?)", (42,))

        assert connection.execute("SELECT length FROM route").fetchone() == (
            ("distance", 42),
        )
        assert inputs == [b"42"]
    finally:
        connection.close()


def test_declared_type_lookup_uses_only_first_word_and_ignores_case():
    """``TYPE(10)``/``TYPE extra`` 都用首词查表，typename 大小写不敏感。"""

    sqlite3.register_converter("TOKEN_110", lambda value: value.decode().upper())
    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    try:
        connection.execute("CREATE TABLE sample(value token_110 extra metadata)")
        connection.execute("INSERT INTO sample VALUES ('converted')")

        assert connection.execute("SELECT value FROM sample").fetchone() == (
            "CONVERTED",
        )
    finally:
        connection.close()


def test_column_name_annotation_enables_explicit_conversion():
    """PARSE_COLNAMES 读取 ``alias [typename]``；展示给 row 的 column name 会去掉标注。"""

    sqlite3.register_converter("REVERSED_110", lambda value: value[::-1])
    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_COLNAMES
    )
    try:
        cursor = connection.execute(
            'SELECT "abc" AS "payload [reversed_110]"'
        )

        assert cursor.fetchone() == (b"cba",)
        assert cursor.description[0][0] == "payload"
    finally:
        connection.close()


def test_column_name_converter_wins_when_both_detection_modes_are_enabled():
    """同一 column 同时有 declared/alias type 时，更局部的 alias 规则优先。"""

    sqlite3.register_converter("DECLARED_110", lambda value: "declared")
    sqlite3.register_converter("ALIAS_110", lambda value: "alias")
    flags = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    connection = sqlite3.connect(":memory:", detect_types=flags)
    try:
        connection.execute("CREATE TABLE sample(value DECLARED_110)")
        connection.execute("INSERT INTO sample VALUES ('raw')")

        row = connection.execute(
            'SELECT value AS "value [ALIAS_110]" FROM sample'
        ).fetchone()

        assert row == ("alias",)
    finally:
        connection.close()


def test_registered_converter_is_inert_when_detection_is_disabled():
    """register_converter 本身不改变所有 connection；detect_types 默认 0。"""

    sqlite3.register_converter("INERT_110", lambda value: "converted")
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE sample(value INERT_110)")
        connection.execute("INSERT INTO sample VALUES ('raw')")

        assert connection.execute("SELECT value FROM sample").fetchone() == ("raw",)
    finally:
        connection.close()


def test_converter_is_not_called_for_sql_null():
    """NULL 始终先映射为 None；converter 不会收到可被误解为文本 ``b'None'`` 的值。"""

    seen = []

    def converter(value):
        seen.append(value)
        return "converted"

    sqlite3.register_converter("NULLABLE_110", converter)
    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    try:
        connection.execute("CREATE TABLE sample(value NULLABLE_110)")
        connection.execute("INSERT INTO sample VALUES (NULL)")

        assert connection.execute("SELECT value FROM sample").fetchone() == (None,)
        assert seen == []
    finally:
        connection.close()


def test_generated_field_does_not_inherit_declared_type_conversion():
    """max(value) 等 expression 没有 declared column type，3.10 不对结果运行 converter。"""

    sqlite3.register_converter("UPPER_110", lambda value: value.decode().upper())
    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    try:
        connection.execute("CREATE TABLE sample(value UPPER_110)")
        connection.executemany("INSERT INTO sample VALUES (?)", [("a",), ("b",)])

        direct = connection.execute("SELECT value FROM sample ORDER BY value").fetchall()
        generated = connection.execute("SELECT max(value) FROM sample").fetchone()

        assert direct == [("A",), ("B",)]
        assert generated == ("b",)
    finally:
        connection.close()


def test_default_date_and_datetime_adapters_need_detection_to_round_trip_types():
    """默认 adapter 写 ISO text；只有启用 declared converter 才恢复 date/datetime。"""

    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    today = datetime.date(2024, 2, 29)
    moment = datetime.datetime(2024, 2, 29, 12, 30, 45, 123456)
    try:
        connection.execute("CREATE TABLE event(day date, happened timestamp)")
        connection.execute("INSERT INTO event VALUES (?, ?)", (today, moment))

        restored = connection.execute("SELECT day, happened FROM event").fetchone()

        assert restored == (today, moment)
        assert type(restored[0]) is datetime.date
        assert type(restored[1]) is datetime.datetime
    finally:
        connection.close()


def test_default_timestamp_converter_truncates_beyond_microseconds():
    """默认 converter 只保留六位 microseconds；更高精度需自定义存储/转换。"""

    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    try:
        connection.execute("CREATE TABLE event(happened timestamp)")
        connection.execute(
            "INSERT INTO event VALUES (?)",
            ("2024-01-02 03:04:05.123456789",),
        )

        restored = connection.execute("SELECT happened FROM event").fetchone()[0]

        assert restored == datetime.datetime(2024, 1, 2, 3, 4, 5, 123456)
    finally:
        connection.close()


def test_default_timestamp_converter_discards_utc_offset():
    """3.10 默认 timestamp converter 返回 naive datetime；保留 offset 必须自定义。"""

    connection = sqlite3.connect(
        ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
    )
    try:
        connection.execute("CREATE TABLE event(happened timestamp)")
        connection.execute(
            "INSERT INTO event VALUES (?)",
            # 3.10 converter 只读取小数部分前六位，因此 offset 被静默截掉。
            ("2024-01-02 03:04:05.000000+02:00",),
        )

        restored = connection.execute("SELECT happened FROM event").fetchone()[0]

        assert restored == datetime.datetime(2024, 1, 2, 3, 4, 5)
        assert restored.tzinfo is None
    finally:
        connection.close()
