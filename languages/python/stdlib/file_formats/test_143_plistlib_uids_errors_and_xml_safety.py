"""143｜``plistlib`` UID、key/type 限制、overflow、无效输入与 XML 安全边界。

plist dictionary 只允许 str key；``skipkeys`` 可跳过不合法 key，但应配合明确的
排序策略。binary plist 支持 NSKeyedArchiver 的 UID token；XML 不支持。自动探测
失败、binary 损坏、XML 语法错误分别有不同异常，调用方不应只捕获一个
笼统错误。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import operator
import plistlib
from xml.parsers.expat import ExpatError

import pytest


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
