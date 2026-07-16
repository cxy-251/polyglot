"""074｜``plistlib`` XML/binary 格式、支持类型、文件 API 与排序控制。

plist 是有类型的序列化格式，但不会保留所有 Python 容器细节：tuple 会读回
list，bytearray 会读回 bytes。XML datetime 只保存到整秒，binary 则保留微秒。
``loads`` 能自动识别 XML/binary；``load``/``dump`` 则要求 binary file object，
不应套 text encoding。

这些案例面向 Python 3.10 当前补丁系列。
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
import operator
from xml.parsers.expat import ExpatError

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


# ``plistlib`` UID、key/type 限制、overflow、无效输入与 XML 安全边界。
#
# plist dictionary 只允许 str key；``skipkeys`` 可跳过不合法 key，但应配合明确的
# 排序策略。binary plist 支持 NSKeyedArchiver 的 UID token；XML 不支持。自动探测
# 失败、binary 损坏、XML 语法错误分别有不同异常，调用方不应只捕获一个
# 笼统错误。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.plistlib.string-keys-only python.plistlib.skipkeys
# polyglot-covers: python.plistlib.skipkeys-sort-trap python.plistlib.unsupported-type
# polyglot-covers: python.plistlib.integer-range python.plistlib.OverflowError
# polyglot-covers: python.plistlib.UID python.plistlib.UID.data
# polyglot-covers: python.plistlib.UID.index python.plistlib.UID-equality-hash
# polyglot-covers: python.plistlib.UID-range python.plistlib.binary-UID
# polyglot-covers: python.plistlib.xml-UID-unsupported
# polyglot-covers: python.plistlib.InvalidFileException python.plistlib.autodetect-failure
# polyglot-covers: python.plistlib.binary-invalid-file python.plistlib.xml-expat-error
# polyglot-covers: python.plistlib.unknown-xml-elements python.plistlib.xml-entity-rejection
# polyglot-covers: python.plistlib.xml-control-character python.plistlib.binary-string




def test_non_string_dictionary_keys_raise_by_default_or_can_be_skipped():
    """skipkeys=True 只移除非法 entry；默认拒绝它，以免数据静默丢失。"""

    value = {1: "drop", "keep": "value"}
    with pytest.raises(TypeError):
        plistlib.dumps(value, sort_keys=False)

    encoded = plistlib.dumps(value, skipkeys=True, sort_keys=False)
    assert plistlib.loads(encoded) == {"keep": "value"}


def test_skipkeys_does_not_run_before_default_mixed_key_sorting():
    """混合 key 在 sorted(items) 时已不可比较；关闭排序后才会 skip。"""

    value = {1: "drop", "keep": "value"}

    with pytest.raises(TypeError):
        plistlib.dumps(value, skipkeys=True)


def test_unsupported_values_and_out_of_range_integers_fail_before_output():
    """set 不属于 plist model；integer 必须落在 writer 支持的 64-bit 范围。"""

    with pytest.raises(TypeError):
        plistlib.dumps({"tags": {"python", "tests"}})

    for fmt in (plistlib.FMT_XML, plistlib.FMT_BINARY):
        with pytest.raises(OverflowError):
            plistlib.dumps({"too_large": 2**64}, fmt=fmt)
        with pytest.raises(OverflowError):
            plistlib.dumps({"too_small": -(2**63) - 1}, fmt=fmt)


def test_uid_is_hashable_indexable_and_validates_unsigned_64_bit_range():
    """UID 是 int wrapper；__index__ 为需要整数索引的协议提供值。"""

    uid = plistlib.UID(42)

    assert uid.data == 42
    assert operator.index(uid) == 42
    assert uid == plistlib.UID(42)
    assert uid != plistlib.UID(43)
    assert len({uid, plistlib.UID(42)}) == 1

    with pytest.raises(TypeError, match="int"):
        plistlib.UID("42")
    with pytest.raises(ValueError, match="positive"):
        plistlib.UID(-1)
    with pytest.raises(ValueError, match=r"2\*\*64"):
        plistlib.UID(2**64)


def test_uid_round_trips_only_through_binary_plist():
    """UID 是 NSKeyedArchiver binary token；XML writer 把它视为 unsupported type。"""

    value = {"object": plistlib.UID(2**32)}
    binary = plistlib.dumps(value, fmt=plistlib.FMT_BINARY)

    restored = plistlib.loads(binary)
    assert restored == value
    assert restored["object"].data == 2**32

    with pytest.raises(TypeError, match="unsupported type"):
        plistlib.dumps(value, fmt=plistlib.FMT_XML)


def test_autodetect_and_binary_parser_use_invalid_file_exception():
    """无已知 header 或损坏 binary 都是 InvalidFileException，它也是 ValueError。"""

    with pytest.raises(plistlib.InvalidFileException) as unknown:
        plistlib.loads(b"not a plist")
    assert isinstance(unknown.value, ValueError)

    with pytest.raises(plistlib.InvalidFileException):
        plistlib.loads(b"bplist00truncated", fmt=plistlib.FMT_BINARY)


def test_malformed_xml_comes_from_expat_instead_of_invalid_file_exception():
    """识别为 XML 后，well-formedness error 由 ExpatError 报告。"""

    with pytest.raises(ExpatError):
        plistlib.loads(b"<plist><dict><key>unfinished</key>")


def test_unknown_xml_elements_are_ignored_but_known_data_still_parses():
    """plist parser 忽略无 handler 的 element；不要依赖它替 schema 做严格验证。"""

    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <plist version="1.0">
      <unknown>metadata</unknown>
      <dict><key>answer</key><integer>42</integer></dict>
    </plist>
    """

    assert plistlib.loads(xml) == {"answer": 42}


def test_xml_entity_declarations_are_rejected_before_expansion():
    """3.10 parser 禁止 entity declaration，避免把 plist 入口变成 XML entity 通道。"""

    xml = b"""<?xml version="1.0"?>
    <!DOCTYPE plist [<!ENTITY secret "expanded">]>
    <plist version="1.0"><string>&secret;</string></plist>
    """

    with pytest.raises(plistlib.InvalidFileException, match="entity declarations"):
        plistlib.loads(xml)


def test_xml_rejects_control_characters_that_binary_strings_can_store():
    """XML 1.0 不允许 NUL 等 control chars；binary plist 的 string encoding 可以保存。"""

    value = {"text": "before\x00after"}
    with pytest.raises(ValueError, match="control characters"):
        plistlib.dumps(value, fmt=plistlib.FMT_XML)

    binary = plistlib.dumps(value, fmt=plistlib.FMT_BINARY)
    assert plistlib.loads(binary) == value
