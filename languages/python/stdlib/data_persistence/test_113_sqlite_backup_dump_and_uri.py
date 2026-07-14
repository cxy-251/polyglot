"""113｜``sqlite3`` SQL dump、online backup、URI 与连接锁等待。

``iterdump`` 产生可读 SQL，适合迁移/审阅；``backup`` 直接复制数据库 pages，并可在源库
仍被访问时工作。``uri=True`` 才能使用 mode=ro/rw、named shared memory 等 SQLite URI
参数。锁等待案例用 ``timeout=0`` 立即失败，不引入 sleep 或时间敏感断言。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sqlite3.iterdump python.sqlite3.sql-dump
# polyglot-covers: python.sqlite3.dump-restore python.sqlite3.executescript-restore
# polyglot-covers: python.sqlite3.backup python.sqlite3.backup-memory
# polyglot-covers: python.sqlite3.backup-progress python.sqlite3.backup-pages
# polyglot-covers: python.sqlite3.backup-attached-database python.sqlite3.backup-name
# polyglot-covers: python.sqlite3.uri python.sqlite3.uri-read-only python.sqlite3.uri-rw
# polyglot-covers: python.sqlite3.shared-memory-uri python.sqlite3.uri-lifetime
# polyglot-covers: python.sqlite3.timeout python.sqlite3.database-lock
# polyglot-covers: python.sqlite3.OperationalError python.sqlite3.no-sleep

import sqlite3

import pytest


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
