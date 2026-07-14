"""129｜``tarfile.open`` 模式、透明压缩、fileobj ownership 与流式归档。

普通 ``:`` 模式提供随机访问，``r:*`` 自动探测 gzip/bz2/xz；``|`` 模式则只顺序处理
blocks，可连接 pipe、socket 或 tape-like 对象。append 只适用于未压缩 TAR，caller 提供的
fileobj 不由 TarFile 关闭。模式字符串决定格式，不能只依赖文件扩展名。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.open python.tarfile.path-like
# polyglot-covers: python.tarfile.mode-r-auto python.tarfile.mode-r-uncompressed
# polyglot-covers: python.tarfile.mode-gz python.tarfile.mode-bz2 python.tarfile.mode-xz
# polyglot-covers: python.tarfile.compresslevel python.tarfile.preset
# polyglot-covers: python.tarfile.mode-w python.tarfile.mode-a python.tarfile.mode-x
# polyglot-covers: python.tarfile.no-compressed-append python.tarfile.ReadError
# polyglot-covers: python.tarfile.CompressionError python.tarfile.is_tarfile
# polyglot-covers: python.tarfile.fileobj-not-closed python.tarfile.context-manager
# polyglot-covers: python.tarfile.stream-read python.tarfile.stream-write
# polyglot-covers: python.tarfile.non-seekable python.tarfile.StreamError

import io
import tarfile

import pytest


class _WriteOnlyStream:
    """不提供 seek/tell，模拟只能顺序发送的 transport。"""

    def __init__(self, raw):
        self.raw = raw

    def write(self, data):
        return self.raw.write(data)


class _ReadOnlyStream:
    """只提供 read；流式 reader 不应向后 seek。"""

    def __init__(self, data):
        self.raw = io.BytesIO(data)

    def read(self, size=-1):
        return self.raw.read(size)


def _add_bytes(archive, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


@pytest.mark.parametrize(
    ("write_mode", "magic"),
    [
        ("w:", None),
        ("w:gz", b"\x1f\x8b"),
        ("w:bz2", b"BZh"),
        ("w:xz", b"\xfd7zXZ\x00"),
    ],
)
def test_write_modes_round_trip_with_transparent_read(write_mode, magic):
    """r:* 根据 header 探测压缩；suffix 不参与 fileobj 场景的格式选择。"""

    buffer = io.BytesIO()
    kwargs = {}
    if write_mode in {"w:gz", "w:bz2"}:
        kwargs["compresslevel"] = 1
    elif write_mode == "w:xz":
        kwargs["preset"] = 0
    with tarfile.open(fileobj=buffer, mode=write_mode, **kwargs) as archive:
        _add_bytes(archive, "payload.txt", b"content")

    raw = buffer.getvalue()
    if magic is not None:
        assert raw.startswith(magic)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as archive:
        member = archive.extractfile("payload.txt")
        assert member is not None
        assert member.read() == b"content"


def test_explicit_uncompressed_reader_rejects_compressed_data():
    """r: 禁止自动解压；若调用方不确定格式，应使用 r 或 r:*。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        _add_bytes(archive, "member", b"content")

    with pytest.raises(tarfile.ReadError):
        tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:")


def test_invalid_bytes_are_not_a_tar_archive():
    """is_tarfile 提供布尔探测；直接 open 则以 ReadError 暴露解析失败。"""

    raw = b"not a tar archive"

    assert tarfile.is_tarfile(io.BytesIO(raw)) is False
    with pytest.raises(tarfile.ReadError):
        tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")


def test_is_tarfile_accepts_a_path_like_object(tmp_path):
    """3.9+ 的探测 API 同时接受 path、文件对象和 file-like object。"""

    path = tmp_path / "archive.data"
    with tarfile.open(path, "w:") as archive:
        _add_bytes(archive, "member", b"content")

    assert tarfile.is_tarfile(path) is True


def test_w_mode_replaces_and_append_mode_preserves_members(tmp_path):
    """w 重建 archive；a 定位结尾 block 后追加 header/data，并保留旧成员顺序。"""

    path = tmp_path / "modes.tar"
    with tarfile.open(path, "w:") as archive:
        _add_bytes(archive, "old.txt", b"old")
    with tarfile.open(path, "w:") as archive:
        _add_bytes(archive, "replacement.txt", b"replacement")
    with tarfile.open(path, "a:") as archive:
        _add_bytes(archive, "appended.txt", b"appended")

    with tarfile.open(path, "r:") as archive:
        assert archive.getnames() == ["replacement.txt", "appended.txt"]


def test_append_creates_a_missing_uncompressed_archive(tmp_path):
    """a 模式兼有 create-if-missing 语义，但不能用于任何压缩 TAR。"""

    path = tmp_path / "new.tar"
    with tarfile.open(path, "a:") as archive:
        _add_bytes(archive, "member", b"content")

    assert tarfile.is_tarfile(path) is True


def test_compressed_append_mode_is_not_supported(tmp_path):
    """压缩流不能原地定位并改写结尾；需要解包重建或使用未压缩 a:。"""

    with pytest.raises(ValueError, match="mode must be"):
        tarfile.open(tmp_path / "archive.tar.gz", "a:gz")


def test_unknown_compression_name_raises_compression_error():
    """已知算法但错误 action 是 ValueError；未知算法本身则是 CompressionError。"""

    with pytest.raises(tarfile.CompressionError, match="unknown compression type"):
        tarfile.open(fileobj=io.BytesIO(), mode="w:unknown")


def test_exclusive_create_refuses_an_existing_path(tmp_path):
    """x 及 x:gz/x:bz2/x:xz 都执行 fail-if-exists；这里用基础格式展示。"""

    path = tmp_path / "existing.tar"
    path.write_bytes(b"preserve")

    with pytest.raises(FileExistsError):
        tarfile.open(path, "x:")
    assert path.read_bytes() == b"preserve"


def test_closing_tarfile_does_not_close_a_caller_owned_fileobj():
    """TarFile 只完成自己的零 block；fileobj 的生命周期仍由 caller 管理。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_bytes(archive, "member", b"content")

    assert buffer.closed is False
    assert tarfile.is_tarfile(io.BytesIO(buffer.getvalue())) is True


def test_stream_modes_round_trip_without_seek_or_tell():
    """w|gz/r|* 只依赖 write/read，适合 transport；成员必须按归档顺序消费。"""

    raw = io.BytesIO()
    with tarfile.open(fileobj=_WriteOnlyStream(raw), mode="w|gz") as archive:
        _add_bytes(archive, "first.txt", b"first")
        _add_bytes(archive, "second.txt", b"second")

    with tarfile.open(fileobj=_ReadOnlyStream(raw.getvalue()), mode="r|*") as archive:
        contents = []
        for info in archive:
            member = archive.extractfile(info)
            assert member is not None
            contents.append((info.name, member.read()))

    assert contents == [("first.txt", b"first"), ("second.txt", b"second")]


def test_stream_reader_rejects_random_access_to_an_earlier_member():
    """流已越过 first 的 data blocks 后不能倒带；错误类型是 StreamError。"""

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:") as archive:
        _add_bytes(archive, "first.txt", b"first")
        _add_bytes(archive, "second.txt", b"second")

    with tarfile.open(fileobj=_ReadOnlyStream(raw.getvalue()), mode="r|") as archive:
        first = archive.next()
        second = archive.next()
        assert first is not None and second is not None
        with pytest.raises(tarfile.StreamError, match="backward"):
            archive.extractfile(first)
