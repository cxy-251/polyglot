"""233｜``multiprocessing`` start methods、context factory 与 ``__main__`` guard。

Context 把 Process/Queue/Lock 等 factory 绑定到同一 start method，library 应允许调用方
传入 context。``set_start_method`` 是 process-global one-shot configuration。spawn 会
重新 import main module，所以启动 child 的 top-level side effect 必须放在 main guard 内。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.get_all_start_methods
# polyglot-covers: python.multiprocessing.get_start_method
# polyglot-covers: python.multiprocessing.get_context
# polyglot-covers: python.multiprocessing.context-bound-factories
# polyglot-covers: python.multiprocessing.invalid-start-method
# polyglot-covers: python.multiprocessing.set_start_method
# polyglot-covers: python.multiprocessing.set-start-method-once
# polyglot-covers: python.multiprocessing.set-start-method-force-reset
# polyglot-covers: python.multiprocessing.spawn
# polyglot-covers: python.multiprocessing.main-guard
# polyglot-covers: python.multiprocessing.spawn-main-importability
# polyglot-covers: python.multiprocessing.freeze_support

import json
import multiprocessing
import subprocess
import sys

import pytest


def test_context_reports_method_and_builds_matching_primitive_family():
    """methods list 的第一项是平台默认；spawn 在受支持的 Python 平台始终存在。"""

    methods = multiprocessing.get_all_start_methods()
    default = multiprocessing.get_start_method()

    assert methods[0] == default
    assert "spawn" in methods
    for method in methods:
        context = multiprocessing.get_context(method)
        assert context.get_start_method() == method
        assert context.Process is not None
        lock = context.Lock()
        with lock:
            assert lock.acquire(block=False) is False

    with pytest.raises(ValueError, match="cannot find context"):
        multiprocessing.get_context("not-a-start-method")


def test_global_start_method_is_one_shot_unless_force_resets_in_child_process():
    """child interpreter 隔离 global state，避免改变同一 pytest process 后续 context。"""

    code = """
import json
import multiprocessing as mp

before = mp.get_start_method(allow_none=True)
mp.set_start_method("spawn")
selected = mp.get_start_method()
try:
    mp.set_start_method("spawn")
except RuntimeError as error:
    repeated = type(error).__name__
mp.set_start_method(None, force=True)
after_reset = mp.get_start_method(allow_none=True)
print(json.dumps([before, selected, repeated, after_reset]))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert json.loads(completed.stdout) == [None, "spawn", "RuntimeError", None]
    assert completed.stderr == ""


def test_spawn_script_uses_main_guard_and_importable_top_level_target(tmp_path):
    """没有 guard 时 child import 会再次执行 Process.start，最终触发 bootstrapping error。"""

    script = tmp_path / "spawn_workflow.py"
    script.write_text(
        """
import json
import multiprocessing as mp

def square(value, output):
    output.put((value * value, __name__))

if __name__ == "__main__":
    mp.freeze_support()
    context = mp.get_context("spawn")
    output = context.Queue()
    process = context.Process(target=square, args=(7, output))
    process.start()
    payload = output.get(timeout=5)
    process.join(timeout=5)
    output.close()
    output.join_thread()
    print(json.dumps([payload, process.exitcode]))
    process.close()
""".lstrip(),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(script)],
        check=True,
        capture_output=True,
        text=True,
        timeout=8,
    )

    payload, exitcode = json.loads(completed.stdout)
    assert payload == [49, "__mp_main__"]
    assert exitcode == 0
    assert completed.stderr == ""
