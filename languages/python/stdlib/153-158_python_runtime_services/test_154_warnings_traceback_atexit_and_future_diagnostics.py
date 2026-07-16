"""154｜warnings、traceback、atexit 与 __future__：诊断、退出和语义开关。

警告和异常栈都是“报告问题但保留上下文”的机制，``atexit`` 则描述正常
解释器退出时的清理顺序。``__future__`` 展示编译期语义开关怎样被记录
并传给 ``compile``。警告过滤器和退出函数均是进程级状态，案例分别使用
上下文恢复和
子解释器隔离，避免影响其他测试。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.warnings python.warnings.warn
# polyglot-covers: python.warnings.categories python.warnings.category-hierarchy
# polyglot-covers: python.warnings.filter-actions python.warnings.filter-precedence
# polyglot-covers: python.warnings.filter-message-module-line
# polyglot-covers: python.warnings.default-once-module-registry
# polyglot-covers: python.warnings.catch-warnings python.warnings.simplefilter
# polyglot-covers: python.warnings.stacklevel python.warnings.source
# polyglot-covers: python.warnings.warn-explicit python.warnings.registry
# polyglot-covers: python.warnings.showwarning python.warnings.formatwarning
# polyglot-covers: python.warnings.warning-message
# polyglot-covers: python.stdlib.traceback python.traceback.print-exc
# polyglot-covers: python.traceback.format-exc python.traceback.extract-tb
# polyglot-covers: python.traceback.walk-tb python.traceback.format-list
# polyglot-covers: python.traceback.positive-negative-limit
# polyglot-covers: python.traceback.traceback-exception
# polyglot-covers: python.traceback.exception-cause-context-suppression
# polyglot-covers: python.traceback.stack-summary python.traceback.frame-summary
# polyglot-covers: python.traceback.capture-locals
# polyglot-covers: python.traceback.syntax-error-formatting
# polyglot-covers: python.traceback.clear-frames
# polyglot-covers: python.stdlib.atexit python.atexit.register
# polyglot-covers: python.atexit.arguments python.atexit.lifo-order
# polyglot-covers: python.atexit.unregister python.atexit.equality-removal
# polyglot-covers: python.atexit.normal-termination-only python.atexit.os-exit
# polyglot-covers: python.stdlib.__future__ python.future.feature-metadata
# polyglot-covers: python.future.optional-mandatory-release
# polyglot-covers: python.future.compiler-flag python.future.compile-dont-inherit
# polyglot-covers: python.future.annotations python.future.all-feature-names
# polyglot-covers: python.future.unknown-feature-syntax-error

import __future__
from io import StringIO
from pathlib import Path
import subprocess
import sys
import traceback
import warnings

import pytest


class DemoWarning(UserWarning):
    """把教程自己的警告与依赖库产生的警告分开。"""


def emit_from_helper(message="helper warning"):
    warnings.warn(message, DemoWarning, stacklevel=2)


def nested_failure():
    return 10 / 0


def call_nested_failure():
    return nested_failure()


def run_child(program, *arguments, check=True):
    return subprocess.run(
        [sys.executable, "-c", program, *map(str, arguments)],
        check=check,
        capture_output=True,
        text=True,
    )


def test_warning_categories_are_exception_classes_with_a_useful_hierarchy():
    assert issubclass(Warning, Exception)
    assert issubclass(DemoWarning, UserWarning)
    assert issubclass(DeprecationWarning, Warning)
    assert issubclass(PendingDeprecationWarning, Warning)
    assert issubclass(ResourceWarning, Warning)
    assert not issubclass(UserWarning, RuntimeWarning)


def test_catch_warnings_records_warning_message_metadata_and_restores_state():
    filters_before = warnings.filters.copy()
    showwarning_before = warnings.showwarning
    marker = object()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DemoWarning)
        warnings.warn("record me", DemoWarning, source=marker)

        assert len(caught) == 1
        message = caught[0]
        assert isinstance(message, warnings.WarningMessage)
        assert str(message.message) == "record me"
        assert message.category is DemoWarning
        assert message.filename == __file__
        assert message.source is marker

    assert warnings.filters == filters_before
    assert warnings.showwarning is showwarning_before


def test_stacklevel_attributes_a_warning_to_the_public_call_site():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DemoWarning)
        expected_line = sys._getframe().f_lineno + 1
        emit_from_helper()

    assert caught[0].filename == __file__
    assert caught[0].lineno == expected_line
    # 包装 API 若仍使用默认 stacklevel=1，用户看到的会是包装器内部
    # 而不是调用点。


def test_filter_actions_ignore_error_and_always_change_control_flow():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("ignore", DemoWarning)
        warnings.warn("hidden", DemoWarning)
        assert caught == []

        warnings.simplefilter("always", DemoWarning)
        warnings.warn("shown twice", DemoWarning)
        warnings.warn("shown twice", DemoWarning)
        assert [str(item.message) for item in caught] == ["shown twice", "shown twice"]

        warnings.simplefilter("error", DemoWarning)
        with pytest.raises(DemoWarning, match="now an exception"):
            warnings.warn("now an exception", DemoWarning)


def test_filterwarnings_uses_regexes_and_new_filters_take_precedence():
    with warnings.catch_warnings(record=True) as caught:
        warnings.resetwarnings()
        warnings.filterwarnings(
            "ignore",
            message=r"^routine ",
            category=DemoWarning,
            module=r".*test_154_.*",
        )
        warnings.filterwarnings(
            "always",
            message=r"^important ",
            category=DemoWarning,
        )
        warnings.warn("routine detail", DemoWarning)
        warnings.warn("important detail", DemoWarning)

    assert [str(item.message) for item in caught] == ["important detail"]
    # 默认 ``append=False`` 把新规则放到列表前面；过滤器采用首个匹配项。


def test_default_and_module_actions_depend_on_each_module_warning_registry():
    namespace = {"warnings": warnings, "DemoWarning": DemoWarning}
    code = compile(
        "warnings.warn('repeat', DemoWarning)\n"
        "warnings.warn('repeat', DemoWarning)\n",
        "generated_warning_module.py",
        "exec",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("default", DemoWarning)
        exec(code, namespace)
        # 两次调用虽然消息相同，却位于不同源码行；default 按
        # (message, category, module, lineno) 判重。
        assert len(caught) == 2
        exec(code, namespace)
        assert len(caught) == 2

        namespace.pop("__warningregistry__", None)
        exec(code, namespace)
        assert len(caught) == 4

    namespace = {"warnings": warnings, "DemoWarning": DemoWarning}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("module", DemoWarning)
        exec(code, namespace)
    assert len(caught) == 1


def test_warn_explicit_accepts_source_coordinates_and_an_explicit_registry():
    registry = {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("default", DemoWarning)
        for _ in range(2):
            warnings.warn_explicit(
                "generated warning",
                DemoWarning,
                "generated_module.py",
                17,
                module="generated_module",
                registry=registry,
            )

    assert len(caught) == 1
    assert caught[0].filename == "generated_module.py"
    assert caught[0].lineno == 17
    assert registry


def test_formatwarning_and_custom_showwarning_separate_format_from_destination(
    monkeypatch,
):
    rendered = warnings.formatwarning(
        "formatted",
        DemoWarning,
        "sample.py",
        9,
        line="value = legacy_call()",
    )
    assert "sample.py:9: DemoWarning: formatted" in rendered
    assert "value = legacy_call()" in rendered

    calls = []

    def capture(message, category, filename, lineno, file=None, line=None):
        calls.append((str(message), category, Path(filename).name, lineno, line))

    monkeypatch.setattr(warnings, "showwarning", capture)
    with warnings.catch_warnings():
        warnings.simplefilter("always", DemoWarning)
        warnings.warn("redirected", DemoWarning)

    assert calls[0][0] == "redirected"
    assert calls[0][1] is DemoWarning
    assert calls[0][2] == Path(__file__).name


def test_format_exc_print_exc_extract_tb_and_walk_tb_offer_layers_of_control():
    try:
        call_nested_failure()
    except ZeroDivisionError as error:
        captured = error
        formatted = traceback.format_exc()
        output = StringIO()
        traceback.print_exc(file=output)

    assert "ZeroDivisionError: division by zero" in formatted
    assert output.getvalue() == formatted

    summaries = traceback.extract_tb(captured.__traceback__)
    assert [item.name for item in summaries][-2:] == [
        "call_nested_failure",
        "nested_failure",
    ]
    walked = list(traceback.walk_tb(captured.__traceback__))
    assert len(walked) == len(summaries)
    assert traceback.format_list(summaries) == traceback.format_tb(
        captured.__traceback__
    )


def test_traceback_limit_selects_outermost_or_innermost_frames():
    try:
        call_nested_failure()
    except ZeroDivisionError as error:
        full = traceback.extract_tb(error.__traceback__)
        first_two = traceback.extract_tb(error.__traceback__, limit=2)
        last_two = traceback.extract_tb(error.__traceback__, limit=-2)

    assert first_two == full[:2]
    assert last_two == full[-2:]
    assert first_two[-1].name == "call_nested_failure"
    assert last_two[-1].name == "nested_failure"


def test_traceback_exception_preserves_explicit_cause_and_suppresses_context():
    try:
        try:
            int("not-an-integer")
        except ValueError as cause:
            raise LookupError("configuration missing") from cause
    except LookupError as error:
        summary = traceback.TracebackException.from_exception(error)

    assert summary.exc_type is LookupError
    assert summary.__cause__.exc_type is ValueError
    # cause 与 context 是同一异常时只保留 cause，避免格式化同一分支两次。
    assert summary.__context__ is None
    assert summary.__suppress_context__ is True
    rendered = "".join(summary.format(chain=True))
    assert "ValueError" in rendered
    assert "direct cause" in rendered
    assert "LookupError: configuration missing" in rendered


def test_implicit_exception_context_is_rendered_when_not_suppressed():
    try:
        try:
            {}["missing"]
        except KeyError:
            raise RuntimeError("fallback failed")
    except RuntimeError as error:
        summary = traceback.TracebackException.from_exception(error)

    assert summary.__cause__ is None
    assert summary.__context__.exc_type is KeyError
    assert summary.__suppress_context__ is False
    rendered = "".join(summary.format(chain=True))
    assert "During handling of the above exception" in rendered


def test_stack_summary_can_capture_repr_of_locals_without_retaining_objects():
    def fail_with_local():
        teaching_value = {"answer": 42}
        raise RuntimeError("inspect locals")

    try:
        fail_with_local()
    except RuntimeError as error:
        stack = traceback.StackSummary.extract(
            traceback.walk_tb(error.__traceback__),
            capture_locals=True,
        )

    inner = stack[-1]
    assert isinstance(inner, traceback.FrameSummary)
    assert inner.name == "fail_with_local"
    assert inner.locals["teaching_value"] == "{'answer': 42}"
    assert "raise RuntimeError" in (inner.line or "")
    # capture_locals 会调用 repr；真实系统中局部变量可能含密钥，
    # 也可能有昂贵或会抛错的 repr，生成诊断信息时需要明确这个成本。


def test_syntax_error_traceback_includes_location_and_source_text():
    try:
        compile("answer = (1 + )\n", "broken_config.py", "exec")
    except SyntaxError as error:
        rendered = "".join(traceback.format_exception_only(type(error), error))

    assert 'File "broken_config.py", line 1' in rendered
    assert "answer = (1 + )" in rendered
    assert "SyntaxError" in rendered


def test_clear_frames_releases_finished_frame_locals_from_a_traceback():
    def fail_with_large_local():
        retained_only_by_traceback = bytearray(1_000)
        raise RuntimeError(len(retained_only_by_traceback))

    try:
        fail_with_large_local()
    except RuntimeError as error:
        saved_traceback = error.__traceback__

    inner_frame = saved_traceback.tb_next.tb_frame
    assert "retained_only_by_traceback" in inner_frame.f_locals
    traceback.clear_frames(saved_traceback)
    assert "retained_only_by_traceback" not in inner_frame.f_locals


def test_atexit_runs_normal_exit_handlers_in_reverse_registration_order():
    program = """
import atexit

def report(label, punctuation=""):
    print(label + punctuation)

atexit.register(report, "first")
decorated = atexit.register(report, "second", punctuation="!")
assert decorated is report
print("body")
"""
    completed = run_child(program)
    assert completed.stdout.splitlines() == ["body", "second!", "first"]


def test_atexit_unregister_removes_all_equal_registrations():
    program = """
import atexit

class Callback:
    def __init__(self, key):
        self.key = key
    def __call__(self, label):
        print(label)
    def __eq__(self, other):
        return isinstance(other, Callback) and self.key == other.key

first = Callback("same")
equal_but_distinct = Callback("same")
atexit.register(first, "first registration")
atexit.register(equal_but_distinct, "second registration")
assert atexit.unregister(Callback("same")) is None
print("body only")
"""
    completed = run_child(program)
    assert completed.stdout.splitlines() == ["body only"]
    # unregister 按 ``==`` 而非 ``is`` 比较，并移除所有相等的注册；注册参数不
    # 参与匹配。


def test_atexit_is_skipped_by_os_exit_because_that_is_not_normal_termination():
    program = """
import atexit
import os
import sys

atexit.register(print, "cleanup")
print("before _exit", flush=True)
os._exit(5)
"""
    completed = run_child(program, check=False)
    assert completed.returncode == 5
    assert completed.stdout.splitlines() == ["before _exit"]
    # 未处理信号、致命解释器错误和 os._exit 也绕过 atexit；需要可靠提交的
    # 数据不能只依赖进程退出钩子。


def test_future_features_expose_release_history_and_compiler_flags():
    names = __future__.all_feature_names
    assert "annotations" in names
    assert "division" in names
    assert "generator_stop" in names

    annotations = __future__.annotations
    assert isinstance(annotations, __future__._Feature)
    assert annotations.getOptionalRelease() == (3, 7, 0, "beta", 1)
    # 3.10 的表仍记录当时计划在 3.11 强制启用；该计划后来撤回。
    assert annotations.getMandatoryRelease() == (3, 11, 0, "alpha", 0)
    assert annotations.compiler_flag > 0

    division = __future__.division
    assert division.getMandatoryRelease() == (3, 0, 0, "alpha", 0)


def test_future_compiler_flag_enables_postponed_annotations_explicitly():
    namespace = {}
    code = compile(
        "def parse(value: MissingType) -> list[MissingType]:\n"
        "    return [value]\n",
        "future_annotations.py",
        "exec",
        flags=__future__.annotations.compiler_flag,
        dont_inherit=True,
    )
    exec(code, namespace)

    assert namespace["parse"].__annotations__ == {
        "value": "MissingType",
        "return": "list[MissingType]",
    }
    # 没有 future flag 时，尚未定义的 MissingType 会在函数定义阶段触发
    # NameError；推迟求值使工具可以稍后通过 typing.get_type_hints 解析。


def test_unknown_future_feature_is_a_compile_time_syntax_error():
    with pytest.raises(SyntaxError, match="future feature .* is not defined"):
        compile(
            "from __future__ import polyglot_time_travel\n",
            "unknown_future.py",
            "exec",
        )
