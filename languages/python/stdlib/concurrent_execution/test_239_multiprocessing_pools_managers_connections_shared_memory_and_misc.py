"""239｜``multiprocessing.Pool`` apply/map families、initializer 与 worker recycling。

Pool methods 只能由创建它的 process 调用。``map`` 保序，``imap`` lazy，
``imap_unordered`` 不保证顺序；函数/参数需可 pickle。Pool 必须显式 close+join/terminate，
或用 context manager，不能依赖 garbage collection。``maxtasksperchild`` 可回收长期 worker。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Pool
# polyglot-covers: python.multiprocessing.Pool.apply
# polyglot-covers: python.multiprocessing.Pool.map
# polyglot-covers: python.multiprocessing.Pool.starmap
# polyglot-covers: python.multiprocessing.Pool.imap
# polyglot-covers: python.multiprocessing.Pool.imap_unordered
# polyglot-covers: python.multiprocessing.Pool-chunksize
# polyglot-covers: python.multiprocessing.Pool-initializer
# polyglot-covers: python.multiprocessing.Pool-context-manager
# polyglot-covers: python.multiprocessing.Pool.close
# polyglot-covers: python.multiprocessing.Pool.join
# polyglot-covers: python.multiprocessing.Pool-owner-process-only
# polyglot-covers: python.multiprocessing.Pool-picklable-callables
# polyglot-covers: python.multiprocessing.Pool.maxtasksperchild




import multiprocessing
import os
import pytest
from multiprocessing.managers import BaseManager
from multiprocessing.connection import Client
from multiprocessing.connection import Listener
from multiprocessing.connection import answer_challenge
from multiprocessing.connection import deliver_challenge
import queue
import threading
import multiprocessing.dummy
import multiprocessing.pool
import subprocess
import sys
from multiprocessing import shared_memory
import pickle
from multiprocessing.managers import SharedMemoryManager

_WORKER_LABEL = None


def _install_worker_label(label):
    global _WORKER_LABEL
    _WORKER_LABEL = label


def _square(value):
    return value * value


def _power(base, exponent):
    return base**exponent


def _labeled_square(value):
    return _WORKER_LABEL, value * value


def _worker_pid(value):
    return value, os.getpid()


def test_pool_apply_and_mapping_variants_return_expected_shapes():
    """imap 返回 iterator；unordered 只断言结果 multiset，不依赖 scheduling order。"""

    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=2) as pool:
        assert pool.apply(_power, args=(2, 5)) == 32
        assert pool.map(_square, range(5), chunksize=2) == [0, 1, 4, 9, 16]
        assert pool.starmap(_power, [(2, 3), (3, 2), (5, 1)]) == [8, 9, 5]
        assert list(pool.imap(_square, [3, 1, 2], chunksize=1)) == [9, 1, 4]
        unordered = list(pool.imap_unordered(_square, [3, 1, 2], chunksize=1))
        assert sorted(unordered) == [1, 4, 9]

    with pytest.raises(ValueError, match="Pool not running"):
        pool.apply(_square, args=(2,))


def test_pool_initializer_configures_each_worker_before_tasks():
    """initializer 参数也必须适合 context serialization；task 读取 worker-local global。"""

    context = multiprocessing.get_context("spawn")
    pool = context.Pool(
        processes=2,
        initializer=_install_worker_label,
        initargs=("ready",),
    )
    try:
        results = pool.map(_labeled_square, [1, 2, 3, 4], chunksize=1)
        assert results == [
            ("ready", 1),
            ("ready", 4),
            ("ready", 9),
            ("ready", 16),
        ]
    finally:
        pool.close()
        pool.join()


def test_maxtasksperchild_replaces_worker_after_configured_task_count():
    """单 worker、chunksize=1、每个 child 仅做一个 task，因此两个结果 pid 必须不同。"""

    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=1, maxtasksperchild=1) as pool:
        results = pool.map(_worker_pid, ["first", "second"], chunksize=1)

    assert [label for label, _ in results] == ["first", "second"]
    assert results[0][1] != results[1][1]


# 240｜Pool async results、timeout、callbacks 与 remote exception transport。
#
# ``apply_async/map_async`` 立即返回 AsyncResult；``get`` 才重抛 worker 异常。callback 在
# parent 的 result-handler thread 运行，必须快速且不能抛出。用 initializer 注入 Event，
# 可确定制造 pending result 并测试 TimeoutError，不用 sleep 猜 worker 调度。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.Pool.apply_async
# polyglot-covers: python.multiprocessing.Pool.map_async
# polyglot-covers: python.multiprocessing.pool.AsyncResult
# polyglot-covers: python.multiprocessing.AsyncResult.ready
# polyglot-covers: python.multiprocessing.AsyncResult.wait
# polyglot-covers: python.multiprocessing.AsyncResult.get
# polyglot-covers: python.multiprocessing.AsyncResult.successful
# polyglot-covers: python.multiprocessing.TimeoutError
# polyglot-covers: python.multiprocessing.pool-callback
# polyglot-covers: python.multiprocessing.pool-error-callback
# polyglot-covers: python.multiprocessing.pool-remote-exception
# polyglot-covers: python.multiprocessing.pool.RemoteTraceback
# polyglot-covers: python.multiprocessing.Pool.terminate




_POOL_GATE = None


def _install_pool_gate(gate):
    global _POOL_GATE
    _POOL_GATE = gate


def _wait_for_pool_gate(value):
    if not _POOL_GATE.wait(timeout=5):
        raise RuntimeError("pool gate timed out")
    return value


def _triple(value):
    return value * 3


def _fail_pool_task(message):
    raise ValueError(message)


def test_async_result_pending_success_and_timeout_protocol():
    """successful 只在 ready 后合法；wait 返回 None，get 返回 task value。"""

    context = multiprocessing.get_context("spawn")
    gate = context.Event()
    pool = context.Pool(
        processes=1,
        initializer=_install_pool_gate,
        initargs=(gate,),
    )
    result = pool.apply_async(_wait_for_pool_gate, args=(42,))

    try:
        assert result.ready() is False
        assert result.wait(timeout=0) is None
        with pytest.raises(ValueError, match="not ready"):
            result.successful()
        with pytest.raises(multiprocessing.TimeoutError):
            result.get(timeout=0)

        gate.set()
        assert result.get(timeout=5) == 42
        assert result.ready() is True
        assert result.successful() is True
    finally:
        gate.set()
        pool.close()
        pool.join()


def test_async_callbacks_run_for_success_and_error_paths():
    """get 建立 callback 已执行的完成边界；error_callback 收到 reconstructed exception。"""

    context = multiprocessing.get_context("spawn")
    successes = []
    failures = []

    with context.Pool(processes=1) as pool:
        successful = pool.apply_async(
            _triple,
            args=(7,),
            callback=successes.append,
            error_callback=failures.append,
        )
        failed = pool.apply_async(
            _fail_pool_task,
            args=("remote failure",),
            callback=successes.append,
            error_callback=failures.append,
        )

        assert successful.get(timeout=5) == 21
        with pytest.raises(ValueError, match="remote failure") as raised:
            failed.get(timeout=5)

    assert successes == [21]
    assert len(failures) == 1
    assert isinstance(failures[0], ValueError)
    assert str(failures[0]) == "remote failure"
    assert raised.value.__cause__.__class__.__name__ == "RemoteTraceback"


def test_map_async_returns_ordered_list_and_pool_terminate_is_explicit():
    """terminate 停止 worker 且丢弃未完成 task；正常结果先 get，再显式终止空闲 pool。"""

    context = multiprocessing.get_context("spawn")
    pool = context.Pool(processes=2)

    try:
        result = pool.map_async(_triple, [1, 2, 3], chunksize=1)
        assert result.get(timeout=5) == [3, 6, 9]
    finally:
        pool.terminate()
        pool.join()


# 241｜``multiprocessing.Manager`` server process、proxy semantics 与 nested state。
#
# Manager referent 活在独立 server process，调用 proxy method 会 IPC；可支持任意 picklable
# 类型和远端共享，但通常慢于 shared memory。普通 mutable object 嵌在 proxy container 中时，
# 取出后原地修改只改本地 copy；要重新赋值，或从一开始嵌套另一个 managed proxy。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.Manager
# polyglot-covers: python.multiprocessing.managers.SyncManager
# polyglot-covers: python.multiprocessing.manager-context-manager
# polyglot-covers: python.multiprocessing.manager-server-process
# polyglot-covers: python.multiprocessing.manager-list
# polyglot-covers: python.multiprocessing.manager-dict
# polyglot-covers: python.multiprocessing.manager-Namespace
# polyglot-covers: python.multiprocessing.manager-Queue
# polyglot-covers: python.multiprocessing.manager-Event
# polyglot-covers: python.multiprocessing.manager-Value
# polyglot-covers: python.multiprocessing.manager-Array
# polyglot-covers: python.multiprocessing.proxy-picklable
# polyglot-covers: python.multiprocessing.proxy-str-vs-repr
# polyglot-covers: python.multiprocessing.proxy-getvalue-copy
# polyglot-covers: python.multiprocessing.proxy-equality-trap
# polyglot-covers: python.multiprocessing.proxy-nested-regular-mutable-trap
# polyglot-covers: python.multiprocessing.nested-proxies
# polyglot-covers: python.multiprocessing.proxy-thread-safety-caveat



def _mutate_manager_proxies(shared_list, shared_dict, namespace, work, ready):
    shared_list.append("child")
    shared_dict["answer"] = 42
    namespace.owner = "child"
    work.put("message")
    ready.set()


def test_sync_manager_proxies_can_be_passed_to_spawned_process():
    """proxy 自身可 pickle；method call 在 manager server 执行而非复制整个 referent。"""

    context = multiprocessing.get_context("spawn")
    with multiprocessing.Manager() as manager:
        shared_list = manager.list(["parent"])
        shared_dict = manager.dict()
        namespace = manager.Namespace()
        work = manager.Queue()
        ready = manager.Event()
        number = manager.Value("i", 7)
        numbers = manager.Array("i", [1, 2, 3])
        process = context.Process(
            target=_mutate_manager_proxies,
            args=(shared_list, shared_dict, namespace, work, ready),
        )

        process.start()
        assert ready.wait(timeout=5)
        assert work.get(timeout=5) == "message"
        process.join(timeout=5)

        assert process.exitcode == 0
        assert list(shared_list) == ["parent", "child"]
        assert dict(shared_dict) == {"answer": 42}
        assert namespace.owner == "child"
        assert number.value == 7
        assert list(numbers) == [1, 2, 3]
        process.close()


def test_proxy_str_represents_referent_but_repr_and_equality_are_proxy_level():
    """显式 list(proxy) 或 _getvalue 才得到普通 list；不要依赖 proxy == referent。"""

    with multiprocessing.Manager() as manager:
        proxy = manager.list([1, 2, 3])

        assert str(proxy) == "[1, 2, 3]"
        assert "ListProxy" in repr(proxy)
        assert proxy != [1, 2, 3]

        snapshot = proxy._getvalue()
        assert snapshot == [1, 2, 3]
        snapshot.append(4)
        assert list(proxy) == [1, 2, 3]


def test_regular_mutable_nested_in_proxy_requires_reassignment():
    """list proxy 的 __getitem__ pickle 出 dict copy；本地原地修改不会自动通知 manager。"""

    with multiprocessing.Manager() as manager:
        outer = manager.list([{"count": 0}])

        local_copy = outer[0]
        local_copy["count"] = 1
        assert outer[0] == {"count": 0}

        outer[0] = local_copy
        assert outer[0] == {"count": 1}


def test_nested_managed_proxy_propagates_inner_mutation():
    """referent 可以保存另一个 picklable proxy；inner method call 直接到 inner referent。"""

    with multiprocessing.Manager() as manager:
        inner = manager.dict(count=0)
        outer = manager.list([inner])

        inner["count"] = 2

        assert outer[0]["count"] == 2
        outer[0]["count"] = 3
        assert inner["count"] == 3


# 242｜``BaseManager.register`` custom referent、exposed methods 与 client authentication。
#
# BaseManager 可在本地 IPC server 暴露自定义 object。``register`` 决定 typeid、factory 和
# 可调用的 public methods；未列入 exposed 的 API 不会穿透 proxy。authkey 用 HMAC 验证
# 同一 secret 的双方身份，但不加密 payload。案例使用 address=None 的本地最快 IPC family。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.managers.BaseManager
# polyglot-covers: python.multiprocessing.BaseManager.register
# polyglot-covers: python.multiprocessing.BaseManager-custom-type
# polyglot-covers: python.multiprocessing.BaseManager-exposed-methods
# polyglot-covers: python.multiprocessing.BaseManager.start
# polyglot-covers: python.multiprocessing.BaseManager.address
# polyglot-covers: python.multiprocessing.BaseManager.connect
# polyglot-covers: python.multiprocessing.BaseManager.shutdown
# polyglot-covers: python.multiprocessing.BaseProxy._callmethod
# polyglot-covers: python.multiprocessing.manager-return-by-value
# polyglot-covers: python.multiprocessing.AuthenticationError
# polyglot-covers: python.multiprocessing.manager-authkey
# polyglot-covers: python.multiprocessing.authkey-authenticates-not-encrypts




class _Calculator:
    def __init__(self, offset=0):
        self.offset = offset
        self._history = []

    def add(self, left, right):
        result = left + right + self.offset
        self._history.append(result)
        return result

    def history(self):
        return list(self._history)

    def secret(self):
        return "not exposed"


class _CalculatorManager(BaseManager):
    pass


class _CalculatorClient(BaseManager):
    pass


_CalculatorManager.register(
    "Calculator",
    _Calculator,
    exposed=("add", "history"),
)
_CalculatorClient.register("Calculator")


def test_custom_manager_proxy_exposes_only_registered_methods():
    """history 返回普通 list copy；改 snapshot 不会回写 referent。"""

    manager = _CalculatorManager(address=None, authkey=b"manager-secret")
    with manager as entered:
        assert entered is manager
        calculator = manager.Calculator(10)

        assert calculator.add(2, 3) == 15
        assert calculator._callmethod("add", (4, 5)) == 19
        snapshot = calculator.history()
        assert snapshot == [15, 19]
        snapshot.append(999)
        assert calculator.history() == [15, 19]
        with pytest.raises(AttributeError):
            calculator.secret()

        assert manager.address is not None


def test_separate_client_connects_with_matching_key_and_rejects_wrong_key():
    """所有连接都留在 manager 选择的 Unix socket/Windows pipe，不访问外部网络。"""

    manager = _CalculatorManager(address=None, authkey=b"correct-key")
    manager.start()
    try:
        client = _CalculatorClient(
            address=manager.address,
            authkey=b"correct-key",
        )
        client.connect()
        remote = client.Calculator(1)
        assert remote.add(20, 21) == 42

        wrong = _CalculatorClient(
            address=manager.address,
            authkey=b"wrong-key",
        )
        with pytest.raises(multiprocessing.AuthenticationError):
            wrong.connect()
    finally:
        manager.shutdown()


# 243｜``multiprocessing.connection`` Listener/Client 与 HMAC challenge helpers。
#
# Listener/Client 在 socket 或 Windows pipe 上提供 message-oriented Connection。这里仅用
# pytest 临时目录中的 AF_UNIX socket，不访问外部网络。auth challenge 验证共享 key，之后
# ``recv`` 仍会 unpickle 数据；认证不等于加密，也不能让恶意 authenticated peer 变安全。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.connection.Listener
# polyglot-covers: python.multiprocessing.connection.Listener-address
# polyglot-covers: python.multiprocessing.connection.Listener.last_accepted
# polyglot-covers: python.multiprocessing.connection.Listener.accept
# polyglot-covers: python.multiprocessing.connection.Listener-context-manager
# polyglot-covers: python.multiprocessing.connection.Client
# polyglot-covers: python.multiprocessing.connection-AF_UNIX-address
# polyglot-covers: python.multiprocessing.connection.deliver_challenge
# polyglot-covers: python.multiprocessing.connection.answer_challenge
# polyglot-covers: python.multiprocessing.connection-challenge-failure
# polyglot-covers: python.multiprocessing.connection-authenticated-pickle-risk




@pytest.mark.skipif(os.name != "posix", reason="案例使用临时 AF_UNIX socket")
def test_listener_and_client_exchange_authenticated_messages_on_unix_socket(tmp_path):
    """listener 在 client thread 启动前已 bind；双方 context manager 都确定 close。"""

    address = str(tmp_path / "multiprocessing-listener.sock")
    authkey = b"local-secret"
    results = queue.Queue()

    with Listener(address, family="AF_UNIX", authkey=authkey) as listener:
        def run_client():
            with Client(listener.address, family="AF_UNIX", authkey=authkey) as connection:
                connection.send({"request": 21})
                results.put(connection.recv())

        thread = threading.Thread(target=run_client)
        thread.start()

        with listener.accept() as connection:
            assert connection.recv() == {"request": 21}
            connection.send({"answer": 42})

        thread.join(timeout=2)
        assert thread.is_alive() is False
        assert results.get_nowait() == {"answer": 42}
        assert listener.address == address
        assert listener.last_accepted is not None


def test_deliver_and_answer_challenge_accept_same_authkey_over_pipe():
    """helpers 对任意 Connection 工作；Pipe 让测试不建立 socket。"""

    server, client = multiprocessing.Pipe()
    completed = threading.Event()

    def answer():
        answer_challenge(client, b"shared-key")
        completed.set()

    thread = threading.Thread(target=answer)
    thread.start()
    deliver_challenge(server, b"shared-key")

    assert completed.wait(timeout=2)
    thread.join()
    server.close()
    client.close()


def test_challenge_mismatch_raises_authentication_error_on_both_sides():
    """server 发 FAILURE，deliver/answer 两端都得到 AuthenticationError 而非静默继续。"""

    server, client = multiprocessing.Pipe()
    client_errors = queue.Queue()

    def answer_with_wrong_key():
        try:
            answer_challenge(client, b"wrong-key")
        except multiprocessing.AuthenticationError as error:
            client_errors.put(type(error))

    thread = threading.Thread(target=answer_with_wrong_key)
    thread.start()

    with pytest.raises(multiprocessing.AuthenticationError):
        deliver_challenge(server, b"correct-key")

    thread.join(timeout=2)
    assert client_errors.get_nowait() is multiprocessing.AuthenticationError
    server.close()
    client.close()


# 244｜multiprocessing misc introspection、logger 与 thread-backed dummy Pool。
#
# ``active_children`` 只看当前 process 的 live children，并顺带 reap 已结束 child。
# ``cpu_count`` 是机器 CPU 数，不一定等于 affinity 可用数。multiprocessing logger 不与普通
# root logger 传播。``multiprocessing.dummy`` 复用 Pool API 但执行于 threads，可接受 lambda。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.active_children
# polyglot-covers: python.multiprocessing.active-children-reaps-finished
# polyglot-covers: python.multiprocessing.cpu_count
# polyglot-covers: python.multiprocessing.cpu-count-vs-affinity
# polyglot-covers: python.multiprocessing.parent_process-main-none
# polyglot-covers: python.multiprocessing.daemon-process-no-children
# polyglot-covers: python.multiprocessing.get_logger
# polyglot-covers: python.multiprocessing.log_to_stderr
# polyglot-covers: python.multiprocessing.logger-no-root-propagation
# polyglot-covers: python.multiprocessing.logging-not-process-shared-lock
# polyglot-covers: python.multiprocessing.dummy
# polyglot-covers: python.multiprocessing.dummy.Pool
# polyglot-covers: python.multiprocessing.pool.ThreadPool
# polyglot-covers: python.multiprocessing.dummy-no-pickling



def _hold_child(started, release):
    started.set()
    if not release.wait(timeout=5):
        raise RuntimeError("parent did not release child")


def _no_op_child():
    return None


def _daemon_attempts_child(connection):
    try:
        child = multiprocessing.Process(target=_no_op_child)
        child.start()
    except AssertionError as error:
        connection.send(str(error))
    finally:
        connection.close()


def _thread_identity(value):
    return value, os.getpid(), threading.get_ident()


def test_active_children_contains_live_child_and_main_has_no_parent_process():
    """Event 让 child 保持 live；显式 join 仍是比依赖 active_children side effect 更清晰的清理。"""

    context = multiprocessing.get_context("spawn")
    started = context.Event()
    release = context.Event()
    process = context.Process(target=_hold_child, args=(started, release))
    process.start()
    assert started.wait(timeout=5)

    try:
        assert process in multiprocessing.active_children()
        assert multiprocessing.parent_process() is None
    finally:
        release.set()
        process.join(timeout=5)

    assert process not in multiprocessing.active_children()
    process.close()


def test_cpu_count_is_machine_capacity_not_current_affinity_limit():
    """Linux affinity 可能由 container/cgroup 限制；调度 worker 数应考虑实际可用 CPU。"""

    count = multiprocessing.cpu_count()

    assert isinstance(count, int)
    assert count >= 1
    if hasattr(os, "sched_getaffinity"):
        assert len(os.sched_getaffinity(0)) <= count


def test_daemonic_process_cannot_create_child_processes():
    """parent exit 会尝试终止 daemon children，因此禁止它们再产生无法可靠清理的 descendants。"""

    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe()
    process = context.Process(
        target=_daemon_attempts_child,
        args=(child_connection,),
        daemon=True,
    )

    process.start()
    child_connection.close()
    assert parent_connection.poll(timeout=5)
    message = parent_connection.recv()
    process.join(timeout=5)

    assert "daemonic processes are not allowed to have children" in message
    assert process.exitcode == 0
    parent_connection.close()
    process.close()


def test_log_to_stderr_adds_process_formatter_without_leaking_handler():
    """child interpreter 隔离 process-global logger 与 spawn logging flag。"""

    code = """
import logging
import multiprocessing

logger = multiprocessing.get_logger()
configured = multiprocessing.log_to_stderr(logging.WARNING)
configured.warning("teaching warning")
print(configured is logger, logger.propagate)
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.stdout.strip() == "True 0"
    assert "[WARNING/MainProcess] teaching warning" in completed.stderr


def test_dummy_pool_uses_threads_shares_pid_and_accepts_lambda():
    """没有 process serialization boundary；lambda 可执行，所有 worker 与 parent pid 相同。"""

    with multiprocessing.dummy.Pool(processes=2) as pool:
        assert isinstance(pool, multiprocessing.pool.ThreadPool)
        assert pool.map(lambda value: value * value, [1, 2, 3]) == [1, 4, 9]
        identities = pool.map(_thread_identity, ["a", "b", "c"])

    assert [value for value, _, _ in identities] == ["a", "b", "c"]
    assert {pid for _, pid, _ in identities} == {os.getpid()}


# 245｜``SharedMemory`` create/attach、memoryview alias 与 close/unlink lifecycle。
#
# SharedMemory 用 name 让不同 process attach 同一 volatile bytes。``close`` 只关闭本 object
# handle，``unlink`` 才请求销毁全局 block，而且所有参与者中只调用一次。``buf`` 是 live
# memoryview，close 前必须释放外部 view；否则 exported pointers 会触发 BufferError。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.shared_memory
# polyglot-covers: python.multiprocessing.shared_memory.SharedMemory
# polyglot-covers: python.multiprocessing.SharedMemory-create
# polyglot-covers: python.multiprocessing.SharedMemory-attach-by-name
# polyglot-covers: python.multiprocessing.SharedMemory-generated-name
# polyglot-covers: python.multiprocessing.SharedMemory-size
# polyglot-covers: python.multiprocessing.SharedMemory-buf
# polyglot-covers: python.multiprocessing.SharedMemory-memoryview-alias
# polyglot-covers: python.multiprocessing.SharedMemory-close
# polyglot-covers: python.multiprocessing.SharedMemory-unlink-once
# polyglot-covers: python.multiprocessing.SharedMemory-close-does-not-unlink
# polyglot-covers: python.multiprocessing.SharedMemory-duplicate-name-error
# polyglot-covers: python.multiprocessing.SharedMemory-missing-attach-error
# polyglot-covers: python.multiprocessing.SharedMemory-release-exported-views




def _modify_named_shared_memory(name):
    attached = shared_memory.SharedMemory(name=name)
    try:
        attached.buf[:5] = b"child"
    finally:
        attached.close()


def test_two_attachments_alias_same_bytes_and_size_is_ignored_on_attach():
    """request 16 bytes，实际 size 可因 page allocation 更大；attach 的 size=1 被忽略。"""

    owner = shared_memory.SharedMemory(create=True, size=16)
    attached = None
    try:
        assert isinstance(owner.name, str)
        assert owner.name
        assert owner.size >= 16
        assert isinstance(owner.buf, memoryview)

        owner.buf[:5] = b"hello"
        attached = shared_memory.SharedMemory(
            name=owner.name,
            create=False,
            size=1,
        )
        assert attached.size == owner.size
        assert bytes(attached.buf[:5]) == b"hello"

        attached.buf[:5] = b"world"
        assert bytes(owner.buf[:5]) == b"world"
    finally:
        if attached is not None:
            attached.close()
        owner.unlink()
        owner.close()


def test_spawned_process_attaches_by_name_and_mutates_without_pickle_copy():
    """child 只接收短 name；payload 不经过 Pipe/Queue serialization。"""

    owner = shared_memory.SharedMemory(create=True, size=8)
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=_modify_named_shared_memory, args=(owner.name,))

    try:
        owner.buf[:5] = b"start"
        process.start()
        process.join(timeout=5)

        assert process.exitcode == 0
        assert bytes(owner.buf[:5]) == b"child"
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        process.close()
        owner.unlink()
        owner.close()


def test_close_drops_one_handle_but_existing_attachment_keeps_block_accessible():
    """最后由仍存活的 attachment unlink；不要把 close 当作全局 delete。"""

    owner = shared_memory.SharedMemory(create=True, size=4)
    name = owner.name
    attached = shared_memory.SharedMemory(name=name)
    owner.buf[:] = b"data"

    owner.close()
    try:
        assert bytes(attached.buf) == b"data"
        third = shared_memory.SharedMemory(name=name)
        third.close()
    finally:
        attached.unlink()
        attached.close()

    with pytest.raises(FileNotFoundError):
        shared_memory.SharedMemory(name=name)


def test_duplicate_name_and_nonpositive_create_size_are_rejected():
    """create=True 是 exclusive allocation；已有 name 不会被悄悄复用或覆盖。"""

    owner = shared_memory.SharedMemory(create=True, size=1)
    try:
        with pytest.raises(FileExistsError):
            shared_memory.SharedMemory(name=owner.name, create=True, size=1)
    finally:
        owner.unlink()
        owner.close()

    with pytest.raises(ValueError, match="size must be a positive number"):
        shared_memory.SharedMemory(create=True, size=0)


def test_external_memoryview_must_be_released_before_shared_memory_close():
    """切片 view 也导出 pointer；release 后 SharedMemory.close 才能安全 unmap。"""

    owner = shared_memory.SharedMemory(create=True, size=8)
    view = owner.buf[2:6]

    try:
        view[:] = b"view"
        assert bytes(owner.buf) == b"\x00\x00view\x00\x00"
        with pytest.raises(BufferError, match="exported pointers"):
            owner.close()
    finally:
        view.release()
        owner.unlink()
        owner.close()


# 246｜``ShareableList`` supported scalars、fixed layout、capacity 与 name attachment。
#
# ShareableList 把有限 scalar types 直接编码进 shared memory，长度固定且不支持 slice 产生
# 新 list。元素可换类型，但 str/bytes 不能超过该 slot 初始化时预留容量。按 name attach 或
# pickle round trip 得到的是同一 backing block 的新 handle，不是 list snapshot。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.shared_memory.ShareableList
# polyglot-covers: python.multiprocessing.ShareableList-supported-types
# polyglot-covers: python.multiprocessing.ShareableList-index-assignment
# polyglot-covers: python.multiprocessing.ShareableList-type-change
# polyglot-covers: python.multiprocessing.ShareableList-fixed-length
# polyglot-covers: python.multiprocessing.ShareableList-no-slicing
# polyglot-covers: python.multiprocessing.ShareableList-slot-capacity
# polyglot-covers: python.multiprocessing.ShareableList.count
# polyglot-covers: python.multiprocessing.ShareableList.index
# polyglot-covers: python.multiprocessing.ShareableList.format
# polyglot-covers: python.multiprocessing.ShareableList.shm
# polyglot-covers: python.multiprocessing.ShareableList-attach-by-name
# polyglot-covers: python.multiprocessing.ShareableList-pickle-preserves-alias
# polyglot-covers: python.multiprocessing.ShareableList-cleanup




def test_shareable_list_preserves_supported_scalar_types_and_mutation():
    """bool 必须保持 bool 而不是 int；None 也有专门 encoding。"""

    values = shared_memory.ShareableList(
        ["text", b"bytes", -2.5, 7, None, True]
    )
    try:
        assert list(values) == ["text", b"bytes", -2.5, 7, None, True]
        assert [type(value) for value in values] == [
            str,
            bytes,
            float,
            int,
            type(None),
            bool,
        ]

        values[2] = "ice"
        values[3] = 42
        assert list(values)[2:4] == ["ice", 42]
        assert values.count(42) == 1
        assert values.index(True) == 5
        assert isinstance(values.format, str)
        assert values.shm.name
    finally:
        values.shm.unlink()
        values.shm.close()


def test_length_is_fixed_and_unsupported_values_or_slices_fail():
    """API 是 list-like 而非完整 list；没有 append，slice 也不创建新 ShareableList。"""

    values = shared_memory.ShareableList([1, 2, 3])
    try:
        assert len(values) == 3
        with pytest.raises(AttributeError):
            values.append(4)
        with pytest.raises(TypeError):
            _ = values[:]
        with pytest.raises(TypeError, match="type"):
            values[0] = {"not": "supported"}
    finally:
        values.shm.unlink()
        values.shm.close()


def test_string_or_bytes_replacement_cannot_exceed_slot_capacity():
    """slot 由初始 value 规划；写入失败后旧 value 保持不变。"""

    values = shared_memory.ShareableList(["short", b"bytes"])
    try:
        values[0] = "tiny"
        with pytest.raises(ValueError, match="exceeds available storage"):
            values[0] = "this replacement is much longer than the slot"
        assert values[0] == "tiny"

        with pytest.raises(ValueError, match="exceeds available storage"):
            values[1] = b"a much longer byte string"
        assert values[1] == b"bytes"
    finally:
        values.shm.unlink()
        values.shm.close()


def test_name_attachment_and_pickle_round_trip_alias_same_backing_block():
    """每个 attachment 都 close local handle，但全局 unlink 只由 owner 做一次。"""

    owner = shared_memory.ShareableList([0, 1, 2])
    attached = shared_memory.ShareableList(name=owner.shm.name)
    deserialized = pickle.loads(pickle.dumps(owner))

    try:
        attached[0] = 10
        deserialized[1] = 20

        assert list(owner) == [10, 20, 2]
        assert list(attached) == [10, 20, 2]
        assert list(deserialized) == [10, 20, 2]
    finally:
        attached.shm.close()
        deserialized.shm.close()
        owner.shm.unlink()
        owner.shm.close()


# 247｜``SharedMemoryManager`` ownership、managed blocks/lists 与 automatic unlink。
#
# SharedMemoryManager 启动专用 process 跟踪由它创建的 blocks。context exit 会对所有 tracked
# SharedMemory/ShareableList backing blocks 调 unlink，再关闭 manager；这适合集中 ownership，
# 避免多个 worker 争抢谁最后 unlink。返回对象仍是直接 shared-memory handle，不是 RPC proxy。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.multiprocessing.managers.SharedMemoryManager
# polyglot-covers: python.multiprocessing.SharedMemoryManager.start
# polyglot-covers: python.multiprocessing.SharedMemoryManager.shutdown
# polyglot-covers: python.multiprocessing.SharedMemoryManager-context-manager
# polyglot-covers: python.multiprocessing.SharedMemoryManager.SharedMemory
# polyglot-covers: python.multiprocessing.SharedMemoryManager.ShareableList
# polyglot-covers: python.multiprocessing.SharedMemoryManager-tracks-lifecycle
# polyglot-covers: python.multiprocessing.SharedMemoryManager-automatic-unlink
# polyglot-covers: python.multiprocessing.SharedMemoryManager-direct-memory-handle




def test_manager_context_creates_direct_handles_and_unlinks_them_on_exit():
    """先 close 当前 process handles；manager exit 负责唯一的 unlink ownership。"""

    with SharedMemoryManager() as manager:
        block = manager.SharedMemory(size=16)
        values = manager.ShareableList([1, 2, 3])
        block_name = block.name
        list_name = values.shm.name

        block.buf[:4] = b"data"
        values[1] = 20

        assert bytes(block.buf[:4]) == b"data"
        assert list(values) == [1, 20, 3]
        assert isinstance(block, shared_memory.SharedMemory)
        assert isinstance(values, shared_memory.ShareableList)

        block.close()
        values.shm.close()

    with pytest.raises(FileNotFoundError):
        shared_memory.SharedMemory(name=block_name)
    with pytest.raises(FileNotFoundError):
        shared_memory.ShareableList(name=list_name)


def test_explicit_start_and_shutdown_release_all_tracked_blocks():
    """不用 with 时必须把 shutdown 放在 finally；它同时停止 manager child。"""

    manager = SharedMemoryManager()
    manager.start()
    block = manager.SharedMemory(size=8)
    name = block.name

    try:
        block.buf[:] = b"12345678"
        assert bytes(block.buf) == b"12345678"
        block.close()
    finally:
        manager.shutdown()

    with pytest.raises(FileNotFoundError):
        shared_memory.SharedMemory(name=name)
