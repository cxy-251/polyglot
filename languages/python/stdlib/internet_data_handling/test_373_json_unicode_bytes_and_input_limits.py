"""373｜Unicode、UTF bytes 自动探测、BOM 差异与不可信输入限额。

loads 接受 str、bytes、bytearray；二进制输入自动识别 UTF-8/16/32。str 开头的 U+FEFF 被视为
意外 BOM 而拒绝，UTF-8-SIG bytes 则在解码阶段剥离 BOM，这是输入类型造成的细微差异。模块不
限制文档大小或嵌套深度，服务必须在解析前实施自己的字节上限以防资源耗尽。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.loads-str-bytes-bytearray
# polyglot-covers: python.json.binary-input-utf8-utf16-utf32
# polyglot-covers: python.json.binary-input-encoding-autodetection
# polyglot-covers: python.json.str-leading-bom-valueerror
# polyglot-covers: python.json.utf8-sig-bytes-bom-stripped
# polyglot-covers: python.json.unpaired-surrogate-roundtrip
# polyglot-covers: python.json.untrusted-input-resource-exhaustion
# polyglot-covers: python.json.limit-input-size-before-parsing-workflow
# polyglot-covers: python.json.no-built-in-document-size-limit

import json

import pytest


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
def test_binary_input_autodetects_supported_unicode_encodings(encoding):
    document = '{"城市": "深圳"}'
    encoded = document.encode(encoding)
    assert json.loads(encoded) == {"城市": "深圳"}
    assert json.loads(bytearray(encoded)) == {"城市": "深圳"}


def test_bom_handling_differs_between_an_already_decoded_str_and_bytes():
    with pytest.raises(ValueError, match="Unexpected UTF-8 BOM"):
        json.loads("\ufeff{}")
    assert json.loads(b"\xef\xbb\xbf{}") == {}


def test_unpaired_surrogate_is_preserved_but_may_not_interoperate():
    value = "\ud800"
    encoded = json.dumps(value)
    assert encoded == '"\\ud800"'
    assert json.loads(encoded) == value


def test_application_can_reject_large_untrusted_payload_before_json_parsing():
    def limited_loads(payload, max_bytes):
        raw = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
        if len(raw) > max_bytes:
            raise ValueError("JSON payload exceeds byte limit")
        return json.loads(raw)

    assert limited_loads('{"ok": true}', 32) == {"ok": True}
    with pytest.raises(ValueError, match="exceeds byte limit"):
        limited_loads('["large value"]', 8)
