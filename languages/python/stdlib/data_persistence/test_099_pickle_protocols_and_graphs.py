"""099｜``pickle`` 数据流、协议选择与对象图 identity。

pickle 是 Python-specific binary serialization：它保存对象图中的共享引用与环，但 class/
function 只按 importable qualified name 引用。协议影响兼容性和编码能力，不改变 load 自动
识别协议的行为。pickle 可在 unpickle 时执行任意代码，本文件只处理可信的本地测试数据。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.pickle.dumps python.pickle.loads python.pickle.binary-format
# polyglot-covers: python.pickle.dump python.pickle.load python.pickle.binary-file
# polyglot-covers: python.pickle.multiple-stream-items python.pickle.trailing-bytes
# polyglot-covers: python.pickle.DEFAULT-PROTOCOL python.pickle.HIGHEST-PROTOCOL
# polyglot-covers: python.pickle.protocol-zero python.pickle.negative-protocol
# polyglot-covers: python.pickle.protocol-auto-detection python.pickle.invalid-protocol
# polyglot-covers: python.pickle.bytes-like-input python.pickle.file-like-protocol
# polyglot-covers: python.pickle.shared-reference python.pickle.memo
# polyglot-covers: python.pickle.recursive-object python.pickle.object-graph
# polyglot-covers: python.pickle.Pickler python.pickle.Unpickler
# polyglot-covers: python.pickle.Pickler-reuse python.pickle.clear-memo
# polyglot-covers: python.pickle.builtin-types python.pickle.custom-instance
# polyglot-covers: python.pickle.qualified-function python.pickle.qualified-class
# polyglot-covers: python.pickle.class-code-not-stored python.pickle.init-not-called
# polyglot-covers: python.pickle.lambda-unpicklable python.pickle.open-file-unpicklable
# polyglot-covers: python.pickle.PickleError python.pickle.PicklingError
# polyglot-covers: python.pickle.UnpicklingError python.pickle.EOFError
# polyglot-covers: python.pickle.trusted-data-only python.pickle.arbitrary-code-risk

import io
import pickle

import pytest


def qualified_double(value):
    """top-level function 可由 module + qualname 重新定位。"""

    return value * 2


class QualifiedRecord:
    """默认 instance state 来自 __dict__，class definition 本身不进入 pickle。"""

    category = "record-v1"

    def __init__(self, name, values):
        self.name = name
        self.values = values

    def __eq__(self, other):
        if not isinstance(other, QualifiedRecord):
            return NotImplemented
        return (self.name, self.values) == (other.name, other.values)


class InitTracked:
    """用于证明默认 unpickle 走 __new__ + state restore，而不是再次调用 __init__。"""

    init_calls = 0

    def __init__(self, value):
        type(self).init_calls += 1
        self.value = value


class BytesSink:
    """Pickler 的最小输出协议只有接受 bytes 的 write。"""

    def __init__(self):
        self.parts = []

    def write(self, data):
        assert isinstance(data, bytes)
        self.parts.append(data)
        return len(data)


def test_dumps_and_loads_round_trip_supported_builtin_types():
    """结果按 value 恢复；不要把 pickle bytes 当作跨语言、人类可读或 canonical 格式。"""

    original = {
        "none": None,
        "booleans": (True, False),
        "numbers": [42, 3.5, 2 + 4j],
        "text": "中文",
        "binary": (b"bytes", bytearray(b"mutable")),
        "containers": ({1, 2}, frozenset({3, 4})),
    }

    payload = pickle.dumps(original)
    restored = pickle.loads(payload)

    assert isinstance(payload, bytes)
    assert restored == original
    assert restored is not original


def test_dump_and_load_use_a_binary_file_and_detect_protocol_automatically(tmp_path):
    """writer 选择 protocol；reader 从 stream 自己识别，不再传 protocol 参数。"""

    path = tmp_path / "record.pickle"
    original = QualifiedRecord("alpha", [1, 2, 3])
    with path.open("wb") as stream:
        returned = pickle.dump(original, stream, protocol=pickle.HIGHEST_PROTOCOL)

    with path.open("rb") as stream:
        restored = pickle.load(stream)

    assert returned is None
    assert restored == original
    assert restored is not original


def test_pickle_rejects_a_text_stream_because_it_writes_bytes():
    """StringIO/write(str) 不满足 binary file contract；先选 wb/BytesIO，而不是手工 decode。"""

    with pytest.raises(TypeError):
        pickle.dump({"item": 1}, io.StringIO())


def test_multiple_pickles_can_be_appended_and_loaded_sequentially():
    """STOP opcode 决定单个对象边界；同一文件可连续 dump，读取到真正 EOF 才抛 EOFError。"""

    stream = io.BytesIO()
    pickle.dump("first", stream)
    pickle.dump({"second": 2}, stream)
    stream.seek(0)

    assert pickle.load(stream) == "first"
    assert pickle.load(stream) == {"second": 2}
    with pytest.raises(EOFError):
        pickle.load(stream)


def test_loads_ignores_bytes_after_the_first_complete_pickle():
    """trailing data 不自动验证；若格式只允许一个对象，调用方要另外检查 framing/EOF。"""

    first = pickle.dumps("first")
    second = pickle.dumps("second")

    assert pickle.loads(first + second) == "first"
    assert pickle.loads(first + b"not validated") == "first"


def test_python_310_default_and_highest_protocols_are_distinct_constants():
    """默认 4 优先兼容性，最高 5 提供最新能力；持久格式应显式记录所选 protocol。"""

    assert pickle.DEFAULT_PROTOCOL == 4
    assert pickle.HIGHEST_PROTOCOL == 5
    assert pickle.DEFAULT_PROTOCOL <= pickle.HIGHEST_PROTOCOL


def test_every_python_310_protocol_round_trips_and_zero_is_textual_opcode_format():
    """protocol 0 的 opcode stream 主要由 printable bytes 构成，但仍是 bytes API，不是 JSON。"""

    original = ["text", 42, {"key": "value"}]

    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        payload = pickle.dumps(original, protocol=protocol)
        assert pickle.loads(payload) == original

    protocol_zero = pickle.dumps(original, protocol=0)
    assert not protocol_zero.startswith(b"\x80")
    assert protocol_zero.endswith(b".")


def test_negative_protocol_selects_the_highest_supported_protocol():
    """-1 是“当前最高”快捷方式；长期兼容数据不应让它随 interpreter version 漂移。"""

    original = {"value": [1, 2, 3]}

    assert pickle.dumps(original, protocol=-1) == pickle.dumps(
        original, protocol=pickle.HIGHEST_PROTOCOL
    )


def test_protocol_outside_the_supported_range_is_rejected():
    """版本号不是 feature flag bitmask；只能取 0..HIGHEST_PROTOCOL 或负数最高值。"""

    with pytest.raises(ValueError):
        pickle.dumps("value", protocol=pickle.HIGHEST_PROTOCOL + 1)


def test_loads_accepts_general_bytes_like_input():
    """无需为 bytearray/memoryview 额外复制成 bytes，consumer API 接受 buffer protocol。"""

    payload = pickle.dumps({"value": 1})

    assert pickle.loads(bytearray(payload)) == {"value": 1}
    assert pickle.loads(memoryview(payload)) == {"value": 1}


def test_pickler_only_needs_a_sink_whose_write_accepts_bytes():
    """可把 pickle 写进 socket/database adapter，但安全与完整 framing 仍由外层负责。"""

    sink = BytesSink()
    pickler = pickle.Pickler(sink, protocol=4)

    assert pickler.dump([1, 2, 3]) is None
    assert pickle.loads(b"".join(sink.parts)) == [1, 2, 3]


def test_unpickler_accepts_buffered_binary_file_protocol_objects():
    """BytesIO 同时提供 read/readinto/readline，可直接交给 Unpickler。"""

    stream = io.BytesIO(pickle.dumps(QualifiedRecord("item", [1])))
    unpickler = pickle.Unpickler(stream)

    assert unpickler.load() == QualifiedRecord("item", [1])


def test_shared_mutable_references_remain_shared_after_round_trip():
    """memo 保存 graph identity；若两个 edge 原来指向同一 list，恢复后也必须是同一 list。"""

    shared = ["value"]
    restored = pickle.loads(pickle.dumps({"left": shared, "right": shared}))

    assert restored["left"] is restored["right"]
    restored["left"].append("changed")
    assert restored["right"] == ["value", "changed"]


def test_recursive_objects_restore_their_self_reference():
    """pickle 先 memoize container 再写 children，因此能表达 cycle；marshal 不适合这一需求。"""

    recursive = ["root"]
    recursive.append(recursive)

    restored = pickle.loads(pickle.dumps(recursive))

    assert restored[0] == "root"
    assert restored[1] is restored


def test_reusing_one_pickler_and_unpickler_can_share_identity_across_dump_calls():
    """Pickler memo 跨 dump 保留；对应 Unpickler 连续 load 时，后一个对象可引用前一个对象。"""

    shared = ["shared"]
    stream = io.BytesIO()
    pickler = pickle.Pickler(stream, protocol=4)
    pickler.dump(shared)
    second_offset = stream.tell()
    pickler.dump(shared)
    payload = stream.getvalue()

    unpickler = pickle.Unpickler(io.BytesIO(payload))
    first = unpickler.load()
    second = unpickler.load()

    assert first is second
    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(payload[second_offset:])


def test_clear_memo_makes_later_pickles_independent_of_earlier_stream_objects():
    """复用 Pickler 写独立 records 时 clear_memo，第二段才能脱离第一段单独加载。"""

    shared = ["shared"]
    stream = io.BytesIO()
    pickler = pickle.Pickler(stream, protocol=4)
    pickler.dump(shared)
    pickler.clear_memo()
    second_offset = stream.tell()
    pickler.dump(shared)

    assert pickle.loads(stream.getvalue()[second_offset:]) == ["shared"]


def test_top_level_functions_and_classes_are_restored_by_qualified_name():
    """pickle 不保存 bytecode/class body；定义它们的 module 与名称在 load 时必须仍可 import。"""

    restored_function = pickle.loads(pickle.dumps(qualified_double))
    restored_class = pickle.loads(pickle.dumps(QualifiedRecord))

    assert restored_function is qualified_double
    assert restored_function(4) == 8
    assert restored_class is QualifiedRecord


def test_instance_state_is_saved_but_live_class_attributes_are_not_snapshotted():
    """旧 instance load 后使用当前 class definition，便于升级方法，也要求自己迁移旧 state。"""

    instance = QualifiedRecord("before", [1])
    payload = pickle.dumps(instance)
    original_category = QualifiedRecord.category
    try:
        QualifiedRecord.category = "record-v2"
        restored = pickle.loads(payload)

        assert restored == instance
        assert restored.category == "record-v2"
    finally:
        QualifiedRecord.category = original_category


def test_default_unpickling_does_not_call_init_again():
    """默认先 __new__ 未初始化对象再恢复 state；维持 invariant 应实现后续 getstate/setstate hook。"""

    InitTracked.init_calls = 0
    original = InitTracked("value")
    payload = pickle.dumps(original)

    restored = pickle.loads(payload)

    assert InitTracked.init_calls == 1
    assert restored.value == "value"


def test_lambda_and_live_file_objects_are_not_picklable(tmp_path):
    """lambda 没有可导入的稳定 qualified name，打开文件则包含 OS resource state。"""

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(lambda value: value)

    path = tmp_path / "item.txt"
    path.touch()
    with path.open("rb") as stream:
        with pytest.raises(TypeError):
            pickle.dumps(stream)


def test_pickle_exception_hierarchy_and_corruption_boundaries():
    """坏 opcode 通常是 UnpicklingError；空/截断输入也可能是 EOFError，而非统一异常。"""

    assert issubclass(pickle.PicklingError, pickle.PickleError)
    assert issubclass(pickle.UnpicklingError, pickle.PickleError)

    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(b"not a pickle")
    with pytest.raises(EOFError):
        pickle.loads(b"")
