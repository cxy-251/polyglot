"""110｜``sqlite3`` 自适配协议、注册 adapter 与 converter。

SQLite 只能绑定五种原生类型。写入方向可由对象的 ``__conform__(PrepareProtocol)`` 或
全局注册 adapter 转换，且注册 adapter 优先；读取方向的 converter 总接收 bytes，只有
connect 启用 PARSE_DECLTYPES/PARSE_COLNAMES 才运行。converter 注册是进程级全局状态，
因此案例使用本文件唯一的类型名，避免相互覆盖。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import datetime
import sqlite3

import pytest


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
