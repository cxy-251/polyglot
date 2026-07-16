"""159｜code 与 codeop：增量编译、解释器状态和自定义 REPL。

交互解释器不能简单地对每行调用 ``compile``：它还要区分完整、尚可补全和
已经错误的输入，缓存多行 suite，并让 ``__future__`` 声明影响后续命令。
``codeop`` 提供这个编译状态机，``code`` 在它上面组合命名空间、异常展示、
提示符和输入循环。本套使用内存输入输出，不启动真实终端。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.codeop python.codeop.compile-command
# polyglot-covers: python.codeop.complete-incomplete-invalid
# polyglot-covers: python.codeop.single-eval-exec-symbols
# polyglot-covers: python.codeop.filename python.codeop.invalid-symbol
# polyglot-covers: python.codeop.compile-class python.codeop.future-memory
# polyglot-covers: python.codeop.command-compiler
# polyglot-covers: python.codeop.command-compiler-incomplete-future
# polyglot-covers: python.stdlib.code python.code.compile-command-alias
# polyglot-covers: python.code.interactive-interpreter
# polyglot-covers: python.code.default-locals python.code.custom-locals
# polyglot-covers: python.code.runsource-return-protocol
# polyglot-covers: python.code.runsource-symbol
# polyglot-covers: python.code.runcode python.code.runtime-error-reporting
# polyglot-covers: python.code.system-exit-propagation
# polyglot-covers: python.code.syntax-error-reporting python.code.filename-rewrite
# polyglot-covers: python.code.traceback-hide-interpreter-frame
# polyglot-covers: python.code.chained-traceback
# polyglot-covers: python.code.write-override
# polyglot-covers: python.code.interactive-console
# polyglot-covers: python.code.console-push-buffer
# polyglot-covers: python.code.console-reset-buffer
# polyglot-covers: python.code.console-raw-input
# polyglot-covers: python.code.console-interact-prompts-banner-exit
# polyglot-covers: python.code.interact-convenience
# polyglot-covers: python.code.expression-displayhook

import __future__
import builtins
import code
import codeop
from io import StringIO
import sys

import pytest


@pytest.fixture(autouse=True)
def use_default_exception_hook(monkeypatch):
    # pytest 会替换 sys.excepthook；InteractiveInterpreter 发现自定义 hook 后会绕过 write()。
    # 恢复默认 hook，准确验证嵌入式终端通过覆盖 write 收集诊断的标准路径。
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)


class RecordingInterpreter(code.InteractiveInterpreter):
    """把解释器诊断收集到列表，模拟编辑器、网页终端等输出面板。"""

    def __init__(self, locals=None):
        super().__init__(locals)
        self.diagnostics = []

    def write(self, data):
        self.diagnostics.append(data)

    @property
    def diagnostic_text(self):
        return "".join(self.diagnostics)


class ScriptedConsole(code.InteractiveConsole):
    """从预设行读取输入，同时记录提示符和所有 write 输出。"""

    def __init__(self, lines, locals=None, filename="<scripted-console>"):
        super().__init__(locals=locals, filename=filename)
        self.lines = iter(lines)
        self.prompts = []
        self.output = []

    def raw_input(self, prompt=""):
        self.prompts.append(prompt)
        try:
            return next(self.lines)
        except StopIteration as error:
            raise EOFError from error

    def write(self, data):
        self.output.append(data)


def test_compile_command_distinguishes_complete_incomplete_and_invalid_input():
    complete = codeop.compile_command("answer = 40 + 2", "lesson.py", "single")
    incomplete = codeop.compile_command("if ready:\n", "lesson.py", "single")

    assert isinstance(complete, type((lambda: None).__code__))
    assert complete.co_filename == "lesson.py"
    assert incomplete is None

    with pytest.raises(SyntaxError):
        codeop.compile_command("if ready print('broken')", "lesson.py", "single")
    # None 不是“编译失败”，而是 REPL 应显示二级提示符并继续收集输入。


def test_compile_command_supports_single_eval_and_exec_grammar_start_symbols(
    monkeypatch,
):
    displayed = []
    monkeypatch.setattr(sys, "displayhook", displayed.append)

    namespace = {}
    single_code = codeop.compile_command("6 * 7", symbol="single")
    eval_code = codeop.compile_command("6 * 7", symbol="eval")
    exec_code = codeop.compile_command("left = 20\nright = 22", symbol="exec")

    exec(single_code, namespace)
    assert displayed == [42]
    assert eval(eval_code, namespace) == 42
    exec(exec_code, namespace)
    assert namespace["left"] + namespace["right"] == 42
    # single 为交互模式，会为顶层表达式生成 displayhook 调用；exec 不会。


def test_compile_command_rejects_unknown_grammar_symbol():
    with pytest.raises(ValueError, match="mode must be"):
        codeop.compile_command("answer = 42", symbol="statement-list")


def test_code_module_reexports_the_same_incremental_compile_function():
    assert code.compile_command is codeop.compile_command
    compiled = code.compile_command("value = 3", "console-cell-7", "exec")
    assert compiled.co_filename == "console-cell-7"


def test_compile_instance_remembers_future_flags_for_later_complete_units():
    compiler = codeop.Compile()
    future_code = compiler(
        "from __future__ import annotations\n",
        "cell-1",
        "exec",
    )
    function_code = compiler(
        "def parse(value: MissingType) -> list[MissingType]:\n"
        "    return [value]\n",
        "cell-2",
        "exec",
    )
    namespace = {}
    exec(future_code, namespace)
    exec(function_code, namespace)

    assert function_code.co_flags & __future__.annotations.compiler_flag
    assert namespace["parse"].__annotations__ == {
        "value": "MissingType",
        "return": "list[MissingType]",
    }


def test_separate_compile_instances_do_not_share_future_state():
    future_aware = codeop.Compile()
    ordinary = codeop.Compile()
    future_aware("from __future__ import annotations\n", "cell", "exec")

    future_code = future_aware("value: MissingType = None\n", "cell", "exec")
    ordinary_code = ordinary("value: MissingType = None\n", "cell", "exec")
    assert future_code.co_flags & __future__.annotations.compiler_flag
    assert not ordinary_code.co_flags & __future__.annotations.compiler_flag

    namespace = {}
    exec(future_code, namespace)
    with pytest.raises(NameError, match="MissingType"):
        exec(ordinary_code, {})


def test_command_compiler_combines_incomplete_detection_with_future_memory():
    compiler = codeop.CommandCompiler()
    assert compiler("def parse(value):\n", "cell-1", "single") is None

    future_code = compiler(
        "from __future__ import annotations\n",
        "cell-2",
        "single",
    )
    later_code = compiler(
        "def convert(value: MissingType):\n"
        "    return value\n",
        "cell-3",
        "exec",
    )
    namespace = {}
    exec(future_code, namespace)
    exec(later_code, namespace)
    assert namespace["convert"].__annotations__ == {"value": "MissingType"}


def test_interactive_interpreter_default_namespace_has_console_identity():
    interpreter = code.InteractiveInterpreter()
    assert interpreter.locals["__name__"] == "__console__"
    assert interpreter.locals["__doc__"] is None

    other = code.InteractiveInterpreter()
    interpreter.locals["answer"] = 42
    assert "answer" not in other.locals


def test_interactive_interpreter_executes_in_the_supplied_live_mapping():
    namespace = {"seed": 40}
    interpreter = RecordingInterpreter(namespace)
    needs_more = interpreter.runsource("answer = seed + 2", "cell-1", "exec")

    assert needs_more is False
    assert interpreter.locals is namespace
    assert namespace["answer"] == 42
    assert interpreter.diagnostics == []


def test_runsource_boolean_selects_primary_or_continuation_prompt():
    interpreter = RecordingInterpreter()

    assert interpreter.runsource("for value in range(2):") is True
    assert interpreter.runsource("answer = 42") is False
    assert interpreter.locals["answer"] == 42

    assert interpreter.runsource("if True print('broken')") is False
    assert "SyntaxError" in interpreter.diagnostic_text


def test_runsource_eval_returns_complete_and_uses_displayhook(monkeypatch):
    displayed = []
    monkeypatch.setattr(sys, "displayhook", displayed.append)
    interpreter = RecordingInterpreter({"value": 21})

    assert interpreter.runsource("value * 2", symbol="single") is False
    assert displayed == [42]
    assert interpreter.diagnostics == []


def test_runcode_reports_runtime_exception_without_propagating_it():
    interpreter = RecordingInterpreter()
    compiled = compile("10 / 0", "runtime-cell", "exec")

    result = interpreter.runcode(compiled)
    assert result is None
    assert "ZeroDivisionError: division by zero" in interpreter.diagnostic_text
    assert 'File "runtime-cell", line 1' in interpreter.diagnostic_text


def test_runcode_allows_system_exit_to_escape_to_the_embedding_application():
    interpreter = RecordingInterpreter()
    compiled = compile("raise SystemExit(7)", "exit-cell", "exec")

    with pytest.raises(SystemExit) as captured:
        interpreter.runcode(compiled)
    assert captured.value.code == 7
    assert interpreter.diagnostics == []
    # 嵌入程序必须决定“退出当前 REPL”“关闭文档”还是“退出整个
    # 进程”。


def test_runtime_traceback_hides_the_interpreter_implementation_frame():
    interpreter = RecordingInterpreter()
    compiled = compile(
        "def fail():\n"
        "    raise LookupError('missing')\n"
        "fail()\n",
        "user-cell",
        "exec",
    )
    interpreter.runcode(compiled)

    diagnostic = interpreter.diagnostic_text
    assert diagnostic.count('File "user-cell"') == 2
    assert "in runcode" not in diagnostic
    assert "LookupError: missing" in diagnostic


def test_runtime_traceback_preserves_explicit_exception_chaining():
    interpreter = RecordingInterpreter()
    compiled = compile(
        "try:\n"
        "    int('bad')\n"
        "except ValueError as error:\n"
        "    raise RuntimeError('conversion failed') from error\n",
        "chain-cell",
        "exec",
    )
    interpreter.runcode(compiled)

    diagnostic = interpreter.diagnostic_text
    assert "ValueError" in diagnostic
    assert "direct cause" in diagnostic
    assert "RuntimeError: conversion failed" in diagnostic


def test_syntax_error_uses_requested_filename_without_a_runtime_stack():
    interpreter = RecordingInterpreter()
    assert interpreter.runsource("value = (1 + )", "editor-cell-9") is False

    diagnostic = interpreter.diagnostic_text
    assert 'File "editor-cell-9", line 1' in diagnostic
    assert "SyntaxError" in diagnostic
    assert "Traceback (most recent call last)" not in diagnostic


def test_write_default_targets_stderr_and_override_can_route_elsewhere(monkeypatch):
    standard_error = StringIO()
    monkeypatch.setattr(sys, "stderr", standard_error)
    ordinary = code.InteractiveInterpreter()
    ordinary.write("ordinary diagnostic")
    assert standard_error.getvalue() == "ordinary diagnostic"

    recording = RecordingInterpreter()
    recording.write("panel diagnostic")
    assert recording.diagnostic_text == "panel diagnostic"


def test_console_push_buffers_a_compound_statement_until_a_blank_line():
    console = ScriptedConsole([], locals={"total": 0})

    assert console.push("for value in range(4):") is True
    assert console.push("    total += value") is True
    assert console.locals["total"] == 0
    assert console.push("") is False
    assert console.locals["total"] == 6
    assert console.buffer == []


def test_console_push_resets_buffer_after_syntax_error():
    console = ScriptedConsole([])
    assert console.push("if True:") is True
    assert console.buffer == ["if True:"]

    assert console.push("not indented") is False
    assert console.buffer == []
    assert "IndentationError" in "".join(console.output)


def test_resetbuffer_discards_an_abandoned_partial_command():
    console = ScriptedConsole([])
    assert console.push("def unfinished():") is True
    assert console.buffer

    console.resetbuffer()
    assert console.buffer == []
    assert console.push("answer = 42") is False
    assert console.locals["answer"] == 42


def test_raw_input_delegates_to_builtin_input_and_strips_newline(monkeypatch):
    prompts = []

    def fake_input(prompt):
        prompts.append(prompt)
        return "answer = 42"

    monkeypatch.setattr(builtins, "input", fake_input)
    console = code.InteractiveConsole()
    assert console.raw_input("primary> ") == "answer = 42"
    assert prompts == ["primary> "]


def test_console_interact_selects_prompts_and_prints_banner_and_exit_message(
    monkeypatch,
):
    displayed = []
    monkeypatch.setattr(sys, "displayhook", displayed.append)
    monkeypatch.setattr(sys, "ps1", ">>> ", raising=False)
    monkeypatch.setattr(sys, "ps2", "... ", raising=False)
    console = ScriptedConsole(
        [
            "total = 0",
            "for value in range(3):",
            "    total += value",
            "",
            "total",
        ]
    )
    console.interact(banner="Teaching Console", exitmsg="Session closed")

    assert console.prompts == [">>> ", ">>> ", "... ", "... ", ">>> ", ">>> "]
    assert displayed == [3]
    output = "".join(console.output)
    assert "Teaching Console" in output
    assert "Session closed" in output


def test_empty_banner_and_exit_message_suppress_decorative_output(monkeypatch):
    monkeypatch.setattr(sys, "ps1", ">>> ", raising=False)
    monkeypatch.setattr(sys, "ps2", "... ", raising=False)
    console = ScriptedConsole([])
    console.interact(banner="", exitmsg="")
    assert console.prompts == [">>> "]
    assert "".join(console.output) == "\n"


def test_code_interact_convenience_forwards_reader_namespace_and_messages(
    monkeypatch,
):
    calls = {}

    class FakeConsole:
        def __init__(self, local):
            calls["local"] = local
            calls["console"] = self

        def interact(self, banner=None, exitmsg=None):
            calls["banner"] = banner
            calls["exitmsg"] = exitmsg

    lines = iter(["answer = 42"])

    def reader(prompt):
        return next(lines)

    monkeypatch.setattr(code, "InteractiveConsole", FakeConsole)
    namespace = {"seed": 40}
    result = code.interact(
        banner="Embedded",
        readfunc=reader,
        local=namespace,
        exitmsg="Done",
    )

    assert result is None
    assert calls["local"] is namespace
    assert calls["banner"] == "Embedded"
    assert calls["exitmsg"] == "Done"
    assert calls["console"].raw_input is reader
