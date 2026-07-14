"""098｜``fileinput`` 多文件行流与 ``linecache`` source line cache。

``fileinput`` 把多个文件串成一个有累计行号的 stream，也提供会修改 global stdin/stdout 或
原文件的便捷模式；应优先使用 instance/context manager 并明确清理。``linecache`` 面向
traceback/source retrieval：行号从 1 开始、失败返回空串，磁盘更新不会自动绕过已有 cache。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.fileinput.FileInput python.fileinput.multiple-files
# polyglot-covers: python.fileinput.context-manager python.fileinput.newline-preservation
# polyglot-covers: python.fileinput.filename python.fileinput.fileno
# polyglot-covers: python.fileinput.lineno python.fileinput.filelineno python.fileinput.isfirstline
# polyglot-covers: python.fileinput.nextfile python.fileinput.skipped-lines-not-counted
# polyglot-covers: python.fileinput.empty-file python.fileinput.stdin-dash python.fileinput.isstdin
# polyglot-covers: python.fileinput.input python.fileinput.module-global-state
# polyglot-covers: python.fileinput.input.active-state-trap python.fileinput.close
# polyglot-covers: python.fileinput.binary-mode python.fileinput.python310-encoding-errors
# polyglot-covers: python.fileinput.openhook python.fileinput.openhook-keywords
# polyglot-covers: python.fileinput.hook-compressed python.fileinput.gzip python.fileinput.bzip2
# polyglot-covers: python.fileinput.hook-encoded python.fileinput.python310-hook-encoded-deprecated
# polyglot-covers: python.fileinput.inplace python.fileinput.backup python.fileinput.stdout-redirection
# polyglot-covers: python.fileinput.inplace-default-backup-deletion
# polyglot-covers: python.fileinput.inplace-openhook-conflict python.fileinput.mode-validation
# polyglot-covers: python.fileinput.readline python.fileinput.deprecated-getitem
# polyglot-covers: python.linecache.getline python.linecache.one-based-lines
# polyglot-covers: python.linecache.getline.never-raises python.linecache.trailing-newline
# polyglot-covers: python.linecache.tokenize-encoding python.linecache.encoding-cookie
# polyglot-covers: python.linecache.cache python.linecache.checkcache python.linecache.clearcache
# polyglot-covers: python.linecache.sys-path-fallback python.linecache.loader-get-source
# polyglot-covers: python.linecache.lazycache python.linecache.deferred-loader-io

import bz2
import fileinput
import gzip
import io
import linecache
from pathlib import Path
import sys

import pytest


@pytest.fixture(autouse=True)
def isolate_module_level_fileinput_and_linecache_state():
    """两个模块都有 process-global cache/state；每例前后恢复，避免阅读顺序影响结果。"""

    fileinput.close()
    linecache.clearcache()
    yield
    fileinput.close()
    linecache.clearcache()


def test_fileinput_concatenates_files_and_preserves_each_physical_newline(tmp_path):
    """每个 file EOF 只是 stream 边界；最后一行没有 newline 时不会凭空补上。"""

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("一\n二\n", encoding="utf-8")
    second.write_text("三", encoding="utf-8")

    with fileinput.FileInput(files=(first, second), encoding="utf-8") as lines:
        assert list(lines) == ["一\n", "二\n", "三"]


def test_fileinput_metadata_changes_after_the_first_line_is_read(tmp_path):
    """打开是 lazy 的；iteration 前 filename=None、fd=-1、两种行号均为 0。"""

    path = tmp_path / "input.txt"
    path.write_text("first\nsecond\n", encoding="utf-8")

    with fileinput.FileInput(files=path, encoding="utf-8") as lines:
        assert lines.filename() is None
        assert lines.fileno() == -1
        assert lines.lineno() == 0
        assert lines.filelineno() == 0

        assert lines.readline() == "first\n"
        assert Path(lines.filename()) == path
        assert lines.fileno() >= 0
        assert lines.lineno() == 1
        assert lines.filelineno() == 1
        assert lines.isfirstline() is True

        assert lines.readline() == "second\n"
        assert lines.lineno() == 2
        assert lines.filelineno() == 2
        assert lines.isfirstline() is False

    assert lines.fileno() == -1


def test_cumulative_and_per_file_line_numbers_diverge_at_file_boundaries(tmp_path):
    """lineno 跨文件累计，filelineno 在每个新文件从 1 重新开始。"""

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("a\nb\n", encoding="utf-8")
    second.write_text("c\n", encoding="utf-8")
    observed = []

    with fileinput.FileInput(files=(first, second), encoding="utf-8") as lines:
        for line in lines:
            observed.append(
                (
                    line.strip(),
                    Path(lines.filename()).name,
                    lines.lineno(),
                    lines.filelineno(),
                    lines.isfirstline(),
                )
            )

    assert observed == [
        ("a", "first.txt", 1, 1, True),
        ("b", "first.txt", 2, 2, False),
        ("c", "second.txt", 3, 1, True),
    ]


def test_nextfile_skips_remaining_lines_without_counting_them(tmp_path):
    """nextfile 后 filename 暂留旧值，下一次读取才切换；被跳过行不制造累计行号空洞。"""

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("keep\nskip-1\nskip-2\n", encoding="utf-8")
    second.write_text("next\n", encoding="utf-8")

    with fileinput.FileInput(files=(first, second), encoding="utf-8") as lines:
        assert next(lines) == "keep\n"
        lines.nextfile()
        assert Path(lines.filename()) == first

        assert next(lines) == "next\n"
        assert Path(lines.filename()) == second
        assert lines.lineno() == 2
        assert lines.filelineno() == 1
        assert lines.isfirstline() is True


def test_an_empty_last_file_is_visible_only_in_final_filename_state(tmp_path):
    """empty file 不产生 iteration item；若它最后被打开，filename 仍记录它而累计行数不变。"""

    nonempty = tmp_path / "nonempty.txt"
    empty = tmp_path / "empty.txt"
    nonempty.write_text("one\n", encoding="utf-8")
    empty.touch()

    with fileinput.FileInput(files=(nonempty, empty), encoding="utf-8") as lines:
        assert list(lines) == ["one\n"]
        assert Path(lines.filename()) == empty
        assert lines.lineno() == 1
        assert lines.filelineno() == 0


def test_dash_uses_stdin_and_does_not_call_the_openhook(monkeypatch):
    """``'-'`` 是 stdin sentinel；openhook/mode 不负责打开它，isstdin 标记当前来源。"""

    monkeypatch.setattr(sys, "stdin", io.StringIO("from stdin\n"))

    def forbidden_hook(*_args, **_kwargs):
        raise AssertionError("stdin must not be passed to openhook")

    with fileinput.FileInput(files=("-",), openhook=forbidden_hook) as lines:
        assert next(lines) == "from stdin\n"
        assert lines.isstdin() is True


def test_module_helpers_reflect_the_single_active_input_instance(tmp_path):
    """fileinput.input 建立 global singleton；library code 更适合持有返回的 instance。"""

    path = tmp_path / "input.txt"
    path.write_text("line\n", encoding="utf-8")

    stream = fileinput.input(files=(path,), encoding="utf-8")
    try:
        assert fileinput.filename() is None
        assert next(stream) == "line\n"
        assert Path(fileinput.filename()) == path
        assert fileinput.lineno() == 1
        assert fileinput.filelineno() == 1
        assert fileinput.isfirstline() is True
        assert fileinput.isstdin() is False
        assert fileinput.fileno() >= 0
    finally:
        fileinput.close()


def test_module_helpers_without_active_state_raise_runtime_error():
    """global convenience functions 不能在 input() 生命周期外调用；close() 本身可重复清理。"""

    fileinput.close()

    for helper in (
        fileinput.filename,
        fileinput.fileno,
        fileinput.lineno,
        fileinput.filelineno,
        fileinput.isfirstline,
        fileinput.isstdin,
        fileinput.nextfile,
    ):
        with pytest.raises(RuntimeError):
            helper()

    fileinput.close()


def test_fileinput_input_rejects_a_second_active_global_sequence(tmp_path):
    """嵌套 input() 会覆盖 singleton，因而直接报错；独立读取应构造 FileInput instance。"""

    path = tmp_path / "input.txt"
    path.touch()
    first = fileinput.input(files=(path,))
    try:
        with pytest.raises(RuntimeError, match="already active"):
            fileinput.input(files=(path,))
    finally:
        fileinput.close()

    assert first.fileno() == -1


def test_binary_mode_yields_bytes_instead_of_decoding(tmp_path):
    """``rb`` 保留原始 bytes/newlines；encoding/errors 只属于 text mode。"""

    path = tmp_path / "input.bin"
    path.write_bytes(b"a\r\nb\n")

    with fileinput.FileInput(files=(path,), mode="rb") as lines:
        assert list(lines) == [b"a\r\n", b"b\n"]


def test_python_310_encoding_and_errors_control_text_decoding(tmp_path):
    """3.10 可直接把 decoding policy 交给 input/FileInput，无需 hook_encoded。"""

    path = tmp_path / "input.txt"
    path.write_bytes(b"ok\nbad:\xff\n")

    with fileinput.FileInput(
        files=(path,), encoding="utf-8", errors="replace"
    ) as lines:
        assert list(lines) == ["ok\n", "bad:\ufffd\n"]


def test_custom_openhook_receives_python_310_encoding_and_errors_keywords(tmp_path):
    """hook 仍负责返回 file-like object；3.10 起必须准备接收可选 keyword arguments。"""

    path = tmp_path / "input.txt"
    path.write_text("内容\n", encoding="utf-8")
    calls = []

    def recording_hook(filename, mode, *, encoding=None, errors=None):
        calls.append((Path(filename), mode, encoding, errors))
        return open(filename, mode, encoding=encoding, errors=errors)

    with fileinput.FileInput(
        files=(path,),
        openhook=recording_hook,
        encoding="utf-8",
        errors="strict",
    ) as lines:
        assert list(lines) == ["内容\n"]

    assert calls == [(path, "r", "utf-8", "strict")]


def test_hook_compressed_dispatches_gzip_bzip2_and_plain_files_by_extension(tmp_path):
    """hook_compressed 只看 .gz/.bz2 extension；其他名称退回普通 open。"""

    gzip_path = tmp_path / "one.txt.gz"
    bzip_path = tmp_path / "two.txt.bz2"
    plain_path = tmp_path / "three.txt"
    with gzip.open(gzip_path, mode="wt", encoding="utf-8") as stream:
        stream.write("gzip\n")
    with bz2.open(bzip_path, mode="wt", encoding="utf-8") as stream:
        stream.write("bzip2\n")
    plain_path.write_text("plain\n", encoding="utf-8")

    with fileinput.FileInput(
        files=(gzip_path, bzip_path, plain_path),
        openhook=fileinput.hook_compressed,
        encoding="utf-8",
    ) as lines:
        assert list(lines) == ["gzip\n", "bzip2\n", "plain\n"]


def test_hook_encoded_is_deprecated_in_favour_of_encoding_parameters(tmp_path):
    """保留案例用于识别旧代码；新代码直接传 encoding/errors，少一层 hook factory。"""

    path = tmp_path / "input.txt"
    path.write_text("café\n", encoding="utf-8")

    with pytest.warns(DeprecationWarning):
        hook = fileinput.hook_encoded("utf-8", "strict")

    with fileinput.FileInput(files=(path,), openhook=hook) as lines:
        assert list(lines) == ["café\n"]


def test_inplace_filter_rewrites_the_file_and_keeps_an_explicit_backup(tmp_path):
    """iteration 期间 stdout 被临时指向原路径；print 的 end 必须保留 input newline 策略。"""

    path = tmp_path / "input.txt"
    path.write_text("one\ntwo\n", encoding="utf-8")

    with fileinput.FileInput(
        files=(path,), inplace=True, backup=".orig", encoding="utf-8"
    ) as lines:
        for line in lines:
            print(line.upper(), end="")

    assert path.read_text(encoding="utf-8") == "ONE\nTWO\n"
    assert (tmp_path / "input.txt.orig").read_text(encoding="utf-8") == "one\ntwo\n"


def test_inplace_filter_deletes_its_implicit_backup_on_success(tmp_path):
    """backup='' 内部仍短暂使用 .bak，但 current file 关闭后删除；审计需要显式 backup suffix。"""

    path = tmp_path / "input.txt"
    path.write_text("old\n", encoding="utf-8")

    with fileinput.FileInput(files=(path,), inplace=True, encoding="utf-8") as lines:
        for line in lines:
            print(line.replace("old", "new"), end="")

    assert path.read_text(encoding="utf-8") == "new\n"
    assert not (tmp_path / "input.txt.bak").exists()


def test_inplace_and_openhook_are_mutually_exclusive(tmp_path):
    """in-place 模式自己控制 rename/open/stdout，不能再由 arbitrary hook 改写打开流程。"""

    path = tmp_path / "input.txt"
    path.touch()

    with pytest.raises(ValueError):
        fileinput.FileInput(
            files=(path,), inplace=True, openhook=lambda filename, mode: None
        )


def test_fileinput_rejects_modes_outside_its_read_only_contract(tmp_path):
    """它是 line input abstraction；写入只能经 inplace stdout flow，不能传 w/a mode。"""

    path = tmp_path / "input.txt"
    path.touch()

    with pytest.raises(ValueError):
        fileinput.FileInput(files=(path,), mode="w")


def test_deprecated_getitem_requires_strict_sequential_indexes(tmp_path):
    """旧 sequence protocol 不是 random access，且不能与 readline 混用；新代码直接 iteration。"""

    path = tmp_path / "input.txt"
    path.write_text("zero\none\n", encoding="utf-8")

    with fileinput.FileInput(files=(path,), encoding="utf-8") as lines:
        with pytest.warns(DeprecationWarning):
            assert lines[0] == "zero\n"
        with pytest.warns(DeprecationWarning):
            assert lines[1] == "one\n"
        with pytest.warns(DeprecationWarning), pytest.raises(RuntimeError):
            lines[3]


def test_linecache_getline_is_one_based_and_returns_empty_string_on_errors(tmp_path):
    """调用方不用捕获 missing/out-of-range 错误；空串同时表示未取到任何 source line。"""

    path = tmp_path / "source.py"
    path.write_text("first\nsecond", encoding="utf-8")

    assert linecache.getline(str(path), 1) == "first\n"
    assert linecache.getline(str(path), 2) == "second\n"
    assert linecache.getline(str(path), 0) == ""
    assert linecache.getline(str(path), -1) == ""
    assert linecache.getline(str(path), 3) == ""
    assert linecache.getline(str(tmp_path / "missing.py"), 1) == ""


def test_linecache_uses_python_encoding_cookie_detection(tmp_path):
    """它通过 tokenize.open 读取 Python source；无 cookie 默认 UTF-8，有 cookie 时遵循声明。"""

    path = tmp_path / "latin_source.py"
    path.write_bytes(b"# -*- coding: latin-1 -*-\nname = 'caf\xe9'\n")

    assert linecache.getline(str(path), 2) == "name = 'café'\n"


def test_checkcache_discards_an_entry_when_the_source_file_changes(tmp_path):
    """getline 命中 cache 时不先 stat；磁盘可能变化的 workflow 要主动 checkcache。"""

    path = tmp_path / "source.py"
    path.write_text("value = 1\n", encoding="utf-8")
    assert linecache.getline(str(path), 1) == "value = 1\n"

    path.write_text("value = 200\n", encoding="utf-8")

    assert linecache.getline(str(path), 1) == "value = 1\n"
    linecache.checkcache(str(path))
    assert linecache.getline(str(path), 1) == "value = 200\n"


def test_clearcache_forces_all_subsequent_lines_to_be_loaded_again(tmp_path):
    """不再需要 source snapshots 时 clearcache 同时释放 memory，并让后续 getline 看见新内容。"""

    path = tmp_path / "source.py"
    path.write_text("old\n", encoding="utf-8")
    assert linecache.getline(str(path), 1) == "old\n"
    path.write_text("new\n", encoding="utf-8")

    linecache.clearcache()

    assert linecache.getline(str(path), 1) == "new\n"


def test_relative_linecache_filename_falls_back_to_sys_path(tmp_path, monkeypatch):
    """traceback 只保存 relative source name 时，linecache 会逐项尝试 module search path。"""

    filename = "polyglot_virtual_source.py"
    (tmp_path / filename).write_text("found_on_sys_path = True\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    assert linecache.getline(filename, 1) == "found_on_sys_path = True\n"


def test_linecache_can_get_source_from_a_pep_302_loader(tmp_path):
    """source 不在文件系统时，module_globals 的 loader.get_source 提供 traceback lines。"""

    calls = []

    class MemoryLoader:
        def get_source(self, fullname):
            calls.append(fullname)
            return "first\nsecond\n"

    filename = str(tmp_path / "not-on-disk.py")
    module_globals = {
        "__name__": "memory_module",
        "__loader__": MemoryLoader(),
    }

    assert linecache.getline(filename, 2, module_globals) == "second\n"
    assert calls == ["memory_module"]


def test_lazycache_retains_loader_details_without_loading_source_yet(tmp_path):
    """lazycache 只保存 callable；以后不再携带 module_globals 的 getline 才真正调用 loader。"""

    calls = []

    class MemoryLoader:
        def get_source(self, fullname):
            calls.append(fullname)
            return "deferred\n"

    filename = str(tmp_path / "lazy-source.py")
    module_globals = {
        "__name__": "lazy_module",
        "__loader__": MemoryLoader(),
    }

    assert linecache.lazycache(filename, module_globals) is True
    assert calls == []

    assert linecache.getline(filename, 1) == "deferred\n"
    assert calls == ["lazy_module"]
