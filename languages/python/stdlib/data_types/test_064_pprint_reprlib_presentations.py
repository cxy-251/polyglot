"""064｜``pprint`` 与 ``reprlib`` 的可读表示、递归保护和输出限额。

``pprint`` 侧重把数据结构排成适合人阅读的多行文本，并尽可能保留可求值表示；
``reprlib`` 侧重为调试器、日志和自定义 ``__repr__`` 限制深度与长度。两者生成的
都是诊断表示，不应代替 JSON、pickle 等明确的持久化格式。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

from array import array
from collections import deque
from dataclasses import dataclass
import io
import pprint
import reprlib
from types import SimpleNamespace


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
