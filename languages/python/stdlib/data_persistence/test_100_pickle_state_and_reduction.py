"""100｜pickle 的 constructor 参数、instance state 与 reduction tuple。

默认 unpickle 不调用 ``__init__``；需要 constructor invariant 时用 ``__new__``，需要向它传参
时用 ``__getnewargs_ex__``。状态迁移优先选择 ``__getstate__/__setstate__``；直接实现最多
六项的 reduce value 更强，但 callable、state、list/dict iterators 的位置很容易写错。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import pickle

import pytest


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
        return {}

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


def test_false_getstate_value_skips_setstate_entirely():
    """None/空 dict 等 false state 不调用 __setstate__；需要 callback 时返回 truthy state。"""

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
