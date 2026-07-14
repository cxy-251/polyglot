"""142｜``plistlib`` XML/binary 格式、支持类型、文件 API 与排序控制。

plist 是有类型的序列化格式，但不会保留所有 Python 容器细节：tuple 会读回
list，bytearray 会读回 bytes。XML datetime 只保存到整秒，binary 则保留微秒。
``loads`` 能自动识别 XML/binary；``load``/``dump`` 则要求 binary file object，
不应套 text encoding。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.plistlib.dumps python.plistlib.loads
# polyglot-covers: python.plistlib.dump python.plistlib.load
# polyglot-covers: python.plistlib.FMT_XML python.plistlib.FMT_BINARY
# polyglot-covers: python.plistlib.format-autodetect python.plistlib.binary-file-object
# polyglot-covers: python.plistlib.string python.plistlib.integer
# polyglot-covers: python.plistlib.float python.plistlib.boolean
# polyglot-covers: python.plistlib.list python.plistlib.tuple-to-list
# polyglot-covers: python.plistlib.dictionary python.plistlib.nested-values
# polyglot-covers: python.plistlib.bytes python.plistlib.bytearray-to-bytes
# polyglot-covers: python.plistlib.datetime python.plistlib.xml-datetime-second-precision
# polyglot-covers: python.plistlib.binary-datetime-fraction
# polyglot-covers: python.plistlib.sort-keys python.plistlib.insertion-order
# polyglot-covers: python.plistlib.dict-type python.plistlib.xml-escaping

from collections import OrderedDict
from datetime import datetime
import plistlib

import pytest


def _representative_plist():
    """只返回官方支持类型；None、set 等不属于 portable plist model。"""

    return {
        "string": "<你好 & plist>",
        "integer": 42,
        "float": 1.25,
        "truth": True,
        "falsehood": False,
        "array": ("first", 2, [3]),
        "mapping": {"name": "nested"},
        "bytes": b"\x00\xff",
        "bytearray": bytearray(b"mutable input"),
        "date": datetime(2024, 2, 29, 12, 34, 56, 500000),
    }


@pytest.mark.parametrize("fmt", [plistlib.FMT_XML, plistlib.FMT_BINARY])
def test_supported_values_round_trip_in_both_formats(fmt):
    """两种 writer 共享值模型；返回容器和 binary data 会规范化为 list/bytes。"""

    encoded = plistlib.dumps(_representative_plist(), fmt=fmt)
    restored = plistlib.loads(encoded)

    assert isinstance(encoded, bytes)
    assert restored["string"] == "<你好 & plist>"
    assert restored["integer"] == 42
    assert type(restored["integer"]) is int
    assert restored["float"] == 1.25
    assert restored["truth"] is True
    assert restored["falsehood"] is False
    assert restored["array"] == ["first", 2, [3]]
    assert type(restored["array"]) is list
    assert restored["mapping"] == {"name": "nested"}
    assert restored["bytes"] == b"\x00\xff"
    assert restored["bytearray"] == b"mutable input"
    assert type(restored["bytearray"]) is bytes
    if fmt is plistlib.FMT_XML:
        # XML date 没有 microsecond 字段；writer 会截断，而不是四舍五入。
        assert restored["date"] == datetime(2024, 2, 29, 12, 34, 56)
    else:
        # binary date 是相对 2001-01-01 的 double seconds，可保留这个微秒值。
        assert restored["date"] == datetime(2024, 2, 29, 12, 34, 56, 500000)


def test_headers_distinguish_formats_and_loads_autodetects_each_one():
    """默认 dumps 是 XML；bplist00 标识 binary，fmt=None 自动选择 parser。"""

    value = {"answer": 42}
    xml_data = plistlib.dumps(value)
    binary_data = plistlib.dumps(value, fmt=plistlib.FMT_BINARY)

    assert xml_data.startswith(b"<?xml")
    assert binary_data.startswith(b"bplist00")
    assert plistlib.loads(xml_data, fmt=None) == value
    assert plistlib.loads(binary_data, fmt=None) == value


@pytest.mark.parametrize("fmt", [plistlib.FMT_XML, plistlib.FMT_BINARY])
def test_dump_and_load_work_with_binary_files(tmp_path, fmt):
    """file API 写/读 bytes；调用方负责以 wb/rb 打开，并可显式锁定格式。"""

    path = tmp_path / "settings.plist"
    value = {"name": "polyglot", "features": ["tests", "examples"]}

    with path.open("wb") as stream:
        assert plistlib.dump(value, stream, fmt=fmt) is None

    with path.open("rb") as stream:
        assert plistlib.load(stream, fmt=None) == value


def test_xml_escapes_markup_and_round_trips_unicode_text():
    """XML output escape <>&，但 loads 恢复原字符串；固定编码是 UTF-8。"""

    encoded = plistlib.dumps({"message": "<你好 & goodbye>"})

    assert b"&lt;" in encoded
    assert b"&amp;" in encoded
    assert "你好".encode("utf-8") in encoded
    assert plistlib.loads(encoded) == {"message": "<你好 & goodbye>"}


def test_sort_keys_controls_serialized_order_not_dictionary_semantics():
    """默认按 key 排序；sort_keys=False 保留 dict iteration order，适合可读配置。"""

    value = {"zeta": 1, "alpha": 2}
    sorted_xml = plistlib.dumps(value)
    insertion_xml = plistlib.dumps(value, sort_keys=False)

    assert sorted_xml.index(b"<key>alpha</key>") < sorted_xml.index(b"<key>zeta</key>")
    assert insertion_xml.index(b"<key>zeta</key>") < insertion_xml.index(
        b"<key>alpha</key>"
    )


def test_dict_type_is_used_for_every_mapping_created_by_parser():
    """dict_type 影响 root 和 nested dict；它不改变 array 的 list 类型。"""

    value = {"zeta": {"second": 2, "first": 1}, "alpha": [1, 2]}
    encoded = plistlib.dumps(value, sort_keys=False)
    restored = plistlib.loads(encoded, dict_type=OrderedDict)

    assert type(restored) is OrderedDict
    assert list(restored) == ["zeta", "alpha"]
    assert type(restored["zeta"]) is OrderedDict
    assert list(restored["zeta"]) == ["second", "first"]
    assert type(restored["alpha"]) is list
