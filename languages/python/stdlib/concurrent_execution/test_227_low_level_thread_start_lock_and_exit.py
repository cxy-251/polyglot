"""227｜``_thread`` raw thread creation、lock type、identity 与 silent exit。

``_thread.start_new_thread`` 只返回 ident，没有 join/lifecycle object；生产代码通常应使用
threading。raw thread 共享相同 lock primitive，未捕获异常走 ``sys.unraisablehook``，
而 ``_thread.exit`` 只是抛 SystemExit，raw thread 会静默结束。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python._thread python._thread.start_new_thread
# polyglot-covers: python._thread.start-new-thread-args
# polyglot-covers: python._thread.start-new-thread-kwargs
# polyglot-covers: python._thread.raw-thread-no-join-object
# polyglot-covers: python._thread.allocate_lock python._thread.LockType
# polyglot-covers: python._thread.lock-context-manager
# polyglot-covers: python._thread.error python._thread.error-runtimeerror-alias
# polyglot-covers: python._thread.get_ident python._thread.get_native_id
# polyglot-covers: python._thread.TIMEOUT_MAX
# polyglot-covers: python._thread.exit python._thread.exit-systemexit

import _thread
import queue
import threading

import pytest


def test_start_new_thread_passes_tuple_args_and_keyword_dict():
    """返回值是 raw integer ident；Event 承担本例的完成通知，因为 API 没有 join。"""

    completed = threading.Event()
    observations = queue.Queue()

    def worker(value, *, multiplier):
        observations.put(
            (value * multiplier, _thread.get_ident(), _thread.get_native_id())
        )
        completed.set()

    returned_ident = _thread.start_new_thread(
        worker,
        (6,),
        {"multiplier": 7},
    )

    assert isinstance(returned_ident, int)
    assert completed.wait(timeout=2)
    result, worker_ident, native_id = observations.get_nowait()
    assert result == 42
    assert worker_ident == returned_ident
    assert isinstance(native_id, int)


def test_start_new_thread_requires_args_tuple():
    """即使 callable 不取参数，args 也必须是 tuple 而不是通用 iterable。"""

    with pytest.raises(TypeError):
        _thread.start_new_thread(lambda: None, [])


def test_allocate_lock_returns_documented_type_and_context_protocol():
    """threading.Lock 建立在同一 primitive 上；_thread.error 现为 RuntimeError alias。"""

    lock = _thread.allocate_lock()

    assert isinstance(lock, _thread.LockType)
    assert _thread.error is RuntimeError
    assert lock.locked() is False
    with lock as acquired:
        assert acquired is True
        assert lock.locked() is True
        assert lock.acquire(False) is False
    assert lock.locked() is False
    assert _thread.TIMEOUT_MAX == threading.TIMEOUT_MAX


def test_thread_exit_raises_systemexit_and_raw_thread_treats_it_as_silent_exit():
    """先在普通 call 中证明异常类型，再由 raw worker 的 finally 通知结束。"""

    with pytest.raises(SystemExit):
        _thread.exit()

    completed = threading.Event()

    def worker():
        try:
            _thread.exit()
        finally:
            completed.set()

    _thread.start_new_thread(worker, ())

    assert completed.wait(timeout=2)
