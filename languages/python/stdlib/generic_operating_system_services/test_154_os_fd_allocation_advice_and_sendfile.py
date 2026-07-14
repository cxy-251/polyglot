"""154｜``os`` 的预分配、访问建议、record lock 与 ``sendfile``。

这些接口把文件系统和 kernel 能力直接暴露给 Python。它们仍以 file descriptor
和 bytes 为边界。“函数存在”不等于当前 filesystem 一定实现；能力差异
应显式 skip，而不能误判为业务断言失败。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.posix-fallocate python.os.file-preallocation
# polyglot-covers: python.os.posix-fadvise python.os.POSIX_FADV_SEQUENTIAL
# polyglot-covers: python.os.lockf python.os.F_LOCK python.os.F_ULOCK
# polyglot-covers: python.os.sendfile python.os.sendfile-offset
# polyglot-covers: python.os.sendfile-short-count python.os.kernel-side-transfer

import errno
import os

import pytest


_CAPABILITY_ERRNOS = {
    errno.ENOSYS,
    errno.EINVAL,
    errno.EOPNOTSUPP,
}


@pytest.mark.skipif(
    not hasattr(os, "posix_fallocate"),
    reason="平台不提供 POSIX file allocation",
)
def test_posix_fallocate_reserves_space_and_extends_logical_size(tmp_path):
    """预分配可减少以后写入时的 ENOSPC 风险，并把文件扩展到给定范围。"""

    path = tmp_path / "allocated.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        try:
            assert os.posix_fallocate(fd, 0, 4096) is None
        except OSError as error:
            if error.errno in _CAPABILITY_ERRNOS:
                pytest.skip(f"filesystem 不支持 posix_fallocate: {error}")
            raise

        assert os.fstat(fd).st_size == 4096
        assert os.pwrite(fd, b"tail", 4092) == 4
    finally:
        os.close(fd)

    assert path.read_bytes().endswith(b"tail")


@pytest.mark.skipif(
    not hasattr(os, "posix_fadvise"),
    reason="平台不提供 POSIX file advice",
)
def test_posix_fadvise_is_a_hint_not_a_data_operation(tmp_path):
    """advice 只给 kernel 优化提示；成功返回 None，内容和 cursor 均不改变。"""

    path = tmp_path / "advice.bin"
    path.write_bytes(b"abcdef")
    fd = os.open(path, os.O_RDONLY)
    try:
        before = os.lseek(fd, 2, os.SEEK_SET)
        try:
            result = os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_SEQUENTIAL)
        except OSError as error:
            if error.errno in _CAPABILITY_ERRNOS:
                pytest.skip(f"filesystem 不支持 posix_fadvise: {error}")
            raise

        assert result is None
        assert os.lseek(fd, 0, os.SEEK_CUR) == before
    finally:
        os.close(fd)

    assert path.read_bytes() == b"abcdef"


@pytest.mark.skipif(not hasattr(os, "lockf"), reason="平台不提供 POSIX record locks")
def test_lockf_lock_and_unlock_wrap_a_descriptor_critical_section(tmp_path):
    """lockf 锁由进程和 byte range 定义；正常路径也必须在 finally 中解锁。"""

    path = tmp_path / "locked.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.lockf(fd, os.F_LOCK, 0)
        try:
            assert os.write(fd, b"protected") == 9
        finally:
            os.lockf(fd, os.F_ULOCK, 0)
    finally:
        os.close(fd)

    assert path.read_bytes() == b"protected"


@pytest.mark.skipif(not hasattr(os, "sendfile"), reason="平台不提供 sendfile")
def test_sendfile_uses_explicit_input_offset_and_returns_actual_count(tmp_path):
    """显式 offset 不推进 input fd cursor；output cursor 仍按实际传输量前进。"""

    source_path = tmp_path / "source.bin"
    target_path = tmp_path / "target.bin"
    source_path.write_bytes(b"0123456789")
    source = os.open(source_path, os.O_RDONLY)
    target = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.lseek(source, 8, os.SEEK_SET)
        sent = 0
        try:
            while sent < 5:
                count = os.sendfile(target, source, 2 + sent, 5 - sent)
                if count == 0:
                    break
                sent += count
        except OSError as error:
            if error.errno in _CAPABILITY_ERRNOS:
                pytest.skip(f"kernel/filesystem 不支持此 sendfile: {error}")
            raise

        assert sent == 5
        assert os.lseek(source, 0, os.SEEK_CUR) == 8
        assert os.lseek(target, 0, os.SEEK_CUR) == 5
    finally:
        os.close(target)
        os.close(source)

    assert target_path.read_bytes() == b"23456"
