"""012｜名字绑定、LEGB 作用域与闭包 cell 的可执行示例。

Python 在编译函数代码块时决定名字属于 local、free 还是 global：只要同一函数
中存在赋值，那个名字默认在整个函数体都被视为 local，而不是从赋值行之后才
开始。读取按 Local、Enclosing、Global、Builtins 查找；``global`` 和
``nonlocal`` 则改变赋值目标。闭包保存的是 enclosing cell，默认参数保存的却是
定义时已经求出的对象。

内容基于 Python 3.10 Execution Model 的 Naming and binding、Global /
Nonlocal statements、Comprehensions 和内置 locals/globals。当前项目处于只
编写、暂不执行的阶段，本文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.execution.names-and-binding python.execution.legb
# polyglot-covers: python.statement.global python.statement.nonlocal
# polyglot-covers: python.statement.del-name python.statement.import
# polyglot-covers: python.exception.UnboundLocalError
# polyglot-covers: python.function.closure python.function.cell
# polyglot-covers: python.scope.comprehension python.scope.class-body
# polyglot-covers: python.builtin.locals python.builtin.globals
# polyglot-covers: python.builtin.compile python.builtin.__import__

import builtins

import pytest


_MODULE_COUNTER = 10
_MODULE_LABEL = "module"


def test_assignment_loop_with_except_and_import_create_name_bindings():
    """多种语句都会在当前代码块绑定名称，生命周期却不完全相同。"""

    class ValueContext:
        def __enter__(self):
            return "context-value"

        def __exit__(self, exception_type, exception, traceback):
            return False

    direct = "assignment"
    left, right = (1, 2)

    for loop_item in ["last-loop-value"]:
        pass

    with ValueContext() as context_item:
        pass

    import math as math_module

    try:
        raise ValueError("temporary")
    except ValueError as error:
        error_message = str(error)

    namespace = locals()

    assert namespace["direct"] == "assignment"
    assert (namespace["left"], namespace["right"]) == (1, 2)
    assert namespace["loop_item"] == "last-loop-value"
    assert namespace["context_item"] == "context-value"
    assert namespace["math_module"].sqrt(9) == 3
    assert namespace["error_message"] == "temporary"
    assert "error" not in namespace

    # 普通赋值、解包、for target、with target 和 import alias 都在代码块结束后
    # 保持绑定；except ... as error 的目标则会在处理器末尾主动清除引用。


def test_legb_lookup_finds_local_enclosing_global_and_builtin_names():
    """同一规则按层级查找，最近一层存在绑定就停止。"""

    def outer():
        enclosing_name = "enclosing"

        def inner():
            local_name = "local"
            return local_name, enclosing_name, _MODULE_LABEL, len([1, 2, 3])

        return inner

    read_names = outer()

    assert read_names() == ("local", "enclosing", "module", 3)
    assert read_names.__code__.co_freevars == ("enclosing_name",)


def test_local_binding_shadows_a_builtin_name():
    """Builtins 是最后 fallback，局部同名变量会阻止继续查找。"""

    list = ["this name now refers to an instance"]

    with pytest.raises(TypeError):
        list((1, 2, 3))

    assert builtins.list((1, 2, 3)) == [1, 2, 3]

    # 遮蔽 list、str、id 等内置名称在语法上合法，却让后面的正常调用变成
    # “对象不可调用”等难读错误。builtins 模块能找回原对象，但更好的办法是
    # 从一开始选择不冲突的业务名称。


def test_assignment_makes_a_name_local_for_the_entire_function_block():
    """函数后半段的赋值会让前半段读取也解析为 local。"""

    def increment_incorrectly():
        current = _MODULE_COUNTER
        _MODULE_COUNTER = current + 1
        return _MODULE_COUNTER

    with pytest.raises(UnboundLocalError):
        increment_incorrectly()

    assert _MODULE_COUNTER == 10

    # 编译器看到 `_MODULE_COUNTER = ...` 后，把该函数里的所有同名引用标成
    # local。第一行不是先读 module 值，而是在局部值尚未绑定时读取它。


def test_global_statement_redirects_assignment_to_the_module_binding():
    """``global`` 让函数读写模块命名空间中的同名对象。"""

    global _MODULE_COUNTER
    original = _MODULE_COUNTER

    def increment():
        global _MODULE_COUNTER
        _MODULE_COUNTER += 1
        return _MODULE_COUNTER

    try:
        assert increment() == original + 1
        assert _MODULE_COUNTER == original + 1
        assert globals()["_MODULE_COUNTER"] == original + 1
    finally:
        _MODULE_COUNTER = original

    # 测试恢复 module 状态，避免执行顺序影响其他案例。业务代码也应谨慎修改
    # global 可变状态，因为隐式共享会让并发、重试和测试隔离更困难。


def test_nonlocal_updates_the_nearest_enclosing_function_binding():
    """``nonlocal`` 修改已存在的 enclosing cell，而不是创建新 local。"""

    def make_counter(start=0):
        count = start

        def increment(step=1):
            nonlocal count
            count += step
            return count

        return increment

    counter = make_counter(10)

    assert counter() == 11
    assert counter(4) == 15
    assert counter.__code__.co_freevars == ("count",)
    assert counter.__closure__[0].cell_contents == 15


def test_nonlocal_chooses_nearest_enclosing_binding_not_global():
    """多层嵌套中，nonlocal 选择最近的已绑定函数作用域。"""

    value = "outer"

    def middle():
        value = "middle"

        def change():
            nonlocal value
            value = "changed-middle"

        change()
        return value

    assert middle() == "changed-middle"
    assert value == "outer"


def test_nonlocal_requires_an_existing_enclosing_function_binding():
    """目标不存在或只有 global 绑定时，nonlocal 在编译阶段就是语法错误。"""

    source = """
def outer():
    def inner():
        nonlocal missing
        missing = 1
"""

    with pytest.raises(SyntaxError, match="no binding for nonlocal"):
        compile(source, "<nonlocal-example>", "exec")

    # nonlocal 不能凭空创建 enclosing 名称，也不会退到 module global；外层函数
    # 必须已有相应绑定。


def test_scope_declaration_must_precede_use_in_the_same_code_block():
    """``global`` / ``nonlocal`` 是解析器指令，不能放在同块相关使用之后。"""

    source = """
value = 1
def read_then_declare():
    print(value)
    global value
"""

    with pytest.raises(SyntaxError, match="used prior to global declaration"):
        compile(source, "<global-example>", "exec")


def test_closure_reads_the_current_cell_value_not_a_creation_time_copy():
    """闭包捕获 cell；外层在返回闭包前更新 cell，读取会看到新值。"""

    def make_reader():
        label = "initial"

        def read():
            return label

        label = "updated"
        return read

    reader = make_reader()

    assert reader() == "updated"
    assert reader.__closure__[0].cell_contents == "updated"


def test_default_argument_captures_now_while_closure_name_is_late_bound():
    """默认参数保存定义时对象，自由变量则在每次调用时读取 cell。"""

    def build_functions():
        label = "initial"

        def late_bound():
            return label

        def captured_now(value=label):
            return value

        label = "updated"
        return late_bound, captured_now

    late_bound, captured_now = build_functions()

    assert late_bound() == "updated"
    assert captured_now() == "initial"

    # 这与 006 中循环 lambda 的现象同源：默认值在 def 执行时求值，自由变量
    # 在函数调用时解析。应根据需要选择，而不是把默认参数捕获当成神秘技巧。


def test_comprehension_iteration_variable_has_an_implicit_inner_scope():
    """list/set/dict comprehension 的循环变量不会泄漏到外围代码块。"""

    item = "outer"

    list_values = [item.upper() for item in ["a", "b"]]
    set_values = {item * 2 for item in [1, 2]}
    dict_values = {item: item**2 for item in [2, 3]}

    assert list_values == ["A", "B"]
    assert set_values == {2, 4}
    assert dict_values == {2: 4, 3: 9}
    assert item == "outer"


def test_class_namespace_is_not_an_enclosing_scope_for_method_bodies():
    """方法不能把类体普通名称当作函数 closure 变量直接读取。"""

    class Report:
        label = "class attribute"

        def incorrect(self):
            return label

        def correct(self):
            return self.label

    report = Report()

    assert report.correct() == "class attribute"

    with pytest.raises(NameError):
        report.incorrect()

    # 方法的 lexical enclosing scope 跳过 class namespace。类属性应通过 self、
    # cls 或明确类名读取；点号查找还会正确遵守继承和 descriptor 规则。


def test_del_removes_a_local_binding_and_later_read_is_unbound():
    """``del name`` 删除绑定，不会把变量设置成 ``None``。"""

    def delete_then_read():
        value = "temporary"
        del value
        return value

    with pytest.raises(UnboundLocalError):
        delete_then_read()


def test_locals_and_globals_expose_current_namespace_mappings_for_inspection():
    """两个内置函数适合查阅命名空间，不应作为局部赋值 API。"""

    def inspect_local(alpha):
        beta = alpha * 2
        namespace = locals()
        return namespace["alpha"], namespace["beta"]

    assert inspect_local(3) == (3, 6)
    assert globals()["_MODULE_LABEL"] == "module"
    assert globals()["__name__"] == __name__

    # 官方契约不保证修改 locals() 返回的映射会同步回优化后的函数局部变量。
    # 它适合调试、模板上下文等读取场景；正常赋值应使用明确的名字或数据结构。
