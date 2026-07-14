"""104｜``marshal`` 的受限类型、format version 与内部用途边界。

marshal 主要服务 ``.pyc`` code object，不是通用持久化格式：它不支持普通
class instance，格式也不承诺跨 Python 版本兼容。version 3 起才记录共享
identity/递归引用。和 pickle 一样，
不要读取不可信 marshal bytes；本文件只加载自己刚生成的隔离数据。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.marshal.dumps python.marshal.loads python.marshal.binary-format
# polyglot-covers: python.marshal.dump python.marshal.load python.marshal.binary-file
# polyglot-covers: python.marshal.supported-scalars python.marshal.supported-containers
# polyglot-covers: python.marshal.None python.marshal.Ellipsis python.marshal.StopIteration
# polyglot-covers: python.marshal.code-object python.marshal.pyc-purpose
# polyglot-covers: python.marshal.unsupported-instance python.marshal.ValueError
# polyglot-covers: python.marshal.dump-partial-garbage python.marshal.unsupported-substitution
# polyglot-covers: python.marshal.version python.marshal.format-zero-to-four
# polyglot-covers: python.marshal.version-three-recursion python.marshal.object-instancing
# polyglot-covers: python.marshal.shared-reference python.marshal.recursive-list
# polyglot-covers: python.marshal.bytes-like-input python.marshal.trailing-bytes
# polyglot-covers: python.marshal.sequential-values python.marshal.EOFError
# polyglot-covers: python.marshal.invalid-data python.marshal.not-general-persistence
# polyglot-covers: python.marshal.trusted-data-only python.marshal.version-compatibility-trap

import io
import marshal

import pytest


class UnsupportedRecord:
    def __init__(self, value):
        self.value = value


def test_supported_scalar_values_round_trip_with_their_python_types():
    """marshal 的 builtin allowlist 较窄，但常见数值、文本与 binary scalar 可保存。"""

    values = [
        None,
        True,
        False,
        0,
        2**100,
        -3.5,
        2 + 4j,
        "中文",
        b"bytes",
        bytearray(b"mutable"),
    ]

    for value in values:
        restored = marshal.loads(marshal.dumps(value))
        assert restored == value
        assert type(restored) is type(value)


def test_supported_containers_round_trip_when_every_member_is_supported():
    """container 本身在 allowlist 还不够，所有递归 members 也必须可 marshal。"""

    original = {
        "tuple": (1, "two"),
        "list": [3, 4],
        "set": {5, 6},
        "frozenset": frozenset({7, 8}),
        "nested": [{"key": b"value"}],
    }

    restored = marshal.loads(marshal.dumps(original))

    assert restored == original
    assert isinstance(restored["tuple"], tuple)
    assert isinstance(restored["frozenset"], frozenset)


def test_special_singletons_keep_identity():
    """None、Ellipsis 与 StopIteration 在 marshal format 中有专用表示。"""

    assert marshal.loads(marshal.dumps(None)) is None
    assert marshal.loads(marshal.dumps(Ellipsis)) is Ellipsis
    assert marshal.loads(marshal.dumps(StopIteration)) is StopIteration


def test_code_objects_are_a_primary_marshal_use_case():
    """marshal 保存 bytecode fields；这里只执行测试自己 compile 的可信 expression。"""

    code = compile("40 + 2", "<polyglot>", "eval")

    restored = marshal.loads(marshal.dumps(code))

    assert restored.co_filename == "<polyglot>"
    assert restored.co_code == code.co_code
    assert eval(restored, {}) == 42


def test_custom_class_instances_are_not_supported():
    """marshal 不按 qualified name 保存 instance；通用对象持久化应选 pickle。"""

    with pytest.raises(ValueError):
        marshal.dumps(UnsupportedRecord("value"))


def test_nested_unsupported_value_makes_dumps_fail():
    """错误可出现在 object graph 深处；不能仅检查 root container 的类型。"""

    with pytest.raises(ValueError):
        marshal.dumps({"valid": 1, "invalid": UnsupportedRecord("value")})


def test_dump_can_write_garbage_before_reporting_an_unsupported_member():
    """dump 不是 transactional：ValueError 后 position 已推进，不能再使用该 record。"""

    stream = io.BytesIO()

    with pytest.raises(ValueError):
        marshal.dump([1, UnsupportedRecord("value"), 3], stream)

    assert stream.tell() > 0
    stream.seek(0)
    assert marshal.load(stream) == [1, None, 3]


def test_dump_and_load_round_trip_through_a_binary_file(tmp_path):
    """file API 要求 binary stream；返回 None，record framing 由 marshal 自己写入。"""

    path = tmp_path / "value.marshal"
    with path.open("wb") as stream:
        returned = marshal.dump({"value": [1, 2, 3]}, stream)

    with path.open("rb") as stream:
        restored = marshal.load(stream)

    assert returned is None
    assert restored == {"value": [1, 2, 3]}


def test_dump_rejects_a_text_stream():
    """marshal bytes 不是字符编码结果，不应 decode 后写入 StringIO/text file。"""

    with pytest.raises(TypeError):
        marshal.dump({"value": 1}, io.StringIO())


def test_python_310_current_format_version_is_four():
    """marshal.version 描述当前 writer format，不是兼容承诺或协议协商。"""

    assert marshal.version == 4


def test_all_documented_python_310_format_versions_round_trip_simple_values():
    """显式旧 version 只改变 encoding features；reader 自动识别 stream 内的表示。"""

    original = {"text": "value", "numbers": [1, 2, 3.5]}

    for version in range(marshal.version + 1):
        payload = marshal.dumps(original, version)
        assert marshal.loads(payload) == original


def test_version_three_adds_shared_object_identity():
    """version 0–2 重复编码 shared value；3+ 用 reference 恢复同一对象。"""

    shared = ["item"]
    original = [shared, shared]

    restored_v2 = marshal.loads(marshal.dumps(original, 2))
    restored_v3 = marshal.loads(marshal.dumps(original, 3))

    assert restored_v2[0] == restored_v2[1]
    assert restored_v2[0] is not restored_v2[1]
    assert restored_v3[0] is restored_v3[1]


def test_recursive_containers_require_format_version_three_or_later():
    """旧 format 没有 back-reference，不能表示 cycle；3/4 恢复 self edge。"""

    recursive = []
    recursive.append(recursive)

    with pytest.raises(ValueError):
        marshal.dumps(recursive, 2)

    for version in (3, 4):
        restored = marshal.loads(marshal.dumps(recursive, version))
        assert restored[0] is restored


def test_loads_accepts_bytes_like_input_and_ignores_trailing_bytes():
    """找到一个完整 value 后不会验证 remainder；外层格式要负责 framing。"""

    payload = marshal.dumps({"value": 1})

    assert marshal.loads(bytearray(payload)) == {"value": 1}
    assert marshal.loads(memoryview(payload)) == {"value": 1}
    assert marshal.loads(payload + b"unvalidated trailing data") == {"value": 1}


def test_multiple_marshaled_values_can_be_loaded_sequentially_from_one_file():
    """连续 dump 可形成 record stream；每次 load 消费一个 value，最终 EOFError。"""

    stream = io.BytesIO()
    marshal.dump("first", stream)
    marshal.dump({"second": 2}, stream)
    stream.seek(0)

    assert marshal.load(stream) == "first"
    assert marshal.load(stream) == {"second": 2}
    with pytest.raises(EOFError):
        marshal.load(stream)


def test_invalid_or_empty_input_uses_more_than_one_failure_type():
    """没有统一 MarshalError；caller 需处理 EOFError/ValueError/TypeError 等错误。"""

    with pytest.raises(EOFError):
        marshal.loads(b"")
    with pytest.raises(ValueError):
        marshal.loads(b"?")
    with pytest.raises(TypeError):
        marshal.loads("not bytes")
