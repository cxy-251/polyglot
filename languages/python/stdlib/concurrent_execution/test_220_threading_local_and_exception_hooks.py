"""220｜``threading.local`` isolation、``__slots__`` trap 与 exception hooks。

thread-local object 的 attribute dictionary 按 thread 隔离；subclass ``__init__`` 也会在
每个首次访问它的 thread 中分别执行。但 subclass slots 属于 class descriptor，不是
thread-local storage。未捕获异常经 ``threading.excepthook`` 报告，不由 ``join`` 传播。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.local python.threading.local-attribute-isolation
# polyglot-covers: python.threading.local-subclass-init-per-thread
# polyglot-covers: python.threading.local-slots-shared-trap
# polyglot-covers: python.threading.excepthook
# polyglot-covers: python.threading.ExceptHookArgs
# polyglot-covers: python.threading.__excepthook__
# polyglot-covers: python.threading.Thread-exception-not-reraised-by-join
# polyglot-covers: python.threading.excepthook-reference-cycle-trap
# polyglot-covers: python.threading.excepthook-thread-resurrection-trap

import queue
import threading


def test_plain_local_has_distinct_attribute_dictionary_per_thread():
    """worker 起初看不到 main 的 value，worker 写入也不会改变 main 的 value。"""

    state = threading.local()
    state.value = "main"
    results = queue.Queue()

    def worker():
        results.put(hasattr(state, "value"))
        state.value = "worker"
        results.put(state.value)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results.get_nowait() is False
    assert results.get_nowait() == "worker"
    assert state.value == "main"


def test_local_subclass_initializer_runs_once_in_each_thread_context():
    """每个 thread 获得自己的 list；不要期待 __init__ 只在 object 创建时执行一次。"""

    initialized_in = []

    class RequestState(threading.local):
        def __init__(self):
            initialized_in.append(threading.get_ident())
            self.values = []

    state = RequestState()
    state.values.append("main")
    results = queue.Queue()

    def worker():
        state.values.append("worker")
        results.put(list(state.values))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results.get_nowait() == ["worker"]
    assert state.values == ["main"]
    assert len(set(initialized_in)) == 2


def test_slots_on_local_subclass_are_shared_instead_of_thread_local():
    """需要隔离的值必须留在 instance dict；slot descriptor 会暴露同一份 storage。"""

    class SlottedState(threading.local):
        __slots__ = ("shared_value",)

    state = SlottedState()
    state.shared_value = "main"
    results = queue.Queue()

    def worker():
        results.put(state.shared_value)
        state.shared_value = "worker"

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results.get_nowait() == "main"
    assert state.shared_value == "worker"


def test_custom_excepthook_receives_uncaught_worker_exception():
    """只保存不可变摘要；长期保存 exc_value/thread 会造成 cycle 或 object resurrection。"""

    original_hook = threading.excepthook
    summaries = []

    def capture(args):
        summaries.append(
            {
                "type": args.exc_type,
                "message": str(args.exc_value),
                "has_traceback": args.exc_traceback is not None,
                "thread_name": args.thread.name,
            }
        )

    threading.excepthook = capture
    try:
        thread = threading.Thread(
            target=lambda: (_ for _ in ()).throw(LookupError("missing")),
            name="failing-worker",
        )
        thread.start()
        assert thread.join() is None
    finally:
        threading.excepthook = original_hook

    assert summaries == [
        {
            "type": LookupError,
            "message": "missing",
            "has_traceback": True,
            "thread_name": "failing-worker",
        }
    ]
    assert threading.__excepthook__ is not None
