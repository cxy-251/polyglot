"""580｜audioop 的采样数学、声道变换、编解码和流式状态。

audioop 处理的是无头部的有符号整数采样字节，不知道采样率、声道布局或
文件格式。案例用 struct 明确样本值，避免混淆字节数和帧数。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.audioop python.audioop.signed-integer-fragments
# polyglot-covers: python.audioop.getsample python.audioop.minmax
# polyglot-covers: python.audioop.avg python.audioop.max python.audioop.rms
# polyglot-covers: python.audioop.cross python.audioop.avgpp python.audioop.maxpp
# polyglot-covers: python.audioop.add-clipping python.audioop.bias-wrapping
# polyglot-covers: python.audioop.mul python.audioop.reverse python.audioop.byteswap
# polyglot-covers: python.audioop.lin2lin python.audioop.eight-bit-wave-bias-trap
# polyglot-covers: python.audioop.tomono python.audioop.tostereo
# polyglot-covers: python.audioop.lin2ulaw python.audioop.ulaw2lin
# polyglot-covers: python.audioop.lin2alaw python.audioop.alaw2lin
# polyglot-covers: python.audioop.lin2adpcm python.audioop.adpcm2lin
# polyglot-covers: python.audioop.adpcm-stream-state python.audioop.adpcm-packet-state-trap
# polyglot-covers: python.audioop.ratecv python.audioop.ratecv-stream-state
# polyglot-covers: python.audioop.findfactor python.audioop.findfit
# polyglot-covers: python.audioop.findmax python.audioop.echo-cancellation-primitives
# polyglot-covers: python.audioop.error python.audioop.width-and-alignment-errors

import struct

import audioop
import pytest


def pack_i8(*samples):
    return struct.pack(f"={len(samples)}b", *samples)


def unpack_i8(fragment):
    return struct.unpack(f"={len(fragment)}b", fragment)


def pack_i16(*samples):
    return struct.pack(f"={len(samples)}h", *samples)


def unpack_i16(fragment):
    return struct.unpack(f"={len(fragment) // 2}h", fragment)


def subtract_i16(left, right):
    """audioop 没有 subtract；乘以 -1 再 add 可表达差值。"""

    return audioop.add(left, audioop.mul(right, 2, -1), 2)


def test_sample_lookup_and_summary_statistics_use_signed_values():
    fragment = pack_i16(-4, 2, 8)

    assert audioop.getsample(fragment, 2, 0) == -4
    assert audioop.getsample(fragment, 2, 2) == 8
    assert audioop.minmax(fragment, 2) == (-4, 8)
    assert audioop.avg(fragment, 2) == 2
    assert audioop.max(fragment, 2) == 8
    assert audioop.rms(fragment, 2) == 5


def test_zero_crossings_count_sign_transitions_not_zero_bytes():
    fragment = pack_i16(-2, -1, 1, 2, -3)

    assert audioop.cross(fragment, 2) == 2


def test_peak_to_peak_functions_measure_local_extrema():
    fragment = pack_i16(-5, 5, -5, 5, -5)

    assert audioop.avgpp(fragment, 2) == 10
    assert audioop.maxpp(fragment, 2) == 10


def test_add_clips_overflow_while_bias_wraps_at_sample_width():
    near_limit = pack_i8(120)
    increment = pack_i8(20)

    # add 饱和到有符号 8 位上限；它适合混音时避免环绕失真。
    assert unpack_i8(audioop.add(near_limit, increment, 1)) == (127,)

    # bias 按固定位宽环绕，120 + 20 会变成 -116。
    assert unpack_i8(audioop.bias(near_limit, 1, 20)) == (-116,)


def test_multiply_clips_and_truncates_each_sample():
    fragment = pack_i16(-10, 20, 30000)

    assert unpack_i16(audioop.mul(fragment, 2, 0.5)) == (-5, 10, 15000)
    assert unpack_i16(audioop.mul(fragment, 2, 2)) == (-20, 40, 32767)


def test_reverse_changes_sample_order_without_reversing_sample_bytes():
    fragment = pack_i16(0x0102, 0x0304, 0x0506)

    assert unpack_i16(audioop.reverse(fragment, 2)) == (
        0x0506,
        0x0304,
        0x0102,
    )


def test_byteswap_reverses_bytes_inside_each_sample_only():
    fragment = pack_i16(0x0102, 0x0304)
    expected = fragment[:2][::-1] + fragment[2:][::-1]

    assert audioop.byteswap(fragment, 2) == expected
    assert audioop.byteswap(expected, 2) == fragment


def test_linear_width_conversion_preserves_high_order_signed_value():
    source = pack_i16(-32768, 0, 32512)
    narrowed = audioop.lin2lin(source, 2, 1)

    assert unpack_i8(narrowed) == (-128, 0, 127)
    widened = audioop.lin2lin(narrowed, 1, 2)
    assert unpack_i16(widened) == (-32768, 0, 32512)


def test_eight_bit_wave_samples_need_explicit_unsigned_bias():
    signed = pack_i8(-128, 0, 127)
    wave_bytes = audioop.bias(signed, 1, 128)

    # audioop 一律把 8 位采样视为有符号；WAV 的 8 位 PCM 却是无符号。
    assert wave_bytes == bytes([0, 128, 255])
    assert audioop.bias(wave_bytes, 1, -128) == signed


def test_stereo_and_mono_helpers_apply_channel_factors_per_frame():
    mono = pack_i16(-10, 20)

    stereo = audioop.tostereo(mono, 2, 1, 0.5)
    assert unpack_i16(stereo) == (-10, -5, 20, 10)
    assert audioop.tomono(stereo, 2, 1, 0) == mono
    assert unpack_i16(audioop.tomono(stereo, 2, 0.5, 1)) == (-10, 20)


@pytest.mark.parametrize(
    ("encoder", "decoder"),
    [
        (audioop.lin2ulaw, audioop.ulaw2lin),
        (audioop.lin2alaw, audioop.alaw2lin),
    ],
)
def test_telephony_codecs_are_lossy_but_preserve_shape_and_signal(encoder, decoder):
    linear = pack_i16(-12000, -1000, 0, 1000, 12000)

    encoded = encoder(linear, 2)
    decoded = decoder(encoded, 2)
    error = subtract_i16(linear, decoded)

    assert len(encoded) == 5
    assert len(decoded) == len(linear)
    assert audioop.rms(error, 2) < 400


def test_adpcm_round_trip_returns_payload_and_evolving_codec_state():
    linear = pack_i16(-1000, -500, 0, 500, 1000, 500, 0, -500)

    encoded, encoder_state = audioop.lin2adpcm(linear, 2, None)
    decoded, decoder_state = audioop.adpcm2lin(encoded, 2, None)

    assert len(encoded) == 4
    assert len(decoded) == len(linear)
    assert len(encoder_state) == len(decoder_state) == 2
    assert all(isinstance(item, int) for item in encoder_state)


def test_adpcm_streaming_must_carry_state_across_chunk_boundaries():
    first = pack_i16(-1000, -500, 0, 500)
    second = pack_i16(1000, 500, 0, -500)
    whole, _ = audioop.lin2adpcm(first + second, 2, None)

    encoded_first, state = audioop.lin2adpcm(first, 2, None)
    encoded_second, _ = audioop.lin2adpcm(second, 2, state)

    assert encoded_first + encoded_second == whole

    # 无状态网络包应携带“本包开始前”的状态，
    # 不能只保存编码后的状态。
    wrong_second, _ = audioop.lin2adpcm(second, 2, None)
    assert wrong_second != encoded_second


def test_rate_conversion_is_equivalent_when_stream_state_is_forwarded():
    first = pack_i16(0, 1000, 2000, 3000)
    second = pack_i16(4000, 5000, 6000, 7000)

    whole, _ = audioop.ratecv(first + second, 2, 1, 8000, 4000, None)
    converted_first, state = audioop.ratecv(first, 2, 1, 8000, 4000, None)
    converted_second, _ = audioop.ratecv(
        second,
        2,
        1,
        8000,
        4000,
        state,
    )

    assert converted_first + converted_second == whole
    assert len(whole) < len(first + second)


def test_rate_conversion_filter_weights_change_interpolation_state():
    fragment = pack_i16(0, 10000, 0, 10000)

    unfiltered, state = audioop.ratecv(fragment, 2, 1, 4000, 4000, None)
    filtered, filtered_state = audioop.ratecv(
        fragment,
        2,
        1,
        4000,
        4000,
        None,
        1,
        1,
    )

    assert unfiltered == fragment
    assert filtered != unfiltered
    assert state is not None
    assert filtered_state is not None


def test_findfactor_recovers_reference_gain_for_sixteen_bit_samples():
    reference = pack_i16(100, -200, 300, -400)
    fragment = audioop.mul(reference, 2, 2)

    assert audioop.findfactor(fragment, reference) == pytest.approx(2.0)


def test_findfit_returns_sample_offset_and_gain_of_best_reference_match():
    reference = pack_i16(100, -200, 300)
    fragment = pack_i16(5, 5) + audioop.mul(reference, 2, 2) + pack_i16(5)

    offset, factor = audioop.findfit(fragment, reference)

    assert offset == 2
    assert factor == pytest.approx(2.0)


def test_findmax_length_is_counted_in_samples_not_bytes():
    fragment = pack_i16(1, 1, 100, -100, 1)

    assert audioop.findmax(fragment, 2) == 2


@pytest.mark.parametrize("width", [0, 5])
def test_invalid_sample_width_raises_module_specific_error(width):
    with pytest.raises(audioop.error):
        audioop.max(b"\x00", width)


def test_misaligned_fragments_and_unequal_mix_lengths_are_rejected():
    with pytest.raises(audioop.error, match="not a whole number of frames"):
        audioop.avg(b"\x00", 2)

    with pytest.raises(audioop.error):
        audioop.add(pack_i16(1), pack_i16(1, 2), 2)


def test_text_is_not_implicitly_encoded_as_audio_bytes():
    with pytest.raises(TypeError):
        audioop.max("not bytes", 1)
