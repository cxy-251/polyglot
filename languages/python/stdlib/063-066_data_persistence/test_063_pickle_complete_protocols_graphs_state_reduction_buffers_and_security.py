"""063｜``pickle`` 数据流、协议选择与对象图 identity。

pickle 是 Python-specific binary serialization：它保存对象图中的共享引用与环，但 class/
function 只按 importable qualified name 引用。协议影响兼容性和编码能力，不改变 load 自动
识别协议的行为。pickle 可在 unpickle 时执行任意代码，本文件只处理可信的本地测试数据。

这些案例面向 Python 3.10。
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
import copy
import copyreg
import builtins

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

    with pytest.raises((pickle.PicklingError, AttributeError)):
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


# pickle 的 constructor 参数、instance state 与 reduction tuple。
#
# 默认 unpickle 不调用 ``__init__``；需要 constructor invariant 时用 ``__new__``，需要向它传参
# 时用 ``__getnewargs_ex__``。状态迁移优先选择 ``__getstate__/__setstate__``；直接实现最多
# 六项的 reduce value 更强，但 callable、state、list/dict iterators 的位置很容易写错。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.pickle.__getnewargs-ex__ python.pickle.keyword-only-new
# polyglot-covers: python.pickle.__getnewargs__ python.pickle.positional-new
# polyglot-covers: python.pickle.getnewargs-ex-precedence python.pickle.protocol-two-newargs
# polyglot-covers: python.pickle.__getstate__ python.pickle.transient-resource
# polyglot-covers: python.pickle.__setstate__ python.pickle.non-dict-state
# polyglot-covers: python.pickle.false-state python.pickle.setstate-not-called
# polyglot-covers: python.pickle.state-version python.pickle.schema-migration
# polyglot-covers: python.pickle.__new__ python.pickle.unpickle-invariant
# polyglot-covers: python.pickle.stateful-file-resume python.pickle.external-file-dependency
# polyglot-covers: python.pickle.__reduce__ python.pickle.reduce-string-singleton
# polyglot-covers: python.pickle.__reduce-ex__ python.pickle.reduce-ex-precedence
# polyglot-covers: python.pickle.reduce-callable-args python.pickle.reduce-state
# polyglot-covers: python.pickle.reduce-list-iterator python.pickle.append-extend
# polyglot-covers: python.pickle.reduce-dict-iterator python.pickle.setitem
# polyglot-covers: python.pickle.reduce-state-updater python.pickle.python38-sixth-item
# polyglot-covers: python.pickle.invalid-reduce python.pickle.iterator-required




class KeywordToken:
    """__new__ 的 keyword-only 参数必须由 __getnewargs_ex__ 重放。"""

    def __new__(cls, value, *, namespace):
        instance = super().__new__(cls)
        instance.constructed_from = (value, namespace)
        return instance

    def __init__(self, value, *, namespace):
        self.value = value
        self.namespace = namespace

    def __getnewargs_ex__(self):
        return (self.value,), {"namespace": self.namespace}


class PositionalToken:
    """只有 positional constructor 参数时可使用更旧的 __getnewargs__ protocol。"""

    def __new__(cls, value):
        instance = super().__new__(cls)
        instance.constructed_value = value
        return instance

    def __init__(self, value):
        self.value = value

    def __getnewargs__(self):
        return (self.value,)


class PreferExtendedNewArgs(KeywordToken):
    """同时存在时 extended hook 必须优先，旧 hook 不应被调用。"""

    def __getnewargs__(self):
        raise AssertionError("__getnewargs_ex__ must take precedence")


class TransientSession:
    """lambda 模拟不能持久化的 live resource；恢复时构造新的 process-local handle。"""

    def __init__(self, user):
        self.user = user
        self.cache = {"visits": 2}
        self.live_handle = lambda: "live"

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("live_handle")
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.live_handle = lambda: "restored"


class CompactPoint:
    """有 __setstate__ 时 state 可选紧凑 tuple，不必伪装成 __dict__。"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getstate__(self):
        return self.x, self.y

    def __setstate__(self, state):
        self.x, self.y = state


class FalseState:
    """false state 不产生 BUILD，因此 __setstate__ 不会运行。"""

    setstate_calls = 0

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        type(self).setstate_calls += 1


class NonDictStateWithoutSetter:
    def __getstate__(self):
        return 42


class VersionedProfile:
    """新代码仍能读取早期 state shape，并立刻升级为 current invariant。"""

    CURRENT_VERSION = 2

    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
        self.version = self.CURRENT_VERSION

    @classmethod
    def legacy(cls, full_name):
        instance = cls.__new__(cls)
        instance._legacy_full_name = full_name
        return instance

    def __getstate__(self):
        if hasattr(self, "_legacy_full_name"):
            return {"version": 1, "full_name": self._legacy_full_name}
        return {
            "version": self.CURRENT_VERSION,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    def __setstate__(self, state):
        if state["version"] == 1:
            first_name, last_name = state["full_name"].split(" ", 1)
        else:
            first_name = state["first_name"]
            last_name = state["last_name"]
        self.first_name = first_name
        self.last_name = last_name
        self.version = self.CURRENT_VERSION


class GuardedState:
    """__new__ 在任何 attribute hook/state restore 之前建立最小 invariant。"""

    def __new__(cls):
        instance = super().__new__(cls)
        instance._ready = True
        return instance

    def __init__(self):
        self.value = "initialized"

    def __getstate__(self):
        return {"value": self.value}

    def __setstate__(self, state):
        if not self._ready:
            raise RuntimeError("__new__ invariant missing")
        self.value = state["value"]


class ResumableReader:
    """pickle 只存 pathname 与 text seek cookie，不尝试序列化打开文件。"""

    def __init__(self, filename):
        self.filename = filename
        self.stream = open(filename, encoding="utf-8")

    def readline(self):
        return self.stream.readline()

    def close(self):
        self.stream.close()

    def __getstate__(self):
        state = self.__dict__.copy()
        state["position"] = self.stream.tell()
        state.pop("stream")
        return state

    def __setstate__(self, state):
        position = state.pop("position")
        self.__dict__.update(state)
        self.stream = open(self.filename, encoding="utf-8")
        self.stream.seek(position)


class ReducedTemperature:
    def __init__(self, celsius):
        self.celsius = celsius

    def __reduce__(self):
        return type(self), (self.celsius,)


class MissingValue:
    def __reduce__(self):
        return "MISSING"


MISSING = MissingValue()


class ProtocolAware:
    def __init__(self, value, reconstructed_with=None):
        self.value = value
        self.reconstructed_with = reconstructed_with

    def __reduce__(self):
        raise AssertionError("__reduce_ex__ must take precedence")

    def __reduce_ex__(self, protocol):
        return type(self), (self.value, protocol)


class StatefulReduction:
    def __init__(self, value):
        self.value = value
        self.status = "fresh"

    def __reduce__(self):
        return type(self), (self.value,), {"status": self.status}


class ListEnvelope(list):
    def __init__(self, values=(), label=None):
        super().__init__(values)
        self.label = label

    def __reduce__(self):
        return type(self), (), {"label": self.label}, iter(self)


class MappingEnvelope(dict):
    def __init__(self, values=(), label=None):
        super().__init__(values)
        self.label = label

    def __reduce__(self):
        return type(self), (), {"label": self.label}, None, iter(self.items())


class InvalidListReduction:
    def __reduce__(self):
        return type(self), (), None, [1, 2, 3]


def apply_six_tuple_state(obj, state):
    obj.status = f"updated:{state['status']}"


class SixTupleState:
    def __init__(self):
        self.status = "initial"

    def __setstate__(self, state):
        raise AssertionError("sixth reduction item must take precedence")

    def __reduce__(self):
        return type(self), (), {"status": "saved"}, None, None, apply_six_tuple_state


def test_getnewargs_ex_supplies_keyword_only_new_arguments_for_protocol_two_and_later():
    """NEWOBJ_EX/兼容 opcode 先调用 __new__，随后 saved state 会覆盖普通 attributes。"""

    original = KeywordToken("abc", namespace="tokens")

    for protocol in (2, 3, 4, 5):
        restored = pickle.loads(pickle.dumps(original, protocol=protocol))
        assert restored.constructed_from == ("abc", "tokens")
        assert (restored.value, restored.namespace) == ("abc", "tokens")


def test_getnewargs_supplies_positional_new_arguments():
    """只要求 positional args 时，__getnewargs__ 可服务旧 protocol；返回值必须是 tuple。"""

    restored = pickle.loads(pickle.dumps(PositionalToken("value"), protocol=2))

    assert restored.constructed_value == "value"
    assert restored.value == "value"


def test_getnewargs_ex_takes_precedence_over_getnewargs():
    """不要同时维护两套不同重建规则；若两者共存，extended version 胜出。"""

    original = PreferExtendedNewArgs("abc", namespace="preferred")
    restored = pickle.loads(pickle.dumps(original, protocol=4))

    assert restored.constructed_from == ("abc", "preferred")


def test_getstate_excludes_unpicklable_transient_resources_without_mutating_original():
    """必须 copy __dict__ 再删 transient key，否则一次 dump 会破坏仍在工作的 live object。"""

    original = TransientSession("ada")
    restored = pickle.loads(pickle.dumps(original))

    assert original.live_handle() == "live"
    assert restored.user == "ada"
    assert restored.cache == {"visits": 2}
    assert restored.live_handle() == "restored"


def test_setstate_accepts_an_arbitrary_picklable_state_shape():
    """定义 __setstate__ 后 state 不限 dict；紧凑 tuple 的 schema 仍需自行版本化。"""

    restored = pickle.loads(pickle.dumps(CompactPoint(3, 4)))

    assert (restored.x, restored.y) == (3, 4)


def test_none_getstate_value_skips_setstate_entirely():
    """None 表示没有 BUILD state；需要恢复 callback 时必须返回实际 state。"""

    FalseState.setstate_calls = 0

    pickle.loads(pickle.dumps(FalseState()))

    assert FalseState.setstate_calls == 0


def test_non_dictionary_state_requires_a_setstate_handler():
    """没有 __setstate__ 时 pickle 只能把 dict state 更新到 instance __dict__。"""

    payload = pickle.dumps(NonDictStateWithoutSetter())

    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(payload)


def test_setstate_can_migrate_a_versioned_legacy_schema():
    """版本号属于 state，而非 class；load 旧 shape 后立刻建立 current fields。"""

    legacy_payload = pickle.dumps(VersionedProfile.legacy("Ada Lovelace"))

    restored = pickle.loads(legacy_payload)

    assert restored.version == VersionedProfile.CURRENT_VERSION
    assert (restored.first_name, restored.last_name) == ("Ada", "Lovelace")
    assert not hasattr(restored, "_legacy_full_name")


def test_new_establishes_invariants_needed_during_state_restoration():
    """__init__ 不会运行，但 __new__ 会；attribute hooks 依赖的 sentinel 应在这里建立。"""

    restored = pickle.loads(pickle.dumps(GuardedState()))

    assert restored._ready is True
    assert restored.value == "initialized"


def test_getstate_and_setstate_can_resume_an_external_file_cursor(tmp_path):
    """恢复的是“重新打开该路径”的 recipe；文件被替换时结果也会改变，并非自包含 snapshot。"""

    path = tmp_path / "lines.txt"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    original = ResumableReader(path)
    restored = None
    try:
        assert original.readline() == "one\n"
        restored = pickle.loads(pickle.dumps(original))

        assert original.readline() == "two\n"
        assert restored.readline() == "two\n"
    finally:
        original.close()
        if restored is not None:
            restored.close()


def test_two_item_reduce_value_calls_the_reconstructor_with_arguments():
    """最小 reduce tuple 是 callable + args tuple；args 不是可省略的 arbitrary sequence。"""

    restored = pickle.loads(pickle.dumps(ReducedTemperature(21.5)))

    assert isinstance(restored, ReducedTemperature)
    assert restored.celsius == 21.5


def test_reduce_string_can_restore_a_module_level_singleton_by_name():
    """string reduce 不是任意 payload；名称必须指回当前 module 中同一个 global object。"""

    assert pickle.loads(pickle.dumps(MISSING)) is MISSING


def test_reduce_ex_receives_protocol_and_takes_precedence_over_reduce():
    """__reduce_ex__ 可按 reader compatibility 生成不同 recipe；pickle 优先调用它。"""

    for protocol in (2, 5):
        restored = pickle.loads(pickle.dumps(ProtocolAware("value"), protocol=protocol))
        assert restored.value == "value"
        assert restored.reconstructed_with == protocol


def test_third_reduce_item_restores_instance_state_after_construction():
    """callable 先产生初始对象，第三项随后通过 __setstate__ 或 __dict__.update 应用。"""

    original = StatefulReduction("value")
    original.status = "saved"

    restored = pickle.loads(pickle.dumps(original))

    assert restored.value == "value"
    assert restored.status == "saved"


def test_fourth_reduce_item_is_an_iterator_used_to_populate_list_like_objects():
    """实现方必须同时容忍 append 与 extend；具体选择受 protocol 和 batch size 影响。"""

    original = ListEnvelope([1, 2, 3], label="numbers")
    restored = pickle.loads(pickle.dumps(original, protocol=4))

    assert list(restored) == [1, 2, 3]
    assert restored.label == "numbers"


def test_fifth_reduce_item_is_a_key_value_iterator_for_mapping_like_objects():
    """每个 pair 通过 ``obj[key] = value`` 恢复，不能把 dict 本身误传成 iterator。"""

    original = MappingEnvelope({"a": 1, "b": 2}, label="mapping")
    restored = pickle.loads(pickle.dumps(original, protocol=4))

    assert dict(restored) == {"a": 1, "b": 2}
    assert restored.label == "mapping"


def test_reduce_population_items_must_be_iterators_not_materialized_lists():
    """第四/第五项严格要求 iterator；若已有 sequence，显式传 iter(sequence)。"""

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(InvalidListReduction())


def test_sixth_reduce_item_overrides_static_setstate_for_one_recipe():
    """3.8+ state updater callable 接收 (obj,state)，优先于 class 的 __setstate__。"""

    restored = pickle.loads(pickle.dumps(SixTupleState(), protocol=5))

    assert restored.status == "updated:saved"


# pickle external reference、dispatch table 与 ``copyreg``。
#
# ``persistent_id`` 把对象替换为外部 store key，load 时解析的是“现在的外部值”；dispatch
# table 则在不修改目标 class 的情况下提供 reduction recipe。优先用单个 Pickler 的私有表；
# ``copyreg`` 修改 process-global registry，也会影响 ``copy.copy``，测试必须恢复原状态。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.pickle.Pickler.persistent-id python.pickle.external-object
# polyglot-covers: python.pickle.Unpickler.persistent-load python.pickle.external-store
# polyglot-covers: python.pickle.persistent-id-none-fallback
# polyglot-covers: python.pickle.invalid-persistent-id python.pickle.UnpicklingError
# polyglot-covers: python.pickle.protocol-zero-persistent-id python.pickle.alphanumeric-id
# polyglot-covers: python.pickle.persistent-load-none-trap
# polyglot-covers: python.pickle.Pickler.dispatch-table python.pickle.private-dispatch
# polyglot-covers: python.pickle.class-dispatch-table python.pickle.dispatch-copy
# polyglot-covers: python.pickle.reducer-override python.pickle.reducer-override-priority
# polyglot-covers: python.pickle.reducer-override-NotImplemented python.pickle.dispatch-fallback
# polyglot-covers: python.copyreg.dispatch-table python.copyreg.global-registry
# polyglot-covers: python.copyreg.pickle python.copyreg.reduction-function
# polyglot-covers: python.copyreg.copy-module-integration python.copyreg.registry-cleanup
# polyglot-covers: python.copyreg.constructor python.copyreg.callable-validation
# polyglot-covers: python.copyreg.legacy-constructor-ignored




class ExternalReference:
    def __init__(self, key):
        self.key = key


class ReferencePickler(pickle.Pickler):
    def persistent_id(self, obj):
        if isinstance(obj, ExternalReference):
            return "ExternalReference", obj.key
        return None


class ReferenceUnpickler(pickle.Unpickler):
    def __init__(self, file, store):
        super().__init__(file)
        self.store = store

    def persistent_load(self, persistent_id):
        type_tag, key = persistent_id
        if type_tag != "ExternalReference":
            raise pickle.UnpicklingError(f"unsupported persistent type: {type_tag}")
        try:
            return self.store[key]
        except KeyError as error:
            raise pickle.UnpicklingError(f"missing external key: {key}") from error


class ReturningNoneUnpickler(pickle.Unpickler):
    def persistent_load(self, persistent_id):
        return None


class TextIdPickler(pickle.Pickler):
    def persistent_id(self, obj):
        if isinstance(obj, ExternalReference):
            return f"ref{obj.key}"
        return None


class TextIdUnpickler(pickle.Unpickler):
    def persistent_load(self, persistent_id):
        return {"resolved": persistent_id}


class ExternalPoint:
    """假设来自不能修改的 third-party class。"""

    def __init__(self, x, y, route="default"):
        self.x = x
        self.y = y
        self.route = route


def rebuild_point(x, y, route):
    return ExternalPoint(x, y, route=route)


def reduce_point_privately(point):
    return rebuild_point, (point.x, point.y, "private-dispatch")


class PointPickler(pickle.Pickler):
    dispatch_table = copyreg.dispatch_table.copy()
    dispatch_table[ExternalPoint] = reduce_point_privately


class GlobalRegisteredValue:
    def __init__(self, value, route="default"):
        self.value = value
        self.route = route


def rebuild_registered_value(value):
    return GlobalRegisteredValue(value, route="copyreg")


def reduce_registered_value(value):
    return rebuild_registered_value, (value.value,)


def legacy_constructor_that_must_not_run():
    raise AssertionError("constructor_ob is a validated but ignored legacy argument")


class ConditionalValue:
    def __init__(self, value, prefer_override):
        self.value = value
        self.prefer_override = prefer_override
        self.route = "original"


def rebuild_conditional_value(value, prefer_override, route):
    rebuilt = ConditionalValue(value, prefer_override)
    rebuilt.route = route
    return rebuilt


def reduce_conditional_by_dispatch(value):
    return rebuild_conditional_value, (
        value.value,
        value.prefer_override,
        "dispatch-table",
    )


class PriorityPickler(pickle.Pickler):
    dispatch_table = copyreg.dispatch_table.copy()
    dispatch_table[ConditionalValue] = reduce_conditional_by_dispatch

    def reducer_override(self, obj):
        if isinstance(obj, ConditionalValue) and obj.prefer_override:
            return rebuild_conditional_value, (
                obj.value,
                obj.prefer_override,
                "reducer-override",
            )
        return NotImplemented


def _dump_with(pickler_type, obj):
    stream = io.BytesIO()
    pickler_type(stream).dump(obj)
    return stream.getvalue()


def test_persistent_id_replaces_an_object_with_an_external_store_reference():
    """payload 保存 type tag + key；外部对象本身的 __dict__ 不写入 stream。"""

    stream = io.BytesIO()
    ReferencePickler(stream, protocol=4).dump(
        {"title": "task", "owner": ExternalReference("user-1")}
    )
    store = {"user-1": {"name": "Ada", "revision": 2}}

    restored = ReferenceUnpickler(io.BytesIO(stream.getvalue()), store).load()

    assert restored == {
        "title": "task",
        "owner": {"name": "Ada", "revision": 2},
    }


def test_external_reference_resolves_the_current_store_value_at_load_time():
    """persistent reference 不是 snapshot；dump 后 store 更新会反映在之后的 load。"""

    stream = io.BytesIO()
    ReferencePickler(stream).dump(ExternalReference("item"))
    store = {"item": {"version": 1}}
    store["item"] = {"version": 2}

    restored = ReferenceUnpickler(io.BytesIO(stream.getvalue()), store).load()

    assert restored == {"version": 2}
    assert restored is store["item"]


def test_persistent_id_none_falls_back_to_normal_recursive_pickling():
    """hook 会看到 graph 中许多对象；非目标类型必须返回 None，不是 arbitrary false value。"""

    stream = io.BytesIO()
    ReferencePickler(stream).dump([1, {"nested": "ordinary"}])

    assert ReferenceUnpickler(io.BytesIO(stream.getvalue()), {}).load() == [
        1,
        {"nested": "ordinary"},
    ]


def test_unknown_persistent_type_and_missing_key_raise_unpickling_error():
    """resolver 不能返回猜测值；不认识的 namespace 与不存在的 key 都是 corrupted reference。"""

    stream = io.BytesIO()
    ReferencePickler(stream).dump(ExternalReference("missing"))
    payload = stream.getvalue()

    with pytest.raises(pickle.UnpicklingError, match="missing external key"):
        ReferenceUnpickler(io.BytesIO(payload), {}).load()

    class WrongTagPickler(pickle.Pickler):
        def persistent_id(self, obj):
            if isinstance(obj, ExternalReference):
                return "WrongType", obj.key
            return None

    wrong_tag_stream = io.BytesIO()
    WrongTagPickler(wrong_tag_stream).dump(ExternalReference("item"))
    with pytest.raises(pickle.UnpicklingError, match="unsupported persistent type"):
        ReferenceUnpickler(io.BytesIO(wrong_tag_stream.getvalue()), {}).load()


def test_default_unpickler_rejects_a_stream_containing_persistent_ids():
    """producer/consumer 必须成对约定 ID schema；普通 loads 不会替调用方猜 resolver。"""

    stream = io.BytesIO()
    ReferencePickler(stream).dump(ExternalReference("item"))

    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(stream.getvalue())


def test_persistent_load_returning_none_silently_substitutes_none():
    """None 被当作解析成功的对象；失败时必须 raise UnpicklingError，不能仅隐式返回。"""

    stream = io.BytesIO()
    ReferencePickler(stream).dump([ExternalReference("missing")])

    restored = ReturningNoneUnpickler(io.BytesIO(stream.getvalue())).load()

    assert restored == [None]


def test_protocol_zero_persistent_ids_use_simple_text_identifiers():
    """protocol 0 的 ID 应是 alphanumeric string；新协议可使用 tuple 等 arbitrary object。"""

    stream = io.BytesIO()
    TextIdPickler(stream, protocol=0).dump(ExternalReference(42))

    restored = TextIdUnpickler(io.BytesIO(stream.getvalue())).load()

    assert restored == {"resolved": "ref42"}


def test_pickler_has_no_instance_dispatch_table_until_one_is_assigned():
    """默认直接使用 copyreg global table；读取未设置的 instance attribute 会是 AttributeError。"""

    pickler = pickle.Pickler(io.BytesIO())

    with pytest.raises(AttributeError):
        _ = pickler.dispatch_table


def test_private_dispatch_table_customizes_one_pickler_without_global_side_effects():
    """从 copyreg table 复制后追加 reducer，保留其他注册项又不会污染普通 pickle.dumps。"""

    original = ExternalPoint(3, 4, route="original")
    stream = io.BytesIO()
    pickler = pickle.Pickler(stream)
    pickler.dispatch_table = copyreg.dispatch_table.copy()
    pickler.dispatch_table[ExternalPoint] = reduce_point_privately
    pickler.dump(original)

    private_restored = pickle.loads(stream.getvalue())
    default_restored = pickle.loads(pickle.dumps(original))

    assert private_restored.route == "private-dispatch"
    assert default_restored.route == "original"


def test_pickler_subclass_can_share_a_private_class_dispatch_table():
    """class attribute 让该 Pickler family 共用策略，但仍不修改 copyreg global mapping。"""

    restored = pickle.loads(_dump_with(PointPickler, ExternalPoint(1, 2)))

    assert (restored.x, restored.y, restored.route) == (1, 2, "private-dispatch")
    assert ExternalPoint not in copyreg.dispatch_table


def test_reducer_override_precedes_dispatch_and_notimplemented_falls_back():
    """override 可按 instance criterion 决策；返回 NotImplemented 才继续查询 dispatch table。"""

    original = [
        ConditionalValue("first", prefer_override=True),
        ConditionalValue("second", prefer_override=False),
    ]

    restored = pickle.loads(_dump_with(PriorityPickler, original))

    assert [item.route for item in restored] == [
        "reducer-override",
        "dispatch-table",
    ]


def test_copyreg_registration_affects_pickle_and_copy_and_is_restored_afterward():
    """global reducer 同时参与 pickle 与 copy protocol；没有 unregister API，要保存并恢复旧 entry。"""

    sentinel = object()
    previous = copyreg.dispatch_table.get(GlobalRegisteredValue, sentinel)
    try:
        copyreg.pickle(GlobalRegisteredValue, reduce_registered_value)
        original = GlobalRegisteredValue("value", route="original")

        pickled_copy = pickle.loads(pickle.dumps(original))
        shallow_copy = copy.copy(original)

        assert pickled_copy.route == "copyreg"
        assert shallow_copy.route == "copyreg"
    finally:
        if previous is sentinel:
            copyreg.dispatch_table.pop(GlobalRegisteredValue, None)
        else:
            copyreg.dispatch_table[GlobalRegisteredValue] = previous

    restored_without_registration = pickle.loads(
        pickle.dumps(GlobalRegisteredValue("value", route="ordinary"))
    )
    assert restored_without_registration.route == "ordinary"


def test_copyreg_constructor_only_validates_callability_in_python_three():
    """constructor registry 是 legacy compatibility surface；有效 callable 返回 None，非 callable 报错。"""

    assert copyreg.constructor(lambda: None) is None

    with pytest.raises(TypeError):
        copyreg.constructor(42)


def test_copyreg_pickle_validates_the_reduction_function():
    """registration 时 reducer 必须 callable；其返回 tuple 的正确性要到实际 pickle 时才检查。"""

    with pytest.raises(TypeError):
        copyreg.pickle(GlobalRegisteredValue, None)


def test_copyreg_legacy_constructor_argument_is_validated_but_not_invoked():
    """constructor_ob 在 Python 3 已忽略；传入时仍必须 callable，不能依赖它参与 reconstruction。"""

    sentinel = object()
    previous = copyreg.dispatch_table.get(GlobalRegisteredValue, sentinel)
    try:
        copyreg.pickle(
            GlobalRegisteredValue,
            reduce_registered_value,
            constructor_ob=legacy_constructor_that_must_not_run,
        )
        restored = pickle.loads(pickle.dumps(GlobalRegisteredValue("value")))

        assert restored.route == "copyreg"
    finally:
        if previous is sentinel:
            copyreg.dispatch_table.pop(GlobalRegisteredValue, None)
        else:
            copyreg.dispatch_table[GlobalRegisteredValue] = previous

    previous = copyreg.dispatch_table.get(GlobalRegisteredValue, sentinel)
    try:
        with pytest.raises(TypeError):
            copyreg.pickle(
                GlobalRegisteredValue,
                reduce_registered_value,
                constructor_ob=42,
            )
    finally:
        # copyreg.pickle 先写 dispatch_table、再验证 legacy constructor，失败也可能留下 entry。
        if previous is sentinel:
            copyreg.dispatch_table.pop(GlobalRegisteredValue, None)
        else:
            copyreg.dispatch_table[GlobalRegisteredValue] = previous


# pickle protocol 5 out-of-band buffer 与 unpickle 安全边界。
#
# ``PickleBuffer`` 只表示大块 buffer 可被外部 transport；producer 的 callback 与 consumer 的
# ``buffers`` iterable 必须按相同顺序配对。unpickle 会调用 stream 指定的 global callable，
# ``find_class`` allowlist 可缩小攻击面但不是通用 sandbox；根本规则仍是只加载可信数据。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.pickle.protocol-five python.pickle.PickleBuffer
# polyglot-covers: python.pickle.PickleBuffer.raw python.pickle.buffer-protocol
# polyglot-covers: python.pickle.PickleBuffer.release python.pickle.noncontiguous-buffer
# polyglot-covers: python.pickle.buffer-callback python.pickle.out-of-band
# polyglot-covers: python.pickle.buffer-callback-false python.pickle.buffer-callback-true
# polyglot-covers: python.pickle.loads-buffers python.pickle.missing-buffers
# polyglot-covers: python.pickle.buffer-order python.pickle.buffer-iterator-consumption
# polyglot-covers: python.pickle.protocol-four-buffer-fallback
# polyglot-covers: python.pickle.Unpickler.find-class python.pickle.function-resolution
# polyglot-covers: python.pickle.restricted-unpickler python.pickle.global-allowlist
# polyglot-covers: python.pickle.no-globals python.pickle.builtin-opcodes
# polyglot-covers: python.pickle.unpickle-calls-code python.pickle.arbitrary-code-risk
# polyglot-covers: python.pickle.restricted-not-sandbox python.pickle.trusted-data-only




class ZeroCopyByteArray(bytearray):
    """protocol 5 提供 PickleBuffer，旧 protocol 退回普通 bytearray copy。"""

    def __reduce_ex__(self, protocol):
        if protocol >= 5:
            return type(self)._reconstruct, (pickle.PickleBuffer(self),), None
        return type(self)._reconstruct, (bytearray(self),)

    @classmethod
    def _reconstruct(cls, obj):
        with memoryview(obj) as view:
            underlying = view.obj
        if type(underlying) is cls:
            return underlying
        return cls(underlying)


SAFE_BUILTINS = {"complex", "frozenset", "range", "set", "slice"}


class RestrictedUnpickler(pickle.Unpickler):
    """示例 allowlist 只允许少量 inert builtins globals。"""

    def find_class(self, module, name):
        if module == "builtins" and name in SAFE_BUILTINS:
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f"forbidden global: {module}.{name}")


class NoGlobalsUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f"globals disabled: {module}.{name}")


class TrackingUnpickler(pickle.Unpickler):
    def __init__(self, file):
        super().__init__(file)
        self.requested_globals = []

    def find_class(self, module, name):
        self.requested_globals.append((module, name))
        return super().find_class(module, name)


LOAD_EVENTS = []


def record_load_event(value):
    """只产生 process-local list event，用安全副作用证明 reduce callable 会在 load 阶段运行。"""

    LOAD_EVENTS.append(value)
    return {"loaded": value}


class CallsCodeWhenLoaded:
    def __init__(self, value):
        self.value = value

    def __reduce__(self):
        return record_load_event, (self.value,)


def restricted_loads(payload):
    return RestrictedUnpickler(io.BytesIO(payload)).load()


def test_picklebuffer_raw_exposes_a_one_dimensional_unsigned_byte_view():
    """raw() 统一返回 C-contiguous format B memoryview，适合直接交给 transport。"""

    source = bytearray(b"abc")
    buffer = pickle.PickleBuffer(source)
    view = buffer.raw()
    try:
        assert isinstance(view, memoryview)
        assert view.ndim == 1
        assert view.format == "B"
        assert view.c_contiguous is True
        assert view.tobytes() == b"abc"

        view[0] = ord("A")
        assert source == bytearray(b"Abc")
    finally:
        view.release()
        buffer.release()


def test_picklebuffer_raw_rejects_a_noncontiguous_view():
    """strided view 既非 C- 也非 Fortran-contiguous，不能降成 raw byte span。"""

    source = memoryview(bytearray(b"abcdef"))[::2]
    buffer = pickle.PickleBuffer(source)
    try:
        with pytest.raises(BufferError):
            buffer.raw()
    finally:
        buffer.release()
        source.release()


def test_picklebuffer_release_forbids_new_raw_views():
    """transport 完成后显式 release；已释放 wrapper 不能再次暴露 underlying buffer。"""

    buffer = pickle.PickleBuffer(bytearray(b"data"))
    buffer.release()

    with pytest.raises(ValueError):
        buffer.raw()


def test_picklebuffer_itself_requires_protocol_five_or_newer():
    """PickleBuffer opcode 不存在于 protocol 4；provider 必须像示例 class 一样提供旧版 fallback。"""

    buffer = pickle.PickleBuffer(bytearray(b"data"))
    try:
        with pytest.raises(pickle.PicklingError):
            pickle.dumps(buffer, protocol=4)
    finally:
        buffer.release()


def test_protocol_four_provider_fallback_round_trips_as_an_independent_copy():
    """旧 reader 得到相同 value，但没有 out-of-band identity/zero-copy 优化。"""

    original = ZeroCopyByteArray(b"payload")

    restored = pickle.loads(pickle.dumps(original, protocol=4))

    assert restored == original
    assert isinstance(restored, ZeroCopyByteArray)
    assert restored is not original


def test_protocol_five_without_callback_keeps_buffer_in_band():
    """仅选择 protocol 5 不会自动拆分 transport；buffer_callback=None 仍把数据写入主 stream。"""

    original = ZeroCopyByteArray(b"payload")

    payload = pickle.dumps(original, protocol=5)
    restored = pickle.loads(payload)

    assert restored == original
    assert restored is not original


def test_false_buffer_callback_moves_data_out_of_band_and_consumer_supplies_it():
    """list.append 返回 None，因此 captured buffer 不进入 pickle bytes，只留下 next-buffer marker。"""

    original = ZeroCopyByteArray(b"payload")
    buffers = []

    payload = pickle.dumps(original, protocol=5, buffer_callback=buffers.append)

    assert len(buffers) == 1
    assert isinstance(buffers[0], pickle.PickleBuffer)
    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(payload)

    restored = pickle.loads(payload, buffers=buffers)
    assert restored is original


def test_truthy_buffer_callback_keeps_data_in_band():
    """callback 返回 truthy 表示仅观察而不外移；consumer 无需 buffers 也能独立 load。"""

    observed = []

    def keep_in_band(buffer):
        observed.append(buffer.raw().tobytes())
        return True

    original = ZeroCopyByteArray(b"payload")
    payload = pickle.dumps(original, protocol=5, buffer_callback=keep_in_band)
    restored = pickle.loads(payload)

    assert observed == [b"payload"]
    assert restored == original
    assert restored is not original


def test_buffer_callback_requires_protocol_five_explicitly():
    """protocol=None 在 3.10 会选默认 4，也因此不能与 callback 组合。"""

    original = ZeroCopyByteArray(b"payload")

    with pytest.raises(ValueError):
        pickle.dumps(original, buffer_callback=lambda buffer: None)
    with pytest.raises(ValueError):
        pickle.dumps(original, protocol=4, buffer_callback=lambda buffer: None)


def test_out_of_band_buffers_are_positional_and_must_keep_provider_order():
    """stream marker 没有自描述 key；reversed iterable 会合法地把 buffer 接到错误对象位置。"""

    first = ZeroCopyByteArray(b"first")
    second = ZeroCopyByteArray(b"second")
    buffers = []
    payload = pickle.dumps(
        [first, second], protocol=5, buffer_callback=buffers.append
    )

    restored_in_order = pickle.loads(payload, buffers=buffers)
    restored_reversed = pickle.loads(payload, buffers=reversed(buffers))

    assert restored_in_order[0] is first
    assert restored_in_order[1] is second
    assert restored_reversed[0] is second
    assert restored_reversed[1] is first


def test_too_few_out_of_band_buffers_raise_unpickling_error():
    """buffers iterable 是按需消费；少一个就无法完成后续 reconstruct。"""

    buffers = []
    payload = pickle.dumps(
        [ZeroCopyByteArray(b"first"), ZeroCopyByteArray(b"second")],
        protocol=5,
        buffer_callback=buffers.append,
    )

    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(payload, buffers=buffers[:1])


def test_find_class_is_used_for_functions_despite_its_name():
    """GLOBAL resolution 不只找 class；reduce callable/function 同样经过 find_class。"""

    payload = pickle.dumps(record_load_event)
    unpickler = TrackingUnpickler(io.BytesIO(payload))

    assert unpickler.load() is record_load_event
    assert unpickler.requested_globals == [(record_load_event.__module__, "record_load_event")]


def test_restricted_unpickler_allows_selected_builtins_and_ordinary_data():
    """list/dict/int 等常有专用 opcode，不经过 find_class；range/complex 等 global 必须 allowlist。"""

    original = {
        "plain": [1, 2, 3],
        "range": range(1, 6, 2),
        "complex": 2 + 3j,
        "slice": slice(1, 5, 2),
    }

    restored = restricted_loads(pickle.dumps(original))

    assert restored == original


def test_restricted_unpickler_rejects_non_allowlisted_functions():
    """拒绝在 callable 被调用前发生；此例不把 payload 交给 unrestricted loads。"""

    payload = pickle.dumps(len)

    with pytest.raises(pickle.UnpicklingError, match="builtins.len"):
        restricted_loads(payload)


def test_no_globals_policy_can_still_load_opcode_only_builtin_containers():
    """完全禁止 GLOBAL/STACK_GLOBAL 不等于禁止所有值；plain container opcodes 可正常恢复。"""

    payload = pickle.dumps({"items": [1, 2, None, True]})

    assert NoGlobalsUnpickler(io.BytesIO(payload)).load() == {
        "items": [1, 2, None, True]
    }


def test_unrestricted_load_invokes_reduce_callable_during_deserialization():
    """用无害的 in-memory event 证明风险机制：load 不只是解析 bytes，它会执行 global callable。"""

    LOAD_EVENTS.clear()
    try:
        payload = pickle.dumps(CallsCodeWhenLoaded("event"))
        assert LOAD_EVENTS == []

        restored = pickle.loads(payload)

        assert restored == {"loaded": "event"}
        assert LOAD_EVENTS == ["event"]
    finally:
        LOAD_EVENTS.clear()


def test_restricted_load_blocks_reduce_callable_before_its_side_effect():
    """allowlist 可拦截此类 global，但允许的任何 callable 仍需安全审计；它不是 general sandbox。"""

    LOAD_EVENTS.clear()
    try:
        payload = pickle.dumps(CallsCodeWhenLoaded("blocked"))

        with pytest.raises(pickle.UnpicklingError, match="record_load_event"):
            restricted_loads(payload)

        assert LOAD_EVENTS == []
    finally:
        LOAD_EVENTS.clear()
