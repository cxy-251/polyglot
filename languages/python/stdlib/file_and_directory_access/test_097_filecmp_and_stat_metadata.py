"""097｜``filecmp`` 的正确性权衡与 ``stat`` mode 位域解释。

``filecmp`` 的 shallow=True 比较 stat signature，不是内容证明；deep comparison 也有按 stat
失效的 process cache。``stat`` 则把一次 system call 的 mode 拆成 file type、普通权限与
set-id/sticky 特殊位，适合在不重复访问文件系统的前提下做多项判断。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.filecmp.cmp python.filecmp.shallow-signature
# polyglot-covers: python.filecmp.deep-content python.filecmp.shallow-fallback
# polyglot-covers: python.filecmp.cache python.filecmp.clear-cache python.filecmp.mtime-resolution-trap
# polyglot-covers: python.filecmp.cmpfiles python.filecmp.match-mismatch-errors
# polyglot-covers: python.filecmp.dircmp python.filecmp.dircmp.lazy-attributes
# polyglot-covers: python.filecmp.dircmp.left-right-only python.filecmp.dircmp.common
# polyglot-covers: python.filecmp.dircmp.common-dirs python.filecmp.dircmp.common-files
# polyglot-covers: python.filecmp.dircmp.common-funny python.filecmp.dircmp.type-mismatch
# polyglot-covers: python.filecmp.dircmp.same-files python.filecmp.dircmp.diff-files
# polyglot-covers: python.filecmp.dircmp.ignore python.filecmp.DEFAULT-IGNORES
# polyglot-covers: python.filecmp.dircmp.subdirs python.filecmp.python310-subclass-preservation
# polyglot-covers: python.filecmp.dircmp.report python.filecmp.dircmp.partial-closure
# polyglot-covers: python.filecmp.dircmp.full-closure
# polyglot-covers: python.stat.S-ISDIR python.stat.S-ISREG python.stat.S-ISLNK
# polyglot-covers: python.stat.S-ISCHR python.stat.S-ISBLK python.stat.S-ISFIFO python.stat.S-ISSOCK
# polyglot-covers: python.stat.S-IFMT python.stat.S-IMODE
# polyglot-covers: python.stat.filemode python.stat.symbolic-permissions
# polyglot-covers: python.stat.permission-masks python.stat.set-id python.stat.sticky-bit
# polyglot-covers: python.stat.stat-result-indexes python.stat.ST-MODE python.stat.ST-SIZE
# polyglot-covers: python.stat.lstat python.stat.symlink-following
# polyglot-covers: python.stat.platform-file-types

import filecmp
import os
from pathlib import Path
import stat


def test_shallow_cmp_can_accept_different_content_with_the_same_stat_signature(tmp_path):
    """type、size、mtime 完全相同就直接判 equal；校验内容必须显式 shallow=False。"""

    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"AAAA")
    right.write_bytes(b"BBBB")
    timestamp_ns = 1_234_567_890_000_000_000
    os.utime(left, ns=(timestamp_ns, timestamp_ns))
    os.utime(right, ns=(timestamp_ns, timestamp_ns))

    assert filecmp.cmp(left, right, shallow=True) is True
    assert filecmp.cmp(left, right, shallow=False) is False


def test_shallow_cmp_falls_back_to_content_when_signatures_are_not_equal(tmp_path):
    """shallow 不是“永不读内容”：mtime 不同而 size 相同，会继续做 byte comparison。"""

    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"same")
    right.write_bytes(b"same")
    os.utime(left, ns=(1_000_000_000, 1_000_000_000))
    os.utime(right, ns=(2_000_000_000, 2_000_000_000))

    assert filecmp.cmp(left, right, shallow=True) is True


def test_cmp_rejects_different_sizes_before_a_full_content_scan(tmp_path):
    """size 不同在 shallow/deep 两种模式下都足以判 mismatch。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.write_bytes(b"short")
    right.write_bytes(b"longer")

    assert filecmp.cmp(left, right, shallow=True) is False
    assert filecmp.cmp(left, right, shallow=False) is False


def test_clear_cache_handles_same_size_same_mtime_rewrites(tmp_path):
    """若 rewrite 落在相同 mtime resolution 且 size 不变，cache key 不变；clear_cache 后才重读。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.write_bytes(b"AAAA")
    right.write_bytes(b"AAAA")
    timestamp_ns = 1_111_111_111_000_000_000
    os.utime(left, ns=(timestamp_ns, timestamp_ns))
    os.utime(right, ns=(timestamp_ns, timestamp_ns))
    filecmp.clear_cache()
    try:
        assert filecmp.cmp(left, right, shallow=False) is True

        right.write_bytes(b"BBBB")
        os.utime(right, ns=(timestamp_ns, timestamp_ns))

        assert filecmp.cmp(left, right, shallow=False) is True
        filecmp.clear_cache()
        assert filecmp.cmp(left, right, shallow=False) is False
    finally:
        filecmp.clear_cache()


def test_cmpfiles_partitions_requested_names_into_three_lists(tmp_path):
    """不存在于任一侧、无权限或其他无法比较项进入 errors，而不是混入 mismatch。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "same.txt").write_text("same", encoding="utf-8")
    (right / "same.txt").write_text("same", encoding="utf-8")
    (left / "different.txt").write_text("left", encoding="utf-8")
    (right / "different.txt").write_text("right", encoding="utf-8")
    (left / "missing.txt").touch()

    match, mismatch, errors = filecmp.cmpfiles(
        left,
        right,
        ["same.txt", "different.txt", "missing.txt"],
        shallow=False,
    )

    assert match == ["same.txt"]
    assert mismatch == ["different.txt"]
    assert errors == ["missing.txt"]


def test_cmpfiles_accepts_relative_names_with_subdirectories(tmp_path):
    """common items 不限 basename；相同 relative route 会分别拼到左右根目录。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    relative = Path("nested") / "item.txt"
    (left / relative).parent.mkdir(parents=True)
    (right / relative).parent.mkdir(parents=True)
    (left / relative).write_text("same", encoding="utf-8")
    (right / relative).write_text("same", encoding="utf-8")

    match, mismatch, errors = filecmp.cmpfiles(
        left, right, [os.fspath(relative)], shallow=False
    )

    assert match == [os.fspath(relative)]
    assert mismatch == []
    assert errors == []


def test_dircmp_computes_lightweight_name_sets_lazily(tmp_path):
    """构造对象不立即做全部递归比较；首次读取 attribute 才运行对应 phase 并缓存结果。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "left-only").touch()
    (right / "right-only").touch()
    (left / "common").touch()
    (right / "common").touch()
    comparison = filecmp.dircmp(left, right)

    assert "left_list" not in comparison.__dict__
    assert comparison.left_only == ["left-only"]
    assert comparison.right_only == ["right-only"]
    assert comparison.common == ["common"]
    assert "left_list" in comparison.__dict__
    assert comparison.left == left
    assert comparison.right == right


def test_dircmp_classifies_common_directories_files_and_type_conflicts(tmp_path):
    """同名但一侧 file、一侧 directory 属于 common_funny，不是 common_files/diff_files。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "directory").mkdir()
    (right / "directory").mkdir()
    (left / "file.txt").touch()
    (right / "file.txt").touch()
    (left / "conflict").touch()
    (right / "conflict").mkdir()
    comparison = filecmp.dircmp(left, right)

    assert comparison.common_dirs == ["directory"]
    assert comparison.common_files == ["file.txt"]
    assert comparison.common_funny == ["conflict"]


def test_dircmp_partitions_comparable_common_files_into_same_and_different(tmp_path):
    """dircmp 固定采用 shallow comparison；让 diff size 不同可避免 timestamp signature 误判。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "same.txt").write_text("same", encoding="utf-8")
    (right / "same.txt").write_text("same", encoding="utf-8")
    (left / "different.txt").write_text("short", encoding="utf-8")
    (right / "different.txt").write_text("a different length", encoding="utf-8")
    comparison = filecmp.dircmp(left, right)

    assert comparison.same_files == ["same.txt"]
    assert comparison.diff_files == ["different.txt"]
    assert comparison.funny_files == []


def test_dircmp_default_and_custom_ignore_names_are_removed_from_lists(tmp_path):
    """DEFAULT_IGNORES 通常排除 VCS/cache 管理目录；自定义 ignore 是完全替换时要保留默认项。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    for root in (left, right):
        (root / ".git").mkdir()
        (root / "generated").mkdir()
        (root / "source").mkdir()

    default_comparison = filecmp.dircmp(left, right)
    custom_comparison = filecmp.dircmp(
        left,
        right,
        ignore=[*filecmp.DEFAULT_IGNORES, "generated"],
    )

    assert ".git" in filecmp.DEFAULT_IGNORES
    assert ".git" not in default_comparison.common
    assert "generated" in default_comparison.common
    assert custom_comparison.common == ["source"]


def test_python_310_subdirs_preserves_a_dircmp_subclass(tmp_path):
    """3.10 起 recursive node 使用 self 的 subclass，便于扩展整棵 comparison tree。"""

    class TaggedDirCmp(filecmp.dircmp):
        pass

    left = tmp_path / "left"
    right = tmp_path / "right"
    (left / "nested").mkdir(parents=True)
    (right / "nested").mkdir(parents=True)
    comparison = TaggedDirCmp(left, right)

    assert isinstance(comparison.subdirs["nested"], TaggedDirCmp)


def test_dircmp_reports_have_current_partial_and_full_recursion_scopes(tmp_path, capsys):
    """report 只看当前层，partial 再看一层，full 才递归到任意深度。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    (left / "level1" / "level2").mkdir(parents=True)
    (right / "level1" / "level2").mkdir(parents=True)
    (left / "level1" / "level2" / "deep.txt").write_text("left", encoding="utf-8")
    (right / "level1" / "level2" / "deep.txt").write_text(
        "a different length", encoding="utf-8"
    )
    comparison = filecmp.dircmp(left, right)

    comparison.report()
    assert "deep.txt" not in capsys.readouterr().out

    comparison.report_partial_closure()
    assert "deep.txt" not in capsys.readouterr().out

    comparison.report_full_closure()
    assert "deep.txt" in capsys.readouterr().out


def test_stat_and_lstat_give_different_type_modes_for_a_symlink(tmp_path):
    """stat 跟随 target；lstat 描述 link directory entry 本身。"""

    target = tmp_path / "target.txt"
    target.touch()
    link = tmp_path / "link"
    link.symlink_to(target)

    assert stat.S_ISREG(os.stat(link).st_mode)
    assert stat.S_ISLNK(os.lstat(link).st_mode)
    assert not stat.S_ISLNK(os.stat(link).st_mode)


def test_file_type_predicates_decode_the_type_field_without_filesystem_access():
    """已有 st_mode 时可重复检查，不要为每种 is* predicate 重做 system call。"""

    predicates = [
        (stat.S_IFDIR, stat.S_ISDIR),
        (stat.S_IFREG, stat.S_ISREG),
        (stat.S_IFLNK, stat.S_ISLNK),
        (stat.S_IFCHR, stat.S_ISCHR),
        (stat.S_IFBLK, stat.S_ISBLK),
        (stat.S_IFIFO, stat.S_ISFIFO),
        (stat.S_IFSOCK, stat.S_ISSOCK),
    ]

    for type_bits, predicate in predicates:
        assert predicate(type_bits)


def test_ifmt_and_imode_split_type_bits_from_settable_permission_bits():
    """S_IFMT 只留 file type；S_IMODE 留 chmod 可设置的 rwx、set-id 与 sticky bits。"""

    permission_bits = 0o640 | stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX
    mode = stat.S_IFREG | permission_bits

    assert stat.S_IFMT(mode) == stat.S_IFREG
    assert stat.S_IMODE(mode) == permission_bits
    assert stat.S_IFMT(mode) & stat.S_IMODE(mode) == 0


def test_permission_constants_are_composable_bit_masks():
    """owner/group/other masks 可整体提取，也可用单 bit 检查；不要比较完整 st_mode 与 0o644。"""

    permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

    assert permissions == 0o644
    assert permissions & stat.S_IRWXU == 0o600
    assert permissions & stat.S_IRWXG == 0o040
    assert permissions & stat.S_IRWXO == 0o004
    assert permissions & stat.S_IXUSR == 0


def test_legacy_permission_aliases_and_enfmt_share_existing_bits():
    """S_IREAD/IWRITE/IEXEC 是 owner bits 的旧别名；S_ENFMT 与 S_ISGID 复用同一 bit。"""

    assert stat.S_IREAD == stat.S_IRUSR
    assert stat.S_IWRITE == stat.S_IWUSR
    assert stat.S_IEXEC == stat.S_IXUSR
    assert stat.S_ENFMT == stat.S_ISGID


def test_filemode_renders_type_permissions_and_special_execute_states():
    """set-id 位在 execute 存在时显示小写 s/t，否则显示大写 S/T。"""

    assert stat.filemode(stat.S_IFREG | 0o754) == "-rwxr-xr--"
    assert stat.filemode(stat.S_IFDIR | 0o700) == "drwx------"
    assert stat.filemode(stat.S_IFLNK | 0o777) == "lrwxrwxrwx"
    assert stat.filemode(stat.S_IFREG | stat.S_IRUSR | stat.S_ISUID) == "-r-S------"
    assert stat.filemode(stat.S_IFREG | stat.S_IXUSR | stat.S_ISUID) == "---s------"
    assert stat.filemode(stat.S_IFDIR | stat.S_ISVTX) == "d--------T"
    assert stat.filemode(stat.S_IFDIR | stat.S_ISVTX | stat.S_IXOTH) == "d--------t"


def test_stat_symbolic_indexes_map_to_the_portable_ten_tuple(tmp_path):
    """stat_result 还可能有平台扩展属性；前十个 sequence slots 由 ST_* 常量稳定索引。"""

    path = tmp_path / "item.txt"
    path.write_bytes(b"abc")
    metadata = path.stat()

    assert len(tuple(metadata)) == 10
    assert metadata[stat.ST_MODE] == metadata.st_mode
    assert metadata[stat.ST_INO] == metadata.st_ino
    assert metadata[stat.ST_DEV] == metadata.st_dev
    assert metadata[stat.ST_NLINK] == metadata.st_nlink
    assert metadata[stat.ST_UID] == metadata.st_uid
    assert metadata[stat.ST_GID] == metadata.st_gid
    assert metadata[stat.ST_SIZE] == metadata.st_size == 3
    assert metadata[stat.ST_ATIME] == metadata.st_atime
    assert metadata[stat.ST_MTIME] == metadata.st_mtime
    assert metadata[stat.ST_CTIME] == metadata.st_ctime


def test_optional_platform_file_type_constants_are_zero_when_unsupported():
    """door/event port/whiteout 并非所有 OS 都有；不能把常量存在误解为当前 filesystem 支持。"""

    for name in ("S_IFDOOR", "S_IFPORT", "S_IFWHT"):
        value = getattr(stat, name)
        assert isinstance(value, int)
        if value == 0:
            predicate = getattr(stat, name.replace("S_IF", "S_IS"))
            assert predicate(stat.S_IFREG) is False
