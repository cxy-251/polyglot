"""090｜``multiprocessing.Process`` lifecycle、child identity、sentinel 与 close。

Process 与 Thread API 相似，但 target 在独立 interpreter/process 中运行，参数必须适合
所选 start method。pid/sentinel 在 start 后可用，exitcode 在结束前为 None；``join`` 仍
总返回 None。``close`` 释放 parent 侧 Process resources，不能用于仍存活的 child。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.multiprocessing.Process
# polyglot-covers: python.multiprocessing.Process-target-args-kwargs
# polyglot-covers: python.multiprocessing.Process.start
# polyglot-covers: python.multiprocessing.Process.join
# polyglot-covers: python.multiprocessing.Process.is_alive
# polyglot-covers: python.multiprocessing.Process.name
# polyglot-covers: python.multiprocessing.Process.pid
# polyglot-covers: python.multiprocessing.Process.exitcode
# polyglot-covers: python.multiprocessing.Process.authkey
# polyglot-covers: python.multiprocessing.Process.sentinel
# polyglot-covers: python.multiprocessing.connection.wait-process-sentinel
# polyglot-covers: python.multiprocessing.current_process
# polyglot-covers: python.multiprocessing.parent_process
# polyglot-covers: python.multiprocessing.Process-close-live-error
# polyglot-covers: python.multiprocessing.Process.close
# polyglot-covers: python.multiprocessing.Process-subclass-run




import multiprocessing
import multiprocessing.connection
import os
import pytest
import json
import subprocess
import sys
import signal
import queue
import ctypes
import multiprocessing.sharedctypes

def _report_process_state(connection, started, release, value, *, multiplier):
    process = multiprocessing.current_process()
    parent = multiprocessing.parent_process()
    started.set()
    if not release.wait(timeout=5):
        raise RuntimeError("parent did not release child")
    connection.send(
        {
            "result": value * multiplier,
            "name": process.name,
            "pid": os.getpid(),
            "parent_pid": parent.pid,
            "daemon": process.daemon,
        }
    )
    connection.close()


class _DoublingProcess(multiprocessing.Process):
    def __init__(self, connection, value):
        super().__init__(name="doubling-process")
        self.connection = connection
        self.value = value

    def run(self):
        self.connection.send(self.value * 2)
        self.connection.close()


def _do_nothing():
    return None


def test_spawn_process_reports_identity_and_sentinel_becomes_ready_on_exit():
    """显式 spawn 证明 target/arguments 可序列化，不依赖 Linux 默认 fork memory snapshot。"""

    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=True)
    started = context.Event()
    release = context.Event()
    process = context.Process(
        target=_report_process_state,
        args=(child_connection, started, release, 6),
        kwargs={"multiplier": 7},
        name="spawned-answer-worker",
    )

    assert process.pid is None
    assert process.exitcode is None
    assert process.is_alive() is False
    assert process.authkey == multiprocessing.current_process().authkey

    process.start()
    child_connection.close()
    assert started.wait(timeout=5)

    try:
        assert process.is_alive() is True
        assert isinstance(process.pid, int)
        assert process.exitcode is None
        assert multiprocessing.connection.wait([process.sentinel], timeout=0) == []

        release.set()
        ready = multiprocessing.connection.wait([process.sentinel], timeout=5)
        assert ready == [process.sentinel]
        assert process.join(timeout=5) is None

        report = parent_connection.recv()
        assert report == {
            "result": 42,
            "name": "spawned-answer-worker",
            "pid": process.pid,
            "parent_pid": os.getpid(),
            "daemon": False,
        }
        assert process.exitcode == 0
        assert process.is_alive() is False
    finally:
        release.set()
        process.join(timeout=5)
        parent_connection.close()
        process.close()


def test_process_start_once_and_join_before_start_are_lifecycle_errors():
    """Process object 与 native process 一一对应；再次执行应创建新 instance。"""

    process = multiprocessing.Process(target=_do_nothing)

    with pytest.raises(AssertionError, match="can only join a started process"):
        process.join()

    process.start()
    process.join()
    with pytest.raises(AssertionError, match="cannot start a process twice"):
        process.start()
    process.close()


def test_close_rejects_live_process_and_invalidates_finished_process_object():
    """close 不是 terminate；必须先建立 child 已结束的同步边界。"""

    context = multiprocessing.get_context()
    started = context.Event()
    release = context.Event()
    process = context.Process(
        target=_wait_for_release,
        args=(started, release),
    )
    process.start()
    assert started.wait(timeout=5)

    with pytest.raises(ValueError, match="Cannot close a process while it is still running"):
        process.close()

    release.set()
    process.join(timeout=5)
    assert process.exitcode == 0
    process.close()

    with pytest.raises(ValueError, match="process object is closed"):
        process.is_alive()


def _wait_for_release(started, release):
    started.set()
    if not release.wait(timeout=5):
        raise RuntimeError("release event timed out")


def test_process_subclass_overrides_run_and_uses_normal_lifecycle():
    """与 Thread 相同，只覆盖 __init__/run，并先调用 Process.__init__。"""

    parent_connection, child_connection = multiprocessing.Pipe()
    process = _DoublingProcess(child_connection, 21)

    process.start()
    child_connection.close()
    process.join(timeout=5)

    assert parent_connection.recv() == 42
    assert process.name == "doubling-process"
    assert process.exitcode == 0
    parent_connection.close()
    process.close()


# ``multiprocessing`` start methods、context factory 与 ``__main__`` guard。
#
# Context 把 Process/Queue/Lock 等 factory 绑定到同一 start method，library 应允许调用方
# 传入 context。``set_start_method`` 是 process-global one-shot configuration。spawn 会
# 重新 import main module，所以启动 child 的 top-level side effect 必须放在 main guard 内。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# Process exitcode 分类、terminate/kill 风险与 authentication key。
#
# 正常 return→0，``sys.exit(N)``→N，未捕获异常→1，Unix signal termination→负 signal。
# terminate/kill 不运行 finally，且可能破坏 child 正在使用的 queue/lock/pipe；本例只终止
# 阻塞在专用 Pipe 的 disposable child。authkey 必须是 bytes，并默认由 parent 继承。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.multiprocessing.Process-exitcode-normal
# polyglot-covers: python.multiprocessing.Process-exitcode-sys-exit
# polyglot-covers: python.multiprocessing.Process-exitcode-unhandled-exception
# polyglot-covers: python.multiprocessing.Process-exitcode-signal
# polyglot-covers: python.multiprocessing.Process.terminate
# polyglot-covers: python.multiprocessing.Process.kill
# polyglot-covers: python.multiprocessing.terminate-finally-not-guaranteed
# polyglot-covers: python.multiprocessing.terminate-shared-resource-corruption-trap
# polyglot-covers: python.multiprocessing.Process.authkey-inheritance
# polyglot-covers: python.multiprocessing.Process-authkey-bytes-only




def _return_normally():
    return None


def _exit_with_status(status):
    raise SystemExit(status)


def _raise_uncaught_without_stderr_noise():
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
    raise LookupError("child failure")


def _block_on_private_connection(connection):
    connection.send("ready")
    connection.recv()


@pytest.mark.parametrize(
    ("target", "args", "expected"),
    [
        (_return_normally, (), 0),
        (_exit_with_status, (7,), 7),
        (_raise_uncaught_without_stderr_noise, (), 1),
    ],
)
def test_process_exitcode_distinguishes_return_sys_exit_and_exception(
    target,
    args,
    expected,
):
    process = multiprocessing.Process(target=target, args=args)

    process.start()
    process.join(timeout=5)

    assert process.is_alive() is False
    assert process.exitcode == expected
    process.close()


def test_terminate_stops_disposable_child_without_graceful_cleanup():
    """Pipe 仅用于确认 child 已进入 target；terminate 后不再复用该 channel。"""

    parent_connection, child_connection = multiprocessing.Pipe()
    process = multiprocessing.Process(
        target=_block_on_private_connection,
        args=(child_connection,),
    )
    process.start()
    child_connection.close()
    assert parent_connection.recv() == "ready"

    process.terminate()
    process.join(timeout=5)

    assert process.is_alive() is False
    assert process.exitcode != 0
    if os.name == "posix":
        assert process.exitcode == -signal.SIGTERM
    parent_connection.close()
    process.close()


def test_kill_uses_sigkill_on_posix():
    """kill 比 terminate 更强，同样不适用于持有共享 synchronization resource 的 child。"""

    parent_connection, child_connection = multiprocessing.Pipe()
    process = multiprocessing.Process(
        target=_block_on_private_connection,
        args=(child_connection,),
    )
    process.start()
    child_connection.close()
    assert parent_connection.recv() == "ready"

    process.kill()
    process.join(timeout=5)

    assert process.is_alive() is False
    if os.name == "posix":
        assert process.exitcode == -signal.SIGKILL
    else:
        assert process.exitcode != 0
    parent_connection.close()
    process.close()


def test_process_inherits_authkey_and_setter_requires_bytes():
    """authkey 用于 multiprocessing connection digest authentication，不是 payload 加密。"""

    parent = multiprocessing.current_process()
    process = multiprocessing.Process(target=_return_normally)

    assert process.authkey == parent.authkey
    process.authkey = b"teaching-secret"
    assert process.authkey == b"teaching-secret"
    with pytest.raises(TypeError, match="encoding"):
        process.authkey = "text-secret"


# ``multiprocessing.Pipe`` message protocol、bytes buffers 与 multi-wait。
#
# Connection 是 message-oriented channel：``send`` pickle object，``send_bytes`` 保留一个
# bytes message boundary。duplex=False 返回 receive-only/send-only 两端。不要让多个 writer
# 并发使用同一 pipe end；frame 可能交错损坏。``connection.wait`` 可统一等待多个 endpoint。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.multiprocessing.Pipe python.multiprocessing.Pipe-duplex
# polyglot-covers: python.multiprocessing.Pipe-simplex-end-order
# polyglot-covers: python.multiprocessing.connection.Connection
# polyglot-covers: python.multiprocessing.Connection.send
# polyglot-covers: python.multiprocessing.Connection.recv
# polyglot-covers: python.multiprocessing.Connection-pickle-copy
# polyglot-covers: python.multiprocessing.Connection.poll
# polyglot-covers: python.multiprocessing.Connection.send_bytes
# polyglot-covers: python.multiprocessing.Connection.recv_bytes
# polyglot-covers: python.multiprocessing.Connection.recv_bytes_into
# polyglot-covers: python.multiprocessing.BufferTooShort
# polyglot-covers: python.multiprocessing.Connection.fileno
# polyglot-covers: python.multiprocessing.Connection.close
# polyglot-covers: python.multiprocessing.Connection-context-manager
# polyglot-covers: python.multiprocessing.connection.wait
# polyglot-covers: python.multiprocessing.pipe-shared-end-corruption-trap




def test_duplex_pipe_pickles_objects_and_preserves_message_boundaries():
    """recv 得到相等但独立 object graph；两个 duplex endpoints 都能 send/recv。"""

    left, right = multiprocessing.Pipe(duplex=True)
    payload = {"items": [1, 2]}

    try:
        left.send(payload)
        received = right.recv()
        assert received == payload
        assert received is not payload
        assert received["items"] is not payload["items"]

        right.send("reply")
        assert left.poll(timeout=0) is True
        assert left.recv() == "reply"
        assert isinstance(left.fileno(), int)
    finally:
        left.close()
        right.close()


def test_simplex_pipe_returns_receive_end_then_send_end():
    """duplex=False 的 tuple 顺序很容易写反；错误方向调用以 OSError 明确失败。"""

    receive_end, send_end = multiprocessing.Pipe(duplex=False)

    try:
        send_end.send({"answer": 42})
        assert receive_end.recv() == {"answer": 42}
        with pytest.raises(OSError, match="write-only"):
            send_end.recv()
        with pytest.raises(OSError, match="read-only"):
            receive_end.send("invalid")
    finally:
        receive_end.close()
        send_end.close()


def test_send_bytes_offset_and_recv_bytes_into_small_buffer_error():
    """BufferTooShort.args[0] 保留完整 message，调用方可据此扩容而不丢数据。"""

    receive_end, send_end = multiprocessing.Pipe(duplex=False)

    try:
        send_end.send_bytes(b"abcdef", offset=1, size=3)
        assert receive_end.recv_bytes() == b"bcd"

        send_end.send_bytes(b"hello")
        small = bytearray(2)
        with pytest.raises(multiprocessing.BufferTooShort) as raised:
            receive_end.recv_bytes_into(small)
        assert raised.value.args == (b"hello",)
    finally:
        receive_end.close()
        send_end.close()


def test_recv_raises_eof_after_peer_closes_and_messages_are_drained():
    """close 不生成普通 sentinel object；读取完 frame 后下一次 recv 抛 EOFError。"""

    receive_end, send_end = multiprocessing.Pipe(duplex=False)
    send_end.send("last")
    send_end.close()

    try:
        assert receive_end.recv() == "last"
        with pytest.raises(EOFError):
            receive_end.recv()
    finally:
        receive_end.close()


def test_connection_context_manager_closes_endpoint():
    """__enter__ 返回自身，__exit__ 无论异常与否调用 close。"""

    left, right = multiprocessing.Pipe()

    with left as entered:
        assert entered is left
        left.send("value")

    assert left.closed is True
    assert right.recv() == "value"
    right.close()


def test_connection_wait_returns_only_ready_endpoints():
    """数据已 send 后用 timeout=0 检查，不依赖调度或 wall-clock delay。"""

    first_receive, first_send = multiprocessing.Pipe(duplex=False)
    second_receive, second_send = multiprocessing.Pipe(duplex=False)

    try:
        second_send.send("second")
        ready = multiprocessing.connection.wait(
            [first_receive, second_receive],
            timeout=0,
        )

        assert ready == [second_receive]
        assert second_receive.recv() == "second"
    finally:
        first_receive.close()
        first_send.close()
        second_receive.close()
        second_send.close()


# multiprocessing ``Queue``/``SimpleQueue``/``JoinableQueue`` lifecycle。
#
# Queue 用 pipe、locks 和 background feeder thread 传送 pickle；``put`` 返回时 bytes 可能
# 尚未进入 pipe，因此 ``empty/qsize`` 只近似，且 producer 在 feeder flush 前退出会影响
# join。SimpleQueue 没有 feeder，JoinableQueue 则以 task_done/join 追踪 unfinished tasks。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.multiprocessing.Queue
# polyglot-covers: python.multiprocessing.Queue-pickle-copy
# polyglot-covers: python.multiprocessing.Queue-background-feeder-thread
# polyglot-covers: python.multiprocessing.Queue.empty-unreliable
# polyglot-covers: python.multiprocessing.Queue.qsize-platform-caveat
# polyglot-covers: python.multiprocessing.Queue.put_nowait
# polyglot-covers: python.multiprocessing.Queue.get_nowait
# polyglot-covers: python.multiprocessing.Queue.Full
# polyglot-covers: python.multiprocessing.Queue.Empty
# polyglot-covers: python.multiprocessing.Queue.close
# polyglot-covers: python.multiprocessing.Queue.join_thread
# polyglot-covers: python.multiprocessing.Queue.cancel_join_thread
# polyglot-covers: python.multiprocessing.SimpleQueue
# polyglot-covers: python.multiprocessing.JoinableQueue
# polyglot-covers: python.multiprocessing.JoinableQueue.task_done
# polyglot-covers: python.multiprocessing.JoinableQueue.join
# polyglot-covers: python.multiprocessing.JoinableQueue-over-task-done




def test_queue_round_trip_returns_pickled_copy_and_nonblocking_errors():
    """full 由 maxsize semaphore 决定；empty/qsize 不用于 correctness protocol。"""

    work = multiprocessing.Queue(maxsize=1)
    payload = {"items": [1, 2]}

    try:
        work.put_nowait(payload)
        with pytest.raises(queue.Full):
            work.put_nowait("too-much")

        received = work.get(timeout=5)
        assert received == payload
        assert received is not payload
        assert received["items"] is not payload["items"]
        with pytest.raises(queue.Empty):
            work.get_nowait()
    finally:
        work.close()
        work.join_thread()

    with pytest.raises(ValueError, match="Queue.*closed"):
        work.put("after-close")


def test_cancel_join_thread_is_explicit_data_loss_tradeoff():
    """它只取消 process exit 时的隐式 feeder join；不代表 queue/feeder 已经关闭。"""

    work = multiprocessing.Queue()
    work.cancel_join_thread()

    work.put("still-usable")
    assert work.get(timeout=5) == "still-usable"
    work.close()


def test_simple_queue_has_synchronous_pipe_api_and_explicit_close():
    """SimpleQueue 没有 timeout/maxsize/task tracking；empty 在本例静态边界可观察。"""

    work = multiprocessing.SimpleQueue()

    assert work.empty() is True
    work.put([1, 2, 3])
    assert work.empty() is False
    assert work.get() == [1, 2, 3]
    assert work.empty() is True
    work.close()

    with pytest.raises(OSError):
        work.put("after-close")


def test_joinable_queue_requires_one_task_done_per_get():
    """join 等 unfinished counter 归零；多调用一次 task_done 是可检测的逻辑错误。"""

    work = multiprocessing.JoinableQueue()

    try:
        work.put("job")
        assert work.get(timeout=5) == "job"
        work.task_done()
        assert work.join() is None
        with pytest.raises(ValueError, match="task_done.*too many times"):
            work.task_done()
    finally:
        work.close()
        work.join_thread()


# multiprocessing synchronization API differences 与 cross-process coordination。
#
# 这些 primitive 基本复刻 threading，但 Lock/RLock/Semaphore 的参数名是 ``block``；负
# timeout 按零处理，unlocked Lock.release 抛 ValueError，RLock ownership 错误抛
# AssertionError。对象必须来自与 Process 兼容的 context，才能安全跨 process 共享。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.multiprocessing.Lock
# polyglot-covers: python.multiprocessing.Lock-acquire-block-parameter
# polyglot-covers: python.multiprocessing.Lock-negative-timeout-is-zero
# polyglot-covers: python.multiprocessing.Lock-release-valueerror
# polyglot-covers: python.multiprocessing.RLock
# polyglot-covers: python.multiprocessing.RLock-release-assertionerror
# polyglot-covers: python.multiprocessing.Semaphore
# polyglot-covers: python.multiprocessing.BoundedSemaphore
# polyglot-covers: python.multiprocessing.BoundedSemaphore-macos-caveat
# polyglot-covers: python.multiprocessing.Event
# polyglot-covers: python.multiprocessing.Condition
# polyglot-covers: python.multiprocessing.Condition.wait_for
# polyglot-covers: python.multiprocessing.Barrier
# polyglot-covers: python.multiprocessing.sync-context-manager
# polyglot-covers: python.multiprocessing.context-compatible-primitives




def _wait_for_shared_value(condition, value, connection):
    with condition:
        matched = condition.wait_for(lambda: value.value == 42, timeout=5)
        connection.send((matched, value.value))
    connection.close()


def _cross_process_barrier(barrier, connection):
    connection.send(barrier.wait(timeout=5))
    connection.close()


def test_lock_signature_and_errors_differ_from_threading_lock():
    """block=False 时 timeout 被忽略；block=True + negative timeout 立即返回 False。"""

    lock = multiprocessing.Lock()

    assert lock.acquire() is True
    assert lock.acquire(block=False, timeout=999) is False
    assert lock.acquire(block=True, timeout=-1) is False
    lock.release()
    with pytest.raises(ValueError, match="released too many times"):
        lock.release()


def test_rlock_is_recursive_but_unowned_release_uses_assertionerror():
    """同一 process/thread acquire 两次就必须 release 两次。"""

    lock = multiprocessing.RLock()

    with lock:
        assert lock.acquire(block=False) is True
        lock.release()

    with pytest.raises(AssertionError, match="attempt to release recursive lock"):
        lock.release()


def test_semaphore_permits_and_bounded_overrelease_detection():
    """macOS 无 sem_getvalue，BoundedSemaphore 无法区别 over-release，故只断言通用部分。"""

    semaphore = multiprocessing.Semaphore(1)
    assert semaphore.acquire(block=False) is True
    assert semaphore.acquire(block=False) is False
    semaphore.release()

    bounded = multiprocessing.BoundedSemaphore(1)
    if sys.platform == "darwin":
        bounded.acquire()
        bounded.release()
    else:
        with pytest.raises(ValueError, match="released too many times"):
            bounded.release()


def test_condition_and_value_coordinate_spawned_process():
    """Value 与 Condition 共用同一个 RLock，predicate/更新始终在同一 critical section。"""

    context = multiprocessing.get_context("spawn")
    lock = context.RLock()
    condition = context.Condition(lock)
    value = context.Value("i", 0, lock=lock)
    parent_connection, child_connection = context.Pipe()
    process = context.Process(
        target=_wait_for_shared_value,
        args=(condition, value, child_connection),
    )
    process.start()
    child_connection.close()

    with condition:
        value.value = 42
        condition.notify_all()

    assert parent_connection.poll(timeout=5)
    assert parent_connection.recv() == (True, 42)
    process.join(timeout=5)
    assert process.exitcode == 0
    parent_connection.close()
    process.close()


def test_barrier_assigns_unique_indices_across_parent_and_children():
    """三个 process 到齐才释放；返回 index 可选一个 participant 执行收尾。"""

    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(3)
    parent_connections = []
    processes = []

    for _ in range(2):
        parent_connection, child_connection = context.Pipe()
        process = context.Process(
            target=_cross_process_barrier,
            args=(barrier, child_connection),
        )
        process.start()
        child_connection.close()
        parent_connections.append(parent_connection)
        processes.append(process)

    parent_index = barrier.wait(timeout=5)
    child_indices = []
    for connection in parent_connections:
        assert connection.poll(timeout=5)
        child_indices.append(connection.recv())
        connection.close()
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0
        process.close()

    assert sorted([parent_index, *child_indices]) == [0, 1, 2]


# ``Value``/``Array``、``sharedctypes`` wrappers 与 compound-operation trap。
#
# Synchronized wrapper 只在单次 attribute/index access 时自动加锁；``value += 1`` 是读改写
# 三步，仍须显式 ``get_lock`` 包住整体。RawValue/RawArray 没有 lock。shared memory 中不可
# 存放供另一 process 解引用的 native pointer，因为每个 process address space 不同。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.multiprocessing.Value python.multiprocessing.Array
# polyglot-covers: python.multiprocessing.synchronized-wrapper
# polyglot-covers: python.multiprocessing.get_obj python.multiprocessing.get_lock
# polyglot-covers: python.multiprocessing.Value-compound-operation-not-atomic
# polyglot-covers: python.multiprocessing.Value-explicit-lock-atomic-update
# polyglot-covers: python.multiprocessing.Value-lock-false
# polyglot-covers: python.multiprocessing.Array-char-value-raw
# polyglot-covers: python.multiprocessing.sharedctypes
# polyglot-covers: python.multiprocessing.sharedctypes.RawValue
# polyglot-covers: python.multiprocessing.sharedctypes.RawArray
# polyglot-covers: python.multiprocessing.sharedctypes.Value
# polyglot-covers: python.multiprocessing.sharedctypes.Array
# polyglot-covers: python.multiprocessing.sharedctypes.copy
# polyglot-covers: python.multiprocessing.sharedctypes.synchronized
# polyglot-covers: python.multiprocessing.shared-memory-pointer-trap



class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _increment_with_wrapper_lock(counter, repetitions):
    for _ in range(repetitions):
        with counter.get_lock():
            counter.value += 1


def _square_shared_objects(number, text, points):
    with number.get_lock():
        number.value **= 2
    with text.get_lock():
        text.value = text.value.upper()
    with points.get_lock():
        for point in points:
            point.x **= 2
            point.y **= 2


def test_value_wrapper_exposes_underlying_ctypes_object_and_lock():
    """lock=False 直接返回 ctypes object，不再提供 get_obj/get_lock。"""

    synchronized = multiprocessing.Value("i", 7)
    raw = multiprocessing.Value("i", 9, lock=False)

    assert synchronized.value == 7
    assert synchronized.get_obj().value == 7
    assert synchronized.get_lock() is not None
    assert isinstance(raw, ctypes.c_int)
    assert raw.value == 9
    assert not hasattr(raw, "get_lock")


def test_explicit_wrapper_lock_makes_compound_increment_atomic_across_processes():
    """三名 child 各递增 500 次；lock 覆盖完整 read-modify-write。"""

    context = multiprocessing.get_context("spawn")
    counter = context.Value("i", 0)
    processes = [
        context.Process(
            target=_increment_with_wrapper_lock,
            args=(counter, 500),
        )
        for _ in range(3)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0
        process.close()

    assert counter.value == 1500


def test_char_array_distinguishes_nul_terminated_value_and_full_raw_storage():
    """Array('c') 保留 ctypes char array 的 value/raw semantics。"""

    text = multiprocessing.Array("c", b"hello\x00world")

    assert text.value == b"hello"
    assert text.raw == b"hello\x00world"
    with text.get_lock():
        text.value = b"hi"
    assert text.value == b"hi"


def test_shared_structure_and_array_are_mutated_by_spawned_child():
    """Structure fields 是 shared bytes；案例不存 pointer，只存可跨 address space 的值。"""

    context = multiprocessing.get_context("spawn")
    number = context.Value("i", 7)
    shared_lock = context.RLock()
    text = context.Array("c", b"hello world", lock=shared_lock)
    points = context.Array(
        _Point,
        [(2.0, -3.0), (4.0, 5.0)],
        lock=shared_lock,
    )
    process = context.Process(
        target=_square_shared_objects,
        args=(number, text, points),
    )

    process.start()
    process.join(timeout=5)

    assert process.exitcode == 0
    assert number.value == 49
    assert text.value == b"HELLO WORLD"
    assert [(point.x, point.y) for point in points] == [(4.0, 9.0), (16.0, 25.0)]
    process.close()


def test_sharedctypes_raw_copy_and_synchronized_adapter():
    """copy 产生新的 shared allocation；synchronized 为既有 ctypes object 加 wrapper。"""

    raw_point = multiprocessing.sharedctypes.RawValue(_Point, 1.5, 2.5)
    raw_numbers = multiprocessing.sharedctypes.RawArray("i", [1, 2, 3])
    copied_point = multiprocessing.sharedctypes.copy(raw_point)
    lock = multiprocessing.RLock()
    wrapped = multiprocessing.sharedctypes.synchronized(raw_numbers, lock)

    assert (raw_point.x, raw_point.y) == (1.5, 2.5)
    assert (copied_point.x, copied_point.y) == (1.5, 2.5)
    copied_point.x = 99.0
    assert raw_point.x == 1.5

    assert wrapped.get_obj() is raw_numbers
    assert wrapped.get_lock() is lock
    with wrapped:
        wrapped[1] = 20
    assert list(raw_numbers) == [1, 20, 3]


def test_sharedctypes_value_and_array_select_synchronized_or_raw_result():
    """sharedctypes.Value/Array 的 lock keyword 与 top-level factory 遵循同一规则。"""

    value = multiprocessing.sharedctypes.Value("d", 1.25)
    array = multiprocessing.sharedctypes.Array("h", [2, 4, 6])
    raw_value = multiprocessing.sharedctypes.Value("i", 8, lock=False)

    assert value.value == 1.25
    assert list(array) == [2, 4, 6]
    assert isinstance(raw_value, ctypes.c_int)
