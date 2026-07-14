"""234｜Process exitcode 分类、terminate/kill 风险与 authentication key。

正常 return→0，``sys.exit(N)``→N，未捕获异常→1，Unix signal termination→负 signal。
terminate/kill 不运行 finally，且可能破坏 child 正在使用的 queue/lock/pipe；本例只终止
阻塞在专用 Pipe 的 disposable child。authkey 必须是 bytes，并默认由 parent 继承。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import multiprocessing
import os
import signal
import sys

import pytest


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
    with pytest.raises(TypeError, match="byte string"):
        process.authkey = "text-secret"
