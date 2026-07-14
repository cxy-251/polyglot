"""120｜``lzma`` container format、integrity check、preset 与 filter chain。

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
