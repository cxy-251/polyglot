"""068｜``bz2`` one-shot、BZ2File 与 concatenated streams。

bzip2 的 level 范围是 1–9，没有 gzip/zlib 的 level 0。``bz2.decompress`` 与 ``BZ2File``
会透明处理拼接的多个 streams；append 因而可逐次增加 stream。传入已有 file object 时，
BZ2File 的 ``w`` 不 truncate，而按 append 语义写入，这是与路径输入的重要差异。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.bz2.compress python.bz2.decompress python.bz2.one-shot
# polyglot-covers: python.bz2.compression-level python.bz2.invalid-level
# polyglot-covers: python.bz2.bytes-like python.bz2.invalid-stream
# polyglot-covers: python.bz2.multistream python.bz2.trailing-garbage
# polyglot-covers: python.bz2.open python.bz2.BZ2File python.bz2.path-like
# polyglot-covers: python.bz2.binary-mode python.bz2.text-mode python.bz2.encoding
# polyglot-covers: python.bz2.append python.bz2.exclusive-create
# polyglot-covers: python.bz2.fileobj-write-does-not-truncate
# polyglot-covers: python.bz2.peek python.bz2.seek python.bz2.readinto
# polyglot-covers: python.bz2.iteration python.bz2.unsupported-detach
# polyglot-covers: python.bz2.unsupported-truncate python.bz2.thread-unsafe




import bz2
import io
import pytest

def test_one_shot_compress_and_decompress_round_trip_bytes():
    """完整内存 payload 使用 convenience functions；输出带 bzip2 ``BZh`` header。"""

    original = b"bzip2 content" * 100
    payload = bz2.compress(original)

    assert isinstance(payload, bytes)
    assert payload.startswith(b"BZh")
    assert bz2.decompress(payload) == original


@pytest.mark.parametrize("level", [1, 5, 9])
def test_documented_compression_levels_preserve_content(level):
    """1–9 调整 block size/压缩取舍，不改变解压后的 bytes。"""

    original = b"compression level" * 100

    assert bz2.decompress(bz2.compress(original, compresslevel=level)) == original


@pytest.mark.parametrize("level", [0, 10, -1])
def test_compression_level_outside_one_to_nine_is_rejected(level):
    """bzip2 不接受 0 或 -1 default sentinel；这点不能照搬 zlib 调用。"""

    with pytest.raises(ValueError):
        bz2.compress(b"payload", compresslevel=level)


def test_one_shot_functions_accept_bytes_like_inputs():
    """buffer protocol 输入避免预先复制；decompress 仍返回 immutable bytes。"""

    original = bytearray(b"mutable buffer" * 20)
    payload = bz2.compress(memoryview(original))

    assert bz2.decompress(bytearray(payload)) == bytes(original)


def test_decompress_rejects_input_that_never_starts_a_bzip2_stream():
    """完全错误的 header 由 low-level library 报 OSError。"""

    with pytest.raises(OSError):
        bz2.decompress(b"not a bzip2 stream")


def test_one_shot_decompress_combines_concatenated_streams():
    """3.3 起 convenience reader 自动迭代所有完整 streams。"""

    payload = bz2.compress(b"first") + bz2.compress(b"second")

    assert bz2.decompress(payload) == b"firstsecond"


def test_one_shot_decompress_ignores_garbage_after_valid_streams():
    """有效 stream 之后无法识别的 remainder 被忽略；严格 framing 需由调用者另行验证。"""

    payload = bz2.compress(b"valid") + b"unvalidated trailer"

    assert bz2.decompress(payload) == b"valid"


def test_binary_open_round_trips_a_path_like_file(tmp_path):
    """bz2.open 接受 PathLike 并返回 buffered binary-compatible file object。"""

    path = tmp_path / "payload.bz2"
    original = b"binary\x00payload" * 20
    with bz2.open(path, "wb", compresslevel=5) as stream:
        assert stream.write(original) == len(original)

    assert path.read_bytes().startswith(b"BZh")
    with bz2.open(path, "rb") as stream:
        assert stream.read() == original


def test_text_mode_applies_encoding_and_newline_translation(tmp_path):
    """text mode 由 TextIOWrapper 实现；压缩层本身仍只看到 encoded bytes。"""

    path = tmp_path / "text.bz2"
    with bz2.open(path, "wt", encoding="utf-8", newline="\n") as stream:
        stream.write("甲\n乙\n")

    with bz2.open(path, "rt", encoding="utf-8", newline=None) as stream:
        assert stream.readlines() == ["甲\n", "乙\n"]


def test_encoding_argument_is_rejected_in_binary_mode(tmp_path):
    """encoding/errors/newline 只适用于带 ``t`` 的 mode。"""

    with pytest.raises(ValueError, match="encoding"):
        bz2.open(tmp_path / "binary.bz2", "wb", encoding="utf-8")


def test_exclusive_create_refuses_an_existing_path(tmp_path):
    """x mode 保留普通文件的 fail-if-exists 语义。"""

    path = tmp_path / "existing.bz2"
    path.write_bytes(b"exists")

    with pytest.raises(FileExistsError):
        bz2.open(path, "xb")


def test_append_creates_another_stream_and_reader_combines_content(tmp_path):
    """每次 append 生成独立 bzip2 stream；读取端透明连接 uncompressed bytes。"""

    path = tmp_path / "members.bz2"
    with bz2.open(path, "wb") as stream:
        stream.write(b"first")
    first_stream_size = path.stat().st_size
    with bz2.open(path, "ab") as stream:
        stream.write(b"second")

    assert path.read_bytes()[first_stream_size : first_stream_size + 3] == b"BZh"
    with bz2.open(path, "rb") as stream:
        assert stream.read() == b"firstsecond"


def test_file_object_w_mode_appends_instead_of_truncating_existing_bytes():
    """filename 是 fileobj 时 ``w`` 等价 ``a``；caller 管理已有前缀和当前 position。"""

    prefix = b"outer-prefix"
    buffer = io.BytesIO(prefix)
    buffer.seek(0, io.SEEK_END)
    with bz2.BZ2File(buffer, "w") as stream:
        stream.write(b"compressed")

    assert buffer.closed is False
    assert buffer.getvalue().startswith(prefix + b"BZh")
    assert bz2.decompress(buffer.getvalue()[len(prefix) :]) == b"compressed"


def test_peek_keeps_uncompressed_position_stable(tmp_path):
    """peek 返回量未指定，且可能推进 underlying file；稳定保证只针对 BZ2File.tell。"""

    path = tmp_path / "peek.bz2"
    path.write_bytes(bz2.compress(b"abcdef"))
    with bz2.BZ2File(path, "rb") as stream:
        assert stream.tell() == 0
        assert stream.peek(2).startswith(b"ab")
        assert stream.tell() == 0
        assert stream.read(2) == b"ab"


def test_buffered_file_methods_support_seek_readinto_and_iteration(tmp_path):
    """BZ2File 支持常用 BufferedIOBase surface，但单实例并发读写不是 thread-safe。"""

    path = tmp_path / "buffered.bz2"
    path.write_bytes(bz2.compress(b"first\nsecond\n"))
    with bz2.BZ2File(path, "rb") as stream:
        assert stream.seek(6) == 6
        target = bytearray(6)
        assert stream.readinto(target) == 6
        assert target == b"second"
        stream.seek(0)
        assert list(stream) == [b"first\n", b"second\n"]


def test_detach_and_truncate_are_not_supported(tmp_path):
    """不能从压缩 wrapper 分离 raw stream，也不能原地截断压缩文件。"""

    path = tmp_path / "unsupported.bz2"
    with bz2.BZ2File(path, "wb") as stream:
        with pytest.raises(io.UnsupportedOperation):
            stream.detach()
        with pytest.raises(io.UnsupportedOperation):
            stream.truncate()


# ``BZ2Compressor``/``BZ2Decompressor`` 的增量状态机。
#
# incremental compressor 必须 flush 才形成完整 stream，且 flush 后不可复用。decompressor
# 没有 flush；``needs_input=False`` 表示内部仍有 output，应以 ``b''`` 继续拉取。它一次只
# 处理一个 stream，末尾内容进入 ``unused_data``，需要新 decompressor 接续。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.bz2.BZ2Compressor python.bz2.incremental-compress
# polyglot-covers: python.bz2.BZ2Compressor.compress python.bz2.BZ2Compressor.flush
# polyglot-covers: python.bz2.compressor-final-state python.bz2.flush-required
# polyglot-covers: python.bz2.BZ2Decompressor python.bz2.incremental-decompress
# polyglot-covers: python.bz2.BZ2Decompressor.eof python.bz2.needs-input
# polyglot-covers: python.bz2.max-length python.bz2.empty-input-drain
# polyglot-covers: python.bz2.unused-data python.bz2.single-stream
# polyglot-covers: python.bz2.multistream-manual python.bz2.EOFError
# polyglot-covers: python.bz2.truncated-stream python.bz2.completion-check
# polyglot-covers: python.bz2.bytes-like-incremental




def test_incremental_compressor_concatenates_outputs_and_flush():
    """compress 可返回空 bytes；所有输出按调用顺序加上最终 flush 才是完整 stream。"""

    chunks = [b"first" * 100, b"second" * 100, b"third" * 100]
    compressor = bz2.BZ2Compressor(5)
    parts = [compressor.compress(chunk) for chunk in chunks]
    parts.append(compressor.flush())

    assert bz2.decompress(b"".join(parts)) == b"".join(chunks)


def test_compressor_cannot_be_used_after_flush():
    """BZ2 flush 等价 finish，没有 sync-flush mode；继续输入必须新建 stream/object。"""

    compressor = bz2.BZ2Compressor()
    compressor.compress(b"payload")
    compressor.flush()

    with pytest.raises(ValueError):
        compressor.compress(b"too late")
    with pytest.raises(ValueError):
        compressor.flush()


def test_incremental_decompressor_accepts_arbitrary_transport_chunks():
    """transport chunk 不必对齐 bzip2 blocks；对象在调用间保留 decoder state。"""

    original = b"incremental content" * 200
    payload = bz2.compress(original)
    decompressor = bz2.BZ2Decompressor()
    output = []
    for start in range(0, len(payload), 9):
        output.append(decompressor.decompress(payload[start : start + 9]))

    assert b"".join(output) == original
    assert decompressor.eof is True
    assert decompressor.unused_data == b""


def test_max_length_uses_needs_input_to_drain_buffered_output():
    """limit 达到后即使没有新 compressed bytes，也应在 needs_input=False 时传 b'' 拉取。"""

    original = bytes(range(256)) * 20
    decompressor = bz2.BZ2Decompressor()
    output = [decompressor.decompress(bz2.compress(original), max_length=127)]

    while not decompressor.eof and not decompressor.needs_input:
        output.append(decompressor.decompress(b"", max_length=127))

    assert b"".join(output) == original
    assert decompressor.eof is True


def test_unused_data_holds_the_next_stream_for_a_new_decompressor():
    """incremental class 不透明处理 multistream；第一对象停止在首个 end marker。"""

    second_stream = bz2.compress(b"second")
    payload = bz2.compress(b"first") + second_stream
    first = bz2.BZ2Decompressor()

    assert first.decompress(payload) == b"first"
    assert first.eof is True
    assert first.unused_data == second_stream

    second = bz2.BZ2Decompressor()
    assert second.decompress(first.unused_data) == b"second"
    assert second.eof is True


def test_decompress_after_end_of_stream_raises_eof_error():
    """unused_data 已被保存；不能把同一对象当成 multistream decoder 继续调用。"""

    decompressor = bz2.BZ2Decompressor()
    assert decompressor.decompress(bz2.compress(b"done")) == b"done"

    with pytest.raises(EOFError):
        decompressor.decompress(b"")


def test_incremental_truncation_requires_explicit_eof_check():
    """不完整输入可能返回全部可解压 bytes 而不立刻报错；transport EOF 时检查属性。"""

    original = b"completion marker" * 100
    payload = bz2.compress(original)
    decompressor = bz2.BZ2Decompressor()
    partial = decompressor.decompress(payload[:-5])

    assert original.startswith(partial)
    assert decompressor.eof is False


def test_one_shot_api_rejects_the_same_truncated_stream():
    """one-shot 已知 input 到此结束，因此能把 eof=False 转换成 ValueError。"""

    payload = bz2.compress(b"completion marker" * 100)

    with pytest.raises(ValueError, match="end-of-stream"):
        bz2.decompress(payload[:-5])


def test_incremental_methods_accept_bytes_like_input():
    """compress/decompress 都接受 buffer protocol；output 始终是 bytes。"""

    compressor = bz2.BZ2Compressor()
    payload = compressor.compress(memoryview(b"buffer" * 20)) + compressor.flush()
    decompressor = bz2.BZ2Decompressor()
    restored = decompressor.decompress(bytearray(payload))

    assert restored == b"buffer" * 20
    assert type(restored) is bytes
