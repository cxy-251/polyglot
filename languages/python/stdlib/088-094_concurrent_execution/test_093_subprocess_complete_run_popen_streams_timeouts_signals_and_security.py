"""093｜``subprocess.run``、CompletedProcess 与标准流重定向。

run 是能满足大多数同步调用时应优先使用的入口：它启动子进程、等待退出，并把参数、
退出码及可选捕获内容汇总成 CompletedProcess。默认不会捕获输出；PIPE、STDOUT 与
DEVNULL 分别表示新管道、合并到 stdout，以及丢弃到操作系统空设备。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.subprocess.run
# polyglot-covers: python.subprocess.CompletedProcess
# polyglot-covers: python.subprocess.CompletedProcess.args
# polyglot-covers: python.subprocess.CompletedProcess.returncode
# polyglot-covers: python.subprocess.CompletedProcess.stdout
# polyglot-covers: python.subprocess.CompletedProcess.stderr
# polyglot-covers: python.subprocess.CompletedProcess.check_returncode
# polyglot-covers: python.subprocess.PIPE
# polyglot-covers: python.subprocess.STDOUT
# polyglot-covers: python.subprocess.DEVNULL
# polyglot-covers: python.subprocess.capture-output




import subprocess
import sys
import pytest
import json
import os
from pathlib import Path
import io
import select
import signal
import fcntl
import stat

def _run_python_command(source, *arguments):
    return [sys.executable, "-c", source, *map(str, arguments)]


def test_run_returns_binary_captured_streams_and_original_arguments():
    command = _run_python_command(
        "import os; os.write(1, b'normal'); os.write(2, b'problem')"
    )

    completed = subprocess.run(command, capture_output=True, check=False)

    assert isinstance(completed, subprocess.CompletedProcess)
    assert completed.args == command
    assert completed.returncode == 0
    assert completed.stdout == b"normal"
    assert completed.stderr == b"problem"
    assert completed.check_returncode() is None


def test_stderr_can_be_combined_into_stdout_in_write_order():
    completed = subprocess.run(
        _run_python_command("import os; os.write(1, b'out|'); os.write(2, b'err')"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )

    assert completed.stdout == b"out|err"
    assert completed.stderr is None


def test_devnull_discards_output_without_creating_captured_attributes():
    completed = subprocess.run(
        _run_python_command("import os; os.write(1, b'out'); os.write(2, b'err')"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    assert completed.stdout is None
    assert completed.stderr is None


def test_completed_process_check_returncode_raises_for_nonzero_status():
    completed = subprocess.run(
        _run_python_command("raise SystemExit(7)"),
        capture_output=True,
        check=False,
    )

    with pytest.raises(subprocess.CalledProcessError) as raised:
        completed.check_returncode()

    assert raised.value.returncode == 7
    assert raised.value.cmd == completed.args


# subprocess 参数边界、二进制/文本模式、环境与工作目录。
#
# shell=False 时参数序列的每个元素就是一个 argv，不再由 shell 二次解析；空格和元字符
# 因此不需要 shell quoting。stdin/stdout/stderr 默认为二进制；text、encoding 或 errors
# 会在管道外包 TextIOWrapper。env 是子进程的整份环境映射，不是对父环境的增量补丁。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.args-sequence
# polyglot-covers: python.subprocess.shell-false-literal-arguments
# polyglot-covers: python.subprocess.run-input
# polyglot-covers: python.subprocess.binary-stream-mode
# polyglot-covers: python.subprocess.text-stream-mode
# polyglot-covers: python.subprocess.encoding
# polyglot-covers: python.subprocess.errors
# polyglot-covers: python.subprocess.universal_newlines
# polyglot-covers: python.subprocess.env-replacement
# polyglot-covers: python.subprocess.cwd
# polyglot-covers: python.subprocess.path-like-arguments



def _arguments_python_command(source, *arguments):
    return [Path(sys.executable), "-c", source, *arguments]


def test_argument_sequence_preserves_spaces_empty_strings_and_metacharacters():
    arguments = ["two words", "", "$(not-a-command)", "semi;colon"]
    completed = subprocess.run(
        _arguments_python_command(
            "import json, sys; print(json.dumps(sys.argv[1:]))",
            *arguments,
        ),
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(completed.stdout) == arguments


def test_binary_input_and_text_input_have_matching_output_types():
    source = "import sys; data = sys.stdin.buffer.read(); sys.stdout.buffer.write(data[::-1])"

    binary = subprocess.run(
        _arguments_python_command(source),
        input=b"abc",
        capture_output=True,
        check=True,
    )
    text = subprocess.run(
        _arguments_python_command(source),
        input="abc",
        capture_output=True,
        text=True,
        check=True,
    )

    assert binary.stdout == b"cba"
    assert text.stdout == "cba"


def test_encoding_and_errors_control_pipe_decoding():
    completed = subprocess.run(
        _arguments_python_command("import sys; sys.stdout.buffer.write(b'valid\\xff')"),
        stdout=subprocess.PIPE,
        encoding="ascii",
        errors="replace",
        check=True,
    )

    assert completed.stdout == "valid\N{REPLACEMENT CHARACTER}"
    assert isinstance(completed.stdout, str)


def test_universal_newlines_is_the_backward_compatible_text_alias():
    completed = subprocess.run(
        _arguments_python_command("print('line')"),
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )

    assert completed.stdout == "line\n"


def test_env_replaces_inheritance_and_cwd_accepts_path_like(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYGLOT_PARENT_ONLY", "parent")
    workdir = tmp_path / "child working directory"
    workdir.mkdir()
    (workdir / "marker.txt").write_text("inside", encoding="utf-8")

    child_env = os.environ.copy()
    child_env.pop("POLYGLOT_PARENT_ONLY")
    child_env["POLYGLOT_CHILD_ONLY"] = "child"
    source = (
        "import json, os, pathlib; "
        "print(json.dumps([os.getenv('POLYGLOT_PARENT_ONLY'), "
        "os.environ['POLYGLOT_CHILD_ONLY'], pathlib.Path('marker.txt').read_text()]))"
    )

    completed = subprocess.run(
        _arguments_python_command(source),
        cwd=workdir,
        env=child_env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(completed.stdout) == [None, "child", "inside"]


# checked subprocess API、异常对象与无效参数。
#
# check=True、check_call 和 check_output 把非零退出码转换成 CalledProcessError，并保留
# command、returncode 及已捕获的标准流。程序根本无法启动时则传播 OSError，而不是伪造
# 一个退出码。capture_output/input 是 run 的便利参数，不能再同时手工指定对应 PIPE。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.SubprocessError
# polyglot-covers: python.subprocess.CalledProcessError
# polyglot-covers: python.subprocess.CalledProcessError.cmd
# polyglot-covers: python.subprocess.CalledProcessError.returncode
# polyglot-covers: python.subprocess.CalledProcessError.output
# polyglot-covers: python.subprocess.CalledProcessError.stdout
# polyglot-covers: python.subprocess.CalledProcessError.stderr
# polyglot-covers: python.subprocess.run-check
# polyglot-covers: python.subprocess.call
# polyglot-covers: python.subprocess.check_call
# polyglot-covers: python.subprocess.check_output
# polyglot-covers: python.subprocess.start-failure-oserror
# polyglot-covers: python.subprocess.invalid-redirection-combinations




def _checked_python_command(source):
    return [sys.executable, "-c", source]


def test_run_check_error_retains_both_captured_streams():
    command = _checked_python_command(
        "import os; os.write(1, b'partial-out'); os.write(2, b'partial-err'); "
        "raise SystemExit(9)"
    )

    with pytest.raises(subprocess.CalledProcessError) as raised:
        subprocess.run(command, capture_output=True, check=True)

    error = raised.value
    assert error.cmd == command
    assert error.returncode == 9
    assert error.output == error.stdout == b"partial-out"
    assert error.stderr == b"partial-err"
    assert "exit status 9" in str(error)
    assert isinstance(error, subprocess.SubprocessError)


def test_call_check_call_and_check_output_express_distinct_policies():
    assert subprocess.call(_checked_python_command("raise SystemExit(4)")) == 4
    assert subprocess.check_call(_checked_python_command("pass")) == 0

    output = subprocess.check_output(
        _checked_python_command(
            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read().upper())"
        ),
        input=b"hello",
    )
    assert output == b"HELLO"

    with pytest.raises(subprocess.CalledProcessError) as raised:
        subprocess.check_output(_checked_python_command("print('kept'); raise SystemExit(3)"))
    assert raised.value.output == b"kept\n"


def test_missing_executable_propagates_oserror_instead_of_returning_status(tmp_path):
    missing = tmp_path / "definitely-missing-program"

    with pytest.raises(FileNotFoundError):
        subprocess.run([missing], check=False)


def test_run_rejects_conflicting_convenience_and_stream_arguments():
    command = _checked_python_command("pass")

    with pytest.raises(ValueError, match="stdout and stderr arguments"):
        subprocess.run(command, capture_output=True, stdout=subprocess.PIPE)
    with pytest.raises(ValueError, match="stdin and input arguments"):
        subprocess.run(command, input=b"", stdin=subprocess.PIPE)


# run/wait/communicate 的 timeout 语义与可靠清理。
#
# run 超时会 kill 并 wait 后再抛 TimeoutExpired；直接 communicate 超时则不会替调用者杀掉
# 子进程，规范清理流程是 kill 后再次 communicate。第二次 communicate 不会丢失第一次已读
# 输出。wait 超时也可安全重试。案例用 Event 或未关闭的 stdin 阻塞，不使用 sleep。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.TimeoutExpired
# polyglot-covers: python.subprocess.TimeoutExpired.cmd
# polyglot-covers: python.subprocess.TimeoutExpired.timeout
# polyglot-covers: python.subprocess.TimeoutExpired.output
# polyglot-covers: python.subprocess.TimeoutExpired.stdout
# polyglot-covers: python.subprocess.TimeoutExpired.stderr
# polyglot-covers: python.subprocess.run-timeout-kill-wait
# polyglot-covers: python.subprocess.Popen.wait-timeout-retry
# polyglot-covers: python.subprocess.Popen.communicate-timeout
# polyglot-covers: python.subprocess.communicate-timeout-output-preserved
# polyglot-covers: python.subprocess.communicate-timeout-manual-cleanup




def _timeout_python_command(source):
    return [sys.executable, "-c", source]


def test_run_timeout_kills_and_waits_before_reraising():
    command = _timeout_python_command(
        "import sys, threading; "
        "sys.stdout.write('ready'); sys.stdout.flush(); threading.Event().wait()"
    )

    with pytest.raises(subprocess.TimeoutExpired) as raised:
        subprocess.run(command, capture_output=True, text=True, timeout=1)

    error = raised.value
    assert error.cmd == command
    assert error.timeout == 1
    # 即便 text=True，TimeoutExpired 中已捕获的部分输出在 3.10 仍规定为 bytes。
    assert error.output == error.stdout == b"ready"
    assert error.stderr is None


def test_wait_timeout_leaves_process_alive_and_can_be_retried():
    process = subprocess.Popen(
        _timeout_python_command("import sys; sys.stdin.buffer.read()"),
        stdin=subprocess.PIPE,
    )
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=0)
        assert process.returncode is None

        process.stdin.close()
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_communicate_timeout_requires_kill_then_preserves_partial_output():
    process = subprocess.Popen(
        _timeout_python_command(
            "import sys, threading; "
            "sys.stdout.buffer.write(b'before-timeout'); sys.stdout.buffer.flush(); "
            "threading.Event().wait()"
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        with pytest.raises(subprocess.TimeoutExpired) as raised:
            process.communicate(timeout=1)

        assert raised.value.output == b"before-timeout"
        assert process.poll() is None
        process.kill()
        stdout, stderr = process.communicate()
        assert stdout == b"before-timeout"
        assert stderr == b""
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


# ``Popen`` 生命周期、属性、poll/wait 与 communicate。
#
# Popen 提供 run 下层的异步句柄。poll 只做状态快照，wait 等待退出，communicate 同时写入
# stdin、排空 stdout/stderr 并 wait，可避免多个 PIPE 互相填满造成死锁。Popen 作为 context
# manager 退出时关闭标准流并等待子进程，适合把资源生命周期限制在一个代码块内。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.Popen
# polyglot-covers: python.subprocess.Popen.args
# polyglot-covers: python.subprocess.Popen.pid
# polyglot-covers: python.subprocess.Popen.returncode
# polyglot-covers: python.subprocess.Popen.stdin
# polyglot-covers: python.subprocess.Popen.stdout
# polyglot-covers: python.subprocess.Popen.stderr
# polyglot-covers: python.subprocess.Popen.poll
# polyglot-covers: python.subprocess.Popen.wait
# polyglot-covers: python.subprocess.Popen.communicate
# polyglot-covers: python.subprocess.Popen-context-manager
# polyglot-covers: python.subprocess.Popen-text-pipes
# polyglot-covers: python.subprocess.communicate-drains-all-pipes



def _popen_python_command(source):
    return [sys.executable, "-c", source]


def test_popen_attributes_and_poll_reflect_a_live_then_finished_child():
    command = _popen_python_command("import sys; sys.stdin.buffer.read()")
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        assert process.args == command
        assert process.pid > 0
        assert process.poll() is None
        assert process.returncode is None

        process.stdin.close()
        assert process.wait(timeout=2) == 0
        assert process.poll() == process.returncode == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_communicate_writes_input_and_drains_stdout_and_stderr_together():
    source = (
        "import sys; data = sys.stdin.read(); "
        "sys.stdout.write(data.upper()); sys.stderr.write(str(len(data)))"
    )
    process = subprocess.Popen(
        _popen_python_command(source),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = process.communicate("hello")

    assert stdout == "HELLO"
    assert stderr == "5"
    assert process.returncode == 0
    assert isinstance(process.stdout, io.TextIOBase)


def test_popen_context_manager_closes_streams_and_waits_on_exit():
    with subprocess.Popen(
        _popen_python_command("print('finished')"),
        stdout=subprocess.PIPE,
        text=True,
    ) as process:
        stream = process.stdout
        assert stream.read() == "finished\n"

    assert process.returncode == 0
    assert stream.closed is True


# 无 shell pipeline、PIPE 容量与 ``communicate`` 排空策略。
#
# 多个 Popen 可用文件对象直接连成 pipeline；父进程必须关闭自己持有的中间 pipe 副本，
# 否则 EOF/SIGPIPE 传播可能被延后。PIPE 有限，先 wait 再读大量 stdout/stderr 可能死锁；
# communicate 会并行排空各流，但会把全部内容缓存在内存，只适合有界输出。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.shell-free-pipeline
# polyglot-covers: python.subprocess.pipeline-close-parent-copy
# polyglot-covers: python.subprocess.pipeline-returncodes
# polyglot-covers: python.subprocess.PIPE-finite-capacity
# polyglot-covers: python.subprocess.wait-pipe-deadlock-trap
# polyglot-covers: python.subprocess.communicate-multiple-pipes
# polyglot-covers: python.subprocess.communicate-memory-buffering
# polyglot-covers: python.subprocess.DEVNULL-stdin



def _pipeline_python_command(source):
    return [sys.executable, "-c", source]


def test_popen_objects_form_a_pipeline_without_invoking_a_shell():
    producer = subprocess.Popen(
        _pipeline_python_command("print('alpha'); print('beta')"),
        stdout=subprocess.PIPE,
    )
    consumer = subprocess.Popen(
        _pipeline_python_command(
            "import sys; "
            "sys.stdout.buffer.write(sys.stdin.buffer.read().upper())"
        ),
        stdin=producer.stdout,
        stdout=subprocess.PIPE,
    )
    # consumer 已复制读端；父进程不再需要自己的副本。大型真实 pipeline 中，这也让
    # consumer 提前退出时的 SIGPIPE 能传回 producer。
    producer.stdout.close()

    try:
        output, _ = consumer.communicate(timeout=2)
        producer_status = producer.wait(timeout=2)
    finally:
        for process in (producer, consumer):
            if process.poll() is None:
                process.kill()
                process.wait()

    assert output == b"ALPHA\nBETA\n"
    assert producer_status == consumer.returncode == 0


def test_communicate_drains_stdout_and_stderr_larger_than_typical_pipe_buffers():
    amount = 100_000
    source = (
        f"import os; os.write(1, b'o' * {amount}); "
        f"os.write(2, b'e' * {amount})"
    )
    process = subprocess.Popen(
        _pipeline_python_command(source),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 若先 wait，child 可能在第一个满 pipe 上停住，永远写不到第二个；communicate
    # 一边等待一边读两个 pipe。生产代码对无界输出应改为流式读取或写入文件。
    stdout, stderr = process.communicate(timeout=2)

    assert process.returncode == 0
    assert stdout == b"o" * amount
    assert stderr == b"e" * amount


def test_devnull_can_supply_immediate_eof_to_child_stdin():
    completed = subprocess.run(
        _pipeline_python_command(
            "import sys; print(len(sys.stdin.buffer.read()))"
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    assert completed.stdout == "0\n"


# POSIX 子进程信号、negative returncode 与新 session。
#
# send_signal 发送指定信号；terminate/kill 在 POSIX 分别对应 SIGTERM/SIGKILL。由信号 N
# 终止时 returncode 为 -N，不是 shell 的 128+N。start_new_session=True 在 exec 前调用
# setsid，常用于服务进程替代线程环境中不安全的 preexec_fn(os.setsid)。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.Popen.send_signal
# polyglot-covers: python.subprocess.Popen.terminate
# polyglot-covers: python.subprocess.Popen.kill
# polyglot-covers: python.subprocess.signal-negative-returncode
# polyglot-covers: python.subprocess.send-signal-finished-noop
# polyglot-covers: python.subprocess.start_new_session
# polyglot-covers: python.subprocess.preexec-fn-thread-deadlock-trap




_section_260_pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例演示 POSIX signal/session")


def _blocking_child(*, start_new_session=False):
    source = (
        "import os, sys, threading; "
        "print(os.getpid(), os.getsid(0), os.getpgrp(), flush=True); "
        "threading.Event().wait()"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", source],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=start_new_session,
    )
    readable, _, _ = select.select([process.stdout], [], [], 2)
    if not readable:
        process.kill()
        process.wait()
        process.stdout.close()
        raise AssertionError("child did not report readiness")
    line = process.stdout.readline()
    try:
        identity = tuple(map(int, line.split()))
        if len(identity) != 3:
            raise ValueError("expected pid, session id and process group")
    except ValueError:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        raise AssertionError(f"invalid child readiness record: {line!r}") from None
    return process, identity


@_section_260_pytestmark
def test_start_new_session_makes_child_its_session_and_process_group_leader():
    process, (pid, session_id, process_group) = _blocking_child(
        start_new_session=True
    )
    try:
        assert pid == process.pid
        assert session_id == process_group == process.pid

        process.terminate()
        assert process.wait(timeout=2) == -signal.SIGTERM
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()


@_section_260_pytestmark
def test_send_signal_and_kill_report_the_signal_as_negative_returncode():
    terminated, _ = _blocking_child()
    try:
        terminated.send_signal(signal.SIGTERM)
        assert terminated.wait(timeout=2) == -signal.SIGTERM
    finally:
        if terminated.poll() is None:
            terminated.kill()
            terminated.wait()
        terminated.stdout.close()

    killed, _ = _blocking_child()
    try:
        killed.kill()
        assert killed.wait(timeout=2) == -signal.SIGKILL
    finally:
        if killed.poll() is None:
            killed.kill()
            killed.wait()
        killed.stdout.close()


@_section_260_pytestmark
def test_send_signal_is_a_noop_after_exit_has_been_observed():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    assert process.wait(timeout=2) == 0

    assert process.send_signal(signal.SIGTERM) is None
    assert process.returncode == 0


# POSIX ``close_fds``、``pass_fds``、child umask 与 Linux pipesize。
#
# PEP 446 后新 fd 默认不可继承，Popen 又默认关闭 0/1/2 以外的描述符。pass_fds 是精确
# 白名单并强制 close_fds=True，避免把 secret/socket 意外泄漏给 child。umask 在 child
# exec 前生效而不改 parent。Python 3.10 的 pipesize 可在 Linux 调整 PIPE 容量。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.Popen.close_fds
# polyglot-covers: python.subprocess.Popen.pass_fds
# polyglot-covers: python.subprocess.pass-fds-forces-close-fds
# polyglot-covers: python.subprocess.file-descriptor-leak-prevention
# polyglot-covers: python.subprocess.Popen.umask
# polyglot-covers: python.subprocess.child-umask-parent-isolation
# polyglot-covers: python.subprocess.Popen.pipesize




_section_261_pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="案例使用 POSIX file descriptors",
)


@_section_261_pytestmark
def test_pass_fds_explicitly_exposes_one_pipe_to_the_child():
    read_fd, write_fd = os.pipe()
    process = None
    os.write(write_fd, b"explicit capability")
    os.close(write_fd)
    command = [
        sys.executable,
        "-c",
        "import os, sys; os.write(1, os.read(int(sys.argv[1]), 1000))",
        str(read_fd),
    ]

    try:
        with pytest.warns(RuntimeWarning, match="pass_fds overriding close_fds"):
            process = subprocess.Popen(
                command,
                pass_fds=(read_fd,),
                close_fds=False,
                stdout=subprocess.PIPE,
            )
        os.close(read_fd)
        read_fd = None
        stdout, _ = process.communicate(timeout=2)
    finally:
        if read_fd is not None:
            os.close(read_fd)
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()

    assert process.returncode == 0
    assert stdout == b"explicit capability"


@_section_261_pytestmark
def test_close_fds_removes_even_an_inheritable_unlisted_descriptor(tmp_path):
    low_fd = os.open(tmp_path / "source.bin", os.O_CREAT | os.O_RDONLY, 0o600)
    high_fd = fcntl.fcntl(low_fd, fcntl.F_DUPFD, 200)
    os.close(low_fd)
    os.set_inheritable(high_fd, True)
    source = (
        "import os, sys; fd = int(sys.argv[1]); "
        "\ntry: os.fstat(fd)"
        "\nexcept OSError: print('closed')"
        "\nelse: print('open')"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-c", source, str(high_fd)],
            close_fds=True,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        os.close(high_fd)

    assert completed.stdout == "closed\n"


@_section_261_pytestmark
def test_child_umask_controls_created_mode_without_changing_parent(tmp_path):
    result = tmp_path / "created-by-child.txt"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('data')",
            str(result),
        ],
        umask=0o077,
        check=True,
    )

    assert stat.S_IMODE(result.stat().st_mode) == 0o600


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or not hasattr(fcntl, "F_GETPIPE_SZ"),
    reason="pipesize introspection 仅在 Linux 提供",
)
@_section_261_pytestmark
def test_pipesize_requests_the_kernel_pipe_capacity():
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.buffer.read()"],
        stdin=subprocess.PIPE,
        pipesize=4096,
    )
    try:
        assert fcntl.fcntl(process.stdin.fileno(), fcntl.F_GETPIPE_SZ) == 4096
        process.stdin.close()
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if not process.stdin.closed:
            process.stdin.close()


# 显式 shell、安全边界与 legacy shell helpers。
#
# subprocess 默认不会隐式启用 shell；只有需要 shell builtin、pipeline 或 expansion 时才应
# shell=True。此时 command string 的 quoting 完全由调用者负责，绝不能拼接不可信输入。
# getstatusoutput/getoutput 也隐式使用 shell，只适合维护旧代码和受控的固定命令。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.shell-true
# polyglot-covers: python.subprocess.shell-expansion
# polyglot-covers: python.subprocess.shell-injection-responsibility
# polyglot-covers: python.subprocess.shell-command-not-found-status
# polyglot-covers: python.subprocess.getstatusoutput
# polyglot-covers: python.subprocess.getstatusoutput-trailing-newline-stripped
# polyglot-covers: python.subprocess.getoutput
# polyglot-covers: python.subprocess.legacy-shell-stderr-merged




_section_262_pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX /bin/sh 语法")


@_section_262_pytestmark
def test_shell_expansion_is_explicit_and_quoted_values_remain_data():
    environment = os.environ.copy()
    environment["POLYGLOT_VALUE"] = "literal; $(not-executed)"

    completed = subprocess.run(
        "printf '%s' \"$POLYGLOT_VALUE\"",
        shell=True,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout == environment["POLYGLOT_VALUE"]
    assert completed.stderr == ""


@_section_262_pytestmark
def test_shell_reports_missing_inner_command_as_status_not_start_oserror():
    completed = subprocess.run(
        "polyglot-command-that-does-not-exist",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    assert completed.returncode == 127


@_section_262_pytestmark
def test_getstatusoutput_returns_exitcode_and_strips_one_trailing_newline():
    status, output = subprocess.getstatusoutput("printf 'line\\n'; exit 7")

    assert status == 7
    assert output == "line"


@_section_262_pytestmark
def test_getoutput_ignores_status_and_combines_shell_stdout_and_stderr():
    output = subprocess.getoutput("printf 'out'; printf 'err' >&2; exit 5")

    assert output == "outerr"


# Popen constructor 的 executable/bufsize 与审计事件。
#
# executable 可替换实际执行文件，而 Popen.args 仍保留调用者传入的 argv；这是少见的高级
# 入口。text=True、bufsize=1 产生 line-buffered stdin，可用于简单请求/响应协议。每次创建
# 进程还会发出 subprocess.Popen audit event；审计 hook 不可移除，所以案例放在隔离子进程。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.subprocess.Popen.executable
# polyglot-covers: python.subprocess.executable-does-not-rewrite-args
# polyglot-covers: python.subprocess.Popen.bufsize
# polyglot-covers: python.subprocess.text-line-buffering
# polyglot-covers: python.subprocess.Popen-audit-event
# polyglot-covers: python.subprocess.Popen-audit-arguments
# polyglot-covers: python.subprocess.audit-hook-process-isolation



def test_executable_replaces_program_but_args_retains_original_argv():
    arguments = [
        "educational-display-name",
        "-c",
        "import sys; print(sys.argv[0])",
    ]

    completed = subprocess.run(
        arguments,
        executable=sys.executable,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.args == arguments
    assert completed.stdout == "-c\n"


def test_text_line_buffering_flushes_a_newline_to_a_waiting_child():
    source = (
        "import sys; line = sys.stdin.readline(); "
        "sys.stdout.write('ack:' + line); sys.stdout.flush()"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", source],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        assert process.stdin.line_buffering is True
        process.stdin.write("request\n")
        assert process.stdout.readline() == "ack:request\n"
        process.stdin.close()
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if not process.stdin.closed:
            process.stdin.close()
        process.stdout.close()


def test_popen_audit_event_exposes_launch_boundary_in_isolated_interpreter():
    source = """
import subprocess
import sys

seen = []


def audit(event, arguments):
    if event == "subprocess.Popen":
        seen.append(arguments)


sys.addaudithook(audit)
command = [sys.executable, "-c", "pass"]
subprocess.run(command, check=True)
executable, arguments, cwd, env = seen[0]
print(executable == sys.executable, arguments == command, cwd is None, env is None)
"""

    completed = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout == "True True True True\n"
