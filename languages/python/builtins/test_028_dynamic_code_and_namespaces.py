"""028｜``compile`` / ``eval`` / ``exec`` 与 globals/locals 命名空间示例。

compile 把源码或 AST 变为 code object；eval 求表达式值，exec 执行 statement suite。
它们可以显式接收 global/local 命名空间，但这不是安全沙箱：动态代码仍是程序代码，
不得直接接受不可信用户输入。

SyntaxError、词法作用域和 import 机制已在 009、012、018 展示；本文件聚焦动态
代码入口的正常工作流。内容基于 Python 3.10 Built-in Functions、Execution
Model 和 ast.literal_eval；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.builtin.compile python.builtin.eval python.builtin.exec
# polyglot-covers: python.builtin.globals python.builtin.locals
# polyglot-covers: python.compile.mode python.compile.flags python.compile.optimize
# polyglot-covers: python.eval.namespaces python.exec.namespaces
# polyglot-covers: python.dynamic-code.builtins-injection
# polyglot-covers: python.dynamic-code.separate-globals-locals
# polyglot-covers: python.ast.literal-eval python.dynamic-code.security-boundary

import ast
import types

import pytest


def test_compile_eval_code_object_can_be_reused_with_different_data():
    """规则文本只编译一次，随后可在多个受控命名空间中求值。"""

    expression = compile(
        "price * quantity",
        "<pricing-rule>",
        "eval",
    )

    assert isinstance(expression, types.CodeType)
    assert expression.co_filename == "<pricing-rule>"
    assert eval(expression, {}, {"price": 12, "quantity": 3}) == 36
    assert eval(expression, {}, {"price": 5, "quantity": 4}) == 20

    # 高频规则应复用 code object，避免为每条数据重复词法分析和编译。


def test_compile_modes_match_expression_suite_or_single_interactive_statement():
    """eval 模式只接收表达式；exec 接收 suite；single 面向一条交互式 statement。"""

    expression = compile("1 + 2", "<expr>", "eval")
    suite = compile("value = 3\nresult = value * 2", "<suite>", "exec")
    single = compile("answer = 42", "<single>", "single")

    assert eval(expression) == 3

    suite_namespace = {}
    assert exec(suite, suite_namespace) is None
    assert suite_namespace["result"] == 6

    single_namespace = {}
    assert exec(single, single_namespace) is None
    assert single_namespace["answer"] == 42

    with pytest.raises(SyntaxError):
        compile("value = 1", "<not-expression>", "eval")

    with pytest.raises(ValueError, match=r"compile\(\) mode"):
        compile("1 + 2", "<bad-mode>", "other")

    # single 中的裸表达式会走交互式 displayhook；普通程序生成代码通常用 eval/exec。


def test_compile_accepts_encoded_bytes_and_respects_source_cookie():
    """bytes 源码可用编码声明解释；没有协议需求时普通 str 更清楚。"""

    source = b"# coding: latin-1\nlabel = 'caf\xe9'\n"
    code = compile(source, "<latin1-source>", "exec")
    namespace = {}

    exec(code, namespace)

    assert namespace["label"] == "café"


def test_compile_accepts_ast_and_only_ast_flag_can_stop_before_code_generation():
    """AST 可先检查/转换再编译；PyCF_ONLY_AST 直接返回语法树。"""

    parsed = ast.parse("value + 1", mode="eval")
    code = compile(parsed, "<ast-expression>", "eval")

    assert eval(code, {}, {"value": 4}) == 5

    tree_only = compile(
        "value + 1",
        "<tree-only>",
        "eval",
        flags=ast.PyCF_ONLY_AST,
        dont_inherit=True,
    )

    assert isinstance(tree_only, ast.Expression)
    assert isinstance(tree_only.body, ast.BinOp)

    # AST 允许做结构检查，但自己拼接/修改树仍需正确位置信息和完整安全审计。


def test_compile_optimize_changes_debug_and_assert_semantics():
    """显式 optimize 等级会改变 ``__debug__``，并在非零等级移除 assert。"""

    normal_debug = compile("__debug__", "<normal>", "eval", optimize=0)
    optimized_debug = compile("__debug__", "<optimized>", "eval", optimize=1)

    assert eval(normal_debug) is True
    assert eval(optimized_debug) is False

    optimized_suite = compile(
        "assert False, 'removed'\nresult = 42",
        "<optimized-suite>",
        "exec",
        optimize=1,
    )
    namespace = {}
    exec(optimized_suite, namespace)

    assert namespace["result"] == 42

    # assert 不能承担输入校验、安全检查或不可移除的业务约束。


def test_compile_error_uses_supplied_filename_and_source_location():
    """有意义的 filename 会进入 SyntaxError/traceback，便于定位动态规则来源。"""

    with pytest.raises(SyntaxError) as captured:
        compile("if True print('broken')", "rules/customer_42.py", "exec")

    error = captured.value
    assert error.filename == "rules/customer_42.py"
    assert error.lineno == 1

    with pytest.raises(ValueError, match="null bytes"):
        compile("value = 1\x00", "<null-byte>", "exec")


def test_eval_returns_expression_value_and_rejects_assignment_statement():
    """eval 是表达式入口；赋值等 statement 应由 exec 执行。"""

    assert eval("(2 + 3) * 4") == 20

    with pytest.raises(SyntaxError):
        eval("value = 20")

    namespace = {}
    assert exec("value = 20", namespace) is None
    assert namespace["value"] == 20


def test_eval_resolves_locals_before_globals_for_regular_names():
    """显式 locals 可补充或遮蔽 globals 中的普通名称。"""

    global_namespace = {"base": 10, "increment": 100}
    local_namespace = {"increment": 2}

    assert eval(
        "base + increment",
        global_namespace,
        local_namespace,
    ) == 12

    assert global_namespace["increment"] == 100
    assert local_namespace["increment"] == 2


def test_eval_and_exec_insert_builtins_when_globals_omits_it():
    """globals 没有 ``__builtins__`` 时，解释器会在执行前插入 builtins dict。"""

    namespace = {}

    assert eval("len([1, 2, 3])", namespace) == 3
    assert "__builtins__" in namespace
    assert namespace["__builtins__"]["len"] is len

    # 自动插入会修改传入 dict；复用命名空间前应知道其中不再只有业务变量。


def test_explicit_builtins_mapping_controls_lookup_but_is_not_a_security_sandbox():
    """可收窄方便脚本能直接访问的名称，但不能据此宣称不可信代码安全。"""

    restricted = {"__builtins__": {"len": len}}

    assert eval("len([1, 2])", restricted) == 2

    with pytest.raises(NameError):
        eval("sum([1, 2])", restricted)

    without_builtins = {"__builtins__": {}}
    assert eval("value + 1", without_builtins, {"value": 4}) == 5

    # Python 对象图、资源消耗和可达能力非常复杂；字典删名不是隔离边界。不可信
    # 代码需要独立进程/容器、资源限制和经过设计的通信协议。


def test_exec_code_object_writes_definitions_and_returns_none():
    """exec 执行 suite，并把赋值、函数定义等结果写入给定命名空间。"""

    source = """
factor = 3

def scale(value):
    return value * factor
"""
    code = compile(source, "<scaler>", "exec")
    namespace = {}

    returned = exec(code, namespace)

    assert returned is None
    assert namespace["factor"] == 3
    assert namespace["scale"](4) == 12


def test_exec_with_one_namespace_uses_it_for_both_global_and_local_names():
    """只传 globals 时，顶层赋值和函数 global 查找共享同一个 dict。"""

    namespace = {}
    exec(
        "factor = 3\ndef scale(value):\n    return value * factor",
        namespace,
    )

    assert namespace["scale"](4) == 12
    namespace["factor"] = 5
    assert namespace["scale"](4) == 20


def test_exec_with_separate_namespaces_binds_function_globals_only_to_globals():
    """分离 globals/locals 时，顶层定义写入 locals，函数全局查找仍使用 globals。"""

    global_namespace = {}
    local_namespace = {}

    exec(
        "factor = 3\ndef scale(value):\n    return value * factor",
        global_namespace,
        local_namespace,
    )

    assert local_namespace["factor"] == 3
    assert callable(local_namespace["scale"])

    with pytest.raises(NameError, match="factor"):
        local_namespace["scale"](4)

    global_namespace["factor"] = 5
    assert local_namespace["scale"](4) == 20

    # 这种执行接近 class body：顶层 local 赋值不是函数的 closure/global。


def test_exec_locals_can_be_custom_mapping_while_globals_must_be_dict():
    """locals 可为 mapping；globals 必须是真正 dict，并承载函数全局环境。"""

    class TrackingLocals(dict):
        def __init__(self):
            super().__init__()
            self.writes = []

        def __setitem__(self, key, value):
            self.writes.append(key)
            super().__setitem__(key, value)

    local_namespace = TrackingLocals()
    exec("first = 1\nsecond = 2", {}, local_namespace)

    assert local_namespace == {"first": 1, "second": 2}
    assert local_namespace.writes == ["first", "second"]

    with pytest.raises(TypeError):
        exec("value = 1", [], {})


def test_globals_returns_current_module_namespace_dictionary():
    """globals() 是当前模块真实全局 dict，同一执行上下文重复调用返回同一对象。"""

    namespace = globals()

    assert namespace is globals()
    assert namespace["__name__"] == __name__
    assert namespace["test_globals_returns_current_module_namespace_dictionary"] is (
        test_globals_returns_current_module_namespace_dictionary
    )

    # 修改 globals 会真实改模块状态；测试中只读取，避免把临时名称泄漏给其他案例。


def test_locals_exposes_function_arguments_and_current_local_bindings_for_reading():
    """函数内 locals 可用于诊断/模板读取，但不应通过修改 mapping 来写 fast locals。"""

    def capture(value):
        doubled = value * 2
        snapshot = locals()
        return snapshot

    namespace = capture(5)

    assert namespace["value"] == 5
    assert namespace["doubled"] == 10

    # Python 3.10 对优化函数局部 mapping 的写回没有可依赖语义；显式变量/参数才是 API。


def test_ast_literal_eval_accepts_literals_but_rejects_calls_and_names():
    """literal_eval 解析有限字面量结构，不执行函数调用或普通变量查找。"""

    value = ast.literal_eval(
        "{'enabled': True, 'ports': [8000, 8001], 'missing': None}"
    )

    assert value == {
        "enabled": True,
        "ports": [8000, 8001],
        "missing": None,
    }

    with pytest.raises(ValueError):
        ast.literal_eval("len([1, 2])")

    with pytest.raises(ValueError):
        ast.literal_eval("unknown_name")

    # literal_eval 比 eval 能力窄，但恶意巨大/深层输入仍可能耗尽内存或 C 栈；外部输入
    # 仍应设置长度、深度和资源限制。
