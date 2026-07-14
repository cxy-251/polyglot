"""115｜``zlib`` one-shot 压缩、校验和与 wrapper format。

zlib API 处理 bytes，不保证压缩后一定更小；level 只在速度/体积间取舍。``wbits`` 同时
决定 DEFLATE window 与 zlib/raw/gzip wrapper，解压端必须匹配。Adler-32/CRC-32 用于
意外损坏检测，不具备密码学认证能力。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
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
