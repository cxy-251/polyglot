"""032｜``tempfile`` 的临时文件、目录与资源所有权示例。

TemporaryFile/NamedTemporaryFile/TemporaryDirectory 用 context manager 管理生命周期；
mkstemp/mkdtemp 只负责安全创建，把关闭和删除责任交给调用者。所有案例都显式使用
pytest tmp_path 作为 dir，不污染系统临时目录。

内容基于 Python 3.10 tempfile 文档；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.tempfile python.tempfile.TemporaryFile
# polyglot-covers: python.tempfile.NamedTemporaryFile
# polyglot-covers: python.tempfile.TemporaryDirectory
# polyglot-covers: python.tempfile.SpooledTemporaryFile
# polyglot-covers: python.tempfile.mkstemp python.tempfile.mkdtemp
# polyglot-covers: python.tempfile.prefix-suffix-dir
# polyglot-covers: python.tempfile.automatic-cleanup python.tempfile.manual-cleanup
# polyglot-covers: python.tempfile.gettempdir python.tempfile.gettempprefix

import os
from pathlib import Path
import tempfile

import pytest


def test_temporary_file_defaults_to_binary_and_closes_on_context_exit(tmp_path):
    """TemporaryFile 默认 ``w+b``，可读写 bytes，并在退出 with 时关闭。"""

    with tempfile.TemporaryFile(dir=tmp_path) as handle:
        assert "b" in handle.mode
        assert handle.write(b"payload") == 7
        assert handle.tell() == 7
        handle.seek(0)
        assert handle.read() == b"payload"
        assert not handle.closed

    assert handle.closed

    with pytest.raises(ValueError, match="closed file"):
        handle.read()


def test_temporary_file_text_mode_requires_explicit_mode_and_encoding(tmp_path):
    """需要 str 时使用文本 mode，并像普通 open 一样声明 encoding/newline。"""

    with tempfile.TemporaryFile(
        mode="w+",
        encoding="utf-8",
        newline="\n",
        dir=tmp_path,
    ) as handle:
        assert handle.write("咖啡\n") == 3
        handle.seek(0)
        assert handle.read() == "咖啡\n"

        with pytest.raises(TypeError):
            handle.write(b"bytes")


def test_named_temporary_file_exposes_name_and_delete_true_removes_on_close(tmp_path):
    """NamedTemporaryFile 提供文件系统名称，默认 delete=True 随关闭删除。"""

    with tempfile.NamedTemporaryFile(
        mode="w+",
        encoding="utf-8",
        dir=tmp_path,
        prefix="report-",
        suffix=".txt",
    ) as handle:
        path = Path(handle.name)
        assert path.parent == tmp_path
        assert path.name.startswith("report-")
        assert path.suffix == ".txt"
        assert path.exists()

        handle.write("temporary")
        handle.seek(0)
        assert handle.read() == "temporary"

    assert not path.exists()

    # context 外不能把 name 当永久产物路径；跨平台也不要依赖文件仍打开时再次打开它。


def test_named_temporary_file_delete_false_allows_reopen_but_requires_cleanup(tmp_path):
    """delete=False 把路径生命周期转交调用者，适合必须按名称交接给另一个 API。"""

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=tmp_path,
        delete=False,
    )
    path = Path(handle.name)

    try:
        handle.write("handoff")
        handle.close()

        assert path.exists()
        assert path.read_text(encoding="utf-8") == "handoff"
    finally:
        if not handle.closed:
            handle.close()
        path.unlink(missing_ok=True)

    assert not path.exists()


def test_temporary_directory_recursively_cleans_nested_contents(tmp_path):
    """TemporaryDirectory 退出时删除其中全部文件和子目录。"""

    with tempfile.TemporaryDirectory(
        dir=tmp_path,
        prefix="workspace-",
        suffix="-cache",
    ) as name:
        directory = Path(name)
        nested = directory / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "data.txt").write_text("data", encoding="ascii")

        assert directory.parent == tmp_path
        assert directory.name.startswith("workspace-")
        assert directory.name.endswith("-cache")
        assert (nested / "data.txt").is_file()

    assert not directory.exists()


def test_temporary_directory_cleans_up_when_body_raises(tmp_path):
    """异常不会跳过 context manager 清理，原异常继续传播。"""

    directory = None

    with pytest.raises(RuntimeError, match="body failed"):
        with tempfile.TemporaryDirectory(dir=tmp_path) as name:
            directory = Path(name)
            (directory / "partial.txt").write_text("partial", encoding="ascii")
            raise RuntimeError("body failed")

    assert directory is not None
    assert not directory.exists()


def test_temporary_directory_cleanup_is_explicit_and_idempotent(tmp_path):
    """非 with 用法必须调用 cleanup；Python 3.10 可选择忽略清理权限错误。"""

    temporary = tempfile.TemporaryDirectory(
        dir=tmp_path,
        ignore_cleanup_errors=True,
    )
    directory = Path(temporary.name)
    (directory / "item.txt").write_text("item", encoding="ascii")

    temporary.cleanup()
    temporary.cleanup()

    assert not directory.exists()

    # 幂等不等于可以忘记调用；优先 with，只有生命周期跨作用域时才显式 cleanup。


def test_spooled_temporary_file_has_one_interface_before_and_after_rollover(tmp_path):
    """超过 max_size 后从内存滚动到磁盘，但读写/seek API 不变。"""

    with tempfile.SpooledTemporaryFile(
        max_size=8,
        mode="w+b",
        dir=tmp_path,
    ) as handle:
        handle.write(b"small")
        handle.seek(0)
        assert handle.read() == b"small"

        handle.seek(0, os.SEEK_END)
        handle.write(b"-and-larger")
        handle.seek(0)
        assert handle.read() == b"small-and-larger"
        assert isinstance(handle.fileno(), int)

    # 不检查私有 `_file` 类型；是否落盘是实现细节，公共文件接口才是调用契约。


def test_spooled_temporary_file_can_rollover_explicitly(tmp_path):
    """rollover/fileno 适合下游必须接收真实文件描述符的边界。"""

    with tempfile.SpooledTemporaryFile(
        max_size=1024,
        mode="w+",
        encoding="utf-8",
        dir=tmp_path,
    ) as handle:
        handle.write("text")
        handle.rollover()

        descriptor = handle.fileno()
        assert isinstance(descriptor, int)
        handle.seek(0)
        assert handle.read() == "text"


def test_mkstemp_returns_open_fd_and_path_both_owned_by_caller(tmp_path):
    """mkstemp 原子创建并打开文件；调用者必须分别 close fd 和 unlink path。"""

    descriptor, name = tempfile.mkstemp(
        dir=tmp_path,
        prefix="packet-",
        suffix=".bin",
    )
    path = Path(name)

    try:
        assert path.exists()
        assert path.parent == tmp_path
        assert path.name.startswith("packet-")
        assert path.suffix == ".bin"

        assert os.write(descriptor, b"abc") == 3
        assert os.lseek(descriptor, 0, os.SEEK_SET) == 0
        assert os.read(descriptor, 3) == b"abc"
    finally:
        os.close(descriptor)
        path.unlink(missing_ok=True)

    assert not path.exists()


def test_mkdtemp_returns_directory_path_with_manual_cleanup_responsibility(tmp_path):
    """mkdtemp 只安全创建目录并返回名称，不提供自动递归清理对象。"""

    name = tempfile.mkdtemp(
        dir=tmp_path,
        prefix="manual-",
        suffix="-dir",
    )
    directory = Path(name)
    nested = directory / "nested"
    file_path = nested / "item.txt"

    try:
        nested.mkdir()
        file_path.write_text("data", encoding="ascii")
        assert file_path.is_file()
    finally:
        file_path.unlink(missing_ok=True)
        if nested.exists():
            nested.rmdir()
        if directory.exists():
            directory.rmdir()

    assert not directory.exists()


def test_temp_directory_and_prefix_helpers_have_stable_types():
    """默认临时位置由平台选择；代码不应硬编码 `/tmp` 或名称前缀。"""

    directory = tempfile.gettempdir()
    directory_bytes = tempfile.gettempdirb()
    prefix = tempfile.gettempprefix()
    prefix_bytes = tempfile.gettempprefixb()

    assert isinstance(directory, str)
    assert isinstance(directory_bytes, bytes)
    assert os.fsdecode(directory_bytes) == directory
    assert isinstance(prefix, str) and prefix
    assert isinstance(prefix_bytes, bytes) and prefix_bytes
    assert os.fsdecode(prefix_bytes) == prefix

    # gettempdir 结果会缓存；测试需要隔离位置时直接给创建函数传 dir=tmp_path。


def test_secure_creation_apis_create_unique_existing_paths(tmp_path):
    """安全 API 在返回名称前已经原子创建对象，避免“先取名、后创建”的竞态。"""

    first_fd, first_name = tempfile.mkstemp(dir=tmp_path)
    second_fd, second_name = tempfile.mkstemp(dir=tmp_path)

    try:
        assert first_name != second_name
        assert Path(first_name).exists()
        assert Path(second_name).exists()
    finally:
        os.close(first_fd)
        os.close(second_fd)
        Path(first_name).unlink(missing_ok=True)
        Path(second_name).unlink(missing_ok=True)

    # tempfile.mktemp() 只生成未占用名字，攻击者可在随后 open 前抢占；不要使用它。
