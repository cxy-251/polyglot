"""126｜``zipfile.Path`` 的 Traversable 视图、文本 I/O 与安全边界。

``Path`` 把中央目录呈现成接近 ``pathlib.Path`` 的只读/可写视图，支持 ``/``、
``joinpath``、目录枚举和 text/binary open。它还能推导未显式存储的父目录，但不会清理
成员名称；将归档路径映射到真实文件系统前，caller 必须自行阻止绝对路径和 ``..``。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.zipfile.Path python.zipfile.Path.root
# polyglot-covers: python.zipfile.Path.truediv python.zipfile.Path.joinpath
# polyglot-covers: python.zipfile.Path.name python.zipfile.Path.iterdir
# polyglot-covers: python.zipfile.Path.exists python.zipfile.Path.is_dir
# polyglot-covers: python.zipfile.Path.is_file python.zipfile.Path.implicit-directory
# polyglot-covers: python.zipfile.Path.open-text python.zipfile.Path.open-binary
# polyglot-covers: python.zipfile.Path.read_text python.zipfile.Path.read_bytes
# polyglot-covers: python.zipfile.Path.write-text python.zipfile.Path.write-binary
# polyglot-covers: python.zipfile.Path.unsanitized python.zipfile.Path.security
# polyglot-covers: python.zipfile.Path.encoding-keyword python.zipfile.Traversable

import io
import zipfile


def _sample_archive():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("docs/guide.txt", "第一行\n第二行\n")
        archive.writestr("docs/raw.bin", b"\x00\xff")
        archive.writestr("top.txt", b"top")
    return buffer.getvalue()


def test_root_iterdir_infers_directories_not_stored_as_members():
    """只有 docs/guide.txt 也足以推导 docs/；调用方不必要求显式 directory entry。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        root = zipfile.Path(archive)
        children = {child.name: child for child in root.iterdir()}

        assert set(children) == {"docs", "top.txt"}
        assert children["docs"].is_dir() is True
        assert children["top.txt"].is_file() is True


def test_slash_and_multi_part_joinpath_traverse_the_same_member():
    """3.10 的 joinpath 可一次接收多个组件；``/`` 逐层组合得到等价位置。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        root = zipfile.Path(archive)
        via_slash = root / "docs" / "guide.txt"
        via_joinpath = root.joinpath("docs", "guide.txt")

        assert via_slash.at == via_joinpath.at == "docs/guide.txt"
        assert via_slash.exists() is True
        assert via_slash.is_file() is True
        assert (root / "missing.txt").exists() is False


def test_read_text_requires_an_explicit_encoding_for_portable_310_code():
    """encoding 用 keyword 兼容未打补丁的 3.10；默认 text open 还会做 newline 处理。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        guide = zipfile.Path(archive) / "docs" / "guide.txt"

        assert guide.read_text(encoding="utf-8") == "第一行\n第二行\n"
        with guide.open("r", encoding="utf-8") as stream:
            assert stream.readlines() == ["第一行\n", "第二行\n"]


def test_read_bytes_and_binary_open_return_member_bytes():
    """binary 模式忽略 TextIOWrapper 参数并直接交付 ZipExtFile 的 bytes。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        raw = zipfile.Path(archive) / "docs" / "raw.bin"

        assert raw.read_bytes() == b"\x00\xff"
        with raw.open("rb") as stream:
            assert stream.read(1) == b"\x00"
            assert stream.read() == b"\xff"


def test_path_open_writes_text_and_binary_members():
    """Path 不是纯只读 facade；root ZipFile 处于写模式时可用 w/wb 新建成员。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        root = zipfile.Path(archive)
        with (root / "text.txt").open("w", encoding="utf-8") as stream:
            assert stream.write("你好") == 2
        with (root / "raw.bin").open("wb") as stream:
            assert stream.write(b"\x00\xff") == 2

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.read("text.txt") == "你好".encode()
        assert archive.read("raw.bin") == b"\x00\xff"


def test_path_can_be_constructed_directly_from_a_path_like_object(tmp_path):
    """root 可是现有 ZipFile，也可是 ZipFile 构造器接受的 path；后者由 Path 内部打开。"""

    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("member.txt", b"content")

    member = zipfile.Path(archive_path) / "member.txt"
    try:
        assert member.read_bytes() == b"content"
    finally:
        member.root.close()


def test_path_exposes_parent_components_without_sanitizing_them():
    """与 extract 不同，Path 忠实访问 ``..`` 名称；复制到磁盘前必须单独验证 at。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../outside.txt", b"untrusted")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        root = zipfile.Path(archive)
        unsafe = root / ".." / "outside.txt"

        assert unsafe.exists() is True
        assert unsafe.read_bytes() == b"untrusted"
        assert unsafe.at == "../outside.txt"
