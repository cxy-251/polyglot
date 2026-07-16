"""171｜termios、tty 与 pty：可恢复的终端模式和伪终端工作流。

termios 暴露 POSIX tty 的七段属性结构，tty 提供 raw/cbreak 配方，pty 则创建
可由程序驱动的主从终端。案例只使用测试进程创建的伪终端；
每次修改都在
finally 中精确恢复并关闭描述符，不依赖宿主的 stdin 是否连接真实终端。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.termios python.termios.tcgetattr
# polyglot-covers: python.termios.attribute-layout python.termios.control-characters
# polyglot-covers: python.termios.tcsetattr python.termios.when-modes
# polyglot-covers: python.termios.tcdrain python.termios.tcflush python.termios.tcflow
# polyglot-covers: python.termios.file-object-fd python.termios.not-a-tty-error
# polyglot-covers: python.stdlib.tty python.tty.setraw python.tty.setcbreak
# polyglot-covers: python.tty.raw-flags python.tty.cbreak-flags
# polyglot-covers: python.tty.restore-in-finally
# polyglot-covers: python.stdlib.pty python.pty.openpty
# polyglot-covers: python.pty.master-slave-data python.pty.ttyname
# polyglot-covers: python.pty.fork python.pty.child-parent-return-values
# polyglot-covers: python.pty.spawn python.pty.spawn-callback-eof
# polyglot-covers: python.pty.wait-status

import contextlib
import errno
import os
import sys

import pytest


pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="termios、tty 和 pty 仅在 Unix 平台提供",
)

if os.name == "posix":
    import pty
    import termios
    import tty
else:
    pty = None
    termios = None
    tty = None


@contextlib.contextmanager
def pseudo_terminal():
    master, slave = pty.openpty()
    try:
        yield master, slave
    finally:
        os.close(master)
        os.close(slave)


def control_character_value(value):
    if isinstance(value, bytes):
        return value[0]
    return value


def test_termios_attribute_list_has_the_posix_seven_part_layout():
    with pseudo_terminal() as (_, slave):
        attributes = termios.tcgetattr(slave)

    assert isinstance(attributes, list)
    assert len(attributes) == 7
    iflag, oflag, cflag, lflag, ispeed, ospeed, control = attributes
    assert all(isinstance(flag, int) for flag in (iflag, oflag, cflag, lflag))
    assert isinstance(ispeed, int)
    assert isinstance(ospeed, int)
    assert isinstance(control, list)
    assert len(control) > max(termios.VMIN, termios.VTIME)
    # cc 多数元素是单字节 bytes；VMIN/VTIME 在不同 Unix 上也可能表现为整数。


def test_tcsetattr_changes_a_copy_and_finally_restores_the_original():
    with pseudo_terminal() as (_, slave):
        original = termios.tcgetattr(slave)
        changed = termios.tcgetattr(slave)
        changed[3] &= ~termios.ECHO
        try:
            assert termios.tcsetattr(slave, termios.TCSANOW, changed) is None
            current = termios.tcgetattr(slave)
            assert current[3] & termios.ECHO == 0
            assert original[3] & termios.ECHO
        finally:
            termios.tcsetattr(slave, termios.TCSADRAIN, original)

        assert termios.tcgetattr(slave) == original
    # 必须复制整份属性并恢复，不能猜测退出时应该把哪些位重新打开。


def test_termios_accepts_file_objects_with_real_fileno_methods():
    with pseudo_terminal() as (_, slave):
        duplicate = os.dup(slave)
        with os.fdopen(duplicate, "rb", buffering=0) as file_object:
            attributes = termios.tcgetattr(file_object)

    assert len(attributes) == 7


def test_termios_queue_and_flow_operations_work_on_a_pseudo_terminal():
    with pseudo_terminal() as (_, slave):
        assert termios.tcdrain(slave) is None
        assert termios.tcflush(slave, termios.TCIOFLUSH) is None
        assert termios.tcflow(slave, termios.TCOOFF) is None
        assert termios.tcflow(slave, termios.TCOON) is None

    assert len({
        termios.TCIFLUSH,
        termios.TCOFLUSH,
        termios.TCIOFLUSH,
    }) == 3
    assert len({
        termios.TCOOFF,
        termios.TCOON,
        termios.TCIOFF,
        termios.TCION,
    }) == 4
    # tcsendbreak 可能真实占用 0.25 秒以上，
    # 自动套件不为覆盖调用而制造等待。


def test_termios_rejects_regular_files_and_invalid_descriptors(tmp_path):
    path = tmp_path / "ordinary.txt"
    path.write_text("not a terminal", encoding="utf-8")
    with path.open("rb") as file_object:
        with pytest.raises(termios.error):
            termios.tcgetattr(file_object)

    with pytest.raises(ValueError, match="negative"):
        termios.tcgetattr(-1)
    # 合法 fd 但不是终端由系统调用报告 termios.error；负数还没进入系统调用，
    # 参数转换阶段就会抛 ValueError。


def test_tty_setraw_disables_line_discipline_and_sets_byte_reads():
    with pseudo_terminal() as (_, slave):
        original = termios.tcgetattr(slave)
        try:
            assert tty.setraw(slave, termios.TCSANOW) is None
            raw = termios.tcgetattr(slave)
        finally:
            termios.tcsetattr(slave, termios.TCSANOW, original)

    assert raw[3] & (
        termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG
    ) == 0
    assert raw[1] & termios.OPOST == 0
    assert control_character_value(raw[6][termios.VMIN]) == 1
    assert control_character_value(raw[6][termios.VTIME]) == 0


def test_tty_setcbreak_keeps_signal_processing_but_disables_line_buffering():
    with pseudo_terminal() as (_, slave):
        original = termios.tcgetattr(slave)
        try:
            assert tty.setcbreak(slave, termios.TCSANOW) is None
            cbreak = termios.tcgetattr(slave)
        finally:
            termios.tcsetattr(slave, termios.TCSANOW, original)

    assert cbreak[3] & (termios.ECHO | termios.ICANON) == 0
    if original[3] & termios.ISIG:
        assert cbreak[3] & termios.ISIG
    assert control_character_value(cbreak[6][termios.VMIN]) == 1
    assert control_character_value(cbreak[6][termios.VTIME]) == 0
    # cbreak 逐字节交付输入但仍处理 Ctrl-C；raw 连信号字符解释也关闭。


def test_openpty_returns_a_named_slave_and_bidirectional_byte_channel():
    with pseudo_terminal() as (master, slave):
        original = termios.tcgetattr(slave)
        try:
            tty.setraw(slave, termios.TCSANOW)
            os.write(slave, b"from-slave")
            assert os.read(master, 10_000) == b"from-slave"

            os.write(master, b"from-master")
            assert os.read(slave, 10_000) == b"from-master"
        finally:
            termios.tcsetattr(slave, termios.TCSANOW, original)

        assert os.isatty(slave) is True
        assert os.ttyname(slave)
    # raw 模式避免 ONLCR、回显和 canonical buffering 改写测试字节。


def test_pty_fork_gives_child_a_controlling_terminal_and_parent_a_master_fd():
    pid, master = pty.fork()
    if pid == 0:
        os.write(1, b"child-on-pty\n")
        os._exit(7)

    chunks = []
    try:
        while True:
            try:
                chunk = os.read(master, 1024)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(master)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 7
    assert b"child-on-pty" in b"".join(chunks)
    # child 分支 pid=0 且返回 fd 无效；parent 分支拿到 child pid 和 master fd。


def test_pty_spawn_callbacks_must_return_bytes_and_empty_bytes_signal_eof():
    captured = []

    def capture_output(descriptor):
        data = os.read(descriptor, 1024)
        captured.append(data)
        return data

    def no_parent_input(_descriptor):
        return b""

    status = pty.spawn(
        [sys.executable, "-c", "print('spawned-on-pty')"],
        master_read=capture_output,
        stdin_read=no_parent_input,
    )

    assert os.waitstatus_to_exitcode(status) == 0
    assert b"spawned-on-pty" in b"".join(captured)
    # 回调必须返回 bytes；stdin_read 的 b"" 只停止继续转发父进程输入，
    # master 仍会读到子进程输出，直到子进程自行退出。若 master_read 过早返回
    # b""，spawn 会关闭 PTY，尚未退出的子进程还可能收到 SIGHUP。
