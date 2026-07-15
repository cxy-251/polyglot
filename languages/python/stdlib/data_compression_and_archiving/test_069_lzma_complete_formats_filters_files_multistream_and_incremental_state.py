"""069｜``lzma`` container format、integrity check、preset 与 filter chain。

默认 FORMAT_XZ 带 container 与 CRC64，FORMAT_ALONE 是受限旧格式，FORMAT_RAW 完全依赖
外部约定的 filter chain。高 preset 同时增加 CPU 与内存，preset 9 甚至可能占用约 800 MiB；
案例只使用低/默认配置，不把“最高”误当普遍最佳实践。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.lzma.compress python.lzma.decompress python.lzma.LZMAError
# polyglot-covers: python.lzma.FORMAT-XZ python.lzma.FORMAT-ALONE
# polyglot-covers: python.lzma.FORMAT-RAW python.lzma.FORMAT-AUTO
# polyglot-covers: python.lzma.raw-filters-required python.lzma.raw-not-auto-detected
# polyglot-covers: python.lzma.CHECK-NONE python.lzma.CHECK-CRC32
# polyglot-covers: python.lzma.CHECK-CRC64 python.lzma.CHECK-SHA256
# polyglot-covers: python.lzma.is-check-supported python.lzma.integrity-check
# polyglot-covers: python.lzma.corruption python.lzma.check-id
# polyglot-covers: python.lzma.preset python.lzma.PRESET-DEFAULT
# polyglot-covers: python.lzma.PRESET-EXTREME python.lzma.high-memory-trap
# polyglot-covers: python.lzma.memlimit python.lzma.preset-filter-exclusive
# polyglot-covers: python.lzma.filter-chain python.lzma.FILTER-DELTA
# polyglot-covers: python.lzma.FILTER-LZMA2 python.lzma.filter-chain-validation
# polyglot-covers: python.lzma.multistream python.lzma.trailing-garbage




import lzma
import pytest
import io

def test_default_one_shot_format_is_xz():
    """FORMAT_XZ 输出标准 XZ magic，FORMAT_AUTO 是 reader 默认。"""

    original = b"xz container" * 100
    payload = lzma.compress(original)

    assert payload.startswith(b"\xfd7zXZ\x00")
    assert lzma.decompress(payload) == original
    assert lzma.decompress(payload, format=lzma.FORMAT_XZ) == original


def test_legacy_alone_format_round_trips_and_auto_detects():
    """FORMAT_ALONE 对应旧 .lzma container，不支持 XZ 的 integrity check/filter 能力。"""

    original = b"legacy alone format" * 50
    payload = lzma.compress(original, format=lzma.FORMAT_ALONE)

    assert lzma.decompress(payload, format=lzma.FORMAT_ALONE) == original
    assert lzma.decompress(payload, format=lzma.FORMAT_AUTO) == original
    with pytest.raises(lzma.LZMAError):
        lzma.decompress(payload, format=lzma.FORMAT_XZ)


def test_raw_format_requires_the_same_explicit_filter_chain_on_both_sides():
    """RAW 无 header 描述 algorithm/options；filters 是调用双方的 out-of-band contract。"""

    filters = [{"id": lzma.FILTER_LZMA2, "dict_size": 1 << 16}]
    original = b"raw lzma2" * 100
    payload = lzma.compress(original, format=lzma.FORMAT_RAW, filters=filters)

    assert lzma.decompress(
        payload,
        format=lzma.FORMAT_RAW,
        filters=filters,
    ) == original
    with pytest.raises(lzma.LZMAError):
        lzma.decompress(payload, format=lzma.FORMAT_AUTO)


def test_raw_format_without_filters_is_rejected_at_construction():
    """RAW 既没有默认可发现配置，也不能只在一侧省略 filters。"""

    with pytest.raises((ValueError, lzma.LZMAError)):
        lzma.compress(b"payload", format=lzma.FORMAT_RAW)
    with pytest.raises((ValueError, lzma.LZMAError)):
        lzma.decompress(b"payload", format=lzma.FORMAT_RAW)


def test_none_and_crc32_checks_are_always_supported():
    """liblzma 构建必须提供 NONE/CRC32；CRC64/SHA256 则要运行时探测。"""

    assert lzma.is_check_supported(lzma.CHECK_NONE) is True
    assert lzma.is_check_supported(lzma.CHECK_CRC32) is True


@pytest.mark.parametrize(
    "check",
    [lzma.CHECK_NONE, lzma.CHECK_CRC32, lzma.CHECK_CRC64, lzma.CHECK_SHA256],
)
def test_supported_xz_checks_are_reported_by_the_decompressor(check):
    """可选 check 只在 is_check_supported 为真时构造；decoder.check 暴露 stream ID。"""

    if not lzma.is_check_supported(check):
        pytest.skip(f"linked liblzma 不支持 integrity check {check}")

    payload = lzma.compress(b"checked content", check=check)
    decompressor = lzma.LZMADecompressor()
    assert decompressor.decompress(payload) == b"checked content"
    assert decompressor.eof is True
    assert decompressor.check == check


def test_integrity_check_detects_corrupted_compressed_data():
    """check 用于意外损坏检测；翻转 payload 中部 byte 后解压失败。"""

    payload = bytearray(lzma.compress(b"protected content" * 500))
    payload[len(payload) // 2] ^= 0x01

    with pytest.raises(lzma.LZMAError):
        lzma.decompress(payload)


@pytest.mark.parametrize("preset", [0, lzma.PRESET_DEFAULT, 6])
def test_low_and_default_presets_round_trip_without_high_memory_settings(preset):
    """PRESET_DEFAULT 等于 6；案例避免 preset 9 的巨大 compressor/decompressor memory。"""

    original = b"preset content" * 100

    assert lzma.decompress(lzma.compress(original, preset=preset)) == original


def test_extreme_flag_is_or_ed_with_a_numeric_preset():
    """PRESET_EXTREME 是 bit flag，不是独立 level；此处配低 level 控制资源。"""

    original = b"extreme mode semantics" * 100
    payload = lzma.compress(original, preset=0 | lzma.PRESET_EXTREME)

    assert lzma.decompress(payload) == original


def test_invalid_preset_is_rejected():
    """有效基本 level 是 0–9，可选 OR EXTREME；其他 bit pattern 不被接受。"""

    with pytest.raises(lzma.LZMAError):
        lzma.compress(b"payload", preset=10)


def test_memlimit_can_refuse_a_stream_requiring_more_decoder_memory():
    """memlimit 是防止 attacker-controlled header 请求过多内存的资源边界。"""

    payload = lzma.compress(b"memory bounded" * 100)

    with pytest.raises(lzma.LZMAError):
        lzma.decompress(payload, memlimit=1024)


def test_preset_and_custom_filters_are_mutually_exclusive():
    """preset 是整套 options，filters 是显式链；同时给出会产生歧义。"""

    filters = [{"id": lzma.FILTER_LZMA2, "preset": 0}]

    with pytest.raises(ValueError):
        lzma.compress(b"payload", preset=0, filters=filters)


def test_delta_then_lzma2_custom_filter_chain_round_trips():
    """非 compression filter 必须在前，最后一个必须是 LZMA1/LZMA2。"""

    filters = [
        {"id": lzma.FILTER_DELTA, "dist": 1},
        {"id": lzma.FILTER_LZMA2, "preset": 1},
    ]
    original = bytes(range(64)) * 100
    payload = lzma.compress(original, format=lzma.FORMAT_XZ, filters=filters)

    assert lzma.decompress(payload) == original


@pytest.mark.parametrize(
    "filters",
    [
        [],
        [{"id": lzma.FILTER_DELTA, "dist": 1}],
        [{"id": lzma.FILTER_LZMA2}] * 5,
    ],
)
def test_filter_chain_must_be_nonempty_valid_and_at_most_four(filters):
    """空链、缺少末端 compression filter、超过四项都在压缩前失败。"""

    with pytest.raises((ValueError, lzma.LZMAError)):
        lzma.compress(b"payload", filters=filters)


def test_one_shot_decompress_combines_concatenated_streams():
    """和 bz2 一样，one-shot reader 自动处理多个完整 containers。"""

    payload = lzma.compress(b"first") + lzma.compress(b"second")

    assert lzma.decompress(payload) == b"firstsecond"


def test_one_shot_decompress_ignores_garbage_after_a_valid_stream():
    """有效 stream 后无法识别的 bytes 不会出现在结果；严格外层格式需自行验证 remainder。"""

    assert lzma.decompress(lzma.compress(b"valid") + b"trailer") == b"valid"


# ``lzma.open``/``LZMAFile`` 的文件、文本与多 stream 行为。
#
# LZMAFile 的 surface 与 BZ2File 类似：支持 XZ/legacy/raw、binary/text wrapper、seek/peek，
# 读取时透明连接多个 streams。已有 fileobj 的 ownership 留给 caller，``w`` 也不会 truncate；
# 单个 LZMAFile 实例不是 thread-safe，并发使用要由应用加锁。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.lzma.open python.lzma.LZMAFile python.lzma.path-like
# polyglot-covers: python.lzma.binary-mode python.lzma.text-mode python.lzma.encoding
# polyglot-covers: python.lzma.file-format python.lzma.file-check python.lzma.file-preset
# polyglot-covers: python.lzma.exclusive-create python.lzma.append
# polyglot-covers: python.lzma.file-multistream python.lzma.fileobj-not-closed
# polyglot-covers: python.lzma.fileobj-write-does-not-truncate
# polyglot-covers: python.lzma.peek python.lzma.seek python.lzma.readinto
# polyglot-covers: python.lzma.iteration python.lzma.unsupported-detach
# polyglot-covers: python.lzma.unsupported-truncate python.lzma.thread-unsafe




def test_binary_open_round_trips_xz_at_a_path_like_object(tmp_path):
    """默认写 FORMAT_XZ；PathLike 直接传入，不依赖 filename extension 选择格式。"""

    path = tmp_path / "payload.xz"
    original = b"binary\x00payload" * 50
    with lzma.open(path, "wb", preset=1) as stream:
        assert stream.write(original) == len(original)

    assert path.read_bytes().startswith(b"\xfd7zXZ\x00")
    with lzma.open(path, "rb") as stream:
        assert stream.read() == original


def test_file_format_can_be_legacy_alone_independent_of_suffix(tmp_path):
    """format 参数而非 .lzma suffix 决定 writer；reader FORMAT_AUTO 可识别。"""

    path = tmp_path / "legacy.data"
    with lzma.open(path, "wb", format=lzma.FORMAT_ALONE) as stream:
        stream.write(b"legacy")

    with lzma.open(path, "rb", format=lzma.FORMAT_AUTO) as stream:
        assert stream.read() == b"legacy"


def test_text_mode_applies_encoding_and_newline_translation(tmp_path):
    """wt/rt 返回 TextIOWrapper；LZMAFile 本体只处理 binary bytes。"""

    path = tmp_path / "text.xz"
    with lzma.open(path, "wt", encoding="utf-8", newline="\n") as stream:
        stream.write("甲\n乙\n")

    with lzma.open(path, "rt", encoding="utf-8", newline=None) as stream:
        assert stream.readlines() == ["甲\n", "乙\n"]


def test_encoding_argument_is_rejected_in_binary_mode(tmp_path):
    """encoding/errors/newline 不能和 binary mode 混用。"""

    with pytest.raises(ValueError, match="encoding"):
        lzma.open(tmp_path / "binary.xz", "wb", encoding="utf-8")


def test_exclusive_create_refuses_an_existing_path(tmp_path):
    """x/xb/xt 与 ordinary open 一样执行 fail-if-exists。"""

    path = tmp_path / "existing.xz"
    path.write_bytes(b"exists")

    with pytest.raises(FileExistsError):
        lzma.open(path, "xb")


def test_append_adds_a_new_stream_and_reader_combines_content(tmp_path):
    """append 不重写旧 XZ container，而是增加独立 stream。"""

    path = tmp_path / "members.xz"
    with lzma.open(path, "wb") as stream:
        stream.write(b"first")
    first_stream_size = path.stat().st_size
    with lzma.open(path, "ab") as stream:
        stream.write(b"second")

    assert path.read_bytes()[first_stream_size : first_stream_size + 6] == b"\xfd7zXZ\x00"
    with lzma.open(path, "rb") as stream:
        assert stream.read() == b"firstsecond"


def test_file_object_w_mode_preserves_prefix_and_does_not_close_owner():
    """fileobj ``w`` 不 truncate；LZMAFile.close 也不关闭 caller-owned stream。"""

    prefix = b"outer-prefix"
    buffer = io.BytesIO(prefix)
    buffer.seek(0, io.SEEK_END)
    with lzma.LZMAFile(buffer, "w", preset=0) as stream:
        stream.write(b"compressed")

    assert buffer.closed is False
    assert buffer.getvalue().startswith(prefix + b"\xfd7zXZ\x00")
    assert lzma.decompress(buffer.getvalue()[len(prefix) :]) == b"compressed"


def test_peek_ignores_size_and_keeps_uncompressed_position(tmp_path):
    """size 只是兼容参数且被忽略；返回量未指定，tell 不前进。"""

    path = tmp_path / "peek.xz"
    path.write_bytes(lzma.compress(b"abcdef"))
    with lzma.LZMAFile(path, "rb") as stream:
        assert stream.tell() == 0
        assert stream.peek(1).startswith(b"a")
        assert stream.tell() == 0
        assert stream.read(2) == b"ab"


def test_buffered_methods_support_seek_readinto_and_iteration(tmp_path):
    """LZMAFile 提供常用 BufferedIOBase 操作，但同一实例并发调用需外部 lock。"""

    path = tmp_path / "buffered.xz"
    path.write_bytes(lzma.compress(b"first\nsecond\n"))
    with lzma.LZMAFile(path, "rb") as stream:
        assert stream.seek(6) == 6
        target = bytearray(6)
        assert stream.readinto(target) == 6
        assert target == b"second"
        stream.seek(0)
        assert list(stream) == [b"first\n", b"second\n"]


def test_detach_and_truncate_are_not_supported(tmp_path):
    """compressed wrapper 不能 detach raw stream，也不能原地 truncate。"""

    path = tmp_path / "unsupported.xz"
    with lzma.LZMAFile(path, "wb") as stream:
        with pytest.raises(io.UnsupportedOperation):
            stream.detach()
        with pytest.raises(io.UnsupportedOperation):
            stream.truncate()


# ``LZMACompressor``/``LZMADecompressor`` 增量状态与 stream 接续。
#
# 和 bz2 相同，compressor 只能 finish-flush 一次；decompressor 依靠 ``needs_input`` 拉取
# buffered output，一次只处理一个 stream。``check`` 可能在读到足够 header 前为 UNKNOWN，
# transport 结束时还必须检查 ``eof``，否则 truncated stream 可能被当成成功。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.lzma.LZMACompressor python.lzma.incremental-compress
# polyglot-covers: python.lzma.Compressor.compress python.lzma.Compressor.flush
# polyglot-covers: python.lzma.compressor-final-state python.lzma.flush-required
# polyglot-covers: python.lzma.LZMADecompressor python.lzma.incremental-decompress
# polyglot-covers: python.lzma.Decompressor.check python.lzma.CHECK-UNKNOWN
# polyglot-covers: python.lzma.Decompressor.eof python.lzma.needs-input
# polyglot-covers: python.lzma.max-length python.lzma.empty-input-drain
# polyglot-covers: python.lzma.unused-data python.lzma.single-stream
# polyglot-covers: python.lzma.multistream-manual python.lzma.EOFError
# polyglot-covers: python.lzma.truncated-stream python.lzma.completion-check
# polyglot-covers: python.lzma.bytes-like-incremental




def test_incremental_compressor_concatenates_outputs_and_flush():
    """部分 output 可能为空；所有 compress 结果加最后 flush 才构成完整 container。"""

    chunks = [b"first" * 100, b"second" * 100, b"third" * 100]
    compressor = lzma.LZMACompressor(preset=1)
    parts = [compressor.compress(chunk) for chunk in chunks]
    parts.append(compressor.flush())

    assert lzma.decompress(b"".join(parts)) == b"".join(chunks)


def test_compressor_cannot_be_used_after_flush():
    """没有 sync-flush；结束后继续输入或再次 flush 都是 ValueError。"""

    compressor = lzma.LZMACompressor(preset=0)
    compressor.compress(b"payload")
    compressor.flush()

    with pytest.raises(ValueError):
        compressor.compress(b"too late")
    with pytest.raises(ValueError):
        compressor.flush()


def test_decompressor_check_starts_unknown_then_reflects_xz_header():
    """decoder 在消费 header 后才能报告 stream 使用的 integrity check。"""

    decompressor = lzma.LZMADecompressor()
    assert decompressor.check == lzma.CHECK_UNKNOWN
    payload = lzma.compress(b"checked", check=lzma.CHECK_CRC32)

    assert decompressor.decompress(payload) == b"checked"
    assert decompressor.check == lzma.CHECK_CRC32


def test_incremental_decompressor_accepts_arbitrary_transport_chunks():
    """compressed block 与 network/file chunk 无需对齐；state 保存在对象中。"""

    original = b"incremental content" * 200
    payload = lzma.compress(original, preset=1)
    decompressor = lzma.LZMADecompressor()
    output = []
    for start in range(0, len(payload), 11):
        output.append(decompressor.decompress(payload[start : start + 11]))

    assert b"".join(output) == original
    assert decompressor.eof is True
    assert decompressor.unused_data == b""


def test_max_length_uses_needs_input_to_drain_buffered_output():
    """needs_input=False 时传 b''，否则会把 decoder 已持有的 output 留在对象里。"""

    original = bytes(range(256)) * 20
    decompressor = lzma.LZMADecompressor()
    output = [decompressor.decompress(lzma.compress(original), max_length=127)]

    while not decompressor.eof and not decompressor.needs_input:
        output.append(decompressor.decompress(b"", max_length=127))

    assert b"".join(output) == original
    assert decompressor.eof is True


def test_unused_data_holds_next_stream_for_a_new_decompressor():
    """incremental class 停在首个 end marker；unused_data 交给新对象。"""

    second_stream = lzma.compress(b"second")
    payload = lzma.compress(b"first") + second_stream
    first = lzma.LZMADecompressor()

    assert first.decompress(payload) == b"first"
    assert first.eof is True
    assert first.unused_data == second_stream

    second = lzma.LZMADecompressor()
    assert second.decompress(first.unused_data) == b"second"
    assert second.eof is True


def test_decompress_after_end_of_stream_raises_eof_error():
    """同一对象不能自动接续 unused_data 中的下一 stream。"""

    decompressor = lzma.LZMADecompressor()
    assert decompressor.decompress(lzma.compress(b"done")) == b"done"

    with pytest.raises(EOFError):
        decompressor.decompress(b"")


def test_incremental_truncation_requires_explicit_eof_check():
    """不完整 input 可能先返回部分/全部可恢复 bytes；transport EOF 时必须检查 eof。"""

    original = b"completion marker" * 100
    payload = lzma.compress(original)
    decompressor = lzma.LZMADecompressor()
    partial = decompressor.decompress(payload[:-5])

    assert original.startswith(partial)
    assert decompressor.eof is False


def test_one_shot_api_rejects_the_same_truncated_stream():
    """one-shot 知道 input 已结束，因此把未到 end marker 报为 LZMAError。"""

    payload = lzma.compress(b"completion marker" * 100)

    with pytest.raises(lzma.LZMAError, match="end-of-stream"):
        lzma.decompress(payload[:-5])


def test_incremental_methods_accept_bytes_like_input():
    """buffer protocol 输入不要求预先转换，返回值仍为 immutable bytes。"""

    compressor = lzma.LZMACompressor(preset=0)
    payload = compressor.compress(memoryview(b"buffer" * 20)) + compressor.flush()
    decompressor = lzma.LZMADecompressor()
    restored = decompressor.decompress(bytearray(payload))

    assert restored == b"buffer" * 20
    assert type(restored) is bytes
