"""067｜``zlib`` one-shot 压缩、校验和与 wrapper format。

zlib API 处理 bytes，不保证压缩后一定更小；level 只在速度/体积间取舍。``wbits`` 同时
决定 DEFLATE window 与 zlib/raw/gzip wrapper，解压端必须匹配。Adler-32/CRC-32 用于
意外损坏检测，不具备密码学认证能力。

这些案例面向 Python 3.10。
"""

# polyglot-covers: python.zlib.compress python.zlib.decompress python.zlib.error
# polyglot-covers: python.zlib.compression-level python.zlib.Z-NO-COMPRESSION
# polyglot-covers: python.zlib.Z-BEST-SPEED python.zlib.Z-BEST-COMPRESSION
# polyglot-covers: python.zlib.bytes-like python.zlib.small-data-expansion
# polyglot-covers: python.zlib.adler32 python.zlib.crc32 python.zlib.running-checksum
# polyglot-covers: python.zlib.unsigned-checksum python.zlib.not-cryptographic
# polyglot-covers: python.zlib.wbits python.zlib.zlib-wrapper python.zlib.raw-deflate
# polyglot-covers: python.zlib.gzip-wrapper python.zlib.auto-wrapper-detection
# polyglot-covers: python.zlib.wrong-wrapper python.zlib.trailing-data
# polyglot-covers: python.zlib.one-shot-truncated-stream python.zlib.bufsize-initial-only
# polyglot-covers: python.zlib.ZLIB-VERSION python.zlib.ZLIB-RUNTIME-VERSION




import zlib
import pytest
import copy
import gzip
import io
import struct

def _compress_with_wbits(data, wbits):
    compressor = zlib.compressobj(wbits=wbits)
    return compressor.compress(data) + compressor.flush()


def test_one_shot_compression_round_trips_binary_data():
    """compress/decompress 最适合已在内存中的完整 payload，返回值始终是 bytes。"""

    original = (b"Python compression semantics\x00" * 40) + bytes(range(64))
    compressed = zlib.compress(original)
    restored = zlib.decompress(compressed)

    assert isinstance(compressed, bytes)
    assert restored == original
    assert type(restored) is bytes


@pytest.mark.parametrize("level", [-1, 0, 1, 6, 9])
def test_documented_compression_levels_all_preserve_content(level):
    """-1 是 library default，0 不压缩，1/9 分别偏速度/体积；都不改变数据语义。"""

    original = b"repeated-value:" * 100

    assert zlib.decompress(zlib.compress(original, level=level)) == original


def test_best_compression_often_beats_no_compression_for_repetitive_data():
    """体积差异依赖 input；只对高度重复的受控样本比较，不能当成任意数据的保证。"""

    original = b"A" * 10_000
    stored = zlib.compress(original, level=zlib.Z_NO_COMPRESSION)
    compressed = zlib.compress(original, level=zlib.Z_BEST_COMPRESSION)

    assert len(compressed) < len(stored)
    assert zlib.decompress(stored) == zlib.decompress(compressed) == original


def test_tiny_input_can_grow_because_stream_metadata_has_a_cost():
    """压缩 wrapper/header/checksum 有固定开销；小消息不应假定 len(output) < len(input)。"""

    original = b"x"
    compressed = zlib.compress(original)

    assert len(compressed) > len(original)
    assert zlib.decompress(compressed) == original


def test_compress_accepts_bytes_like_objects_but_returns_immutable_bytes():
    """bytearray/memoryview 可直接作为 input buffer；output 不共享可变源内存。"""

    source = bytearray(b"buffer protocol" * 20)
    from_bytearray = zlib.compress(source)
    from_view = zlib.compress(memoryview(source))
    source[0] = ord("B")

    assert from_bytearray == from_view
    assert zlib.decompress(from_bytearray).startswith(b"buffer")


@pytest.mark.parametrize("level", [-2, 10, 100])
def test_invalid_compression_level_raises_zlib_error(level):
    """level 不是任意整数 hint；范围外由 linked zlib 拒绝。"""

    with pytest.raises(zlib.error):
        zlib.compress(b"payload", level=level)


def test_adler32_can_be_updated_incrementally():
    """把前一段 checksum 作为 value，结果等于一次计算 concatenated bytes。"""

    first = b"first chunk"
    second = b"second chunk"
    running = zlib.adler32(second, zlib.adler32(first))

    assert running == zlib.adler32(first + second)
    assert 0 <= running <= 0xFFFFFFFF


def test_crc32_can_be_updated_incrementally():
    """CRC-32 同样支持 streaming state，但碰撞风险使它不适合签名或身份认证。"""

    chunks = [b"header", b"body", b"trailer"]
    running = 0
    for chunk in chunks:
        running = zlib.crc32(chunk, running)

    assert running == zlib.crc32(b"".join(chunks))
    assert 0 <= running <= 0xFFFFFFFF


def test_positive_wbits_produces_and_requires_a_zlib_wrapper():
    """默认正 MAX_WBITS 带 zlib header/trailer；raw/gzip decoder 不能替代。"""

    original = b"zlib wrapped" * 20
    payload = _compress_with_wbits(original, zlib.MAX_WBITS)

    assert zlib.decompress(payload, wbits=zlib.MAX_WBITS) == original
    with pytest.raises(zlib.error):
        zlib.decompress(payload, wbits=-zlib.MAX_WBITS)


def test_negative_wbits_produces_raw_deflate_without_wrapper():
    """raw DEFLATE 没有 header/trailing checksum，必须由外层格式负责 framing/integrity。"""

    original = b"raw deflate" * 20
    payload = _compress_with_wbits(original, -zlib.MAX_WBITS)

    assert zlib.decompress(payload, wbits=-zlib.MAX_WBITS) == original
    with pytest.raises(zlib.error):
        zlib.decompress(payload)


def test_wbits_plus_sixteen_produces_a_gzip_compatible_stream():
    """16 + window bits 添加 gzip wrapper；输出以 gzip magic bytes 开始。"""

    original = b"gzip wrapper" * 20
    gzip_wbits = zlib.MAX_WBITS | 16
    payload = _compress_with_wbits(original, gzip_wbits)

    assert payload.startswith(b"\x1f\x8b")
    assert zlib.decompress(payload, wbits=gzip_wbits) == original


def test_wbits_plus_thirty_two_accepts_zlib_or_gzip_but_not_raw():
    """32 + window bits 只在解压端自动识别 zlib/gzip wrapper。"""

    original = b"auto detect" * 20
    zlib_payload = _compress_with_wbits(original, zlib.MAX_WBITS)
    gzip_payload = _compress_with_wbits(original, zlib.MAX_WBITS | 16)
    raw_payload = _compress_with_wbits(original, -zlib.MAX_WBITS)
    auto_wbits = zlib.MAX_WBITS | 32

    assert zlib.decompress(zlib_payload, wbits=auto_wbits) == original
    assert zlib.decompress(gzip_payload, wbits=auto_wbits) == original
    with pytest.raises(zlib.error):
        zlib.decompress(raw_payload, wbits=auto_wbits)


def test_one_shot_decompress_ignores_bytes_after_first_stream():
    """one-shot API 不返回 remainder；需要解析 concatenated/framed 数据时改用 decompressobj。"""

    first = zlib.compress(b"first")
    second = zlib.compress(b"second")

    assert zlib.decompress(first + second) == b"first"
    assert zlib.decompress(first + b"application trailer") == b"first"


def test_one_shot_decompress_rejects_a_truncated_stream():
    """完整性检查需要读到 trailer；截短 payload 不能被当作部分成功。"""

    payload = zlib.compress(b"content" * 100)

    with pytest.raises(zlib.error, match="incomplete|truncated"):
        zlib.decompress(payload[:-2])


def test_bufsize_is_only_an_initial_allocation_hint():
    """bufsize 太小不会截断 output；buffer 会按需增长，max_length 属于 streaming API。"""

    original = b"large output" * 1000
    payload = zlib.compress(original)

    assert zlib.decompress(payload, bufsize=1) == original


def test_build_and_runtime_zlib_versions_are_separate_strings():
    """编译时与运行时 library 可能不同；排查兼容问题时应同时记录。"""

    assert isinstance(zlib.ZLIB_VERSION, str)
    assert isinstance(zlib.ZLIB_RUNTIME_VERSION, str)
    assert zlib.ZLIB_VERSION
    assert zlib.ZLIB_RUNTIME_VERSION


# ``zlib`` incremental object、flush、remainder 与预置字典。
#
# streaming compressor/decompressor 带可变状态：每次输出都要按顺序拼接；``Z_FINISH``/
# ``flush()`` 后对象不可复用。``unused_data`` 是完整 stream 之后的外层数据，
# ``unconsumed_tail`` 则是 max_length 暂未处理的压缩输入，两者不可混淆。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.zlib.compressobj python.zlib.Compress.compress
# polyglot-covers: python.zlib.Compress.flush python.zlib.Z-FINISH
# polyglot-covers: python.zlib.Z-SYNC-FLUSH python.zlib.continue-after-sync
# polyglot-covers: python.zlib.decompressobj python.zlib.Decompress.decompress
# polyglot-covers: python.zlib.Decompress.flush python.zlib.Decompress.eof
# polyglot-covers: python.zlib.unused-data python.zlib.outer-framing
# polyglot-covers: python.zlib.unconsumed-tail python.zlib.max-length
# polyglot-covers: python.zlib.truncated-stream python.zlib.eof-check
# polyglot-covers: python.zlib.Compress.copy python.zlib.shared-prefix
# polyglot-covers: python.zlib.Decompress.copy python.zlib.random-seek-checkpoint
# polyglot-covers: python.zlib.copy-module-support python.zlib.deepcopy
# polyglot-covers: python.zlib.zdict python.zlib.dictionary-required
# polyglot-covers: python.zlib.dictionary-mismatch python.zlib.dictionary-ordering




def test_streaming_compressor_concatenates_each_output_and_final_flush():
    """compress 可能因内部 buffering 返回空 bytes；不能丢弃任何一段，也不能漏掉 flush。"""

    chunks = [b"first-" * 20, b"second-" * 20, b"third" * 20]
    compressor = zlib.compressobj()
    output_parts = [compressor.compress(chunk) for chunk in chunks]
    output_parts.append(compressor.flush())

    assert zlib.decompress(b"".join(output_parts)) == b"".join(chunks)


def test_sync_flush_exposes_pending_output_but_allows_more_input():
    """Z_SYNC_FLUSH 建立可消费边界但不结束 stream，后续仍能 compress 并最终 finish。"""

    compressor = zlib.compressobj()
    prefix = compressor.compress(b"prefix" * 20)
    checkpoint = compressor.flush(zlib.Z_SYNC_FLUSH)
    suffix = compressor.compress(b"suffix" * 20)
    finished = compressor.flush(zlib.Z_FINISH)
    payload = prefix + checkpoint + suffix + finished

    assert checkpoint
    assert zlib.decompress(payload) == (b"prefix" * 20) + (b"suffix" * 20)


def test_finish_flush_invalidates_the_compression_object():
    """默认 flush mode 是 Z_FINISH；结束后再次 compress 属于 inconsistent stream state。"""

    compressor = zlib.compressobj()
    compressor.compress(b"payload")
    compressor.flush()

    with pytest.raises(zlib.error):
        compressor.compress(b"too late")
    with pytest.raises(zlib.error):
        compressor.flush()


def test_streaming_decompressor_accepts_arbitrary_input_chunks():
    """压缩 block 边界与 transport chunk 边界无关，decompressor 会保存跨调用状态。"""

    original = b"streaming content:" * 100
    payload = zlib.compress(original)
    decompressor = zlib.decompressobj()
    output = []
    for start in range(0, len(payload), 7):
        output.append(decompressor.decompress(payload[start : start + 7]))
    output.append(decompressor.flush())

    assert b"".join(output) == original
    assert decompressor.eof is True
    assert decompressor.unused_data == b""
    assert decompressor.unconsumed_tail == b""


def test_eof_distinguishes_complete_from_silently_truncated_incremental_input():
    """incremental decompress 可先返回部分 output 而不报错；结束 transport 时必须检查 eof。"""

    original = b"complete me" * 100
    payload = zlib.compress(original)
    decompressor = zlib.decompressobj()
    partial = decompressor.decompress(payload[:-2])

    assert partial
    assert partial == original
    assert decompressor.eof is False


def test_unused_data_contains_bytes_after_the_complete_stream():
    """unused_data 已越过 compression framing，可交给下一个 parser 或新 decompressor。"""

    payload = zlib.compress(b"first stream")
    remainder = zlib.compress(b"second stream")
    decompressor = zlib.decompressobj()
    restored = decompressor.decompress(payload + remainder)

    assert restored == b"first stream"
    assert decompressor.eof is True
    assert decompressor.unused_data == remainder
    assert decompressor.unconsumed_tail == b""
    assert zlib.decompress(decompressor.unused_data) == b"second stream"


def test_max_length_places_unprocessed_input_in_unconsumed_tail():
    """限制每次 output 时必须反复回送 unconsumed_tail，否则会静默丢数据。"""

    original = bytes(range(256)) * 20
    payload = zlib.compress(original)
    decompressor = zlib.decompressobj()
    output = []
    pending = payload

    while pending:
        output.append(decompressor.decompress(pending, max_length=113))
        pending = decompressor.unconsumed_tail
    output.append(decompressor.flush())

    assert b"".join(output) == original
    assert decompressor.eof is True


def test_decompress_flush_finishes_the_object_and_prevents_reuse():
    """flush 处理 pending output 并结束 object；之后应创建新 decompressor。"""

    payload = zlib.compress(b"payload")
    decompressor = zlib.decompressobj()
    restored = decompressor.decompress(payload) + decompressor.flush()

    assert restored == b"payload"
    with pytest.raises(zlib.error):
        decompressor.decompress(b"")


def test_compressor_copy_branches_after_a_shared_prefix():
    """copy snapshot 可复用昂贵 prefix state，生成内容不同但 prefix 相同的独立 streams。"""

    prefix = b"common dictionary-like prefix:" * 30
    compressor = zlib.compressobj()
    prefix_output = compressor.compress(prefix)
    left = compressor.copy()
    right = copy.copy(compressor)

    left_payload = prefix_output + left.compress(b"left") + left.flush()
    right_payload = prefix_output + right.compress(b"right") + right.flush()

    assert zlib.decompress(left_payload) == prefix + b"left"
    assert zlib.decompress(right_payload) == prefix + b"right"


def test_decompressor_copy_restores_the_same_midstream_checkpoint():
    """复制 midstream state 可从同一 compressed offset 重放，用于实现 seek checkpoint。"""

    original = b"decompression checkpoint" * 200
    payload = zlib.compress(original)
    split = len(payload) // 2
    decompressor = zlib.decompressobj()
    prefix = decompressor.decompress(payload[:split])
    shallow = decompressor.copy()
    deep = copy.deepcopy(decompressor)

    first = prefix + decompressor.decompress(payload[split:]) + decompressor.flush()
    second = prefix + shallow.decompress(payload[split:]) + shallow.flush()
    third = prefix + deep.decompress(payload[split:]) + deep.flush()

    assert first == second == third == original


def test_predefined_dictionary_must_be_supplied_to_both_sides():
    """zdict 是 out-of-band contract，不嵌入完整 dictionary；最常见 byte sequences 放在末尾。"""

    dictionary = b"field=;value=;status=;common-prefix="
    original = (b"common-prefix=active;status=ready;" * 50) + b"done"
    compressor = zlib.compressobj(level=9, zdict=dictionary)
    payload = compressor.compress(original) + compressor.flush()

    decompressor = zlib.decompressobj(zdict=dictionary)
    restored = decompressor.decompress(payload) + decompressor.flush()

    assert restored == original
    with pytest.raises(zlib.error):
        zlib.decompress(payload)


def test_wrong_predefined_dictionary_is_rejected():
    """只有 dictionary ID/内容匹配才能恢复；相似 bytes 也不能作为 fallback。"""

    dictionary = b"shared vocabulary and common suffix"
    compressor = zlib.compressobj(zdict=dictionary)
    payload = compressor.compress(dictionary * 10) + compressor.flush()
    decompressor = zlib.decompressobj(zdict=b"different dictionary")

    with pytest.raises(zlib.error):
        decompressor.decompress(payload)


# ``gzip`` one-shot、压缩文件、member 与可复现 header。
#
# gzip 在 DEFLATE 外增加 filename/mtime/checksum 等 file wrapper。``gzip.open`` 支持 binary
# 和 text mode；append 会增加 gzip member，reader 自动拼接 member 的解压内容。``GzipFile``
# 关闭时故意不关闭传入的 fileobj，便于从 BytesIO 取结果或继续写外层数据。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.gzip.compress python.gzip.decompress python.gzip.one-shot
# polyglot-covers: python.gzip.mtime python.gzip.reproducible-output python.gzip.header
# polyglot-covers: python.gzip.multi-member python.gzip.concatenated-streams
# polyglot-covers: python.gzip.open python.gzip.binary-mode python.gzip.path-like
# polyglot-covers: python.gzip.text-mode python.gzip.encoding python.gzip.newline
# polyglot-covers: python.gzip.append python.gzip.exclusive-create
# polyglot-covers: python.gzip.GzipFile python.gzip.fileobj-not-closed python.gzip.name
# polyglot-covers: python.gzip.peek python.gzip.tell python.gzip.seek
# polyglot-covers: python.gzip.read1 python.gzip.readinto python.gzip.iteration
# polyglot-covers: python.gzip.bytes-like-write python.gzip.truncate-unsupported
# polyglot-covers: python.gzip.BadGzipFile python.gzip.EOFError python.gzip.invalid-file
# polyglot-covers: python.gzip.binary-encoding-error python.gzip.compression-level




def test_one_shot_compress_and_decompress_round_trip_bytes():
    """完整 payload 已在内存时，convenience functions 避免手动管理 file object。"""

    original = b"gzip one-shot" * 100
    payload = gzip.compress(original)

    assert isinstance(payload, bytes)
    assert payload.startswith(b"\x1f\x8b")
    assert gzip.decompress(payload) == original


@pytest.mark.parametrize("level", [0, 1, 6, 9])
def test_documented_compression_levels_preserve_content(level):
    """0–9 只改变压缩取舍；gzip 默认 level 9，与 zlib one-shot 默认不同。"""

    original = b"level semantics" * 100

    assert gzip.decompress(gzip.compress(original, compresslevel=level)) == original


def test_fixed_mtime_makes_repeated_output_reproducible():
    """默认 mtime 取当前时间；构建 artifact 应显式固定为 0 或 source timestamp。"""

    original = b"reproducible artifact"
    first = gzip.compress(original, mtime=0)
    second = gzip.compress(original, mtime=0)

    assert first == second
    assert struct.unpack("<I", first[4:8]) == (0,)


def test_numeric_mtime_is_stored_as_unsigned_header_seconds():
    """gzip header 的 4-byte MTIME 可由 reader 暴露；它不是 filesystem mtime 自动同步。"""

    payload = gzip.compress(b"payload", mtime=1_234_567)

    assert struct.unpack("<I", payload[4:8]) == (1_234_567,)


def test_one_shot_decompress_combines_concatenated_members():
    """gzip 允许多个 members 直接拼接；解压结果是各 member 内容的连接。"""

    payload = gzip.compress(b"first", mtime=0) + gzip.compress(
        b"second", mtime=0
    )

    assert gzip.decompress(payload) == b"firstsecond"


def test_binary_open_round_trips_a_path_like_file(tmp_path):
    """gzip.open 接受 PathLike，读写视角像 ordinary binary file。"""

    path = tmp_path / "payload.gz"
    original = b"binary\x00payload" * 20
    with gzip.open(path, "wb", compresslevel=6) as stream:
        assert stream.write(original) == len(original)

    assert path.read_bytes().startswith(b"\x1f\x8b")
    with gzip.open(path, "rb") as stream:
        assert stream.read() == original


def test_text_mode_wraps_gzip_file_with_encoding_and_newline_handling(tmp_path):
    """wt/rt 使用 TextIOWrapper；encoding/newline 只属于 text mode。"""

    path = tmp_path / "text.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as stream:
        stream.write("第一行\n第二行\n")

    with gzip.open(path, "rt", encoding="utf-8", newline=None) as stream:
        assert stream.readlines() == ["第一行\n", "第二行\n"]


def test_encoding_argument_is_rejected_in_binary_mode(tmp_path):
    """binary stream 只接受 bytes；提供 encoding 通常意味着 mode 写错。"""

    path = tmp_path / "binary.gz"

    with pytest.raises(ValueError, match="encoding"):
        gzip.open(path, "wb", encoding="utf-8")


def test_exclusive_create_refuses_to_replace_an_existing_file(tmp_path):
    """x/xb/xt 是原子 fail-if-exists 语义，适合避免覆盖 artifact。"""

    path = tmp_path / "existing.gz"
    path.write_bytes(b"already exists")

    with pytest.raises(FileExistsError):
        gzip.open(path, "xb")


def test_append_mode_adds_a_member_and_reader_combines_them(tmp_path):
    """append 不重写既有 compressed data，而是在末尾创建新 gzip member。"""

    path = tmp_path / "members.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(b"first\n")
    first_member_size = path.stat().st_size
    with gzip.open(path, "ab") as stream:
        stream.write(b"second\n")

    assert path.read_bytes()[first_member_size : first_member_size + 2] == b"\x1f\x8b"
    with gzip.open(path, "rb") as stream:
        assert stream.read() == b"first\nsecond\n"


def test_gzipfile_close_keeps_caller_owned_file_object_open():
    """ownership 不转移给 GzipFile；close 完成 trailer 后仍可读取/追加 underlying BytesIO。"""

    buffer = io.BytesIO()
    stream = gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0)
    stream.write(b"compressed content")
    stream.close()

    assert buffer.closed is False
    payload = buffer.getvalue()
    assert gzip.decompress(payload) == b"compressed content"
    buffer.write(b"outer trailer")
    assert buffer.getvalue().endswith(b"outer trailer")


def test_reading_header_populates_mtime_and_fileobj_stays_open():
    """reader.mtime 初始 None；读到 member header 后变为该 member 的 timestamp。"""

    buffer = io.BytesIO(gzip.compress(b"content", mtime=123))
    stream = gzip.GzipFile(fileobj=buffer, mode="rb")
    assert stream.mtime is None

    assert stream.read(1) == b"c"
    assert stream.mtime == 123
    stream.close()
    assert buffer.closed is False


def test_gzipfile_name_reflects_original_path_without_resolution(tmp_path):
    """name 来自 os.fspath(input)，不会 resolve、expanduser 或改成 member header filename。"""

    path = tmp_path / "named.gz"
    with gzip.GzipFile(filename=path, mode="wb", mtime=0) as stream:
        assert stream.name == str(path)
        stream.write(b"content")


def test_peek_does_not_advance_uncompressed_position():
    """peek 返回数量可多可少，唯一稳定保证是 GzipFile.tell() 不前进。"""

    stream = gzip.GzipFile(
        fileobj=io.BytesIO(gzip.compress(b"abcdef", mtime=0)),
        mode="rb",
    )
    try:
        assert stream.tell() == 0
        preview = stream.peek(2)
        assert preview.startswith(b"ab")
        assert stream.tell() == 0
        assert stream.read(2) == b"ab"
    finally:
        stream.close()


def test_buffered_interface_supports_seek_read1_readinto_and_iteration(tmp_path):
    """GzipFile 模拟 buffered binary file，可随机定位解压位置，但不支持 truncate。"""

    path = tmp_path / "buffered.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(b"first\nsecond\nthird\n")

    with gzip.open(path, "rb") as stream:
        assert stream.readline() == b"first\n"
        assert stream.tell() == len(b"first\n")
        assert stream.seek(0) == 0
        assert stream.read1(5) == b"first"
        target = bytearray(2)
        assert stream.readinto(target) == 2
        assert target == b"\ns"
        stream.seek(0)
        assert list(stream) == [b"first\n", b"second\n", b"third\n"]


def test_gzipfile_accepts_arbitrary_bytes_like_writes():
    """3.5 起 write 接受 buffer protocol，不必先复制 memoryview/bytearray 为 bytes。"""

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as stream:
        stream.write(bytearray(b"mutable"))
        stream.write(memoryview(b" view"))

    assert gzip.decompress(buffer.getvalue()) == b"mutable view"


def test_truncate_is_not_supported_by_gzipfile(tmp_path):
    """压缩 stream 无法像普通文件原地截短；需重新生成目标 gzip。"""

    path = tmp_path / "truncate.gz"
    with gzip.open(path, "wb") as stream:
        with pytest.raises(io.UnsupportedOperation):
            stream.truncate()


def test_invalid_magic_raises_bad_gzip_file():
    """BadGzipFile 是 OSError subclass；损坏类型不同也可能出现 EOFError/zlib.error。"""

    assert issubclass(gzip.BadGzipFile, OSError)
    with pytest.raises(gzip.BadGzipFile):
        gzip.decompress(b"not a gzip stream")


def test_truncated_member_can_raise_eof_error():
    """magic/header 合法但 trailer 不完整时，错误与完全错误的 magic 不同。"""

    payload = gzip.compress(b"content" * 100, mtime=0)

    with pytest.raises(EOFError):
        gzip.decompress(payload[:-4])
