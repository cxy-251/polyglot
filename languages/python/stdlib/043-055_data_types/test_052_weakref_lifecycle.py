"""052｜``weakref`` 引用、弱容器与 finalizer 生命周期示例。

弱引用不会让 referent 仅因为出现在缓存或观察者结构中而继续存活。低层 ``ref``
需要显式调用取得对象，``proxy`` 透明转发操作，弱容器则在 key/value 被回收后自动
删除条目。``finalize`` 保存清理函数直到目标消失，但清理函数及参数绝不能反向强引用
目标，否则会自己阻止回收。

案例用 ``gc.collect()`` 完成确定的本地生命周期检查，不依赖 sleep。
"""

# polyglot-covers: python.weakref.ref python.weakref.referent-lifecycle
# polyglot-covers: python.weakref.callback python.weakref.callback-order
# polyglot-covers: python.weakref.supported-types python.weakref.slots-weakref
# polyglot-covers: python.weakref.hash-cache python.weakref.equality
# polyglot-covers: python.weakref.proxy python.weakref.proxy-reference-error
# polyglot-covers: python.weakref.callable-proxy python.weakref.proxy-unhashable
# polyglot-covers: python.weakref.getweakrefcount python.weakref.getweakrefs
# polyglot-covers: python.weakref.WeakValueDictionary python.weakref.valuerefs
# polyglot-covers: python.weakref.WeakKeyDictionary python.weakref.keyrefs
# polyglot-covers: python.weakref.equal-key-identity python.weakref.WeakSet
# polyglot-covers: python.weakref.WeakMethod python.weakref.bound-method-ephemeral
# polyglot-covers: python.weakref.finalize python.weakref.finalize-once
# polyglot-covers: python.weakref.finalize-peek python.weakref.finalize-detach
# polyglot-covers: python.weakref.finalize-atexit python.weakref.finalize-strong-capture

import gc
import weakref

import pytest


class Payload:
    def __init__(self, name):
        self.name = name

    def describe(self):
        return f"payload:{self.name}"


class EqualKey:
    """按 value 相等且可哈希，用于展示 WeakKeyDictionary 的 identity 陷阱。"""

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, EqualKey):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


def collect_garbage():
    """显式触发循环 GC；普通 CPython 引用计数对象通常在调用前已被回收。"""

    gc.collect()


def test_ref_returns_live_referent_then_none_without_keeping_it_alive():
    """调用 ref 是原子化的存活检查和取值；只剩弱引用时 referent 可以被回收。"""

    target = Payload("image")
    reference = weakref.ref(target)

    assert reference() is target
    assert reference().describe() == "payload:image"

    del target
    collect_garbage()

    assert reference() is None


def test_ref_callbacks_run_newest_first_and_receive_a_dead_reference():
    """同一对象的多个 callback 按注册逆序执行；回调发生时已经不能再取得 referent。"""

    events = []
    target = Payload("temporary")

    def record(name):
        return lambda reference: events.append((name, reference()))

    older = weakref.ref(target, record("older"))
    newer = weakref.ref(target, record("newer"))

    assert older.__callback__ is not None
    assert newer.__callback__ is not None

    del target
    collect_garbage()

    assert events == [("newer", None), ("older", None)]
    assert older.__callback__ is None
    assert newer.__callback__ is None


def test_builtin_list_needs_a_subclass_to_gain_weak_reference_support():
    """普通 list/dict 不支持弱引用；具有实例布局的 Python 子类可以增加该能力。"""

    class WeakList(list):
        pass

    with pytest.raises(TypeError, match="weak reference"):
        weakref.ref([])

    target = WeakList([1, 2])
    reference = weakref.ref(target)

    assert reference() is target
    del target
    collect_garbage()
    assert reference() is None


def test_slots_class_must_explicitly_reserve_weakref_slot():
    """声明 __slots__ 会默认关闭弱引用；加入 '__weakref__' 才保留运行时槽位。"""

    class WithoutWeakReference:
        __slots__ = ("value",)

    class WithWeakReference:
        __slots__ = ("value", "__weakref__")

    with pytest.raises(TypeError, match="weak reference"):
        weakref.ref(WithoutWeakReference())

    target = WithWeakReference()
    target.value = 42
    reference = weakref.ref(target)

    assert reference().value == 42


def test_ref_hash_is_cached_if_computed_while_referent_is_alive():
    """先 hash 的弱引用会保存 referent hash；回收后首次才 hash 则无法再取得该值。"""

    first = Payload("first")
    cached_reference = weakref.ref(first)
    cached_hash = hash(cached_reference)

    del first
    collect_garbage()

    assert hash(cached_reference) == cached_hash

    second = Payload("second")
    late_reference = weakref.ref(second)
    del second
    collect_garbage()

    with pytest.raises(TypeError, match="weak object has gone away"):
        hash(late_reference)


def test_ref_equality_uses_live_referents_but_dead_refs_only_equal_themselves():
    """活 referent 沿用对象 equality；任一侧死亡后，不同 ref object 不再按旧值相等。"""

    first = EqualKey("same")
    second = EqualKey("same")
    first_ref = weakref.ref(first)
    second_ref = weakref.ref(second)

    assert first_ref == second_ref
    assert first_ref is not second_ref

    del first, second
    collect_garbage()

    assert first_ref != second_ref
    assert first_ref == first_ref


def test_proxy_forwards_operations_but_is_never_hashable():
    """proxy 省去显式 ref() 调用并透明访问属性；即使 referent 可哈希，proxy 也不可哈希。"""

    target = Payload("cached")
    proxy = weakref.proxy(target)

    assert isinstance(proxy, Payload)
    assert proxy.name == "cached"
    assert proxy.describe() == "payload:cached"

    with pytest.raises(TypeError, match="unhashable"):
        hash(proxy)

    del target
    collect_garbage()

    with pytest.raises(ReferenceError, match="weakly-referenced object"):
        proxy.describe()


def test_callable_proxy_remains_callable_only_while_function_is_alive():
    """函数 proxy 使用 CallableProxyType；函数回收后调用也会抛 ReferenceError。"""

    def multiply(value):
        return value * 2

    proxy = weakref.proxy(multiply)

    assert type(proxy) is weakref.CallableProxyType
    assert isinstance(proxy, weakref.ProxyTypes)
    assert proxy(21) == 42

    del multiply
    collect_garbage()

    with pytest.raises(ReferenceError):
        proxy(21)


def test_getweakrefs_counts_refs_and_proxies_that_are_themselves_kept_alive():
    """弱引用对象本身若没有强引用也会消失；这里保存三个 handle 再检查枚举结果。"""

    target = Payload("observed")
    first = weakref.ref(target, lambda reference: None)
    second = weakref.ref(target, lambda reference: None)
    proxy = weakref.proxy(target)

    references = weakref.getweakrefs(target)

    assert weakref.getweakrefcount(target) == 3
    assert any(reference is first for reference in references)
    assert any(reference is second for reference in references)
    assert any(reference is proxy for reference in references)


def test_weak_value_dictionary_drops_cache_entry_after_value_collection():
    """mapping 对 key 是强引用、对 value 是弱引用，适合不延长对象生命的缓存。"""

    cache = weakref.WeakValueDictionary()
    target = Payload("thumbnail")
    cache["image-id"] = target
    value_refs = list(cache.valuerefs())

    assert cache["image-id"] is target
    assert len(value_refs) == 1
    assert value_refs[0]() is target

    del target
    collect_garbage()

    assert "image-id" not in cache
    assert value_refs[0]() is None


def test_weak_key_dictionary_drops_metadata_after_key_collection():
    """mapping 对 value 是强引用、对 key 是弱引用，可给外部拥有的对象附加元数据。"""

    metadata = weakref.WeakKeyDictionary()
    target = Payload("request")
    metadata[target] = {"trace_id": "abc"}
    key_refs = list(metadata.keyrefs())

    assert metadata[target] == {"trace_id": "abc"}
    assert key_refs[0]() is target

    del target
    collect_garbage()

    assert len(metadata) == 0
    assert key_refs[0]() is None


def test_equal_but_nonidentical_weak_key_updates_value_not_stored_key_identity():
    """相等 key 写入会更新旧 entry 的值却保留原 key；原 key 死亡时条目随之删除。"""

    first = EqualKey("same")
    second = EqualKey("same")
    metadata = weakref.WeakKeyDictionary()

    metadata[first] = "first value"
    metadata[second] = "updated value"
    stored_key_ref = next(iter(metadata.keyrefs()))

    assert len(metadata) == 1
    assert metadata[second] == "updated value"
    assert stored_key_ref() is first

    del first
    collect_garbage()

    assert second is not None
    assert len(metadata) == 0


def test_remove_equal_weak_key_before_reassignment_to_replace_identity():
    """若新 identity 必须拥有条目，应先显式删除相等旧 key，再插入新 key。"""

    first = EqualKey("same")
    second = EqualKey("same")
    metadata = weakref.WeakKeyDictionary({first: "old"})

    del metadata[first]
    metadata[second] = "new"
    stored_key_ref = next(iter(metadata.keyrefs()))

    del first
    collect_garbage()

    assert stored_key_ref() is second
    assert metadata[second] == "new"


def test_weak_set_discards_members_without_other_strong_references():
    """WeakSet 提供 set 接口但不拥有元素，适合对象注册表或观察者集合。"""

    first = Payload("first")
    second = Payload("second")
    members = weakref.WeakSet([first, second])
    first_ref = weakref.ref(first)

    assert len(members) == 2
    assert first in members

    del first
    collect_garbage()

    assert first_ref() is None
    assert list(members) == [second]


def test_weakmethod_recreates_bound_method_without_owning_the_instance():
    """普通 ref 指向临时 bound-method 对象会立刻失效；WeakMethod 分别跟踪实例和函数。"""

    class Listener:
        def handle(self, event):
            return f"handled:{event}"

    listener = Listener()
    ordinary = weakref.ref(listener.handle)
    method_ref = weakref.WeakMethod(listener.handle)

    assert ordinary() is None
    bound_method = method_ref()
    assert bound_method("update") == "handled:update"

    del bound_method
    del listener
    collect_garbage()

    assert method_ref() is None


def test_finalize_can_be_called_manually_at_most_once_and_returns_callback_value():
    """手动调用 live finalizer 会执行并标记 dead；再次调用或随后 GC 都不会重复。"""

    events = []
    target = Payload("resource")

    def cleanup(name, *, status):
        events.append((name, status))
        return "cleaned"

    finalizer = weakref.finalize(target, cleanup, target.name, status="manual")

    assert finalizer.alive is True
    assert finalizer() == "cleaned"
    assert finalizer.alive is False
    assert finalizer() is None

    del target
    collect_garbage()
    assert events == [("resource", "manual")]


def test_finalize_runs_after_collection_without_needing_to_keep_handle_alive():
    """finalize 注册表会保存自身；callback 参数只含独立字符串，不会反向拥有 target。"""

    events = []
    target = Payload("automatic")
    target_ref = weakref.ref(target)
    finalizer = weakref.finalize(target, events.append, target.name)

    del target
    collect_garbage()

    assert target_ref() is None
    assert events == ["automatic"]
    assert finalizer.alive is False


def test_finalize_peek_inspects_registration_without_consuming_it():
    """peek 返回当前 obj/func/args/kwargs 但仍保持 alive；atexit 是可写退出策略。"""

    events = []
    target = Payload("peeked")
    finalizer = weakref.finalize(target, events.append, "cleanup")

    registered_object, function, args, kwargs = finalizer.peek()

    assert registered_object is target
    assert function == events.append
    assert args == ("cleanup",)
    assert kwargs == {}
    assert finalizer.alive is True
    assert finalizer.atexit is True

    finalizer.atexit = False
    assert finalizer.atexit is False
    assert finalizer() is None
    assert events == ["cleanup"]


def test_finalize_detach_returns_registration_and_prevents_automatic_callback():
    """detach 注销 live finalizer 并交还四元组；目标之后回收也不再执行 callback。"""

    events = []
    target = Payload("detached")
    target_ref = weakref.ref(target)
    finalizer = weakref.finalize(target, events.append, "should not run")

    registered_object, function, args, kwargs = finalizer.detach()

    assert registered_object is target
    assert function == events.append
    assert args == ("should not run",)
    assert kwargs == {}
    assert finalizer.alive is False
    assert finalizer.peek() is None

    del registered_object, function, args, kwargs
    del target
    collect_garbage()

    assert target_ref() is None
    assert events == []


def test_bound_method_finalizer_callback_strongly_captures_and_keeps_target_alive():
    """把 obj.bound_method 交给 finalize 会经 method.__self__ 强引用 obj，形成自阻塞。"""

    events = []

    class Owner:
        def cleanup(self):
            events.append("cleaned")

    owner = Owner()
    owner_ref = weakref.ref(owner)
    finalizer = weakref.finalize(owner, owner.cleanup)

    del owner
    collect_garbage()

    assert owner_ref() is not None
    assert finalizer.alive is True
    assert events == []

    # 注销并释放 detach 返回的 obj 与 bound method，避免本测试把对象泄漏到进程退出。
    detached = finalizer.detach()
    del detached
    collect_garbage()

    assert owner_ref() is None
    assert events == []
