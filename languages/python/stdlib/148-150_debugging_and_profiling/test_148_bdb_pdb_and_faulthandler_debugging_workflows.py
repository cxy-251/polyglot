"""148｜bdb、pdb 与 faulthandler：可编程调试、交互命令和故障栈。

``bdb`` 提供基于 ``sys.settrace`` 的调试器骨架，``pdb`` 在其上叠加命令循环，
``faulthandler`` 则在解释器故障或超时场景用更受限但更可靠的方式写出栈。
案例使用内存命令流和临时日志，不进入人工交互，也不制造真正的崩溃。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.bdb python.bdb.breakpoint
# polyglot-covers: python.bdb.breakpoint-enable-disable-delete
# polyglot-covers: python.bdb.breakpoint-condition-ignore-hits-format
# polyglot-covers: python.bdb.effective python.bdb.condition-evaluation-fallback
# polyglot-covers: python.bdb.breakpoint-global-indexes
# polyglot-covers: python.bdb.canonic python.bdb.skip-module-patterns
# polyglot-covers: python.bdb.set-break python.bdb.get-breaks
# polyglot-covers: python.bdb.clear-break python.bdb.breakpoint-validation
# polyglot-covers: python.bdb.run python.bdb.runeval python.bdb.runcall
# polyglot-covers: python.bdb.user-line python.bdb.set-continue
# polyglot-covers: python.bdb.get-stack python.bdb.format-stack-entry
# polyglot-covers: python.bdb.set-quit python.bdb.bdb-quit
# polyglot-covers: python.stdlib.pdb python.pdb.pdb-class
# polyglot-covers: python.pdb.stdin-stdout-command-loop python.pdb.runcall
# polyglot-covers: python.pdb.print-command python.pdb.continue-command
# polyglot-covers: python.pdb.alias-command python.pdb.alias-substitution
# polyglot-covers: python.pdb.post-mortem python.pdb.where-command
# polyglot-covers: python.pdb.frame-expression-evaluation
# polyglot-covers: python.pdb.readrc-boundary python.pdb.arbitrary-code-warning
# polyglot-covers: python.stdlib.faulthandler python.faulthandler.dump-traceback
# polyglot-covers: python.faulthandler.enable-disable-is-enabled
# polyglot-covers: python.faulthandler.file-descriptor-lifetime
# polyglot-covers: python.faulthandler.dump-traceback-later-cancel
# polyglot-covers: python.faulthandler.register-unregister-user-signal
# polyglot-covers: python.faulthandler.output-limitations

import bdb
import faulthandler
from io import StringIO
import os
from pathlib import Path
import pdb
import signal
import sys

import pytest


def debugger_target(value):
    doubled = value * 2
    return doubled + 1


def crashing_target(numerator, denominator):
    quotient = numerator / denominator
    return quotient


class RecordingDebugger(bdb.Bdb):
    """在第一次 line 事件记录状态后继续，避免进入人工命令循环。"""

    def __init__(self, **options):
        super().__init__(**options)
        self.events = []
        self.stack_text = None

    def user_line(self, frame):
        stack, index = self.get_stack(frame, None)
        self.events.append(
            {
                "function": frame.f_code.co_name,
                "line": frame.f_lineno,
                "locals": frame.f_locals.copy(),
                "stack_depth": len(stack),
                "selected_index": index,
            }
        )
        self.stack_text = self.format_stack_entry(stack[index])
        self.set_continue()

    def do_clear(self, arg):
        self.clear_bpbynumber(arg)


def make_pdb(commands):
    output = StringIO()
    debugger = pdb.Pdb(
        stdin=StringIO(commands),
        stdout=output,
        nosigint=True,
        readrc=False,
    )
    debugger.use_rawinput = False
    return debugger, output


def evaluate_breakpoint_sequence(condition, *, ignore=0, attempts=2, local_value=1):
    """让同一 source line 多次经过 effective，暴露条件和 ignore 状态机。"""

    frame = sys._getframe()
    filename = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
    # funcname breakpoint 首次命中时记住真正可执行行，
    # 因此无需硬编码本文件行号。
    breakpoint = bdb.Breakpoint(
        filename,
        999_999,
        temporary=True,
        cond=condition,
        funcname=frame.f_code.co_name,
    )
    breakpoint.ignore = ignore
    outcomes = []
    try:
        for _ in range(attempts):
            outcomes.append(bdb.effective(filename, breakpoint.line, frame))
        return breakpoint, outcomes
    finally:
        breakpoint.deleteMe()


def test_breakpoint_tracks_global_indexes_state_and_formatting():
    filename = os.path.normcase(os.path.abspath("debugger-example.py"))
    breakpoint = bdb.Breakpoint(
        filename,
        12,
        temporary=True,
        cond="value > 3",
        funcname="work",
    )
    try:
        assert breakpoint.file == filename
        assert breakpoint.line == 12
        assert breakpoint.temporary is True
        assert breakpoint.cond == "value > 3"
        assert breakpoint.funcname == "work"
        assert breakpoint.enabled is True
        assert bdb.Breakpoint.bpbynumber[breakpoint.number] is breakpoint
        assert breakpoint in bdb.Breakpoint.bplist[(filename, 12)]

        breakpoint.ignore = 2
        breakpoint.hits = 5
        formatted = breakpoint.bpformat()
        assert f"{breakpoint.number}" in formatted
        assert "del" in formatted
        assert "value > 3" in formatted
        assert "ignore next 2 hits" in formatted
        assert "breakpoint already hit 5 times" in formatted

        breakpoint.disable()
        assert breakpoint.enabled is False
        breakpoint.enable()
        assert breakpoint.enabled is True
    finally:
        breakpoint.deleteMe()

    assert bdb.Breakpoint.bpbynumber[breakpoint.number] is None
    assert (filename, 12) not in bdb.Breakpoint.bplist


def test_effective_breakpoint_applies_conditions_ignore_counts_and_fallbacks():
    breakpoint, outcomes = evaluate_breakpoint_sequence(
        "local_value > 0",
        ignore=1,
    )
    assert outcomes[0] == (None, None)
    assert outcomes[1] == (breakpoint, True)
    assert breakpoint.hits == 2
    assert breakpoint.ignore == 0

    false_breakpoint, false_outcomes = evaluate_breakpoint_sequence(
        "local_value < 0",
        ignore=1,
    )
    assert false_outcomes == [(None, None), (None, None)]
    assert false_breakpoint.hits == 2
    # condition 为 False 时甚至没有形成“可忽略的一次命中”，
    # 所以 ignore 不递减。
    assert false_breakpoint.ignore == 1

    broken, broken_outcomes = evaluate_breakpoint_sequence(
        "name_that_does_not_exist",
        attempts=1,
    )
    assert broken_outcomes == [(broken, False)]
    # 条件求值异常时宁可停下，但返回 False 告诉 Bdb
    # 不要自动删除 temporary bp，方便用户检查错误条件。


def test_bdb_canonicalizes_real_paths_but_preserves_pseudo_filenames(tmp_path):
    debugger = bdb.Bdb(skip=["vendor.*", "generated_module"])
    relative = tmp_path / "nested" / ".." / "script.py"

    assert debugger.canonic("<string>") == "<string>"
    assert debugger.canonic("<stdin>") == "<stdin>"
    assert debugger.canonic(str(relative)) == os.path.normcase(
        os.path.abspath(relative)
    )
    assert debugger.is_skipped_module("vendor.parser") is True
    assert debugger.is_skipped_module("generated_module") is True
    assert debugger.is_skipped_module("application.service") is False


def test_bdb_validates_sets_queries_and_clears_source_breakpoints(tmp_path):
    source = tmp_path / "debuggee.py"
    source.write_text("value = 1\nvalue += 2\n", encoding="utf-8")
    debugger = bdb.Bdb()
    canonical = debugger.canonic(str(source))

    assert debugger.set_break(str(source), 2, cond="value == 1") is None
    try:
        assert debugger.get_break(canonical, 2) is True
        breakpoints = debugger.get_breaks(canonical, 2)
        assert len(breakpoints) == 1
        assert breakpoints[0].cond == "value == 1"
        assert debugger.get_file_breaks(canonical) == [2]
        assert debugger.get_all_breaks() == {canonical: [2]}
        assert debugger.get_bpbynumber(str(breakpoints[0].number)) is breakpoints[0]

        # set_break 只接受 linecache 能从真实文件读到的行；失败以字符串返回，
        # 而不是抛出异常。
        error = debugger.set_break(str(source), 99)
        assert f"{source}:99" in error
        assert "does not exist" in error
    finally:
        debugger.clear_break(canonical, 2)

    assert debugger.get_breaks(canonical, 2) == []
    missing = debugger.clear_break(canonical, 2)
    assert missing.startswith("There are no breakpoints ")
    assert canonical in missing


def test_bdb_runcall_records_frame_stack_and_returns_function_result():
    debugger = RecordingDebugger()
    result = debugger.runcall(debugger_target, 4)

    assert result == 9
    assert len(debugger.events) == 1
    event = debugger.events[0]
    assert event["function"] == "debugger_target"
    assert event["locals"] == {"value": 4}
    assert event["stack_depth"] >= 1
    assert event["selected_index"] == event["stack_depth"] - 1
    assert "debugger_target" in debugger.stack_text
    assert __file__ in debugger.stack_text


def test_bdb_run_and_runeval_use_explicit_namespaces():
    debugger = RecordingDebugger()
    globals_namespace = {"factor": 3}
    locals_namespace = {"value": 7}

    debugger.run(
        "result = value * factor",
        globals_namespace,
        locals_namespace,
    )
    assert locals_namespace["result"] == 21

    evaluator = RecordingDebugger()
    assert evaluator.runeval(
        "value + factor",
        globals_namespace,
        locals_namespace,
    ) == 10
    assert evaluator.events[0]["function"] == "<module>"


def test_set_quit_turns_the_next_dispatch_into_bdbquit():
    debugger = bdb.Bdb()
    debugger.reset()
    debugger.set_quit()

    with pytest.raises(bdb.BdbQuit):
        debugger.dispatch_line(sys._getframe())


def test_pdb_runcall_reads_commands_from_injected_streams():
    debugger, output = make_pdb("p value\ncontinue\n")

    result = debugger.runcall(debugger_target, 3)
    transcript = output.getvalue()

    assert result == 7
    assert "debugger_target" in transcript
    assert "-> doubled = value * 2" in transcript
    assert "3" in transcript
    assert "(Pdb)" in transcript

    # readrc=False 防止用户目录中的 .pdbrc 改写命令；生产工具若选择读取 rc，
    # 必须把它视为会执行 debugger commands 乃至任意 Python 表达式的代码配置。


def test_pdb_aliases_expand_positional_arguments_before_dispatch():
    debugger, _ = make_pdb("")

    assert debugger.onecmd("alias double p %1 * 2") is None
    assert debugger.aliases["double"] == "p %1 * 2"
    assert debugger.precmd("double 6") == "p 6 * 2"

    debugger.onecmd("unalias double")
    assert "double" not in debugger.aliases


def test_pdb_post_mortem_navigates_traceback_and_evaluates_frame_locals():
    try:
        crashing_target(10, 0)
    except ZeroDivisionError:
        traceback = sys.exc_info()[2]
    else:
        raise AssertionError("the teaching target must fail")

    debugger, output = make_pdb("where\np numerator\np denominator\nquit\n")
    debugger.reset()
    debugger.interaction(None, traceback)
    transcript = output.getvalue()

    assert "crashing_target" in transcript
    assert "quotient = numerator / denominator" in transcript
    assert "10" in transcript
    assert "0" in transcript


def test_faulthandler_dump_traceback_writes_a_minimal_fd_based_stack(tmp_path):
    output = tmp_path / "fault-stack.log"
    with output.open("w", encoding="ascii", errors="backslashreplace") as stream:
        faulthandler.dump_traceback(file=stream, all_threads=False)
        stream.flush()

    text = output.read_text(encoding="ascii")
    assert "Stack (most recent call first):" in text
    assert Path(__file__).name in text
    assert "test_faulthandler_dump_traceback" in text
    # 故障处理器只保证 ASCII、文件名/函数名/行号，最多 100 frames/threads，
    # 顺序还是最近调用在前；需要源码行和丰富异常信息时应使用 traceback。


def test_faulthandler_enable_disable_owns_the_output_descriptor(tmp_path):
    if faulthandler.is_enabled():
        pytest.skip("do not replace a handler configured by the outer test process")

    output = tmp_path / "fatal-errors.log"
    with output.open("w", encoding="ascii") as stream:
        faulthandler.enable(file=stream, all_threads=False)
        try:
            assert faulthandler.is_enabled() is True
        finally:
            # 必须在关闭/复用 stream 的 fd 前禁用；
            # faulthandler 保存的是 descriptor，
            # 并不会持有一个能感知 Python file object 生命周期的高级包装器。
            faulthandler.disable()

    assert faulthandler.is_enabled() is False


def test_faulthandler_delayed_dump_can_be_cancelled_without_waiting(tmp_path):
    output = tmp_path / "later.log"
    with output.open("w", encoding="ascii") as stream:
        faulthandler.dump_traceback_later(
            60,
            repeat=True,
            file=stream,
            exit=False,
        )
        try:
            assert faulthandler.cancel_dump_traceback_later() is None
        finally:
            # cancel 是幂等清理，保证断言异常时也不会留下 process-global timer。
            faulthandler.cancel_dump_traceback_later()

    assert output.read_text(encoding="ascii") == ""


@pytest.mark.skipif(not hasattr(signal, "SIGUSR1"), reason="requires a user signal")
def test_faulthandler_registers_and_unregisters_a_user_signal(tmp_path):
    output = tmp_path / "signal-stack.log"
    signum = signal.SIGUSR1
    previous = signal.getsignal(signum)

    with output.open("w", encoding="ascii") as stream:
        faulthandler.register(signum, file=stream, all_threads=False, chain=False)
        try:
            os.kill(os.getpid(), signum)
            stream.flush()
        finally:
            assert faulthandler.unregister(signum) is True
            signal.signal(signum, previous)

    text = output.read_text(encoding="ascii")
    assert "Stack (most recent call first):" in text
    assert "test_faulthandler_registers" in text
    assert faulthandler.unregister(signum) is False
