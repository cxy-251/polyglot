"""167｜py_compile 与 compileall：可复现的字节码预编译工作流。

py_compile 负责把单个源文件写成 PEP 3147/488/552 形式的 pyc，compileall
在其上增加目录遍历、增量判断、路径改写、多优化级别和并行入口。
本套直接读取
公开 pyc 头部与 marshal code object，讲清“编译成功”返回值、缓存命名、
时间戳/哈希失效策略，以及安装阶段最常见的路径和符号链接陷阱。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.py-compile python.py-compile.compile
# polyglot-covers: python.py-compile.default-cache-path python.py-compile.custom-cfile
# polyglot-covers: python.py-compile.dfile python.py-compile.pycompileerror
# polyglot-covers: python.py-compile.doraise python.py-compile.quiet
# polyglot-covers: python.py-compile.pyc-header python.py-compile.magic-number
# polyglot-covers: python.py-compile.timestamp-invalidation
# polyglot-covers: python.py-compile.checked-hash python.py-compile.unchecked-hash
# polyglot-covers: python.py-compile.source-date-epoch
# polyglot-covers: python.py-compile.optimize-levels python.py-compile.optimize-cache-tag
# polyglot-covers: python.py-compile.symlink-protection
# polyglot-covers: python.stdlib.compileall python.compileall.compile-file
# polyglot-covers: python.compileall.compile-dir python.compileall.compile-path
# polyglot-covers: python.compileall.return-status python.compileall.recursion-level
# polyglot-covers: python.compileall.regex-exclusion python.compileall.legacy-layout
# polyglot-covers: python.compileall.multiple-optimization-levels
# polyglot-covers: python.compileall.hardlink-dupes python.compileall.force
# polyglot-covers: python.compileall.incremental-timestamp-check
# polyglot-covers: python.compileall.ddir python.compileall.stripdir-prependdir
# polyglot-covers: python.compileall.limit-symlink-destination
# polyglot-covers: python.compileall.workers-validation

import compileall
import importlib.util
import marshal
import os
import py_compile
import re
import struct

import pytest


def read_pyc(path):
    """返回公开 16 字节 pyc 头和其后的 code object。"""

    data = path.read_bytes()
    magic = data[:4]
    flags = struct.unpack("<I", data[4:8])[0]
    payload = data[8:16]
    code = marshal.loads(data[16:])
    return magic, flags, payload, code


def cache_path(source, optimization=None):
    return source.parent / os.path.basename(
        importlib.util.cache_from_source(
            str(source),
            optimization=optimization,
        )
    )


def test_py_compile_uses_the_tagged_cache_path_and_returns_it(tmp_path):
    source = tmp_path / "answer.py"
    source.write_text("answer = 6 * 7\n", encoding="utf-8")
    expected = importlib.util.cache_from_source(str(source))

    result = py_compile.compile(
        str(source),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
    )

    assert result == expected
    pyc = tmp_path / "__pycache__" / os.path.basename(expected)
    assert pyc.is_file()
    magic, flags, _, code = read_pyc(pyc)
    assert magic == importlib.util.MAGIC_NUMBER
    assert flags == 0

    namespace = {}
    exec(code, namespace)
    assert namespace["answer"] == 42


def test_custom_cfile_controls_storage_and_dfile_controls_code_filename(tmp_path):
    source = tmp_path / "source_name.py"
    source.write_text("value = 42\n", encoding="utf-8")
    target = tmp_path / "compiled" / "lesson.pyc"

    result = py_compile.compile(
        str(source),
        cfile=str(target),
        dfile="/installed/package/lesson.py",
        doraise=True,
    )

    assert result == str(target)
    assert not (tmp_path / "__pycache__").exists()
    _, _, _, code = read_pyc(target)
    assert code.co_filename == "/installed/package/lesson.py"
    # cfile 是实际写入位置；dfile 只改变错误和 traceback 暴露的逻辑源路径。


def test_compile_error_can_be_raised_or_reported_and_silenced(tmp_path, capsys):
    source = tmp_path / "broken.py"
    source.write_text("if True print('broken')\n", encoding="utf-8")

    with pytest.raises(py_compile.PyCompileError) as caught:
        py_compile.compile(
            str(source),
            dfile="virtual/broken.py",
            doraise=True,
        )

    error = caught.value
    assert error.exc_type_name == "SyntaxError"
    assert isinstance(error.exc_value, SyntaxError)
    assert error.file == "virtual/broken.py"
    assert "virtual/broken.py" in error.msg
    assert str(error) == error.msg

    assert py_compile.compile(str(source), doraise=False, quiet=0) is None
    first = capsys.readouterr()
    assert "SyntaxError" in first.err

    assert py_compile.compile(str(source), doraise=False, quiet=2) is None
    second = capsys.readouterr()
    assert second.out == ""
    assert second.err == ""
    # 默认错误只是写 stderr 并返回 None；自动化流水线应使用 doraise=True。


@pytest.mark.parametrize(
    ("mode", "expected_flags"),
    [
        (py_compile.PycInvalidationMode.TIMESTAMP, 0),
        (py_compile.PycInvalidationMode.CHECKED_HASH, 3),
        (py_compile.PycInvalidationMode.UNCHECKED_HASH, 1),
    ],
)
def test_invalidation_modes_are_encoded_in_the_pep_552_header(
    tmp_path,
    mode,
    expected_flags,
):
    source = tmp_path / f"mode_{mode.name.lower()}.py"
    source.write_text("value = 42\n", encoding="utf-8")
    target = tmp_path / f"mode_{mode.name.lower()}.pyc"

    py_compile.compile(
        str(source),
        cfile=str(target),
        doraise=True,
        invalidation_mode=mode,
    )
    magic, flags, payload, _ = read_pyc(target)

    assert magic == importlib.util.MAGIC_NUMBER
    assert flags == expected_flags
    if mode is py_compile.PycInvalidationMode.TIMESTAMP:
        mtime, size = struct.unpack("<II", payload)
        assert mtime == int(source.stat().st_mtime) & 0xFFFF_FFFF
        assert size == source.stat().st_size
    else:
        assert payload == importlib.util.source_hash(source.read_bytes())


def test_source_date_epoch_changes_only_the_default_invalidation_mode(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "reproducible.py"
    source.write_text("value = 42\n", encoding="utf-8")
    timestamp_target = tmp_path / "timestamp.pyc"
    hash_target = tmp_path / "hash.pyc"

    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    py_compile.compile(
        str(source),
        cfile=str(timestamp_target),
        doraise=True,
    )
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1")
    py_compile.compile(
        str(source),
        cfile=str(hash_target),
        doraise=True,
    )

    assert read_pyc(timestamp_target)[1] == 0
    assert read_pyc(hash_target)[1] == 3

    explicit = tmp_path / "explicit.pyc"
    py_compile.compile(
        str(source),
        cfile=str(explicit),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    assert read_pyc(explicit)[1] == 1
    # 环境变量只选择默认值；显式 invalidation_mode 始终优先。


def test_optimization_levels_change_asserts_docstrings_and_cache_names(tmp_path):
    source = tmp_path / "optimized.py"
    source.write_text(
        '"""module documentation"""\n'
        "assert ready, 'ready must be true'\n"
        "value = 42\n",
        encoding="utf-8",
    )

    targets = {}
    codes = {}
    for level in (0, 1, 2):
        result = py_compile.compile(
            str(source),
            doraise=True,
            optimize=level,
            invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH,
        )
        targets[level] = result
        codes[level] = read_pyc(tmp_path / "__pycache__" / os.path.basename(result))[3]

    assert ".opt-" not in targets[0]
    assert ".opt-1." in targets[1]
    assert ".opt-2." in targets[2]
    assert "ready must be true" in codes[0].co_consts
    assert "ready must be true" not in codes[1].co_consts
    assert codes[0].co_consts[0] == "module documentation"
    assert codes[1].co_consts[0] == "module documentation"
    assert "module documentation" not in codes[2].co_consts
    # -O 去 assert，-OO 还去 docstring；二者都可能改变程序行为，
    # 不能只当性能选项。


def test_py_compile_refuses_to_replace_symlinks_or_non_regular_targets(tmp_path):
    source = tmp_path / "safe.py"
    source.write_text("value = 42\n", encoding="utf-8")
    real_target = tmp_path / "real.pyc"
    real_target.write_bytes(b"keep")
    symlink_target = tmp_path / "linked.pyc"
    symlink_target.symlink_to(real_target)

    with pytest.raises(FileExistsError, match="symlink"):
        py_compile.compile(
            str(source),
            cfile=str(symlink_target),
            doraise=True,
        )
    assert real_target.read_bytes() == b"keep"

    directory_target = tmp_path / "directory.pyc"
    directory_target.mkdir()
    with pytest.raises(FileExistsError, match="non-regular"):
        py_compile.compile(
            str(source),
            cfile=str(directory_target),
            doraise=True,
        )


def test_compile_file_returns_status_and_ignores_non_python_files(
    tmp_path,
    capsys,
):
    valid = tmp_path / "valid.py"
    valid.write_text("value = 42\n", encoding="utf-8")
    broken = tmp_path / "broken.py"
    broken.write_text("def broken(:\n", encoding="utf-8")
    text = tmp_path / "notes.txt"
    text.write_text("not Python", encoding="utf-8")

    assert compileall.compile_file(valid, quiet=2) is True
    assert compileall.compile_file(text, quiet=2) is True
    assert compileall.compile_file(broken, quiet=2) is False
    assert capsys.readouterr() == ("", "")
    assert cache_path(valid).is_file()
    # “忽略非 .py”也返回 True；返回值表达是否遇到失败，
    # 不表达是否真的生成了文件。


def test_compile_dir_honors_recursion_depth_and_regex_exclusion(tmp_path):
    root = tmp_path / "tree"
    nested = root / "nested"
    nested.mkdir(parents=True)
    root_file = root / "root_module.py"
    root_file.write_text("root = True\n", encoding="utf-8")
    nested_file = nested / "nested_module.py"
    nested_file.write_text("nested = True\n", encoding="utf-8")
    skipped = root / "skip_generated.py"
    skipped.write_text("skip = True\n", encoding="utf-8")

    result = compileall.compile_dir(
        root,
        maxlevels=0,
        rx=re.compile(r"skip_generated"),
        quiet=2,
    )

    assert result is True
    assert cache_path(root_file).is_file()
    assert not cache_path(nested_file).exists()
    assert not cache_path(skipped).exists()

    assert compileall.compile_dir(root, maxlevels=1, quiet=2) is True
    assert cache_path(nested_file).is_file()


def test_compile_dir_returns_false_if_any_source_fails(tmp_path):
    root = tmp_path / "mixed"
    root.mkdir()
    valid = root / "valid.py"
    valid.write_text("value = 42\n", encoding="utf-8")
    (root / "broken.py").write_text("if True print(42)\n", encoding="utf-8")

    assert compileall.compile_dir(root, quiet=2) is False
    assert cache_path(valid).is_file()
    # 目录内一个文件失败不会阻止其他文件尝试编译，
    # 但聚合状态会是 False。


def test_legacy_layout_places_pyc_beside_the_source(tmp_path):
    source = tmp_path / "legacy.py"
    source.write_text("value = 42\n", encoding="utf-8")

    assert compileall.compile_file(source, legacy=True, quiet=2) is True

    assert (tmp_path / "legacy.pyc").is_file()
    assert not (tmp_path / "__pycache__").exists()


def test_multiple_optimization_levels_are_deduplicated_and_sorted(tmp_path):
    source = tmp_path / "levels.py"
    source.write_text("value = 42\n", encoding="utf-8")

    assert compileall.compile_file(
        source,
        quiet=2,
        optimize=[2, 1, 0, 1],
    ) is True

    assert cache_path(source, "").is_file()
    assert cache_path(source, 1).is_file()
    assert cache_path(source, 2).is_file()


def test_hardlink_dupes_reuses_identical_optimized_bytecode(tmp_path):
    source = tmp_path / "same_at_all_levels.py"
    source.write_text("value = 42\n", encoding="utf-8")

    assert compileall.compile_file(
        source,
        quiet=2,
        optimize=[1, 2],
        hardlink_dupes=True,
    ) is True

    first = cache_path(source, 1)
    second = cache_path(source, 2)
    assert first.read_bytes() == second.read_bytes()
    assert first.stat().st_ino == second.stat().st_ino

    with pytest.raises(ValueError, match="more than one optimization"):
        compileall.compile_file(
            source,
            quiet=2,
            optimize=1,
            hardlink_dupes=True,
        )


def test_incremental_timestamp_check_skips_matching_pyc_unless_forced(tmp_path):
    source = tmp_path / "incremental.py"
    source.write_text("value = 42\n", encoding="utf-8")
    assert compileall.compile_file(source, quiet=2) is True
    pyc = cache_path(source)

    marker = b"trailing marker"
    pyc.write_bytes(pyc.read_bytes() + marker)
    assert compileall.compile_file(source, force=False, quiet=2) is True
    assert pyc.read_bytes().endswith(marker)

    assert compileall.compile_file(source, force=True, quiet=2) is True
    assert not pyc.read_bytes().endswith(marker)
    # 增量判断只看魔数、flags 与时间戳头；force 才无条件重建。


def test_ddir_rewrites_the_embedded_filename_and_rejects_new_path_options(
    tmp_path,
):
    source = tmp_path / "ddir_lesson.py"
    source.write_text("value = 42\n", encoding="utf-8")

    assert compileall.compile_file(
        source,
        ddir="/virtual/package",
        force=True,
        quiet=2,
    ) is True
    assert read_pyc(cache_path(source))[3].co_filename == (
        "/virtual/package/ddir_lesson.py"
    )

    with pytest.raises(ValueError, match="cannot be used"):
        compileall.compile_file(
            source,
            ddir="/old",
            stripdir=str(tmp_path),
            quiet=2,
        )


def test_stripdir_then_prependdir_builds_install_time_traceback_paths(tmp_path):
    build_root = tmp_path / "build-root"
    package = build_root / "package"
    package.mkdir(parents=True)
    source = package / "installed.py"
    source.write_text("value = 42\n", encoding="utf-8")

    assert compileall.compile_file(
        source,
        force=True,
        quiet=2,
        stripdir=str(build_root),
        prependdir="/opt/application",
    ) is True

    _, _, _, code = read_pyc(cache_path(source))
    assert code.co_filename == "/opt/application/package/installed.py"
    # 构建机临时根目录不会泄漏进最终 traceback，安装前缀则被明确记录。


def test_limit_symlink_destination_skips_sources_outside_allowed_tree(tmp_path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    real_source = outside / "external.py"
    real_source.write_text("value = 42\n", encoding="utf-8")
    linked_source = allowed / "linked.py"
    linked_source.symlink_to(real_source)

    assert compileall.compile_file(
        linked_source,
        quiet=2,
        limit_sl_dest=str(allowed),
    ) is True
    assert not cache_path(linked_source).exists()
    # 安全边界外的链接被“成功跳过”；调用者不能用 True
    # 推断每个文件都生成了 pyc。


def test_compile_path_uses_sys_path_and_can_skip_the_current_directory(
    tmp_path,
    monkeypatch,
    capsys,
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "from_path.py"
    source.write_text("value = 42\n", encoding="utf-8")
    monkeypatch.setattr(compileall.sys, "path", ["", str(library)])

    assert compileall.compile_path(
        skip_curdir=1,
        maxlevels=0,
        quiet=2,
    ) is True

    assert cache_path(source).is_file()
    assert capsys.readouterr() == ("", "")


def test_compile_dir_rejects_negative_worker_counts(tmp_path):
    with pytest.raises(ValueError, match="greater or equal to 0"):
        compileall.compile_dir(tmp_path, workers=-1, quiet=2)
    # workers=0 表示由执行器选择进程数；只有负数是无效配置。
