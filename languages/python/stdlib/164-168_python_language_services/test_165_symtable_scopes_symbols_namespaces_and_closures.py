"""165｜symtable：编译器作用域、符号标志、namespace 与闭包分析。

AST 回答“源码写了什么结构”，symtable 则回答
“每个名字在哪个作用域解析”。
这一阶段位于 AST 与字节码之间，会在不执行代码的情况下区分局部、
隐式/显式全局、nonlocal、free variable，并暴露函数、类、lambda 与
comprehension 引入的 namespace。本套也专门讲清“赋值使整个函数域变成局部”
以及“类体不是方法的闭包外层”这两个常见陷阱。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.symtable python.symtable.generate
# polyglot-covers: python.symtable.compile-types python.symtable.syntax-errors
# polyglot-covers: python.symtable.symbol-table python.symtable.table-type-name-line
# polyglot-covers: python.symtable.table-id python.symtable.optimized-nested
# polyglot-covers: python.symtable.children python.symtable.identifiers-lookup-symbols
# polyglot-covers: python.symtable.function python.symtable.parameters-locals
# polyglot-covers: python.symtable.globals-nonlocals-frees
# polyglot-covers: python.symtable.class python.symtable.class-methods
# polyglot-covers: python.symtable.symbol python.symtable.symbol-flags
# polyglot-covers: python.symtable.imported-annotated-assigned-referenced
# polyglot-covers: python.symtable.local python.symtable.global
# polyglot-covers: python.symtable.declared-global python.symtable.implicit-global
# polyglot-covers: python.symtable.nonlocal python.symtable.free-variable
# polyglot-covers: python.symtable.closure python.symtable.assignment-makes-local
# polyglot-covers: python.symtable.definition-time-scope
# polyglot-covers: python.symtable.class-scope-not-method-closure
# polyglot-covers: python.symtable.implicit-class-cell
# polyglot-covers: python.symtable.namespace python.symtable.get-namespace
# polyglot-covers: python.symtable.multiple-namespaces
# polyglot-covers: python.symtable.lambda-namespace python.symtable.comprehension-scope

import symtable

import pytest


def child_named(table, name):
    return next(child for child in table.get_children() if child.get_name() == name)


def test_symtable_accepts_compile_modes_and_returns_a_top_level_table():
    execution = symtable.symtable("value = 42\n", "module.py", "exec")
    expression = symtable.symtable("value + 1", "expression.py", "eval")
    interactive = symtable.symtable("value = 42\n", "console.py", "single")

    for table in (execution, expression, interactive):
        assert isinstance(table, symtable.SymbolTable)
        assert table.get_type() == "module"
        assert table.get_name() == "top"

    assert expression.lookup("value").is_referenced()
    assert expression.lookup("value").is_global()
    assert interactive.lookup("value").is_assigned()

    with pytest.raises(ValueError):
        symtable.symtable("value = 1", "module.py", "unsupported")


def test_table_metadata_describes_block_kind_location_and_optimization():
    source = (
        "module_value = 1\n"
        "def function(argument):\n"
        "    local_value = argument\n"
        "    return local_value\n"
        "class Example:\n"
        "    class_value = 2\n"
    )
    top = symtable.symtable(source, "lesson.py", "exec")
    function = child_named(top, "function")
    class_table = child_named(top, "Example")

    assert top.get_lineno() == 0
    assert top.is_optimized() is False
    assert top.is_nested() is False

    assert function.get_type() == "function"
    assert function.get_lineno() == 2
    assert function.is_optimized() is True
    assert function.is_nested() is False

    assert class_table.get_type() == "class"
    assert class_table.get_lineno() == 5
    assert class_table.is_optimized() is False


def test_children_are_direct_namespaces_and_ids_are_opaque_per_block():
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        return 42\n"
        "    return inner\n"
        "class Example:\n"
        "    def method(self):\n"
        "        return None\n"
    )
    top = symtable.symtable(source, "nested.py", "exec")
    outer = child_named(top, "outer")
    inner = child_named(outer, "inner")
    example = child_named(top, "Example")

    assert top.has_children() is True
    assert {child.get_name() for child in top.get_children()} == {
        "outer",
        "Example",
    }
    assert [child.get_name() for child in outer.get_children()] == ["inner"]
    assert inner.get_children() == []
    assert isinstance(top.get_id(), int)
    assert len({top.get_id(), outer.get_id(), inner.get_id(), example.get_id()}) == 4
    # get_id 只适合在本次分析中区分 block，它不是可跨进程或版本持久的 ID。


def test_function_summary_partitions_parameters_locals_and_globals():
    source = (
        "def calculate(first, /, second=1, *items, flag=True, **options):\n"
        "    subtotal = first + second\n"
        "    return helper(subtotal, items, flag, options)\n"
    )
    table = child_named(symtable.symtable(source, "function.py", "exec"), "calculate")

    assert table.get_parameters() == (
        "first",
        "second",
        "items",
        "flag",
        "options",
    )
    assert set(table.get_locals()) == {
        "first",
        "second",
        "items",
        "flag",
        "options",
        "subtotal",
    }
    assert set(table.get_globals()) == {"helper"}
    assert table.get_nonlocals() == ()
    assert table.get_frees() == ()


def test_symbol_flags_can_overlap_and_describe_use_separately_from_binding():
    source = (
        "import math as mathematics\n"
        "count: int = 1\n"
        "unused = 2\n"
        "result = mathematics.ceil(count)\n"
    )
    table = symtable.symtable(source, "symbols.py", "exec")
    imported = table.lookup("mathematics")
    count = table.lookup("count")
    unused = table.lookup("unused")
    result = table.lookup("result")

    assert imported.get_name() == "mathematics"
    assert imported.is_imported() is True
    assert imported.is_referenced() is True
    assert imported.is_assigned() is False
    assert imported.is_local() is True
    assert imported.is_global() is True

    assert count.is_annotated() is True
    assert count.is_assigned() is True
    assert count.is_referenced() is True
    assert unused.is_assigned() is True
    assert unused.is_referenced() is False
    assert result.is_assigned() is True
    assert result.is_referenced() is False
    # 模块域名字同时是 local 和 global 并不矛盾：它在当前 block 绑定，
    # 也就是运行时的全局 namespace。


def test_declared_global_differs_from_an_implicit_global_reference():
    source = (
        "def update():\n"
        "    global counter\n"
        "    counter = counter + external_value\n"
    )
    function = child_named(symtable.symtable(source, "globals.py", "exec"), "update")
    counter = function.lookup("counter")
    external = function.lookup("external_value")

    assert counter.is_global() is True
    assert counter.is_declared_global() is True
    assert counter.is_assigned() is True
    assert counter.is_referenced() is True

    assert external.is_global() is True
    assert external.is_declared_global() is False
    assert external.is_assigned() is False
    assert external.is_referenced() is True


def test_nonlocal_is_both_a_declaration_and_a_free_variable_in_the_inner_block():
    source = (
        "def outer(start):\n"
        "    total = start\n"
        "    def add(amount):\n"
        "        nonlocal total\n"
        "        total += amount\n"
        "        return total\n"
        "    return add\n"
    )
    outer = child_named(symtable.symtable(source, "closure.py", "exec"), "outer")
    inner = child_named(outer, "add")
    outer_total = outer.lookup("total")
    inner_total = inner.lookup("total")

    assert outer_total.is_local() is True
    assert outer_total.is_free() is False
    assert inner_total.is_nonlocal() is True
    assert inner_total.is_free() is True
    assert inner_total.is_local() is False
    assert inner.get_nonlocals() == ("total",)
    assert inner.get_frees() == ("total",)
    # 3.10 的公开 Symbol API 没有 is_cell；外层 local 是否升格为 closure cell
    # 可以由内层 get_frees 反向判断，不要依赖私有标志整数。


def test_nested_function_and_class_flags_follow_enclosing_function_scope():
    source = (
        "def outer():\n"
        "    class LocalClass:\n"
        "        pass\n"
        "    def inner():\n"
        "        return LocalClass\n"
        "    return inner\n"
    )
    outer = child_named(symtable.symtable(source, "nested.py", "exec"), "outer")
    local_class = child_named(outer, "LocalClass")
    inner = child_named(outer, "inner")

    assert outer.is_nested() is False
    assert local_class.is_nested() is True
    assert inner.is_nested() is True
    assert inner.is_optimized() is True
    assert inner.lookup("LocalClass").is_free() is True


def test_any_assignment_makes_a_name_local_for_the_whole_function_block():
    source = (
        "def surprising():\n"
        "    observed = value\n"
        "    value = 42\n"
        "    return observed\n"
    )
    function = child_named(symtable.symtable(source, "locals.py", "exec"), "surprising")
    value = function.lookup("value")

    assert value.is_local() is True
    assert value.is_global() is False
    assert value.is_assigned() is True
    assert value.is_referenced() is True
    # 符号表在整个 block 上决定作用域，不按执行顺序逐行切换；这段代码
    # 真正运行时会在第一次读 value 处触发 UnboundLocalError。


def test_decorators_defaults_and_annotations_are_resolved_in_defining_scope():
    source = (
        "@decorate\n"
        "def function(argument: Input = default_value) -> Output:\n"
        "    return argument + runtime_global\n"
    )
    top = symtable.symtable(source, "definitions.py", "exec")
    function = child_named(top, "function")

    for name in ("decorate", "Input", "default_value", "Output"):
        symbol = top.lookup(name)
        assert symbol.is_referenced() is True
        assert symbol.is_global() is True

    assert set(function.get_parameters()) == {"argument"}
    assert set(function.get_globals()) == {"runtime_global"}
    assert "default_value" not in function.get_identifiers()
    assert "Input" not in function.get_identifiers()
    # def 的装饰器、默认值和 3.10 默认的注解表达式都在定义现场求值，
    # 不属于新建函数 block 的局部名字。


def test_class_table_reports_methods_and_class_body_bindings():
    source = (
        "class Service(Base):\n"
        "    version: int = 1\n"
        "    def run(self):\n"
        "        return self.version\n"
        "    async def stop(self):\n"
        "        return None\n"
        "    alias = run\n"
    )
    class_table = child_named(symtable.symtable(source, "class.py", "exec"), "Service")

    assert isinstance(class_table, symtable.Class)
    assert set(class_table.get_methods()) == {"run", "stop"}
    assert class_table.lookup("version").is_annotated() is True
    assert class_table.lookup("version").is_assigned() is True
    assert class_table.lookup("run").is_namespace() is True
    assert class_table.lookup("alias").is_namespace() is False
    assert class_table.lookup("alias").is_assigned() is True
    assert class_table.lookup("run").is_referenced() is True


def test_class_body_is_not_an_enclosing_lexical_scope_for_methods():
    source = (
        "class Example:\n"
        "    class_value = 42\n"
        "    def read(self):\n"
        "        return class_value\n"
    )
    class_table = child_named(symtable.symtable(source, "class_scope.py", "exec"), "Example")
    method = child_named(class_table, "read")
    class_value = method.lookup("class_value")

    assert class_table.lookup("class_value").is_local() is True
    assert class_value.is_global() is True
    assert class_value.is_free() is False
    # 方法需要 self.class_value、type(self).class_value 或类名才能取类属性；
    # 裸 class_value 不会从类 namespace 形成闭包。


def test_zero_argument_super_creates_an_implicit_class_free_variable():
    source = (
        "class Child(Parent):\n"
        "    def method(self):\n"
        "        return super().method()\n"
    )
    class_table = child_named(symtable.symtable(source, "super.py", "exec"), "Child")
    method = child_named(class_table, "method")

    implicit_class = method.lookup("__class__")
    assert implicit_class.is_free() is True
    assert "__class__" in method.get_frees()
    # 源码没写 __class__，但编译器为零参 super() 创建了隐式 class cell。


def test_namespace_symbol_links_a_definition_to_its_child_table():
    source = (
        "def function():\n"
        "    return 42\n"
        "class Example:\n"
        "    pass\n"
    )
    top = symtable.symtable(source, "namespaces.py", "exec")

    function_symbol = top.lookup("function")
    class_symbol = top.lookup("Example")
    assert function_symbol.is_namespace() is True
    assert class_symbol.is_namespace() is True
    assert function_symbol.get_namespace().get_name() == "function"
    assert function_symbol.get_namespace().get_type() == "function"
    assert class_symbol.get_namespace().get_name() == "Example"
    assert class_symbol.get_namespace().get_type() == "class"
    assert function_symbol.get_namespaces()[0].get_id() == (
        function_symbol.get_namespace().get_id()
    )


def test_one_name_can_bind_multiple_namespaces_and_get_namespace_then_fails():
    source = (
        "def handler():\n"
        "    return 1\n"
        "def handler(value):\n"
        "    return value\n"
    )
    top = symtable.symtable(source, "redefined.py", "exec")
    symbol = top.lookup("handler")
    namespaces = symbol.get_namespaces()

    assert symbol.is_namespace() is True
    assert len(namespaces) == 2
    assert [namespace.get_name() for namespace in namespaces] == [
        "handler",
        "handler",
    ]
    with pytest.raises(ValueError, match="multiple namespaces"):
        symbol.get_namespace()


def test_namespace_flag_can_coexist_with_an_ordinary_rebinding():
    source = (
        "def target():\n"
        "    return 1\n"
        "target = 42\n"
    )
    symbol = symtable.symtable(source, "mixed.py", "exec").lookup("target")

    assert symbol.is_namespace() is True
    assert symbol.is_assigned() is True
    assert len(symbol.get_namespaces()) == 1
    assert symbol.get_namespace().get_type() == "function"
    # is_namespace 表示该名字至少有一次绑定引入 namespace，不保证运行到
    # block 结尾时该名字仍指向函数或类。


def test_lambda_and_comprehension_create_hidden_function_tables():
    source = (
        "transform = lambda value: value + offset\n"
        "results = [item * scale for item in source if item > threshold]\n"
    )
    top = symtable.symtable(source, "implicit_blocks.py", "exec")
    children = {child.get_name(): child for child in top.get_children()}
    lambda_table = children["lambda"]
    listcomp = children["listcomp"]

    assert isinstance(lambda_table, symtable.Function)
    assert lambda_table.get_parameters() == ("value",)
    assert set(lambda_table.get_globals()) == {"offset"}

    assert isinstance(listcomp, symtable.Function)
    assert listcomp.get_parameters() == (".0",)
    assert {".0", "item"} <= set(listcomp.get_locals())
    assert set(listcomp.get_globals()) == {"scale", "threshold"}
    assert top.lookup("source").is_referenced() is True
    # 最外层 iterable ``source`` 在包含式外部先求值；迭代参数以内部名 ``.0``
    # 传入隐式函数，item 不会泄漏回模块域。


def test_comprehension_inside_function_closes_over_function_locals():
    source = (
        "def scale_all(values, factor):\n"
        "    return [value * factor for value in values]\n"
    )
    function = child_named(symtable.symtable(source, "comprehension.py", "exec"), "scale_all")
    listcomp = child_named(function, "listcomp")

    assert listcomp.is_nested() is True
    assert listcomp.get_frees() == ("factor",)
    assert listcomp.lookup("factor").is_free() is True
    assert function.lookup("factor").is_local() is True
    assert "value" not in function.get_identifiers()


def test_identifier_view_symbols_and_lookup_are_consistent_views_of_one_table():
    table = symtable.symtable(
        "first = 1\nsecond = first + missing\n",
        "views.py",
        "exec",
    )
    identifiers = table.get_identifiers()
    symbols = table.get_symbols()

    assert set(identifiers) == {"first", "second", "missing"}
    assert {symbol.get_name() for symbol in symbols} == set(identifiers)
    assert table.lookup("first").get_name() == "first"
    assert table.lookup("missing").is_global() is True
    with pytest.raises(KeyError):
        table.lookup("not_present")


@pytest.mark.parametrize(
    "source",
    [
        "def bad():\n    value = 1\n    global value\n",
        "def bad():\n    nonlocal missing\n",
        "def bad(argument):\n    global argument\n",
    ],
)
def test_symbol_table_generation_runs_scope_declaration_syntax_checks(source):
    with pytest.raises(SyntaxError):
        symtable.symtable(source, "invalid_scope.py", "exec")
    # symtable 不执行用户代码，但它是真实编译管线的一部分，因此 global/
    # nonlocal 的冲突会在生成符号表时就以 SyntaxError 拒绝。
