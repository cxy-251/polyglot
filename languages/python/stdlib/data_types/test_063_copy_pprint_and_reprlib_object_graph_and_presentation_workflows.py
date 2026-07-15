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
from array import array
from collections import deque
from dataclasses import dataclass
import io
import pprint
import reprlib
from types import SimpleNamespace

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


# 064｜``pprint`` 与 ``reprlib`` 的可读表示、递归保护和输出限额。
#
# ``pprint`` 侧重把数据结构排成适合人阅读的多行文本，并尽可能保留可求值表示；
# ``reprlib`` 侧重为调试器、日志和自定义 ``__repr__`` 限制深度与长度。两者生成的
# 都是诊断表示，不应代替 JSON、pickle 等明确的持久化格式。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.pprint.pformat python.pprint.pprint python.pprint.pp
# polyglot-covers: python.pprint.width python.pprint.indent python.pprint.compact
# polyglot-covers: python.pprint.depth python.pprint.sort-dicts python.pprint.underscore-numbers
# polyglot-covers: python.pprint.saferepr python.pprint.isrecursive python.pprint.isreadable
# polyglot-covers: python.pprint.PrettyPrinter python.pprint.format-hook
# polyglot-covers: python.pprint.dataclass python.pprint.SimpleNamespace
# polyglot-covers: python.reprlib.repr python.reprlib.Repr python.reprlib.aRepr
# polyglot-covers: python.reprlib.container-limits python.reprlib.string-integer-limits
# polyglot-covers: python.reprlib.maxlevel python.reprlib.maxother
# polyglot-covers: python.reprlib.type-dispatch python.reprlib.recursive-repr



def test_pformat_returns_text_while_pprint_writes_one_trailing_newline():
    """``pformat`` 便于继续处理字符串；``pprint`` 面向 stream 并自动补换行。"""

    value = {"b": 2, "a": 1}
    formatted = pprint.pformat(value)
    stream = io.StringIO()

    result = pprint.pprint(value, stream=stream)

    assert formatted == "{'a': 1, 'b': 2}"
    assert result is None
    assert stream.getvalue() == formatted + "\n"


def test_width_selects_single_or_multiple_lines_but_is_only_a_best_effort_limit():
    """可拆结构会按 width 换行；一个不可拆的长原子仍可能超过指定宽度。"""

    value = ["alpha", "beta", "gamma"]

    wide = pprint.pformat(value, width=80)
    narrow = pprint.pformat(value, width=12)
    indivisible = pprint.pformat("x" * 30, width=10)

    assert "\n" not in wide
    assert len(narrow.splitlines()) > 1
    assert eval(narrow) == value
    assert len(indivisible) > 10


def test_indent_changes_nested_layout_without_changing_the_represented_value():
    """indent 是每个嵌套层级增加的空格数；它只改变展示，不改变值。"""

    value = {"outer": [1, 2, 3]}

    one_space = pprint.pformat(value, width=12, indent=1, sort_dicts=False)
    four_spaces = pprint.pformat(value, width=12, indent=4, sort_dicts=False)

    assert one_space != four_spaces
    assert max(len(line) - len(line.lstrip()) for line in four_spaces.splitlines()) > 1
    assert eval(one_space) == eval(four_spaces) == value


def test_depth_replaces_deeper_containers_with_ellipsis_and_is_not_round_trippable():
    """depth 限制容器嵌套层数，省略号表示未展开内容，不是原值的完整序列化。"""

    value = {"outer": {"inner": {"answer": 42}}}
    printer = pprint.PrettyPrinter(depth=1, sort_dicts=False)

    formatted = printer.pformat(value)

    assert formatted == "{'outer': {...}}"
    assert not printer.isreadable(value)


def test_compact_packs_multiple_sequence_items_on_each_available_line():
    """compact=False 倾向每行一个元素；True 会在 width 内尽量多放几个。"""

    value = list(range(12))

    expanded = pprint.pformat(value, width=16, compact=False)
    compact = pprint.pformat(value, width=16, compact=True)

    assert eval(expanded) == eval(compact) == value
    assert len(compact.splitlines()) < len(expanded.splitlines())


def test_sort_dicts_controls_sorted_keys_versus_insertion_order():
    """pformat/pprint 默认按 key 排序；关闭后才保留现代 dict 的插入顺序。"""

    value = {"z": 1, "a": 2, "m": 3}

    sorted_output = pprint.pformat(value)
    insertion_output = pprint.pformat(value, sort_dicts=False)

    assert sorted_output == "{'a': 2, 'm': 3, 'z': 1}"
    assert insertion_output == "{'z': 1, 'a': 2, 'm': 3}"


def test_pp_defaults_to_insertion_order_unlike_pprint():
    """便捷函数 ``pp`` 的 sort_dicts 默认是 False；``pprint`` 的默认值是 True。"""

    value = {"z": 1, "a": 2}
    pp_stream = io.StringIO()
    pprint_stream = io.StringIO()

    pprint.pp(value, stream=pp_stream)
    pprint.pprint(value, stream=pprint_stream)

    assert pp_stream.getvalue() == "{'z': 1, 'a': 2}\n"
    assert pprint_stream.getvalue() == "{'a': 2, 'z': 1}\n"


def test_underscore_numbers_improves_large_integer_readability_in_python_310():
    """3.10 新增选项只改变整数表示；下划线仍是合法 Python 数字分隔符。"""

    value = {"population": 1234567890}

    plain = pprint.pformat(value)
    grouped = pprint.pformat(value, underscore_numbers=True)

    assert "1234567890" in plain
    assert "1_234_567_890" in grouped
    assert eval(grouped) == value


def test_pretty_printer_supports_dataclass_layout_in_python_310():
    """3.10 会识别自动生成 repr 的 dataclass，并在窄宽度下展开字段。"""

    @dataclass
    class Package:
        name: str
        versions: list

    value = Package("polyglot", ["3.10", "3.11", "3.12"])
    formatted = pprint.pformat(value, width=24)

    assert formatted.startswith("Package(")
    assert "name='polyglot'" in formatted
    assert "versions=['3.10'," in formatted
    assert "\n" in formatted


def test_pretty_printer_supports_simple_namespace_as_a_structured_value():
    """SimpleNamespace 在宽度不足时按 attribute 展开，而非退化成不透明地址。"""

    value = SimpleNamespace(name="polyglot", enabled=True, retries=3)
    formatted = pprint.pformat(value, width=25, sort_dicts=False)

    assert formatted.startswith("namespace(")
    assert "name='polyglot'" in formatted
    assert "enabled=True" in formatted
    assert "\n" in formatted


def test_saferepr_marks_a_recursive_reference_instead_of_recursing_forever():
    """递归容器中的回边会变成带类型和 id 的标记，其余元素仍正常表示。"""

    value = ["root"]
    value.append(value)

    formatted = pprint.saferepr(value)

    assert formatted.startswith("['root', <Recursion on list with id=")
    assert formatted.endswith(">]")
    assert pprint.isrecursive(value)
    assert not pprint.isreadable(value)


def test_readability_and_recursion_are_separate_properties_for_normal_data():
    """普通 literal 数据既无递归又可 eval 重建；判断不等同于数据格式安全校验。"""

    value = {"items": [1, 2], "flags": (True, None)}
    formatted = pprint.saferepr(value)

    assert not pprint.isrecursive(value)
    assert pprint.isreadable(value)
    assert eval(formatted) == value


def test_pretty_printer_instance_reuses_configuration_and_output_stream():
    """重复输出时显式实例可复用 width、排序与 stream 配置。"""

    stream = io.StringIO()
    printer = pprint.PrettyPrinter(stream=stream, width=12, sort_dicts=False)

    printer.pprint({"first": [1, 2, 3]})
    printer.pprint({"second": [4, 5, 6]})

    output = stream.getvalue()
    assert output.count("\n") >= 4
    assert "'first'" in output
    assert "'second'" in output


def test_pretty_printer_format_returns_text_readability_and_recursion_flags():
    """底层 format hook 的三元组分别是表示文本、可读标志和递归标志。"""

    printer = pprint.PrettyPrinter()

    text, readable, recursive = printer.format({"answer": 42}, {}, 0, 0)

    assert text == "{'answer': 42}"
    assert readable is True
    assert recursive is False


def test_pretty_printer_subclass_can_replace_object_formatting():
    """重写 format 可为领域对象提供诊断表示；False 表示它不保证可由 eval 重建。"""

    class Secret:
        pass

    class RedactingPrinter(pprint.PrettyPrinter):
        def format(self, value, context, maxlevels, level):
            if isinstance(value, Secret):
                return "<redacted>", False, False
            return super().format(value, context, maxlevels, level)

    printer = RedactingPrinter()

    assert printer.pformat(Secret()) == "<redacted>"
    assert not printer.isreadable(Secret())


def test_reprlib_module_function_limits_a_long_container_representation():
    """模块级 repr 使用共享 aRepr 配置，默认省略长容器的尾部。"""

    value = list(range(20))
    limited = reprlib.repr(value)

    assert limited.startswith("[0, 1, 2")
    assert limited.endswith(", ...]")
    assert len(limited) < len(repr(value))


def test_repr_object_has_independent_limits_for_different_container_types():
    """maxlist/maxdict 分别限制展示的 entry 数，避免一个全局字符上限误伤结构。"""

    formatter = reprlib.Repr()
    formatter.maxlist = 2
    formatter.maxdict = 1

    list_text = formatter.repr([0, 1, 2, 3])
    dict_text = formatter.repr({"first": 1, "second": 2})

    assert list_text == "[0, 1, ...]"
    assert dict_text == "{'first': 1, ...}"


def test_repr_object_limits_strings_and_integers_by_dropping_the_middle():
    """maxstring/maxlong 保留首尾上下文并用省略号替换中间，适合诊断而非恢复数据。"""

    formatter = reprlib.Repr()
    formatter.maxstring = 12
    formatter.maxlong = 12

    string_text = formatter.repr("abcdefghijklmnopqrstuvwxyz")
    integer_text = formatter.repr(12345678901234567890)

    assert "..." in string_text
    assert string_text.startswith("'") and string_text.endswith("'")
    assert len(string_text) <= 12
    assert "..." in integer_text
    assert integer_text.startswith("123")
    assert integer_text.endswith("890")
    assert len(integer_text) <= 12


def test_repr_maxlevel_stops_nested_container_expansion():
    """递归深度耗尽后使用 ``[...]``、``{...}`` 等类型相应占位符。"""

    formatter = reprlib.Repr()
    formatter.maxlevel = 1

    text = formatter.repr([[1, 2], {"key": "value"}])

    assert text == "[[...], {...}]"


def test_repr_has_separate_entry_limits_for_deque_and_array():
    """deque/array 使用各自的 max* 配置，同时保留可辨认的容器外形。"""

    formatter = reprlib.Repr()
    formatter.maxdeque = 2
    formatter.maxarray = 2

    deque_text = formatter.repr(deque(range(5)))
    array_text = formatter.repr(array("i", range(5)))

    assert deque_text == "deque([0, 1, ...])"
    assert array_text == "array('i', [0, 1, ...])"


def test_repr_maxother_truncates_an_unrecognized_custom_repr():
    """没有 repr_TYPENAME 方法的对象走 maxother，仍调用其 repr 后限制最终文本。"""

    class Verbose:
        def __repr__(self):
            return "VerboseObjectWithAQuiteLongDiagnosticValue"

    formatter = reprlib.Repr()
    formatter.maxother = 16

    text = formatter.repr(Verbose())

    assert len(text) <= 16
    assert "..." in text


def test_repr_subclass_dispatches_to_a_method_named_for_the_runtime_type():
    """``repr1`` 根据 type 名寻找 repr_TYPE，可为领域类型添加稳定的短表示。"""

    class Coordinate:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class DomainRepr(reprlib.Repr):
        def repr_Coordinate(self, value, level):
            return f"point({value.x},{value.y})@level={level}"

    formatter = DomainRepr()

    assert formatter.repr(Coordinate(3, 4)) == "point(3,4)@level=6"


def test_recursive_repr_decorator_replaces_only_the_recursive_call():
    """同一线程再次进入同一对象的 __repr__ 时返回 fillvalue，外层调用仍完成。"""

    class Node:
        def __init__(self, name):
            self.name = name
            self.child = None

        @reprlib.recursive_repr(fillvalue="<cycle>")
        def __repr__(self):
            return f"Node({self.name!r}, child={self.child!r})"

    node = Node("root")
    node.child = node

    assert repr(node) == "Node('root', child=<cycle>)"


def test_arepr_is_shared_global_configuration_and_should_be_changed_temporarily(monkeypatch):
    """模块函数绑定共享 aRepr；修改会影响进程内其他调用，测试用 monkeypatch 自动恢复。"""

    monkeypatch.setattr(reprlib.aRepr, "maxlist", 1)

    assert reprlib.repr([1, 2, 3]) == "[1, ...]"
