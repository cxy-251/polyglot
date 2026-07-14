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
