"""035｜``fileinput`` / ``stat`` / ``linecache`` 专门文件访问示例。

fileinput 把多个文本文件视为连续行流；stat 解释 os.stat_result 中的类型/权限位；
linecache 按 filename/1-based lineno 缓存源码行。三者分别处理输入状态、metadata
位字段和可失效缓存，不能替代普通文件读写。

内容基于 Python 3.10 fileinput、stat、linecache 文档。所有路径位于 pytest
tmp_path；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.fileinput python.fileinput.input
# polyglot-covers: python.fileinput.FileInput python.fileinput.line-state
# polyglot-covers: python.fileinput.nextfile python.fileinput.hook_encoded
# polyglot-covers: python.fileinput.inplace python.fileinput.backup
# polyglot-covers: python.stdlib.stat python.stat.S_IMODE python.stat.S_IFMT
# polyglot-covers: python.stat.file-types python.stat.permission-bits
# polyglot-covers: python.stat.filemode python.stat.stat-result-indices
# polyglot-covers: python.stdlib.linecache python.linecache.getline
# polyglot-covers: python.linecache.checkcache python.linecache.clearcache
# polyglot-covers: python.linecache.lazycache

import fileinput
import io
import linecache
import os
from pathlib import Path
import stat
import sys

import pytest


def test_fileinput_iterates_files_as_one_stream_and_reports_both_line_numbers(tmp_path):
    """lineno 跨文件累计，filelineno 在每个新文件从 1 重新开始。"""

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("a1\na2\n", encoding="utf-8")
    second.write_text("b1\n", encoding="utf-8")

    records = []
    with fileinput.input(
        files=(str(first), str(second)),
        encoding="utf-8",
    ) as lines:
        for line in lines:
            records.append(
                (
                    line,
                    Path(fileinput.filename()),
                    fileinput.lineno(),
                    fileinput.filelineno(),
                    fileinput.isfirstline(),
                    fileinput.isstdin(),
                )
            )

    assert records == [
        ("a1\n", first, 1, 1, True, False),
        ("a2\n", first, 2, 2, False, False),
        ("b1\n", second, 3, 1, True, False),
    ]

    # line 保留原终止符；需要移除时应选择 rstrip("\n") 或明确的换行策略。


def test_fileinput_instance_methods_work_without_module_global_helpers(tmp_path):
    """直接 FileInput 适合显式持有状态；module helper 只指向 input() 的 active state。"""

    path = tmp_path / "items.txt"
    path.write_text("one\ntwo\n", encoding="ascii")

    with fileinput.FileInput(
        files=(str(path),),
        encoding="ascii",
    ) as lines:
        assert next(lines) == "one\n"
        assert lines.filename() == str(path)
        assert lines.lineno() == 1
        assert lines.filelineno() == 1
        assert lines.isfirstline()
        assert not lines.isstdin()
        assert list(lines) == ["two\n"]

    with pytest.raises(StopIteration):
        next(lines)


def test_nextfile_skips_remainder_without_counting_skipped_lines(tmp_path):
    """nextfile 关闭当前文件，未读取的行不会增加累计 lineno。"""

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("a1\na2\na3\n", encoding="ascii")
    second.write_text("b1\nb2\n", encoding="ascii")

    first_lines = []
    with fileinput.input(
        files=(str(first), str(second)),
        encoding="ascii",
    ) as lines:
        for line in lines:
            if fileinput.isfirstline():
                first_lines.append(
                    (Path(fileinput.filename()), line, fileinput.lineno())
                )
                fileinput.nextfile()

    assert first_lines == [
        (first, "a1\n", 1),
        (second, "b1\n", 2),
    ]


def test_fileinput_dash_reads_controlled_stdin_and_marks_isstdin(monkeypatch):
    """文件名 ``-`` 表示 sys.stdin；测试用 StringIO 替换真实终端。"""

    fake_stdin = io.StringIO("stdin-one\nstdin-two\n")
    monkeypatch.setattr(sys, "stdin", fake_stdin)

    records = []
    with fileinput.input(files=("-",)) as lines:
        for line in lines:
            records.append((line, fileinput.filename(), fileinput.isstdin()))

    assert records == [
        ("stdin-one\n", "<stdin>", True),
        ("stdin-two\n", "<stdin>", True),
    ]
    assert fake_stdin.closed is False


def test_fileinput_only_allows_one_module_global_active_input(tmp_path):
    """fileinput.input 使用模块级状态，因此不能嵌套第二个 active input。"""

    path = tmp_path / "items.txt"
    path.write_text("one\n", encoding="ascii")

    with fileinput.input(files=(str(path),), encoding="ascii") as active:
        assert next(active) == "one\n"

        with pytest.raises(RuntimeError, match="already active"):
            fileinput.input(files=(str(path),), encoding="ascii")


def test_hook_encoded_opens_each_file_with_explicit_encoding(tmp_path):
    """openhook 可统一打开策略；hook_encoded 适用于 Python 3.10 的显式文本编码。"""

    path = tmp_path / "utf8.txt"
    path.write_bytes("咖啡\n".encode("utf-8"))

    with fileinput.FileInput(
        files=(str(path),),
        openhook=fileinput.hook_encoded("utf-8"),
    ) as lines:
        assert list(lines) == ["咖啡\n"]

    with pytest.raises(ValueError, match="openhook"):
        fileinput.FileInput(
            files=(str(path),),
            inplace=True,
            openhook=fileinput.hook_encoded("utf-8"),
        )

    # inplace 与 openhook 互斥，因为 inplace 自己控制原文件/备份/输出文件的打开流程。


def test_inplace_mode_rewrites_file_and_keeps_requested_backup(tmp_path):
    """inplace 把 sys.stdout 暂时重定向到原路径，并把旧内容重命名为 backup。"""

    path = tmp_path / "items.txt"
    path.write_text("one\ntwo\n", encoding="utf-8")
    original_stdout = sys.stdout

    with fileinput.input(
        files=(str(path),),
        inplace=True,
        backup=".bak",
        encoding="utf-8",
    ) as lines:
        for line in lines:
            print(line.rstrip("\n").upper())

    assert sys.stdout is original_stdout
    assert path.read_text(encoding="utf-8") == "ONE\nTWO\n"
    assert path.with_name(path.name + ".bak").read_text(
        encoding="utf-8"
    ) == "one\ntwo\n"

    # 这是原地覆盖，不是事务；生产代码应考虑临时文件+原子 replace 和失败恢复。


def test_inplace_context_restores_stdout_when_body_raises(tmp_path):
    """context exit 会恢复 stdout，但目标文件可能已部分改写，backup 才保留原文。"""

    path = tmp_path / "items.txt"
    path.write_text("one\ntwo\n", encoding="ascii")
    original_stdout = sys.stdout

    with pytest.raises(RuntimeError, match="stop midway"):
        with fileinput.input(
            files=(str(path),),
            inplace=True,
            backup=".bak",
            encoding="ascii",
        ) as lines:
            for line in lines:
                print(line.upper(), end="")
                raise RuntimeError("stop midway")

    assert sys.stdout is original_stdout
    assert path.read_text(encoding="ascii") == "ONE\n"
    assert path.with_name(path.name + ".bak").read_text(
        encoding="ascii"
    ) == "one\ntwo\n"


def test_stat_type_bits_distinguish_regular_directory_and_symlink(tmp_path):
    """S_IFMT 提取文件类型字段，S_IS* predicate 更便于可读判断。"""

    regular = tmp_path / "item.txt"
    regular.write_text("data", encoding="ascii")
    directory = tmp_path / "folder"
    directory.mkdir()
    link = tmp_path / "item-link"
    link.symlink_to(regular.name)

    regular_mode = os.stat(regular).st_mode
    directory_mode = os.stat(directory).st_mode
    link_mode = os.lstat(link).st_mode

    assert stat.S_IFMT(regular_mode) == stat.S_IFREG
    assert stat.S_IFMT(directory_mode) == stat.S_IFDIR
    assert stat.S_IFMT(link_mode) == stat.S_IFLNK
    assert stat.S_ISREG(regular_mode)
    assert stat.S_ISDIR(directory_mode)
    assert stat.S_ISLNK(link_mode)

    # stat(link) 跟随目标会得到 regular；判断链接本身必须使用 lstat/follow_symlinks=False。


def test_s_imode_extracts_permissions_from_mode_with_file_type_bits(tmp_path):
    """st_mode 同时含类型与权限，不能直接与 0o754 比较。"""

    path = tmp_path / "script.sh"
    path.write_text("#!/bin/sh\n", encoding="ascii")
    path.chmod(0o754)
    mode = path.stat().st_mode

    assert mode != 0o754
    assert stat.S_IMODE(mode) == 0o754
    assert mode & stat.S_IRUSR
    assert mode & stat.S_IWUSR
    assert mode & stat.S_IXUSR
    assert mode & stat.S_IRGRP
    assert mode & stat.S_IXGRP
    assert mode & stat.S_IROTH
    assert not mode & stat.S_IWOTH


def test_permission_and_special_bit_constants_can_build_mode_masks():
    """八进制写法最紧凑，命名常量适合说明要检查的具体位。"""

    permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
    assert permissions == 0o640

    special = stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX | 0o755
    assert stat.S_IMODE(special) == 0o7755
    assert special & stat.S_ISUID
    assert special & stat.S_ISGID
    assert special & stat.S_ISVTX

    # 设置特殊位还受平台、文件系统和权限限制；这里只演示位运算，不修改真实权限策略。


def test_filemode_formats_type_and_permission_bits_for_humans():
    """filemode 生成类似 `ls -l` 的十字符表示。"""

    assert stat.filemode(stat.S_IFREG | 0o754) == "-rwxr-xr--"
    assert stat.filemode(stat.S_IFDIR | 0o750) == "drwxr-x---"
    assert stat.filemode(stat.S_IFLNK | 0o777) == "lrwxrwxrwx"


def test_stat_result_index_constants_match_named_attributes(tmp_path):
    """ST_* 索引兼容 tuple 接口，业务代码通常优先命名属性。"""

    path = tmp_path / "item.bin"
    path.write_bytes(b"abc")
    metadata = path.stat()

    assert metadata[stat.ST_MODE] == metadata.st_mode
    assert metadata[stat.ST_SIZE] == metadata.st_size == 3
    assert metadata[stat.ST_MTIME] == metadata.st_mtime


def test_linecache_getline_is_one_based_and_missing_is_empty_string(tmp_path):
    """getline 保留换行；行号越界/文件缺失返回 ``''`` 而不是抛异常。"""

    path = tmp_path / "source.py"
    path.write_text("first\n\nthird\n", encoding="utf-8")
    linecache.clearcache()

    assert linecache.getline(str(path), 1) == "first\n"
    assert linecache.getline(str(path), 2) == "\n"
    assert linecache.getline(str(path), 3) == "third\n"
    assert linecache.getline(str(path), 0) == ""
    assert linecache.getline(str(path), 99) == ""
    assert linecache.getline(str(tmp_path / "missing.py"), 1) == ""

    # `"\n"` 是真实空白行；`""` 表示没有该行，二者不能混为一谈。
    linecache.clearcache()


def test_linecache_getlines_caches_until_checkcache_detects_change(tmp_path):
    """getline/getlines 不会每次重读；checkcache 比较 stat 后使变化文件失效。"""

    path = tmp_path / "source.py"
    path.write_text("old\n", encoding="utf-8")
    linecache.clearcache()

    assert linecache.getlines(str(path)) == ["old\n"]

    path.write_text("new and longer\n", encoding="utf-8")
    assert linecache.getline(str(path), 1) == "old\n"

    linecache.checkcache(str(path))
    assert linecache.getline(str(path), 1) == "new and longer\n"

    linecache.clearcache()
    assert linecache.getlines(str(path)) == ["new and longer\n"]


def test_linecache_lazycache_defers_loader_get_source_until_first_read(tmp_path):
    """lazycache 注册 loader 回调，真正 getline 时才请求模块源码。"""

    calls = []

    class Loader:
        def get_source(self, fullname):
            calls.append(fullname)
            return "alpha\nbeta\n"

    filename = str(tmp_path / "virtual_module.py")
    module_globals = {
        "__name__": "virtual_module",
        "__loader__": Loader(),
    }
    linecache.clearcache()

    assert linecache.lazycache(filename, module_globals) is True
    assert calls == []
    assert linecache.getline(filename, 2, module_globals) == "beta\n"
    assert calls == ["virtual_module"]

    # 首次加载后进入普通缓存；后续读取不会再次调用 loader。
    assert linecache.getline(filename, 1, module_globals) == "alpha\n"
    assert calls == ["virtual_module"]
    linecache.clearcache()
