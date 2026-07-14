"""063｜``copy`` 的浅拷贝、深拷贝与对象图协议。

赋值只建立新绑定；浅拷贝只复制最外层容器；深拷贝则沿对象图递归复制，
同时用 ``memo`` 处理环和重复引用。本文件也展示用户类型如何通过
``__copy__``、``__deepcopy__`` 以及 pickle/copyreg 协议控制复制边界。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.copy.assignment-binding python.copy.shallow-copy
# polyglot-covers: python.copy.deepcopy python.copy.compound-objects
# polyglot-covers: python.copy.deepcopy-alias-topology python.copy.deepcopy-cycles
# polyglot-covers: python.copy.deepcopy-memo python.copy.deepcopy-selective-sharing
# polyglot-covers: python.copy.__copy__ python.copy.__deepcopy__
# polyglot-covers: python.copy.copyreg python.copy.pickle-reduction
# polyglot-covers: python.copy.immutable-atoms python.copy.tuple-optimization
# polyglot-covers: python.copy.functions-classes-unchanged python.copy.unsupported-types

import copy
import copyreg
import sys

import pytest


def test_assignment_creates_an_alias_instead_of_copying_the_object():
    """赋值后的两个名字指向同一对象；经任一名字修改都会从另一边看到。"""

    original = {"topics": ["syntax"]}
    alias = original

    alias["topics"].append("protocols")

    assert alias is original
    assert original == {"topics": ["syntax", "protocols"]}


def test_shallow_copy_rebuilds_outer_list_but_reuses_nested_objects():
    """浅拷贝隔离外层结构，却把原有元素引用直接插入新容器。"""

    original = [["shared"], ["also shared"]]
    cloned = copy.copy(original)

    cloned.append(["new outer item"])
    cloned[0].append("visible from both")

    assert cloned is not original
    assert len(original) == 2
    assert cloned[0] is original[0]
    assert original[0] == ["shared", "visible from both"]


def test_shallow_copy_of_dictionary_matches_the_builtin_copy_workflow():
    """``copy.copy(mapping)`` 与 ``dict.copy`` 都是新 dict 加共享 value。"""

    nested = {"enabled": True}
    original = {"options": nested}

    generic = copy.copy(original)
    idiomatic = original.copy()

    assert generic == idiomatic == original
    assert generic is not original
    assert idiomatic is not original
    assert generic["options"] is idiomatic["options"] is nested


def test_deepcopy_recursively_detaches_nested_mutable_values():
    """深拷贝得到独立的可变后代，修改 clone 不再穿透到源对象。"""

    original = {"groups": [{"members": ["Ada"]}]}
    cloned = copy.deepcopy(original)

    cloned["groups"][0]["members"].append("Grace")

    assert cloned == {"groups": [{"members": ["Ada", "Grace"]}]}
    assert original == {"groups": [{"members": ["Ada"]}]}
    assert cloned["groups"][0] is not original["groups"][0]


def test_deepcopy_preserves_repeated_reference_topology_with_one_clone():
    """同一源对象出现多次时，memo 让结果仍共享同一个“复制品”，而非复制多份。"""

    shared = {"tags": []}
    original = {"primary": shared, "backup": shared}

    cloned = copy.deepcopy(original)

    assert cloned["primary"] is cloned["backup"]
    assert cloned["primary"] is not shared

    cloned["primary"]["tags"].append("one clone")
    assert cloned["backup"]["tags"] == ["one clone"]
    assert shared["tags"] == []


def test_deepcopy_handles_a_self_referential_builtin_container():
    """memo 在递归前记住已复制对象，因此自引用 list 不会无限递归。"""

    original = ["root"]
    original.append(original)

    cloned = copy.deepcopy(original)

    assert cloned is not original
    assert cloned[0] == "root"
    assert cloned[1] is cloned


def test_copy_and_deepcopy_reuse_atomic_immutable_values():
    """数字、字符串、bytes 等原子不可变对象没有独立副本需求，通常直接复用。"""

    values = (None, True, 42, 3.5, "text", b"bytes")

    for value in values:
        assert copy.copy(value) is value
        assert copy.deepcopy(value) is value


def test_deepcopy_of_tuple_may_reuse_or_rebuild_it_based_on_its_items():
    """tuple 本身不可变，但包含可变元素时必须重建；全为原子值时可返回原对象。"""

    atomic = (1, "two", None)
    compound = ([1], "two")

    atomic_clone = copy.deepcopy(atomic)
    compound_clone = copy.deepcopy(compound)

    assert atomic_clone is atomic
    assert compound_clone is not compound
    assert compound_clone[0] is not compound[0]
    assert compound_clone == compound


def test_user_defined_copy_method_controls_the_shallow_copy_result():
    """``copy.copy`` 优先调用 ``__copy__()``，协议方法不接收 memo。"""

    class VersionedList:
        def __init__(self, values, version=1):
            self.values = values
            self.version = version

        def __copy__(self):
            return type(self)(self.values, version=self.version + 1)

    original = VersionedList(["shared"])
    cloned = copy.copy(original)

    assert cloned is not original
    assert cloned.version == 2
    assert cloned.values is original.values


def test_user_defined_deepcopy_passes_the_same_memo_to_components():
    """自定义实现应把 memo 传给递归 deepcopy，才能保持共享引用关系。"""

    class Pair:
        def __init__(self, left, right):
            self.left = left
            self.right = right

        def __deepcopy__(self, memo):
            clone = type(self).__new__(type(self))
            memo[id(self)] = clone
            clone.left = copy.deepcopy(self.left, memo)
            clone.right = copy.deepcopy(self.right, memo)
            return clone

    shared = ["one object"]
    original = Pair(shared, shared)
    cloned = copy.deepcopy(original)

    assert cloned is not original
    assert cloned.left is cloned.right
    assert cloned.left is not shared


def test_custom_deepcopy_must_memoize_before_copying_a_recursive_component():
    """先登记空 clone 再递归，才能让指回自身的边落到 clone，而不是无限调用。"""

    class Node:
        def __init__(self, name):
            self.name = name
            self.children = []

        def __deepcopy__(self, memo):
            clone = type(self).__new__(type(self))
            memo[id(self)] = clone
            clone.name = self.name
            clone.children = copy.deepcopy(self.children, memo)
            return clone

    root = Node("root")
    root.children.append(root)

    cloned = copy.deepcopy(root)

    assert cloned is not root
    assert cloned.children[0] is cloned


def test_custom_deepcopy_can_intentionally_keep_shared_read_only_context():
    """深拷贝可能“复制过多”；协议可只复制可变状态，并显式共享只读配置。"""

    class Job:
        def __init__(self, payload, schema):
            self.payload = payload
            self.schema = schema

        def __deepcopy__(self, memo):
            clone = type(self).__new__(type(self))
            memo[id(self)] = clone
            clone.payload = copy.deepcopy(self.payload, memo)
            clone.schema = self.schema
            return clone

    shared_schema = ("name", "email")
    original = Job({"name": ["Ada"]}, shared_schema)
    cloned = copy.deepcopy(original)

    assert cloned.payload is not original.payload
    assert cloned.payload["name"] is not original.payload["name"]
    assert cloned.schema is original.schema is shared_schema


def test_default_instance_copy_is_shallow_and_preserves_the_runtime_class():
    """没有自定义协议时，普通实例仍可复制；实例壳不同，attribute 引用保持共享。"""

    class Record:
        def __init__(self, values):
            self.values = values

    original = Record([1, 2])
    cloned = copy.copy(original)

    assert type(cloned) is Record
    assert cloned is not original
    assert cloned.values is original.values


def test_copyreg_reducer_is_used_when_a_type_has_no_copy_protocol(monkeypatch):
    """copy 会复用 pickle 的注册 reducer；深拷贝还会递归复制 reducer 参数。"""

    class Registered:
        def __init__(self, values):
            self.values = values

    calls = []

    def reduce_registered(value):
        calls.append(value)
        return Registered, (value.values,)

    monkeypatch.setitem(copyreg.dispatch_table, Registered, reduce_registered)
    original = Registered([1, 2])

    shallow = copy.copy(original)
    deep = copy.deepcopy(original)

    assert calls == [original, original]
    assert shallow is not original
    assert shallow.values is original.values
    assert deep is not original
    assert deep.values == original.values
    assert deep.values is not original.values


def test_reduce_protocol_can_reconstruct_state_for_both_copy_operations():
    """若没有专用复制方法，``__reduce_ex__`` 可同时描述构造参数和额外状态。"""

    class ReducedRecord:
        seen_protocols = []

        def __init__(self, name):
            self.name = name
            self.metadata = None

        def __reduce_ex__(self, protocol):
            type(self).seen_protocols.append(protocol)
            return type(self), (self.name,), {"metadata": self.metadata}

    original = ReducedRecord("entry")
    original.metadata = ["mutable"]

    shallow = copy.copy(original)
    deep = copy.deepcopy(original)

    assert ReducedRecord.seen_protocols == [4, 4]
    assert shallow.name == deep.name == "entry"
    assert shallow.metadata is original.metadata
    assert deep.metadata == original.metadata
    assert deep.metadata is not original.metadata


def test_functions_and_classes_are_returned_unchanged():
    """copy 对 function 与 class 的处理和 pickle 兼容：浅拷贝、深拷贝都复用 identity。"""

    def operation():
        return "result"

    class Service:
        pass

    for value in (operation, Service):
        assert copy.copy(value) is value
        assert copy.deepcopy(value) is value


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy])
def test_modules_are_not_copyable(operation):
    """module、frame、socket 等运行时资源没有通用复制语义；调用会失败而非造假副本。"""

    with pytest.raises(TypeError, match="cannot pickle 'module' object"):
        operation(sys)


def test_copy_protocol_errors_propagate_to_the_caller():
    """``copy.Error`` 是模块专用异常；自定义协议可用它明确报告无法复制。"""

    class UniqueResource:
        def __copy__(self):
            raise copy.Error("resource identity must stay unique")

    with pytest.raises(copy.Error, match="identity must stay unique"):
        copy.copy(UniqueResource())
