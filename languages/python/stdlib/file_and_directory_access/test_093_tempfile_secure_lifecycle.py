"""093｜``tempfile`` 的安全创建、生命周期与清理责任。

高层对象把随机命名、关闭和删除组合成 context manager；低层 ``mkstemp`` / ``mkdtemp``
只负责安全创建，调用方仍必须关闭 descriptor 并删除路径。不要用已弃用的 ``mktemp``
做“先取名字、再创建”流程：两步之间存在其他进程抢占路径的竞态。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tempfile.TemporaryFile python.tempfile.binary-default
# polyglot-covers: python.tempfile.TemporaryFile.text-mode python.tempfile.context-manager
# polyglot-covers: python.tempfile.NamedTemporaryFile python.tempfile.delete-on-close
# polyglot-covers: python.tempfile.NamedTemporaryFile.delete-false python.tempfile.manual-cleanup
# polyglot-covers: python.tempfile.SpooledTemporaryFile python.tempfile.max-size
# polyglot-covers: python.tempfile.SpooledTemporaryFile.fileno-rollover
# polyglot-covers: python.tempfile.SpooledTemporaryFile.rollover python.tempfile.truncate
# polyglot-covers: python.tempfile.TemporaryDirectory python.tempfile.recursive-cleanup
# polyglot-covers: python.tempfile.TemporaryDirectory.cleanup
# polyglot-covers: python.tempfile.TemporaryDirectory.ignore-cleanup-errors
# polyglot-covers: python.tempfile.mkstemp python.tempfile.atomic-creation
# polyglot-covers: python.tempfile.mkstemp.non-inheritable-fd python.tempfile.fd-io
# polyglot-covers: python.tempfile.mkstemp.prefix-suffix python.tempfile.no-implicit-dot
# polyglot-covers: python.tempfile.str-bytes-domain python.tempfile.mixed-path-types
# polyglot-covers: python.tempfile.mkdtemp python.tempfile.mkdtemp-manual-cleanup
# polyglot-covers: python.tempfile.gettempdir python.tempfile.gettempdirb
# polyglot-covers: python.tempfile.gettempprefix python.tempfile.gettempprefixb
# polyglot-covers: python.tempfile.unique-names python.tempfile.mktemp-race-trap

import os
from pathlib import Path
import shutil
import tempfile

import pytest


def test_temporary_file_defaults_to_binary_update_mode(tmp_path):
    """默认 ``w+b`` 可读写 bytes；读取前必须像普通文件一样调整当前 offset。"""

    with tempfile.TemporaryFile(dir=tmp_path) as stream:
        assert stream.write(b"python\x00temp") == 11
        assert stream.tell() == 11
        stream.seek(0)
        assert stream.read() == b"python\x00temp"

    assert stream.closed is True


def test_temporary_file_text_options_require_an_explicit_text_mode(tmp_path):
    """encoding/errors/newline 交给 ``open`` 语义；文本内容不能写入默认 binary stream。"""

    with tempfile.TemporaryFile(
        mode="w+t",
        encoding="utf-8",
        errors="strict",
        newline="",
        dir=tmp_path,
    ) as stream:
        stream.write("甲\r\n乙")
        stream.seek(0)
        assert stream.read() == "甲\r\n乙"

    with tempfile.TemporaryFile(dir=tmp_path) as binary_stream:
        with pytest.raises(TypeError):
            binary_stream.write("text")


def test_temporary_file_name_visibility_is_intentionally_not_assumed(tmp_path):
    """TemporaryFile 在不同平台可能无 directory entry，也可能有名字；可移植代码只持有 stream。"""

    with tempfile.TemporaryFile(dir=tmp_path) as stream:
        stream.write(b"data")
        assert stream.closed is False

    assert stream.closed is True


def test_named_temporary_file_exposes_a_name_and_deletes_it_on_close(tmp_path):
    """需要把 pathname 交给只接受路径的 API 时使用 NamedTemporaryFile。"""

    with tempfile.NamedTemporaryFile(
        prefix="report-", suffix=".txt", dir=tmp_path
    ) as stream:
        path = Path(stream.name)
        stream.write(b"draft")
        stream.flush()
        stream.seek(0)

        assert path.parent == tmp_path
        assert path.name.startswith("report-")
        assert path.suffix == ".txt"
        assert stream.read() == b"draft"

    assert path.exists() is False


def test_named_temporary_file_delete_false_transfers_cleanup_to_the_caller(tmp_path):
    """delete=False 让路径越过 close 存活；生产代码应在 finally 中明确 unlink。"""

    stream = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=tmp_path
    )
    path = Path(stream.name)
    try:
        stream.write("交付给外部程序")
        stream.close()

        assert path.read_text(encoding="utf-8") == "交付给外部程序"
    finally:
        stream.close()
        path.unlink(missing_ok=True)

    assert path.exists() is False


def test_named_temporary_file_does_not_promise_cross_platform_reopen_rules(tmp_path):
    """Windows 对仍打开文件的共享删除规则不同；可移植流程先 close，再从公开 name 重开。"""

    stream = tempfile.NamedTemporaryFile(delete=False, dir=tmp_path)
    path = Path(stream.name)
    try:
        stream.write(b"portable")
        stream.close()

        with path.open("rb") as reopened:
            assert reopened.read() == b"portable"
    finally:
        stream.close()
        path.unlink(missing_ok=True)


def test_spooled_temporary_file_has_normal_seek_read_and_context_semantics(tmp_path):
    """调用方不需要判断内容仍在 memory 还是已转到磁盘；公开 file API 保持一致。"""

    with tempfile.SpooledTemporaryFile(max_size=32, dir=tmp_path) as stream:
        stream.write(b"small payload")
        stream.seek(6)
        assert stream.read() == b"payload"

    assert stream.closed is True


def test_spooled_temporary_file_preserves_data_after_size_rollover(tmp_path):
    """写入量超过 max_size 会自动 rollover，已写内容和当前位置不能丢失。"""

    with tempfile.SpooledTemporaryFile(max_size=4, dir=tmp_path) as stream:
        stream.write(b"12345")
        assert stream.tell() == 5
        stream.seek(0)
        assert stream.read() == b"12345"


def test_requesting_fileno_forces_a_spooled_file_to_roll_over(tmp_path):
    """内存 backend 没有真实 descriptor，因此 ``fileno()`` 本身就是显式落盘边界。"""

    with tempfile.SpooledTemporaryFile(max_size=1024, dir=tmp_path) as stream:
        stream.write(b"abc")
        descriptor = stream.fileno()
        stream.flush()

        assert isinstance(descriptor, int)
        assert os.fstat(descriptor).st_size == 3
        stream.seek(0)
        assert stream.read() == b"abc"


def test_explicit_rollover_is_idempotent_and_keeps_the_current_position(tmp_path):
    """可在交给需要真实文件的下游前主动 rollover；重复调用不应重置 offset。"""

    with tempfile.SpooledTemporaryFile(max_size=1024, dir=tmp_path) as stream:
        stream.write(b"abcdef")
        stream.seek(2)
        stream.rollover()
        stream.rollover()

        assert stream.tell() == 2
        assert stream.read() == b"cdef"


def test_spooled_file_truncate_uses_the_same_file_object_contract(tmp_path):
    """truncate 返回目标 size；它不负责把 cursor 自动移动到新文件末尾。"""

    with tempfile.SpooledTemporaryFile(max_size=2, dir=tmp_path) as stream:
        stream.write(b"abcdef")
        assert stream.truncate(3) == 3
        assert stream.tell() == 6
        stream.seek(0)
        assert stream.read() == b"abc"


def test_temporary_directory_recursively_cleans_nested_content(tmp_path):
    """context 退出时按目录树清理，而不要求调用方逐个 unlink/rmdir。"""

    with tempfile.TemporaryDirectory(prefix="workspace-", dir=tmp_path) as name:
        root = Path(name)
        nested = root / "cache" / "result.txt"
        nested.parent.mkdir()
        nested.write_text("result", encoding="utf-8")

        assert root.parent == tmp_path
        assert nested.read_text(encoding="utf-8") == "result"

    assert root.exists() is False


def test_temporary_directory_cleans_up_when_the_body_raises(tmp_path):
    """``__exit__`` 在异常传播前仍执行清理；它不会吞掉业务异常。"""

    root = None
    with pytest.raises(RuntimeError, match="failed"):
        with tempfile.TemporaryDirectory(dir=tmp_path) as name:
            root = Path(name)
            (root / "partial.txt").write_text("partial", encoding="utf-8")
            raise RuntimeError("failed")

    assert root is not None
    assert root.exists() is False


def test_temporary_directory_supports_explicit_idempotent_cleanup(tmp_path):
    """不使用 with 时必须主动 cleanup；重复调用不会把已释放资源重新创建。"""

    directory = tempfile.TemporaryDirectory(dir=tmp_path)
    root = Path(directory.name)
    (root / "item").touch()

    directory.cleanup()
    directory.cleanup()

    assert root.exists() is False


def test_python_310_ignore_cleanup_errors_keeps_normal_cleanup_semantics(tmp_path):
    """3.10 的 ignore_cleanup_errors 只改变失败策略，不代表跳过正常 recursive cleanup。"""

    with tempfile.TemporaryDirectory(
        dir=tmp_path, ignore_cleanup_errors=True
    ) as name:
        root = Path(name)
        (root / "item").touch()

    assert root.exists() is False


def test_mkstemp_returns_an_open_non_inheritable_descriptor(tmp_path):
    """mkstemp 已原子创建并打开文件；返回 fd 默认不会泄漏给 child process。"""

    descriptor, name = tempfile.mkstemp(dir=tmp_path)
    path = Path(name)
    try:
        assert path.exists() is True
        assert os.get_inheritable(descriptor) is False

        os.write(descriptor, b"abc")
        os.lseek(descriptor, 0, os.SEEK_SET)
        assert os.read(descriptor, 3) == b"abc"
    finally:
        os.close(descriptor)
        path.unlink(missing_ok=True)


def test_mkstemp_has_separate_close_and_unlink_responsibilities(tmp_path):
    """close(fd) 只释放打开资源，不删除 pathname；这是它与高层 context object 的关键差异。"""

    descriptor, name = tempfile.mkstemp(dir=tmp_path)
    path = Path(name)
    os.close(descriptor)

    try:
        assert path.exists() is True
    finally:
        path.unlink()

    assert path.exists() is False


def test_mkstemp_prefix_and_suffix_are_literal_name_fragments(tmp_path):
    """suffix 不会自动补 dot；想得到扩展名必须明确传 ``.json``。"""

    first_fd, first_name = tempfile.mkstemp(prefix="job-", suffix="json", dir=tmp_path)
    second_fd, second_name = tempfile.mkstemp(prefix="job-", suffix=".json", dir=tmp_path)
    try:
        assert Path(first_name).name.startswith("job-")
        assert Path(first_name).suffix == ""
        assert Path(first_name).name.endswith("json")
        assert Path(second_name).suffix == ".json"
    finally:
        os.close(first_fd)
        os.close(second_fd)
        Path(first_name).unlink(missing_ok=True)
        Path(second_name).unlink(missing_ok=True)


def test_tempfile_low_level_names_preserve_the_bytes_domain(tmp_path):
    """prefix/suffix/dir 全是 bytes 时结果也是 bytes，适合无法解码的底层文件系统名称。"""

    descriptor, name = tempfile.mkstemp(
        prefix=b"item-",
        suffix=b".bin",
        dir=os.fsencode(tmp_path),
    )
    try:
        assert isinstance(name, bytes)
        assert os.path.basename(name).startswith(b"item-")
        assert name.endswith(b".bin")
    finally:
        os.close(descriptor)
        os.unlink(name)


def test_tempfile_rejects_mixed_text_and_bytes_name_components(tmp_path):
    """混合域无法定义可靠返回类型，应先由调用方统一编码边界。"""

    with pytest.raises(TypeError):
        tempfile.mkstemp(prefix=b"bytes-", suffix=".txt", dir=tmp_path)


def test_mkdtemp_creates_a_directory_but_never_removes_it_for_the_caller(tmp_path):
    """mkdtemp 只返回 pathname；即使目录为空，也必须由调用方显式 rmtree/rmdir。"""

    name = tempfile.mkdtemp(prefix="build-", suffix=".work", dir=tmp_path)
    root = Path(name)
    try:
        (root / "nested").mkdir()
        (root / "nested" / "artifact").touch()

        assert root.is_dir()
        assert root.name.startswith("build-")
        assert root.name.endswith(".work")
    finally:
        shutil.rmtree(root)

    assert root.exists() is False


def test_temp_directory_and_prefix_helpers_have_explicit_text_and_bytes_variants():
    """不要通过修改 global ``tempfile.tempdir`` 偷换返回类型；使用公开的 b-suffixed helpers。"""

    assert isinstance(tempfile.gettempdir(), str)
    assert isinstance(tempfile.gettempdirb(), bytes)
    assert isinstance(tempfile.gettempprefix(), str)
    assert isinstance(tempfile.gettempprefixb(), bytes)


def test_secure_creators_choose_distinct_names_and_create_them_immediately(tmp_path):
    """名字不可预测且创建是 atomic；这避免 ``mktemp`` 的 check-then-create 抢占窗口。"""

    first_fd, first_name = tempfile.mkstemp(dir=tmp_path)
    second_fd, second_name = tempfile.mkstemp(dir=tmp_path)
    try:
        assert first_name != second_name
        assert Path(first_name).exists()
        assert Path(second_name).exists()

        with pytest.raises(FileExistsError):
            os.open(first_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    finally:
        os.close(first_fd)
        os.close(second_fd)
        Path(first_name).unlink(missing_ok=True)
        Path(second_name).unlink(missing_ok=True)
