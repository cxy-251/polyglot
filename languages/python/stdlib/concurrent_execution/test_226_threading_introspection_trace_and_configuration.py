"""226｜``threading`` introspection、trace/profile hooks 与 process-wide configuration。

``enumerate``/``current_thread`` 提供 Thread wrapper 视图，ident 只是可回收的 magic cookie，
native_id 也只在线程存活期间唯一。settrace/setprofile 是后续 ``threading.Thread`` 的全局
默认 hook，测试必须恢复；stack_size 同样影响之后创建的 thread。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.current_thread python.threading.main_thread
# polyglot-covers: python.threading.enumerate python.threading.active_count
# polyglot-covers: python.threading.get_ident python.threading.get_native_id
# polyglot-covers: python.threading.ident-recycling-caveat
# polyglot-covers: python.threading.settrace python.threading.gettrace
# polyglot-covers: python.threading.setprofile python.threading.getprofile
# polyglot-covers: python.threading.stack_size python.threading.stack-size-minimum
# polyglot-covers: python.threading.deprecated-camelcase-aliases
# polyglot-covers: python.threading.Thread-default-target-name
# polyglot-covers: python.threading.Thread-group-reserved

import threading

import pytest


def test_module_introspection_tracks_a_live_thread_and_its_ids():
    """用 Event 保持 worker 存活，避免在 enumerate 检查前已经退出的 race。"""

    started = threading.Event()
    release = threading.Event()
    observations = {}

    def worker():
        observations["current"] = threading.current_thread()
        observations["ident"] = threading.get_ident()
        observations["native_id"] = threading.get_native_id()
        started.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(target=worker)
    thread.start()
    assert started.wait(timeout=2)

    try:
        assert observations["current"] is thread
        assert observations["ident"] == thread.ident
        assert observations["native_id"] == thread.native_id
        assert thread in threading.enumerate()
        assert threading.active_count() >= 2
        assert threading.current_thread() is threading.main_thread()
        assert threading.main_thread() in threading.enumerate()
    finally:
        release.set()
        thread.join()


def test_trace_hook_is_installed_for_threads_started_after_settrace():
    """threading.settrace 不改变当前 thread；新 worker 启动前会调用 sys.settrace。"""

    original = threading.gettrace()
    events = []

    def trace(frame, event, argument):
        if frame.f_code.co_name == "traced_worker":
            events.append(event)
        return trace

    def traced_worker():
        value = 40
        return value + 2

    threading.settrace(trace)
    try:
        thread = threading.Thread(target=traced_worker)
        thread.start()
        thread.join()
    finally:
        threading.settrace(original)

    assert "call" in events
    assert "return" in events


def test_profile_hook_is_installed_for_future_threading_threads():
    """profile hook 只需返回 None；与 trace hook 不同，不为每个 frame 返回下级 hook。"""

    original = threading.getprofile()
    calls = []

    def profile(frame, event, argument):
        if event == "call" and frame.f_code.co_name == "profiled_worker":
            calls.append(frame.f_code.co_name)

    def profiled_worker():
        return sum((1, 2, 3))

    threading.setprofile(profile)
    try:
        thread = threading.Thread(target=profiled_worker)
        thread.start()
        thread.join()
    finally:
        threading.setprofile(original)

    assert calls == ["profiled_worker"]


def test_stack_size_rejects_too_small_value_and_restores_global_setting():
    """32768 是解释器保证的下限，但 OS 仍可要求更高或不允许修改，此时明确 skip。"""

    original = threading.stack_size()

    with pytest.raises(ValueError):
        threading.stack_size(1)
    assert threading.stack_size() == original

    try:
        previous = threading.stack_size(32768)
    except (RuntimeError, ValueError):
        pytest.skip("当前 thread implementation 不接受 32 KiB stack size")
    else:
        try:
            assert previous == original
            assert threading.stack_size() == 32768
        finally:
            threading.stack_size(original)


def test_python_310_deprecates_legacy_camelcase_aliases():
    """alias 仍可工作以兼容旧代码，但新代码直接使用 property 与 snake_case API。"""

    thread = threading.Thread(name="before")

    with pytest.warns(DeprecationWarning):
        assert thread.getName() == "before"
    with pytest.warns(DeprecationWarning):
        thread.setName("after")
    with pytest.warns(DeprecationWarning):
        thread.setDaemon(True)
    with pytest.warns(DeprecationWarning):
        assert thread.isDaemon() is True
    with pytest.warns(DeprecationWarning):
        assert threading.currentThread() is threading.current_thread()
    with pytest.warns(DeprecationWarning):
        assert threading.activeCount() >= 1

    assert (thread.name, thread.daemon) == ("after", True)


def test_default_name_uses_target_name_and_group_is_reserved():
    """3.10 默认名称包含 target.__name__；group 参数当前必须保持 None。"""

    def synchronize_cache():
        pass

    thread = threading.Thread(target=synchronize_cache)

    assert "synchronize_cache" in thread.name
    with pytest.raises(AssertionError, match="group argument must be None"):
        threading.Thread(group=object())
