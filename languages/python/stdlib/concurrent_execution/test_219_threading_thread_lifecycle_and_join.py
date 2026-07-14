"""219｜``threading.Thread`` lifecycle、target dispatch、identity 与 ``join``。

``run()`` 只是普通 method call；``start()`` 才会创建 OS thread，并且每个 Thread object
只能 start 一次。``join()`` 始终返回 None，判断 timeout 应再看 ``is_alive()``。Thread
异常不会由 join 重新抛给调用方，而是交给 ``threading.excepthook``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.Thread python.threading.Thread-target
# polyglot-covers: python.threading.Thread-args python.threading.Thread-kwargs
# polyglot-covers: python.threading.Thread.start python.threading.Thread.run
# polyglot-covers: python.threading.Thread-start-once
# polyglot-covers: python.threading.Thread.join python.threading.Thread-join-returns-none
# polyglot-covers: python.threading.Thread-join-before-start-error
# polyglot-covers: python.threading.Thread-self-join-error
# polyglot-covers: python.threading.Thread.is_alive
# polyglot-covers: python.threading.Thread.name python.threading.Thread.daemon
# polyglot-covers: python.threading.Thread.ident python.threading.Thread.native_id
# polyglot-covers: python.threading.Thread-subclass-run

import queue
import threading

import pytest


def test_start_dispatches_target_in_another_thread_and_join_waits_for_exit():
    """ident/native_id 在 start 前为 None，结束后仍保留最后一次 thread identity。"""

    started = threading.Event()
    release = threading.Event()
    observations = {}

    def worker(value, *, scale):
        observations["result"] = value * scale
        observations["thread"] = threading.current_thread()
        observations["ident"] = threading.get_ident()
        started.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(
        target=worker,
        args=(6,),
        kwargs={"scale": 7},
        name="answer-worker",
    )

    assert thread.ident is None
    assert thread.native_id is None
    assert thread.is_alive() is False
    assert thread.daemon is False

    thread.start()
    assert started.wait(timeout=2)
    assert thread.is_alive() is True
    assert observations["thread"] is thread
    assert observations["ident"] == thread.ident
    assert thread.name == "answer-worker"
    assert isinstance(thread.native_id, int)

    release.set()
    assert thread.join(timeout=2) is None
    assert thread.is_alive() is False
    assert thread.ident == observations["ident"]
    assert observations["result"] == 42


def test_calling_run_directly_is_synchronous_and_does_not_start_thread():
    """直接 run 可用于窄范围测试 target，但不会赋 ident，也不消耗一次 start 机会。"""

    calls = []
    thread = threading.Thread(target=calls.append, args=(threading.get_ident(),))

    thread.run()

    assert calls == [threading.get_ident()]
    assert thread.ident is None
    assert thread.is_alive() is False


def test_start_twice_and_join_before_start_are_lifecycle_errors():
    """Thread object 不可复用；需要再次运行应创建新 object。"""

    unstarted = threading.Thread(target=lambda: None)
    with pytest.raises(RuntimeError, match="cannot join thread before it is started"):
        unstarted.join()

    thread = threading.Thread(target=lambda: None)
    thread.start()
    thread.join()
    with pytest.raises(RuntimeError, match="threads can only be started once"):
        thread.start()


def test_thread_cannot_join_itself_because_that_would_deadlock():
    """错误发生在 worker 内；用 Queue 把异常类型和文本安全送回 main thread。"""

    outcomes = queue.Queue()

    def worker():
        try:
            threading.current_thread().join()
        except RuntimeError as error:
            outcomes.put((type(error), str(error)))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    error_type, message = outcomes.get_nowait()
    assert error_type is RuntimeError
    assert "cannot join current thread" in message


def test_subclass_overrides_run_and_calls_base_initializer_first():
    """官方扩展点是 __init__/run；不要覆盖 start/join 等 lifecycle machinery。"""

    class RecordingThread(threading.Thread):
        def __init__(self, value):
            super().__init__(name="recording-thread")
            self.value = value
            self.result = None

        def run(self):
            self.result = self.value.upper()

    thread = RecordingThread("python")
    thread.start()
    thread.join()

    assert thread.result == "PYTHON"


def test_daemon_flag_must_be_configured_before_start():
    """daemon thread 会在 process shutdown 被突然终止，不能承担必须清理的持久工作。"""

    release = threading.Event()
    started = threading.Event()

    def worker():
        started.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    assert started.wait(timeout=2)

    try:
        with pytest.raises(RuntimeError, match="cannot set daemon status"):
            thread.daemon = False
    finally:
        release.set()
        thread.join()
