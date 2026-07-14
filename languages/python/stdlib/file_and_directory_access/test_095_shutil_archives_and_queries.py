"""095｜``shutil`` 的归档、命令查找与环境查询。

高层归档 API 适合可信目录的打包与解包，但 extension 只负责选择 unpacker，不证明内容
安全；不可信 archive 必须先检查 member path，防止 absolute/``..`` 越过 extract_dir。
格式注册表是 process-global mutable state，扩展它时要用唯一名称并在 finally 中恢复。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.shutil.disk-usage python.shutil.disk-usage.namedtuple
# polyglot-covers: python.shutil.which python.shutil.which.path-order
# polyglot-covers: python.shutil.which.permission-mode python.shutil.which.direct-path
# polyglot-covers: python.shutil.which.environment-path python.shutil.which.bytes
# polyglot-covers: python.shutil.chown python.shutil.chown.argument-validation
# polyglot-covers: python.shutil.get-terminal-size python.shutil.terminal-environment
# polyglot-covers: python.shutil.get-terminal-size.fallback
# polyglot-covers: python.shutil.get-archive-formats python.shutil.get-unpack-formats
# polyglot-covers: python.shutil.make-archive python.shutil.archive-root-dir
# polyglot-covers: python.shutil.make-archive.base-dir python.shutil.archive-relative-members
# polyglot-covers: python.shutil.make-archive.zip python.shutil.unpack-archive
# polyglot-covers: python.shutil.make-archive.dry-run python.shutil.archive-logger
# polyglot-covers: python.shutil.unpack-archive.extension-detection
# polyglot-covers: python.shutil.unpack-archive.explicit-format
# polyglot-covers: python.shutil.unpack-archive.unknown-format python.shutil.ReadError
# polyglot-covers: python.shutil.unpack-archive.path-traversal python.archive.preinspection
# polyglot-covers: python.shutil.register-archive-format python.shutil.unregister-archive-format
# polyglot-covers: python.shutil.archive-extra-args python.shutil.archive-global-registry
# polyglot-covers: python.shutil.register-unpack-format python.shutil.unregister-unpack-format
# polyglot-covers: python.shutil.unpack-extra-args

import io
import logging
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import tarfile

import pytest


def _make_executable(path, content="#!/bin/sh\nexit 0\n"):
    """测试只需要 which 的 permission contract，不真正执行创建出的文件。"""

    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _archive_name_is_relative_and_contained(name):
    """archive name 使用 POSIX slash，同时拒绝可能在 Windows 生效的 drive/UNC。"""

    posix_path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    return (
        not posix_path.is_absolute()
        and ".." not in posix_path.parts
        and not windows_path.drive
    )


def _tar_member_passes_basic_data_only_policy(member):
    """除检查 entry name，还拒绝可再次跳转的 links 与 special device entries。"""

    return (
        _archive_name_is_relative_and_contained(member.name)
        and (member.isfile() or member.isdir())
    )


def test_disk_usage_returns_named_byte_counts_for_a_file_or_directory(tmp_path):
    """结果属于 containing filesystem，不是该文件自身占用量；属性均以 bytes 表示。"""

    file_path = tmp_path / "item.bin"
    file_path.write_bytes(b"small")

    for usage in (shutil.disk_usage(tmp_path), shutil.disk_usage(file_path)):
        assert usage.total > 0
        assert usage.used >= 0
        assert usage.free >= 0
        assert usage.total >= usage.used
        assert usage.total >= usage.free
        assert tuple(usage) == (usage.total, usage.used, usage.free)


def test_which_searches_path_entries_in_order_and_requires_executable_mode(tmp_path):
    """同名命令取 PATH 中第一个可执行 regular file，而不是最新或内容最匹配的文件。"""

    first_bin = tmp_path / "first"
    second_bin = tmp_path / "second"
    first_bin.mkdir()
    second_bin.mkdir()
    _make_executable(first_bin / "tool")
    _make_executable(second_bin / "tool")
    search_path = os.pathsep.join((str(first_bin), str(second_bin)))

    assert shutil.which("tool", path=search_path) == str(first_bin / "tool")


def test_which_mode_can_request_existence_without_execute_permission(tmp_path):
    """默认 mode 含 X_OK；若只是定位 data file，可显式传 F_OK，但通常不应把它当 command。"""

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    candidate = bin_directory / "tool"
    candidate.write_text("not executable", encoding="utf-8")
    candidate.chmod(0o644)

    assert shutil.which("tool", path=str(bin_directory)) is None
    assert shutil.which("tool", mode=os.F_OK, path=str(bin_directory)) == str(candidate)


def test_which_with_a_directory_component_checks_that_path_directly(tmp_path):
    """cmd 已含 separator 时不遍历 PATH；调用方仍得到 access mode 校验。"""

    explicit = tmp_path / "local" / "tool"
    explicit.parent.mkdir()
    _make_executable(explicit)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()

    assert shutil.which(str(explicit), path=str(unrelated)) == str(explicit)


def test_which_uses_environment_path_when_path_is_omitted(tmp_path, monkeypatch):
    """默认读取 process PATH；测试必须隔离该 global input，不能依赖容器已安装哪些命令。"""

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _make_executable(bin_directory / "polyglot-tool")
    monkeypatch.setenv("PATH", str(bin_directory))

    assert shutil.which("polyglot-tool") == str(bin_directory / "polyglot-tool")
    assert shutil.which("missing-tool") is None


def test_which_preserves_bytes_input_in_its_result(tmp_path):
    """bytes command 让 PATH 也跨入 filesystem bytes 域，结果不会隐式 decode。"""

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _make_executable(bin_directory / "tool")

    found = shutil.which(b"tool", path=os.fsencode(bin_directory))

    assert isinstance(found, bytes)
    assert found == os.fsencode(bin_directory / "tool")


def test_chown_requires_at_least_one_owner_or_group_argument(tmp_path):
    """不做真实 ownership 修改也能验证 API guard；名称/uid 的有效性取决于宿主账号数据库。"""

    path = tmp_path / "item"
    path.touch()

    with pytest.raises(ValueError):
        shutil.chown(path)


def test_terminal_size_prefers_positive_environment_dimensions(monkeypatch):
    """COLUMNS/LINES 可覆盖 terminal query，返回值仍是 os.terminal_size tuple subtype。"""

    monkeypatch.setenv("COLUMNS", "132")
    monkeypatch.setenv("LINES", "43")

    size = shutil.get_terminal_size(fallback=(1, 1))

    assert isinstance(size, os.terminal_size)
    assert (size.columns, size.lines) == (132, 43)


def test_terminal_size_uses_fallback_when_no_terminal_can_be_queried(monkeypatch):
    """CI 的 stdout 常不是 TTY；fallback 让 formatter 不依赖交互式 machine state。"""

    monkeypatch.delenv("COLUMNS", raising=False)
    monkeypatch.delenv("LINES", raising=False)

    def unavailable_terminal_size(*_args, **_kwargs):
        raise OSError("not attached to a terminal")

    monkeypatch.setattr(shutil.os, "get_terminal_size", unavailable_terminal_size)

    assert shutil.get_terminal_size(fallback=(100, 30)) == os.terminal_size((100, 30))


def test_default_archive_registries_expose_names_and_descriptions():
    """注册表适合 capability discovery；压缩格式是否存在仍受可选 compression module 影响。"""

    archive_formats = dict(shutil.get_archive_formats())
    unpack_formats = {name: (extensions, description) for name, extensions, description in shutil.get_unpack_formats()}

    assert "tar" in archive_formats
    assert archive_formats["tar"]
    assert ".tar" in unpack_formats["tar"][0]
    assert unpack_formats["tar"][1]


def test_make_tar_archive_uses_root_dir_and_relative_base_dir(tmp_path):
    """root_dir 是 filesystem 参照点；base_dir 是写入 archive 的 relative common prefix。"""

    root = tmp_path / "root"
    bundle = root / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "data.txt").write_text("payload", encoding="utf-8")
    (root / "excluded.txt").write_text("excluded", encoding="utf-8")

    archive_name = shutil.make_archive(
        str(tmp_path / "snapshot"),
        "tar",
        root_dir=root,
        base_dir="bundle",
    )

    assert archive_name == str(tmp_path / "snapshot.tar")
    with tarfile.open(archive_name, mode="r") as archive:
        member_names = set(archive.getnames())

    assert "bundle" in member_names
    assert "bundle/data.txt" in member_names
    assert "excluded.txt" not in member_names


def test_make_zip_and_unpack_archive_form_a_high_level_round_trip(tmp_path):
    """filename extension 自动选择 unpacker；调用方仍要为 extract_dir 选择隔离位置。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "nested" / "item.txt").write_text("item", encoding="utf-8")
    archive_name = shutil.make_archive(
        str(tmp_path / "package"), "zip", root_dir=source
    )
    extracted = tmp_path / "extracted"

    returned = shutil.unpack_archive(archive_name, extracted)

    assert returned is None
    assert (extracted / "nested" / "item.txt").read_text(encoding="utf-8") == "item"


def test_unpack_archive_explicit_format_does_not_require_a_known_extension(tmp_path):
    """format 已由可信 metadata 给出时，archive pathname 可以没有注册 extension。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "item.txt").write_text("item", encoding="utf-8")
    generated = Path(
        shutil.make_archive(str(tmp_path / "generated"), "tar", root_dir=source)
    )
    opaque = generated.with_suffix(".bundle")
    generated.rename(opaque)
    destination = tmp_path / "destination"

    shutil.unpack_archive(opaque, destination, format="tar")

    assert (destination / "item.txt").read_text(encoding="utf-8") == "item"


def test_unpack_archive_distinguishes_unknown_name_from_unknown_explicit_format(tmp_path):
    """无法从 extension 推断时是 ReadError；显式给出未注册 format 属于 ValueError。"""

    archive = tmp_path / "payload.unknown"
    archive.write_bytes(b"not an archive")

    with pytest.raises(shutil.ReadError):
        shutil.unpack_archive(archive, tmp_path / "implicit")
    with pytest.raises(ValueError):
        shutil.unpack_archive(archive, tmp_path / "explicit", format="missing")


def test_make_archive_dry_run_reports_a_name_without_creating_the_archive(tmp_path):
    """dry_run 供部署预演；logger 接收计划，返回 pathname 不代表 artifact 已存在。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "item").touch()
    logger = logging.getLogger("polyglot.shutil.dry-run")

    archive_name = shutil.make_archive(
        str(tmp_path / "planned"),
        "tar",
        root_dir=source,
        dry_run=True,
        logger=logger,
    )

    assert archive_name == str(tmp_path / "planned.tar")
    assert not Path(archive_name).exists()


def test_untrusted_archive_members_are_rejected_before_unpacking(tmp_path):
    """extension 与 format 都不是 sandbox；data-only policy 还要拒绝 links 与 special files。"""

    archive_name = tmp_path / "untrusted.tar"
    payload = b"escaped"
    malicious_member = tarfile.TarInfo(name="../escape.txt")
    malicious_member.size = len(payload)
    malicious_link = tarfile.TarInfo(name="safe-looking-link")
    malicious_link.type = tarfile.SYMTYPE
    malicious_link.linkname = "../../escape.txt"
    with tarfile.open(archive_name, mode="w") as archive:
        archive.addfile(malicious_member, io.BytesIO(payload))
        archive.addfile(malicious_link)

    with tarfile.open(archive_name, mode="r") as archive:
        unsafe_names = [
            member.name
            for member in archive.getmembers()
            if not _tar_member_passes_basic_data_only_policy(member)
        ]

    assert unsafe_names == ["../escape.txt", "safe-looking-link"]
    assert not (tmp_path / "escape.txt").exists()
    # 发现不安全 member 后故意不调用 unpack_archive；“解包后再检查”已经太晚。


def test_custom_archive_format_receives_extra_args_and_is_always_unregistered(tmp_path):
    """自定义 archiver 修改 process-global registry；finally 防止后续测试或应用行为被污染。"""

    format_name = "polyglot-manifest"
    calls = []

    def make_manifest(base_name, base_dir, *, marker, **options):
        output = f"{base_name}.manifest"
        calls.append((base_dir, marker, options["dry_run"]))
        if not options["dry_run"]:
            Path(output).write_text(f"{base_dir}:{marker}", encoding="utf-8")
        return output

    shutil.register_archive_format(
        format_name,
        make_manifest,
        extra_args=(("marker", "v1"),),
        description="Polyglot manifest example",
    )
    try:
        source = tmp_path / "payload"
        source.mkdir()
        output = shutil.make_archive(
            str(tmp_path / "custom"),
            format_name,
            root_dir=tmp_path,
            base_dir="payload",
        )

        assert Path(output).read_text(encoding="utf-8") == "payload:v1"
        assert calls == [("payload", "v1", False)]
        assert dict(shutil.get_archive_formats())[format_name] == "Polyglot manifest example"
    finally:
        shutil.unregister_archive_format(format_name)

    assert format_name not in dict(shutil.get_archive_formats())


def test_custom_unpack_format_is_selected_by_extension_and_cleaned_up(tmp_path):
    """extensions 用于 dispatch，不用于内容验证；extra_args 可传固定 decoder 配置。"""

    format_name = "polyglot-bundle"
    extension = ".polyglot-bundle"
    calls = []

    def unpack_bundle(filename, extract_dir, *, marker):
        calls.append((Path(filename).name, marker))
        destination = Path(extract_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "content.txt").write_text(
            Path(filename).read_text(encoding="utf-8"), encoding="utf-8"
        )

    shutil.register_unpack_format(
        format_name,
        [extension],
        unpack_bundle,
        extra_args=(("marker", "v1"),),
        description="Polyglot bundle example",
    )
    try:
        archive = tmp_path / f"input{extension}"
        archive.write_text("payload", encoding="utf-8")
        destination = tmp_path / "destination"

        shutil.unpack_archive(archive, destination)

        assert (destination / "content.txt").read_text(encoding="utf-8") == "payload"
        assert calls == [(archive.name, "v1")]
        registered = {name: extensions for name, extensions, _ in shutil.get_unpack_formats()}
        assert registered[format_name] == [extension]
    finally:
        shutil.unregister_unpack_format(format_name)

    assert format_name not in {name for name, _, _ in shutil.get_unpack_formats()}
