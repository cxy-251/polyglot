"""对象构造、初始化与生命周期。

共同问题：分配与初始化能否分开；复制是否自动发生；销毁时机是否确定；
类型如何定制创建结果。
"""

# polyglot-family: objects_and_dispatch
# polyglot-concept: construction_initialization_and_lifetime
# polyglot-related: languages/python/language/test_011_classes_construction_and_inheritance.py

import copy
import gc
import weakref


def test_new_allocates_then_init_initializes_the_same_instance():
    events = []

    class Record:
        def __new__(cls, value):
            instance = super().__new__(cls)
            events.append(("new", type(instance)))
            return instance

        def __init__(self, value):
            events.append(("init", value))
            self.value = value

    record = Record(3)

    assert record.value == 3
    assert events == [("new", Record), ("init", 3)]


def test_new_can_return_another_type_and_skip_init():
    class Factory:
        def __new__(cls):
            return {"created": True}

        def __init__(self):
            raise AssertionError("not called")

    assert Factory() == {"created": True}


def test_assignment_aliases_while_copy_protocol_creates_another_object():
    class Box:
        def __init__(self, value):
            self.value = value

    original = Box([1])
    alias = original
    cloned = copy.copy(original)

    assert alias is original
    assert cloned is not original
    assert cloned.value is original.value


def test_finalization_is_gc_driven_not_scope_bound():
    events = []

    class Resource:
        pass

    resource = Resource()
    finalizer = weakref.finalize(resource, events.append, "finalized")
    del resource
    gc.collect()

    assert finalizer.alive is False
    assert events == ["finalized"]

    # CPython 常会立即引用计数回收，但语言级资源清理应使用 with，不依赖 __del__ 时点。
