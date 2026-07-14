"""134｜TAR extraction filters、安全默认值、异常策略与有状态限制。

Python 3.10 的安全补丁系列回移了 PEP 706 filters。``fully_trusted`` 保留传统 TAR
能力，``tar`` 阻止明显路径越界并收紧 mode，``data`` 进一步限制链接、特殊文件和 owner
metadata。filter 不是 DoS 沙箱；文件数/总体积等预算仍需应用补充，失败后也可能已部分解压。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.extraction-filter python.tarfile.filter-availability
# polyglot-covers: python.tarfile.fully-trusted-filter python.tarfile.tar-filter
# polyglot-covers: python.tarfile.data-filter python.tarfile.filter-string-name
# polyglot-covers: python.tarfile.OutsideDestinationError
# polyglot-covers: python.tarfile.SpecialFileError python.tarfile.AbsoluteLinkError
# polyglot-covers: python.tarfile.LinkOutsideDestinationError python.tarfile.FilterError
# polyglot-covers: python.tarfile.filter-skip python.tarfile.filter-replace-metadata
# polyglot-covers: python.tarfile.extraction-filter-attribute
# polyglot-covers: python.tarfile.extraction-filter-callable-only
# polyglot-covers: python.tarfile.errorlevel-zero python.tarfile.errorlevel-one
# polyglot-covers: python.tarfile.partial-extraction python.tarfile.stateful-filter
# polyglot-covers: python.tarfile.resource-budget python.tarfile.filter-not-sandbox

import io
import stat
import tarfile

import pytest


_HAS_FILTERS = hasattr(tarfile, "data_filter")
pytestmark = pytest.mark.skipif(
    not _HAS_FILTERS,
    reason="extraction filters require a Python 3.10 security patch release",
)


def _add_bytes(archive, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def _build_archive(*members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for name, payload in members:
            _add_bytes(archive, name, payload)
    return buffer.getvalue()


def test_feature_detection_uses_capability_not_python_minor_version():
    """filters 是安全补丁回移功能；兼容代码应 hasattr，而不是假设所有 3.10 都相同。"""

    assert _HAS_FILTERS is True
    assert callable(tarfile.data_filter)


def test_fully_trusted_can_write_a_parent_path_but_data_filter_refuses(tmp_path):
    """传统行为允许 ``..``；data 在落盘前解析目标并抛 OutsideDestinationError。"""

    trusted_raw = _build_archive(("../trusted-escape.txt", b"escaped"))
    trusted_destination = tmp_path / "trusted"
    with tarfile.open(fileobj=io.BytesIO(trusted_raw), mode="r:") as archive:
        archive.extractall(trusted_destination, filter="fully_trusted")

    assert (tmp_path / "trusted-escape.txt").read_bytes() == b"escaped"

    blocked_raw = _build_archive(("../blocked-escape.txt", b"blocked"))
    blocked_destination = tmp_path / "blocked"
    with tarfile.open(fileobj=io.BytesIO(blocked_raw), mode="r:") as archive:
        with pytest.raises(tarfile.OutsideDestinationError):
            archive.extractall(blocked_destination, filter="data")
    assert not (tmp_path / "blocked-escape.txt").exists()


def test_fully_trusted_filter_returns_the_original_member():
    """该 filter 不复制、不清理 metadata，适用于来源确实完全可信的 archive。"""

    info = tarfile.TarInfo("member.txt")

    assert tarfile.fully_trusted_filter(info, "/unused") is info


def test_tar_filter_strips_leading_slash_and_dangerous_mode_bits(tmp_path):
    """tar profile 保留 Unix TAR 能力，但清掉 set-id/sticky 与 group/other write。"""

    info = tarfile.TarInfo("/leading.txt")
    info.mode = 0o7777

    filtered = tarfile.tar_filter(info, str(tmp_path))

    assert filtered.name == "leading.txt"
    assert filtered.mode == 0o755
    assert info.name == "/leading.txt"


def test_data_filter_removes_owner_and_normalizes_regular_file_mode(tmp_path):
    """data profile 保证 owner 可读写，并在 owner 不可执行时清除所有 execute bits。"""

    info = tarfile.TarInfo("document.txt")
    info.mode = 0o477
    info.uid = 1000
    info.gid = 100
    info.uname = "alice"
    info.gname = "staff"

    filtered = tarfile.data_filter(info, str(tmp_path))

    assert filtered.mode == 0o644
    assert filtered.uid is None
    assert filtered.gid is None
    assert filtered.uname is None
    assert filtered.gname is None


def test_data_filter_leaves_directory_mode_unspecified(tmp_path):
    """跨平台数据目录不强制 archive permission；mode=None 让 extract 跳过 chmod。"""

    info = tarfile.TarInfo("directory/")
    info.type = tarfile.DIRTYPE
    info.mode = 0o700

    filtered = tarfile.data_filter(info, str(tmp_path))

    assert filtered.mode is None


def test_data_filter_refuses_special_files(tmp_path):
    """FIFO、character/block device 可产生系统副作用，data profile 一律拒绝。"""

    fifo = tarfile.TarInfo("pipe")
    fifo.type = tarfile.FIFOTYPE

    with pytest.raises(tarfile.SpecialFileError) as captured:
        tarfile.data_filter(fifo, str(tmp_path))
    assert isinstance(captured.value, tarfile.FilterError)
    assert captured.value.tarinfo is fifo


def test_data_filter_refuses_absolute_and_outside_link_targets(tmp_path):
    """symlink 相对所在目录，hard link 相对 archive root；两种 linkname 分别计算。"""

    symbolic = tarfile.TarInfo("nested/link")
    symbolic.type = tarfile.SYMTYPE
    symbolic.linkname = "/etc/passwd"
    with pytest.raises(tarfile.AbsoluteLinkError):
        tarfile.data_filter(symbolic, str(tmp_path))

    hard = tarfile.TarInfo("hard-link")
    hard.type = tarfile.LNKTYPE
    hard.linkname = "../outside"
    with pytest.raises(tarfile.LinkOutsideDestinationError):
        tarfile.data_filter(hard, str(tmp_path))


def test_custom_filter_can_skip_members_and_replace_metadata(tmp_path):
    """callable 在每个成员落盘前运行；返回 None 跳过，返回副本替换实际 metadata。"""

    raw = _build_archive(("keep.txt", b"keep"), ("discard.tmp", b"discard"))
    seen_destinations = []

    def application_filter(info, destination):
        seen_destinations.append(destination)
        if info.name.endswith(".tmp"):
            return None
        return info.replace(
            mode=0o600,
            uid=None,
            gid=None,
            uname=None,
            gname=None,
        )

    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extractall(destination, filter=application_filter)

    assert (destination / "keep.txt").read_bytes() == b"keep"
    assert stat.S_IMODE((destination / "keep.txt").stat().st_mode) == 0o600
    assert not (destination / "discard.tmp").exists()
    assert seen_destinations == [str(destination), str(destination)]


def test_instance_extraction_filter_supplies_the_default_policy(tmp_path):
    """省略 extractall(filter=...) 时使用实例属性；适合封装后的 application boundary。"""

    raw = _build_archive(("../outside.txt", b"outside"))
    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extraction_filter = tarfile.data_filter
        with pytest.raises(tarfile.OutsideDestinationError):
            archive.extractall(destination)


def test_extraction_filter_attribute_rejects_a_string_name(tmp_path):
    """extract 参数接受 'data'；实例属性必须是 callable，避免配置字符串被静默绑定。"""

    raw = _build_archive(("member.txt", b"content"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extraction_filter = "data"
        with pytest.raises(TypeError):
            archive.extractall(tmp_path)


def test_errorlevel_zero_skips_rejected_member_and_continues(tmp_path):
    """errorlevel=0 将 FilterError 记为 debug 信息并跳过该成员；后续安全成员仍展开。"""

    raw = _build_archive(
        ("../outside.txt", b"outside"),
        ("safe.txt", b"safe"),
    )
    destination = tmp_path / "output"
    with tarfile.open(
        fileobj=io.BytesIO(raw),
        mode="r:",
        errorlevel=0,
    ) as archive:
        archive.extractall(destination, filter="data")

    assert not (tmp_path / "outside.txt").exists()
    assert (destination / "safe.txt").read_bytes() == b"safe"


def test_errorlevel_one_aborts_but_does_not_roll_back_prior_members(tmp_path):
    """默认 fatal filter error 终止流程；此前已写入的文件由 caller 负责清理。"""

    raw = _build_archive(
        ("safe.txt", b"safe"),
        ("../outside.txt", b"outside"),
    )
    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        with pytest.raises(tarfile.OutsideDestinationError):
            archive.extractall(destination, filter="data")

    assert (destination / "safe.txt").read_bytes() == b"safe"
    assert not (tmp_path / "outside.txt").exists()


def test_stateful_filter_enforces_count_and_total_size_budgets(tmp_path):
    """named filters不防资源耗尽；stateful callable 可按业务预算跳过后续成员。"""

    raw = _build_archive(
        ("first.bin", b"1234"),
        ("second.bin", b"5678"),
        ("third.bin", b"90"),
    )

    class BudgetFilter:
        def __init__(self, max_files, max_size):
            self.max_files = max_files
            self.max_size = max_size
            self.files = 0
            self.size = 0

        def __call__(self, info, destination):
            if self.files + 1 > self.max_files:
                return None
            if self.size + info.size > self.max_size:
                return None
            self.files += 1
            self.size += info.size
            return tarfile.data_filter(info, destination)

    budget = BudgetFilter(max_files=2, max_size=8)
    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extractall(destination, filter=budget)

    assert budget.files == 2
    assert budget.size == 8
    assert (destination / "first.bin").exists()
    assert (destination / "second.bin").exists()
    assert not (destination / "third.bin").exists()
