"""109｜``sqlite3`` 隐式事务、autocommit 与 connection context manager。

Python 3.10 的 sqlite3 事务规则不同于 PEP 249 推荐：默认只在 DML 前隐式 BEGIN，
SELECT/DDL 不会自行开启事务；``isolation_level=None`` 才把控制完全交给 SQLite
autocommit/显式 SQL。Connection 的 with 只负责 commit/rollback，既不 BEGIN 也不 close。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sqlite3.isolation-level python.sqlite3.deferred-default
# polyglot-covers: python.sqlite3.in-transaction python.sqlite3.implicit-begin
# polyglot-covers: python.sqlite3.DML-transaction python.sqlite3.DDL-transaction
# polyglot-covers: python.sqlite3.commit python.sqlite3.rollback python.sqlite3.no-op
# polyglot-covers: python.sqlite3.close-without-commit python.sqlite3.persistence
# polyglot-covers: python.sqlite3.connection-context python.sqlite3.context-commit
# polyglot-covers: python.sqlite3.context-rollback python.sqlite3.context-does-not-close
# polyglot-covers: python.sqlite3.autocommit python.sqlite3.explicit-begin
# polyglot-covers: python.sqlite3.executescript-implicit-commit python.sqlite3.savepoint

import sqlite3

import pytest


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
