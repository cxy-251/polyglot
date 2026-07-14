"""051｜``Sequence``、``MutableSequence`` 与 ``ByteString`` mixin 示例。

真正继承 sequence ABC 时，少量 primitive method 会换来一组可运行的默认算法。
这些算法通过 ``self[...]`` 等公开协议回调具体实现。
它们不会替实现者决定负索引、切片、元素约束或存储复杂度。

辅助类型中的调用日志只用于讲清分派路径，不是内部调用次数的通用承诺。
当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.collections.abc.Sequence python.sequence.abstract-primitives
# polyglot-covers: python.sequence.iter-mixin python.sequence.contains-mixin
# polyglot-covers: python.sequence.reversed-mixin python.sequence.index-mixin
# polyglot-covers: python.sequence.count-mixin python.sequence.identity-before-equality
# polyglot-covers: python.sequence.index-error-termination python.sequence.slice-responsibility
# polyglot-covers: python.sequence.negative-index-responsibility python.sequence.mixin-complexity
# polyglot-covers: python.collections.abc.MutableSequence python.mutable-sequence.primitives
# polyglot-covers: python.mutable-sequence.append-extend python.mutable-sequence.iadd
# polyglot-covers: python.mutable-sequence.pop-remove python.mutable-sequence.reverse
# polyglot-covers: python.mutable-sequence.slice-mutation python.mutable-sequence.insert-normalization
# polyglot-covers: python.mutable-sequence.failure-atomicity python.mutable-sequence.clear
# polyglot-covers: python.collections.abc.ByteString python.bytes.integer-elements

from collections.abc import ByteString
from collections.abc import MutableSequence
from collections.abc import Sequence

import pytest


class AtlasSequence(Sequence):
    """以 tuple 存储的正确只读示例；getitem 日志暴露默认 mixin 的回调。"""

    def __init__(self, values):
        self.values = tuple(values)
        self.getitem_calls = []

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        self.getitem_calls.append(index)
        # 直接委托 tuple，因此负索引、slice 和越界 IndexError 都有明确语义。
        return self.values[index]


class EditableSequence(MutableSequence):
    """用 list 实现五个 mutable primitive，并记录 mixin 如何回调它们。"""

    def __init__(self, values=()):
        self.storage = list(values)
        self.calls = []

    def __len__(self):
        return len(self.storage)

    def __getitem__(self, index):
        self.calls.append(("get", index))
        return self.storage[index]

    def __setitem__(self, index, value):
        self.calls.append(("set", index, value))
        self.storage[index] = value

    def __delitem__(self, index):
        self.calls.append(("del", index))
        del self.storage[index]

    def insert(self, index, value):
        self.calls.append(("insert", index, value))
        self.storage.insert(index, value)


def test_sequence_requires_getitem_and_len_before_instantiation():
    """Sequence 是名义 ABC；仅写 class 声明不会自动提供两个核心 primitive。"""

    class MissingPrimitives(Sequence):
        pass

    assert MissingPrimitives.__abstractmethods__ == {
        "__getitem__",
        "__len__",
    }
    with pytest.raises(TypeError, match="abstract method"):
        MissingPrimitives()


def test_sequence_primitives_unlock_iteration_membership_and_reverse_mixins():
    """只实现 getitem/len 后，ABC 的默认算法仍通过公开 self[index] 工作。"""

    sequence = AtlasSequence(["language", "builtins", "stdlib"])

    assert isinstance(sequence, Sequence)
    assert len(sequence) == 3
    assert list(sequence) == ["language", "builtins", "stdlib"]
    assert "builtins" in sequence
    assert "missing" not in sequence
    assert list(reversed(sequence)) == ["stdlib", "builtins", "language"]


def test_sequence_iteration_stops_only_when_getitem_raises_index_error():
    """默认 __iter__ 不读取 len；越界返回 sentinel 会让它继续产生值而不是结束。"""

    class SentinelEndedSequence(Sequence):
        def __len__(self):
            return 1

        def __getitem__(self, index):
            if index == 0:
                return "only"
            return None

    iterator = iter(SentinelEndedSequence())

    # 不调用 list(iterator)，否则这个故意错误的实现永远不会停止。
    assert [next(iterator) for _ in range(4)] == ["only", None, None, None]


def test_sequence_does_not_supply_negative_index_or_slice_semantics():
    """ABC 只调用 __getitem__；一个故意受限的 primitive 不会被 mixin 神奇修复。"""

    class ForwardOnlySequence(Sequence):
        def __init__(self, values):
            self.values = tuple(values)

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise TypeError("slicing is not implemented")
            if index < 0:
                raise IndexError("negative indexes are not implemented")
            return self.values[index]

    sequence = ForwardOnlySequence(["a", "b", "c"])

    assert list(sequence) == ["a", "b", "c"]
    with pytest.raises(IndexError, match="negative"):
        sequence[-1]
    with pytest.raises(TypeError, match="slicing"):
        sequence[1:]


def test_concrete_getitem_can_choose_slice_result_type_explicitly():
    """AtlasSequence 委托 tuple，所以 slice 返回 tuple；Sequence 不要求保留自定义 class。"""

    sequence = AtlasSequence(["a", "b", "c", "d"])
    sliced = sequence[1:3]

    assert type(sliced) is tuple
    assert sliced == ("b", "c")
    assert sequence[-1] == "d"


def test_sequence_index_and_count_support_normal_search_workflows():
    """index 处理 start/stop 及负边界；count 遍历所有值并返回出现次数。"""

    sequence = AtlasSequence(["a", "b", "a", "c"])

    assert sequence.index("a") == 0
    assert sequence.index("a", 1) == 2
    assert sequence.index("a", -3) == 2
    assert sequence.index("a", 0, -1) == 0
    assert sequence.count("a") == 2
    assert sequence.count("missing") == 0

    with pytest.raises(ValueError):
        sequence.index("c", 0, -1)
    with pytest.raises(ValueError):
        sequence.index("missing")


def test_sequence_mixins_check_identity_before_calling_equality():
    """contains/index/count 使用 ``is`` 短路，不必对同一对象调用 __eq__。"""

    class IdentityOnly:
        def __eq__(self, other):
            raise AssertionError("equality should not run for identical object")

    marker = IdentityOnly()
    sequence = AtlasSequence([marker])

    assert marker in sequence
    assert sequence.index(marker) == 0
    assert sequence.count(marker) == 1


def test_sequence_mixins_dispatch_through_getitem_with_distinct_patterns():
    """iteration 递增到失败；contains 提前结束；reversed 生成倒序索引。"""

    sequence = AtlasSequence(["a", "b", "c"])

    assert list(sequence) == ["a", "b", "c"]
    assert sequence.getitem_calls == [0, 1, 2, 3]

    sequence.getitem_calls.clear()
    assert "b" in sequence
    assert sequence.getitem_calls == [0, 1]

    sequence.getitem_calls.clear()
    assert list(reversed(sequence)) == ["c", "b", "a"]
    assert sequence.getitem_calls == [2, 1, 0]


def test_linear_getitem_makes_default_iteration_quadratic_in_traversal_work():
    """默认 mixin 假定随机访问合算；线性 getitem 的累计 traversal steps 呈平方增长。"""

    class LinearAccessSequence(Sequence):
        def __init__(self, values):
            self.values = tuple(values)
            self.traversal_steps = 0

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            if index < 0:
                index += len(self)
            if not 0 <= index < len(self):
                raise IndexError(index)

            # 模拟从链表头走到 index；底层 tuple 只用来保持示例简洁、结果稳定。
            self.traversal_steps += index + 1
            return self.values[index]

    sequence = LinearAccessSequence(range(5))

    assert list(sequence) == [0, 1, 2, 3, 4]
    assert sequence.traversal_steps == 1 + 2 + 3 + 4 + 5


def test_overriding_iter_avoids_linear_random_access_for_common_traversal():
    """iteration/count 可提供直接 iterator；index 仍沿用 getitem。"""

    class FastIterationSequence(Sequence):
        def __init__(self, values):
            self.values = tuple(values)
            self.getitem_steps = 0

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            if not 0 <= index < len(self):
                raise IndexError(index)
            self.getitem_steps += index + 1
            return self.values[index]

        def __iter__(self):
            return iter(self.values)

    sequence = FastIterationSequence(range(5))

    assert list(sequence) == [0, 1, 2, 3, 4]
    assert sequence.count(4) == 1
    assert sequence.getitem_steps == 0

    assert sequence.index(4) == 4
    assert sequence.getitem_steps == 1 + 2 + 3 + 4 + 5


def test_duck_primitives_do_not_structurally_create_a_sequence():
    """Sequence 是复杂接口；未继承/注册的 len+getitem 对象虽可迭代，却不通过 ABC。"""

    class DuckSequence:
        def __len__(self):
            return 2

        def __getitem__(self, index):
            return ("a", "b")[index]

    duck = DuckSequence()

    assert list(duck) == ["a", "b"]
    assert not isinstance(duck, Sequence)
    assert not isinstance(duck, ByteString)


def test_mutable_sequence_requires_three_additional_mutation_primitives():
    """只有只读 primitives 时，set/del/insert 仍保持 abstract，类型不能实例化。"""

    class ReadOnlyImplementation(MutableSequence):
        def __len__(self):
            return 0

        def __getitem__(self, index):
            raise IndexError(index)

    assert ReadOnlyImplementation.__abstractmethods__ == {
        "__delitem__",
        "__setitem__",
        "insert",
    }
    with pytest.raises(TypeError, match="abstract method"):
        ReadOnlyImplementation()


def test_append_extend_and_iadd_route_new_values_through_insert():
    """默认 append 使用 insert(len)，extend 重复 append，+= 调用 extend 并返回 self。"""

    sequence = EditableSequence(["a"])

    assert sequence.append("b") is None
    assert sequence.calls == [("insert", 1, "b")]

    sequence.calls.clear()
    assert sequence.extend(["c", "d"]) is None
    assert sequence.calls == [
        ("insert", 2, "c"),
        ("insert", 3, "d"),
    ]

    sequence.calls.clear()
    identity = id(sequence)
    sequence += ["e", "f"]
    assert id(sequence) == identity
    assert sequence.calls == [
        ("insert", 4, "e"),
        ("insert", 5, "f"),
    ]
    assert sequence.storage == ["a", "b", "c", "d", "e", "f"]


def test_extend_self_snapshots_values_before_mutating():
    """extend(self) 先用 list() 固化原值，避免边迭代边追加导致无限增长。"""

    sequence = EditableSequence(["a", "b"])
    sequence.extend(sequence)

    assert sequence.storage == ["a", "b", "a", "b"]
    assert [call for call in sequence.calls if call[0] == "insert"] == [
        ("insert", 2, "a"),
        ("insert", 3, "b"),
    ]


def test_pop_and_remove_compose_getitem_index_and_delitem():
    """pop 先读取再删除同一位置；remove 用 Sequence.index 找首个相等值后删除。"""

    sequence = EditableSequence(["a", "b", "a"])

    assert sequence.pop() == "a"
    assert sequence.calls == [("get", -1), ("del", -1)]
    assert sequence.storage == ["a", "b"]

    sequence.calls.clear()
    assert sequence.remove("b") is None
    assert sequence.calls == [
        ("get", 0),
        ("get", 1),
        ("del", 1),
    ]
    assert sequence.storage == ["a"]


def test_reverse_uses_paired_get_and_set_primitives_in_place():
    """默认 reverse 交换两端元素并返回 None，无需额外 primitive。"""

    sequence = EditableSequence(["a", "b", "c", "d"])

    identity = id(sequence)
    assert sequence.reverse() is None

    assert id(sequence) == identity
    assert sequence.storage == ["d", "c", "b", "a"]
    assert sequence.calls == [
        ("get", 3),
        ("get", 0),
        ("set", 0, "d"),
        ("set", 3, "a"),
        ("get", 2),
        ("get", 1),
        ("set", 1, "c"),
        ("set", 2, "b"),
    ]


def test_slice_assignment_and_deletion_are_concrete_primitive_responsibilities():
    """语法把 slice 交给 primitive；本示例委托 list 获得完整切片 mutation。"""

    sequence = EditableSequence([0, 1, 2, 3, 4])

    sequence[1:3] = [10, 20, 30]
    assert sequence.calls == [("set", slice(1, 3), [10, 20, 30])]
    assert sequence.storage == [0, 10, 20, 30, 3, 4]

    sequence.calls.clear()
    del sequence[::2]
    assert sequence.calls == [("del", slice(None, None, 2))]
    assert sequence.storage == [10, 30, 4]


def test_concrete_insert_decides_negative_and_oversized_index_normalization():
    """MutableSequence 只调用 insert；这里因委托 list，极小位置归零、极大位置归尾。"""

    sequence = EditableSequence(["middle"])

    assert sequence.insert(-100, "start") is None
    assert sequence.insert(100, "end") is None
    assert sequence.storage == ["start", "middle", "end"]
    assert sequence.calls == [
        ("insert", -100, "start"),
        ("insert", 100, "end"),
    ]


def test_failed_pop_and_remove_do_not_mutate_the_sequence():
    """读取/搜索先失败时 del hook 不会执行，原 storage 保持不变。"""

    sequence = EditableSequence(["a", "b"])

    with pytest.raises(IndexError):
        sequence.pop(99)
    assert sequence.storage == ["a", "b"]
    assert sequence.calls == [("get", 99)]

    sequence.calls.clear()
    with pytest.raises(ValueError):
        sequence.remove("missing")
    assert sequence.storage == ["a", "b"]
    assert all(call[0] == "get" for call in sequence.calls)


def test_clear_repeatedly_pops_until_empty_and_returns_none():
    """默认 clear 捕获空容器的 IndexError；它不要求额外 clear primitive。"""

    sequence = EditableSequence(["a", "b", "c"])

    assert sequence.clear() is None
    assert sequence.storage == []
    # 最后一次 get(-1) 在空 list 上失败，随后 clear 正常结束。
    assert sequence.calls[-1] == ("get", -1)
    assert sum(call[0] == "del" for call in sequence.calls) == 3


def test_mutable_sequence_mixin_does_not_enforce_element_domain_rules():
    """ABC 只组合协议；若容器要求同质元素，必须在 insert/set primitive 自行校验。"""

    sequence = EditableSequence([1, 2])
    sequence.append("not-an-integer")
    sequence[0] = None

    assert sequence.storage == [None, 2, "not-an-integer"]


def test_bytes_and_bytearray_are_registered_byte_strings_with_integer_items():
    """ByteString 表示 byte sequence；单元素是 0..255 的 int，不是长度一的 bytes。"""

    immutable = b"ABC"
    mutable = bytearray(b"ABC")

    assert isinstance(immutable, ByteString)
    assert isinstance(immutable, Sequence)
    assert isinstance(mutable, ByteString)
    assert isinstance(mutable, MutableSequence)
    assert list(immutable) == [65, 66, 67]
    assert immutable[0] == 65
    assert mutable[1] == 66


def test_memoryview_is_sequence_but_not_registered_as_byte_string():
    """3.10 将 memoryview 注册为 Sequence；ByteString 只注册 bytes 与 bytearray。"""

    view = memoryview(b"ABC")

    assert isinstance(view, Sequence)
    assert not isinstance(view, ByteString)
    assert list(view) == [65, 66, 67]


def test_direct_byte_string_subclass_still_controls_its_element_semantics():
    """ByteString 本身不验证元素；直接继承只获得 Sequence 合同与 mixin。"""

    class MisnamedByteString(ByteString):
        def __init__(self, values):
            self.values = tuple(values)

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            return self.values[index]

    value = MisnamedByteString(["not", "bytes"])

    assert isinstance(value, ByteString)
    assert list(value) == ["not", "bytes"]
