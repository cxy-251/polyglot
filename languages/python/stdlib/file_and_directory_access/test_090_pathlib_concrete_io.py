"""090｜``pathlib.Path`` 目录、文件 I/O 与基础状态变更。

Path 继承纯路径的词法 API，并增加真实系统调用。所有案例只在 pytest tmp_path 下工作；
目录枚举不依赖系统返回顺序，权限只检查 chmod 后的 mode bits，不访问真实用户目录。
write_text/write_bytes 会覆盖同名文件，mkdir/touch/unlink 则通过选项明确幂等边界。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.pathlib.Path python.pathlib.concrete-platform-flavour
# polyglot-covers: python.pathlib.Path.cwd python.pathlib.Path.home python.pathlib.expanduser
# polyglot-covers: python.pathlib.mkdir python.pathlib.mkdir-parents python.pathlib.mkdir-exist-ok
# polyglot-covers: python.pathlib.open python.pathlib.open-modes
# polyglot-covers: python.pathlib.write_text python.pathlib.read_text python.pathlib.python310-newline
# polyglot-covers: python.pathlib.write_bytes python.pathlib.read_bytes python.pathlib.overwrite
# polyglot-covers: python.pathlib.touch python.pathlib.touch-exist-ok
# polyglot-covers: python.pathlib.exists python.pathlib.is_file python.pathlib.is_dir
# polyglot-covers: python.pathlib.special-file-predicates python.pathlib.missing-predicate-false
# polyglot-covers: python.pathlib.iterdir python.pathlib.iterdir-order
# polyglot-covers: python.pathlib.stat python.pathlib.lstat python.pathlib.stat-fresh-lookup
# polyglot-covers: python.pathlib.chmod python.pathlib.permissions
# polyglot-covers: python.pathlib.unlink python.pathlib.unlink-missing-ok
# polyglot-covers: python.pathlib.rmdir python.pathlib.remove-kind-boundary
# polyglot-covers: python.pathlib.rename python.pathlib.replace python.pathlib.rename-return
# polyglot-covers: python.pathlib.resolve python.pathlib.resolve-strict

import os
from pathlib import Path, PosixPath, WindowsPath
import stat

import pytest


def test_path_selects_the_concrete_flavour_for_the_running_platform(tmp_path):
    """Path 是 factory-like concrete class，结果 flavour 与宿主系统一致并可直接 I/O。"""

    path = Path(tmp_path, "example.txt")

    assert isinstance(path, Path)
    assert isinstance(path, PosixPath if os.name == "posix" else WindowsPath)
    assert os.fspath(path).endswith("example.txt")


def test_cwd_and_home_can_be_isolated_to_temporary_locations(tmp_path, monkeypatch):
    """测试不依赖真实用户目录：临时改变 cwd/HOME 后，两个 classmethod 返回对应 Path。"""

    working = tmp_path / "working"
    home = tmp_path / "home"
    working.mkdir()
    home.mkdir()
    monkeypatch.chdir(working)
    monkeypatch.setenv("HOME", str(home))

    assert Path.cwd() == working
    assert Path.home() == home
    assert Path("~/documents").expanduser() == home / "documents"


def test_mkdir_default_requires_an_existing_parent(tmp_path):
    """parents=False 只创建最后一层，缺失 parent 会抛 FileNotFoundError。"""

    target = tmp_path / "missing" / "child"

    with pytest.raises(FileNotFoundError):
        target.mkdir()


def test_mkdir_parents_creates_a_tree_and_exist_ok_makes_retry_idempotent(tmp_path):
    """parents=True 类似 mkdir -p；exist_ok=True 只忽略最后目标已经是 directory 的情况。"""

    target = tmp_path / "one" / "two" / "three"

    assert target.mkdir(parents=True) is None
    assert target.is_dir()
    assert target.mkdir(parents=True, exist_ok=True) is None

    with pytest.raises(FileExistsError):
        target.mkdir(exist_ok=False)


def test_mkdir_exist_ok_does_not_accept_an_existing_regular_file(tmp_path):
    """同名 file 不是已经满足的 directory，exist_ok=True 仍必须失败。"""

    target = tmp_path / "not-a-directory"
    target.write_text("content", encoding="utf-8")

    with pytest.raises(FileExistsError):
        target.mkdir(exist_ok=True)


def test_write_and_read_text_round_trip_explicit_encoding(tmp_path):
    """显式 encoding 让结果不依赖 locale；write_text 返回写入的字符数而非 byte 数。"""

    path = tmp_path / "message.txt"
    text = "你好，Python"

    written = path.write_text(text, encoding="utf-8")

    assert written == len(text)
    assert path.read_text(encoding="utf-8") == text
    assert len(path.read_bytes()) > written


def test_python_310_write_text_newline_controls_translation(tmp_path):
    """3.10 新增 newline；指定 CRLF 后，输入中的 \n 以两个 bytes 写入。"""

    path = tmp_path / "windows-lines.txt"

    path.write_text("first\nsecond\n", encoding="ascii", newline="\r\n")

    assert path.read_bytes() == b"first\r\nsecond\r\n"


def test_write_text_overwrites_an_existing_file(tmp_path):
    """便利方法等价于 mode='w'，不是 append；第二次写会 truncate 原内容。"""

    path = tmp_path / "state.txt"
    path.write_text("old data", encoding="utf-8")
    path.write_text("new", encoding="utf-8")

    assert path.read_text(encoding="utf-8") == "new"


def test_write_and_read_bytes_preserve_arbitrary_binary_data(tmp_path):
    """bytes API 不做编码/换行转换，返回值是实际写入 byte 数。"""

    path = tmp_path / "payload.bin"
    payload = bytes([0, 1, 2, 255])

    assert path.write_bytes(payload) == 4
    assert path.read_bytes() == payload


def test_write_bytes_overwrites_instead_of_appending(tmp_path):
    """和 write_text 一样，write_bytes 重新以 wb 打开并清空旧文件。"""

    path = tmp_path / "payload.bin"
    path.write_bytes(b"abcdef")
    path.write_bytes(b"xy")

    assert path.read_bytes() == b"xy"


def test_path_open_exposes_normal_file_modes_and_context_management(tmp_path):
    """open 转交 builtins.open 参数；需要 append/exclusive 等模式时用它而非 read/write 便利方法。"""

    path = tmp_path / "events.txt"

    with path.open("x", encoding="utf-8") as stream:
        assert stream.write("first\n") == 6
    with path.open("a", encoding="utf-8") as stream:
        stream.write("second\n")
    with path.open("r", encoding="utf-8") as stream:
        assert stream.readlines() == ["first\n", "second\n"]

    with pytest.raises(FileExistsError):
        path.open("x").close()


def test_touch_creates_an_empty_file_and_exist_ok_controls_collision(tmp_path):
    """默认 exist_ok=True 适合确保存在；False 可检测意外覆盖。"""

    path = tmp_path / "marker"

    assert path.touch() is None
    assert path.is_file()
    assert path.read_bytes() == b""
    assert path.touch(exist_ok=True) is None

    with pytest.raises(FileExistsError):
        path.touch(exist_ok=False)


def test_exists_is_file_and_is_dir_distinguish_path_kinds(tmp_path):
    """exists 只说明有对象；后续操作前通常还要区分 regular file 与 directory。"""

    file_path = tmp_path / "file.txt"
    directory = tmp_path / "folder"
    missing = tmp_path / "missing"
    file_path.write_text("x", encoding="utf-8")
    directory.mkdir()

    assert (file_path.exists(), file_path.is_file(), file_path.is_dir()) == (True, True, False)
    assert (directory.exists(), directory.is_file(), directory.is_dir()) == (True, False, True)
    assert (missing.exists(), missing.is_file(), missing.is_dir()) == (False, False, False)


def test_special_file_predicates_are_false_for_regular_files_and_missing_paths(tmp_path):
    """is_socket/is_fifo/device 不因“存在”就成立；缺失路径也统一返回 False。"""

    regular = tmp_path / "regular"
    missing = tmp_path / "missing"
    regular.touch()

    predicates = [Path.is_socket, Path.is_fifo, Path.is_block_device, Path.is_char_device]

    assert all(predicate(regular) is False for predicate in predicates)
    assert all(predicate(missing) is False for predicate in predicates)


def test_iterdir_yields_direct_children_without_dot_entries_or_order_guarantee(tmp_path):
    """系统顺序任意，断言前应按 name 排序；递归需求应使用 glob/rglob。"""

    (tmp_path / "b.txt").touch()
    (tmp_path / "a.txt").touch()
    (tmp_path / "folder").mkdir()

    children = sorted(tmp_path.iterdir(), key=lambda path: path.name)

    assert [path.name for path in children] == ["a.txt", "b.txt", "folder"]
    assert all(path.parent == tmp_path for path in children)


def test_stat_is_looked_up_again_on_each_call(tmp_path):
    """Path 不缓存 stat_result；文件变化后下一次 stat 反映新 size。"""

    path = tmp_path / "growing.bin"
    path.write_bytes(b"abc")
    first = path.stat()
    path.write_bytes(b"abcdefgh")
    second = path.stat()

    assert first.st_size == 3
    assert second.st_size == 8
    assert first is not second


def test_lstat_matches_stat_for_a_non_symlink(tmp_path):
    """普通文件没有“link 本身/target”区别；两种调用看到相同 inode 与 size。"""

    path = tmp_path / "plain.txt"
    path.write_text("plain", encoding="utf-8")

    assert path.stat().st_ino == path.lstat().st_ino
    assert path.stat().st_size == path.lstat().st_size == 5


def test_chmod_changes_permission_bits_on_the_temporary_file(tmp_path):
    """stat().st_mode 还含 file-type bits；用 stat.S_IMODE 只提取 permission 部分。"""

    path = tmp_path / "private.txt"
    path.touch()

    path.chmod(0o600)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_unlink_missing_ok_controls_idempotent_removal(tmp_path):
    """missing_ok=True 类似 rm -f；默认模式让“不该缺失”的数据问题可见。"""

    path = tmp_path / "remove-me.txt"
    path.touch()

    assert path.unlink() is None
    assert not path.exists()
    assert path.unlink(missing_ok=True) is None

    with pytest.raises(FileNotFoundError):
        path.unlink()


def test_unlink_and_rmdir_enforce_file_directory_boundary(tmp_path):
    """unlink 不删除 directory，rmdir 只删除空 directory，递归树需 shutil.rmtree。"""

    directory = tmp_path / "folder"
    directory.mkdir()
    child = directory / "child.txt"
    child.touch()

    with pytest.raises(OSError):
        directory.unlink()
    with pytest.raises(OSError):
        directory.rmdir()

    child.unlink()
    assert directory.rmdir() is None
    assert not directory.exists()


def test_rename_returns_a_new_path_and_moves_the_entry(tmp_path):
    """原 Path 对象不可变，rename 返回指向 target 的新 Path；旧对象仍保存旧文本但已不存在。"""

    source = tmp_path / "before.txt"
    target = tmp_path / "after.txt"
    source.write_text("content", encoding="utf-8")

    returned = source.rename(target)

    assert returned == target
    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "content"


def test_replace_unconditionally_replaces_an_existing_file(tmp_path):
    """replace 明确提供覆盖目标的语义，比依赖 rename 的平台差异更可移植。"""

    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("new", encoding="utf-8")
    target.write_text("old", encoding="utf-8")

    returned = source.replace(target)

    assert returned == target
    assert target.read_text(encoding="utf-8") == "new"
    assert not source.exists()


def test_resolve_makes_paths_absolute_and_eliminates_dotdot(tmp_path):
    """resolve 是 pathlib 中会消除 ``..`` 的 concrete 方法，并从真实 filesystem 起点形成 absolute。"""

    folder = tmp_path / "folder"
    folder.mkdir()
    path = folder / ".." / "folder" / "file.txt"

    assert path.resolve(strict=False) == folder / "file.txt"
    assert path.resolve(strict=False).is_absolute()


def test_resolve_strict_controls_missing_remainder_handling(tmp_path):
    """strict=False 尽量解析后附上缺失 remainder；True 要求整条路径都真实存在。"""

    missing = tmp_path / "missing" / "child.txt"

    assert missing.resolve(strict=False) == missing
    with pytest.raises(FileNotFoundError):
        missing.resolve(strict=True)
