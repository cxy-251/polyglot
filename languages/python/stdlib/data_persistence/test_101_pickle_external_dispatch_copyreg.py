"""101｜pickle external reference、dispatch table 与 ``copyreg``。

``persistent_id`` 把对象替换为外部 store key，load 时解析的是“现在的外部值”；dispatch
table 则在不修改目标 class 的情况下提供 reduction recipe。优先用单个 Pickler 的私有表；
``copyreg`` 修改 process-global registry，也会影响 ``copy.copy``，测试必须恢复原状态。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import copy
import copyreg
import io
import pickle

import pytest


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
