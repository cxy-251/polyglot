"""582｜颜色转换、媒体头识别与 OSS 平台设备契约。

这些小模块都位于多媒体服务，但职责彼此独立：colorsys 变换数值空间，
imghdr/sndhdr 只检查文件头，ossaudiodev 则暴露平台驱动接口。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.colorsys python.colorsys.rgb-yiq-roundtrip
# polyglot-covers: python.colorsys.rgb-hls-roundtrip python.colorsys.HLS-order
# polyglot-covers: python.colorsys.rgb-hsv-roundtrip python.colorsys.hue-cycle
# polyglot-covers: python.colorsys.grayscale python.colorsys.yiq-rgb-clamping
# polyglot-covers: python.stdlib.imghdr python.imghdr.what-bytes
# polyglot-covers: python.imghdr.recognized-image-headers python.imghdr.first-match
# polyglot-covers: python.imghdr.pathlike-and-file-object python.imghdr.position-restore
# polyglot-covers: python.imghdr.custom-tests python.imghdr.header-overrides-file
# polyglot-covers: python.stdlib.sndhdr python.sndhdr.what-whathdr
# polyglot-covers: python.sndhdr.SndHeaders python.sndhdr.recognized-sound-headers
# polyglot-covers: python.sndhdr.wav-aiff-aifc-workflows python.sndhdr.unknown
# polyglot-covers: python.stdlib.ossaudiodev python.ossaudiodev.platform-optional
# polyglot-covers: python.ossaudiodev.error-alias python.ossaudiodev.mode-validation
# polyglot-covers: python.ossaudiodev.system-call-errors python.ossaudiodev.AUDIODEV
# polyglot-covers: python.ossaudiodev.MIXERDEV python.ossaudiodev.format-bitmask
# polyglot-covers: python.ossaudiodev.mixer-control-bitmask

from io import BytesIO
import importlib
import struct
import sys

import aifc
import colorsys
import imghdr
import sndhdr
import wave
import pytest


def assert_color_close(actual, expected):
    assert actual == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize(
    "rgb",
    [
        (0.0, 0.0, 0.0),
        (1.0, 1.0, 1.0),
        (1.0, 0.0, 0.0),
        (0.2, 0.4, 0.8),
    ],
)
def test_colorsys_yiq_round_trip_preserves_in_range_rgb(rgb):
    yiq = colorsys.rgb_to_yiq(*rgb)

    assert_color_close(colorsys.yiq_to_rgb(*yiq), rgb)
    # I/Q 是色差信号，和其他分量不同，合法值可以为负数。
    if rgb == (0.2, 0.4, 0.8):
        assert yiq[2] > 0
        assert yiq[1] < 0


def test_colorsys_yiq_inverse_clamps_out_of_gamut_rgb_components():
    converted = colorsys.yiq_to_rgb(0.5, 10.0, -10.0)

    assert all(0.0 <= component <= 1.0 for component in converted)
    assert 0.0 in converted
    assert 1.0 in converted


@pytest.mark.parametrize(
    "rgb",
    [
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.1, 0.7, 0.3),
    ],
)
def test_colorsys_hls_and_hsv_round_trips_preserve_rgb(rgb):
    hls = colorsys.rgb_to_hls(*rgb)
    hsv = colorsys.rgb_to_hsv(*rgb)

    # HLS 的参数顺序是 hue、lightness、saturation，并不是常写的 HSL。
    assert_color_close(colorsys.hls_to_rgb(*hls), rgb)
    assert_color_close(colorsys.hsv_to_rgb(*hsv), rgb)


def test_colorsys_primary_hues_and_lightness_value_mean_different_things():
    assert_color_close(colorsys.rgb_to_hls(1, 0, 0), (0.0, 0.5, 1.0))
    assert_color_close(colorsys.rgb_to_hsv(1, 0, 0), (0.0, 1.0, 1.0))
    assert colorsys.rgb_to_hsv(0, 1, 0)[0] == pytest.approx(1 / 3)
    assert colorsys.rgb_to_hsv(0, 0, 1)[0] == pytest.approx(2 / 3)


def test_colorsys_grayscale_has_zero_saturation_and_canonical_zero_hue():
    assert colorsys.rgb_to_hls(0.4, 0.4, 0.4) == (0.0, 0.4, 0.0)
    assert colorsys.rgb_to_hsv(0.4, 0.4, 0.4) == (0.0, 0.0, 0.4)
    assert colorsys.hls_to_rgb(0.8, 0.4, 0.0) == (0.4, 0.4, 0.4)
    assert colorsys.hsv_to_rgb(0.8, 0.0, 0.4) == (0.4, 0.4, 0.4)


def test_colorsys_hue_is_cyclic_for_hls_and_hsv_conversions():
    assert_color_close(
        colorsys.hls_to_rgb(1.0, 0.5, 1.0),
        colorsys.hls_to_rgb(0.0, 0.5, 1.0),
    )
    assert_color_close(
        colorsys.hsv_to_rgb(1.0, 1.0, 1.0),
        colorsys.hsv_to_rgb(0.0, 1.0, 1.0),
    )


IMAGE_HEADERS = [
    ("jpeg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"),
    ("png", b"\x89PNG\r\n\x1a\n"),
    ("gif", b"GIF89a"),
    ("tiff", b"II\x2a\x00"),
    ("rgb", b"\x01\xda"),
    ("pbm", b"P1 2 2\n"),
    ("pgm", b"P5\n2 2\n255\n"),
    ("ppm", b"P6\n2 2\n255\n"),
    ("rast", b"\x59\xa6\x6a\x95"),
    ("xbm", b"#define icon_width 8\n"),
    ("bmp", b"BM"),
    ("webp", b"RIFF\x04\x00\x00\x00WEBP"),
    ("exr", b"\x76\x2f\x31\x01"),
]


@pytest.mark.parametrize(("expected", "header"), IMAGE_HEADERS)
def test_imghdr_recognizes_each_builtin_header_from_bytes(expected, header):
    assert imghdr.what(None, h=header) == expected


def test_imghdr_header_argument_bypasses_the_file_argument():
    missing = "/path/that/must/not/be/opened.png"

    assert imghdr.what(missing, h=b"GIF87a") == "gif"
    assert imghdr.what(missing, h=b"unknown") is None


def test_imghdr_pathlike_and_file_object_forms_preserve_caller_state(tmp_path):
    path = tmp_path / "image.bin"
    path.write_bytes(b"prefix" + b"\x89PNG\r\n\x1a\n")

    # 路径检测总是从文件开头开始，所以带 prefix 的文件不是 PNG。
    assert imghdr.what(path) is None

    stream = BytesIO(path.read_bytes())
    stream.seek(6)
    assert imghdr.what(stream) == "png"
    assert stream.tell() == 6
    assert stream.closed is False


def test_imghdr_custom_detector_receives_header_and_can_extend_formats(monkeypatch):
    calls = []

    def test_teaching_format(header, file_object):
        calls.append((header, file_object))
        if header.startswith(b"TEACH"):
            return "teaching"
        return None

    monkeypatch.setattr(imghdr, "tests", imghdr.tests + [test_teaching_format])

    assert imghdr.what(None, h=b"TEACH-v1") == "teaching"
    assert calls == [(b"TEACH-v1", None)]


def test_imghdr_first_matching_detector_wins(monkeypatch):
    def classify_as_custom(header, file_object):
        if header.startswith(b"\x89PNG"):
            return "preferred-png"
        return None

    monkeypatch.setattr(imghdr, "tests", [classify_as_custom] + imghdr.tests)

    assert imghdr.what(None, h=b"\x89PNG\r\n\x1a\n") == "preferred-png"


def make_wav(path):
    with wave.open(str(path), "wb") as writer:
        writer.setparams((1, 2, 8000, 2, "NONE", "not compressed"))
        writer.writeframes(b"\x00\x00\x01\x00")


def make_aiff_family(path):
    with aifc.open(str(path), "wb") as writer:
        writer.setparams((1, 1, 11025, 2, b"NONE", b"not compressed"))
        writer.writeframes(b"\x00\x01")


def test_sndhdr_wav_result_is_namedtuple_with_frame_semantics(tmp_path):
    path = tmp_path / "lesson.wav"
    make_wav(path)

    result = sndhdr.what(path)

    assert result == sndhdr.whathdr(path)
    assert result.filetype == "wav"
    assert result.framerate == 8000
    assert result.nchannels == 1
    assert result.nframes == 2
    assert result.sampwidth == 16
    assert tuple(result) == ("wav", 8000, 1, 2, 16)


@pytest.mark.parametrize(
    ("suffix", "expected_type"),
    [(".aiff", "aiff"), (".aifc", "aifc")],
)
def test_sndhdr_delegates_valid_aiff_family_headers_to_aifc(
    tmp_path,
    suffix,
    expected_type,
):
    path = tmp_path / f"lesson{suffix}"
    make_aiff_family(path)

    result = sndhdr.what(path)

    assert result.filetype == expected_type
    assert result[1:] == (11025, 1, 2, 8)


def synthetic_sound_headers():
    au = (
        b".snd"
        + struct.pack(">IIIII", 24, 8, 3, 8000, 1)
        + b"\x00" * 8
    )

    hcom = bytearray(148)
    hcom[65:69] = b"FSSD"
    hcom[128:132] = b"HCOM"
    hcom[144:148] = (2).to_bytes(4, "big")

    voc = bytearray(31)
    voc[:20] = b"Creative Voice File\x1a"
    voc[20:22] = (26).to_bytes(2, "little")
    voc[26] = 1
    voc[30] = 131

    sndt = bytearray(22)
    sndt[:5] = b"SOUND"
    sndt[8:12] = (100).to_bytes(4, "little")
    sndt[20:22] = (8000).to_bytes(2, "little")

    sndr = b"\x00\x00" + (8000).to_bytes(2, "little")

    return [
        ("au", bytes(au), (8000, 1, 4.0, 16)),
        ("hcom", bytes(hcom), (11025.0, 1, -1, 8)),
        ("voc", bytes(voc), (8000, 1, -1, 8)),
        ("8svx", b"FORM\x00\x00\x00\x00" + b"8SVX", (0, 1, 0, 8)),
        ("sndt", bytes(sndt), (8000, 1, 100, 8)),
        ("sndr", sndr, (8000, 1, -1, 8)),
    ]


@pytest.mark.parametrize(
    ("expected_type", "header", "expected_fields"),
    synthetic_sound_headers(),
)
def test_sndhdr_recognizes_legacy_headers_without_decoding_payload(
    tmp_path,
    expected_type,
    header,
    expected_fields,
):
    path = tmp_path / f"sample-{expected_type}.bin"
    path.write_bytes(header)

    result = sndhdr.whathdr(path)

    assert result.filetype == expected_type
    assert result[1:] == expected_fields


def test_sndhdr_unknown_is_none_but_missing_file_is_os_error(tmp_path):
    unknown = tmp_path / "unknown.bin"
    unknown.write_bytes(b"not a recognized sound header")

    assert sndhdr.what(unknown) is None
    with pytest.raises(OSError):
        sndhdr.what(tmp_path / "missing.bin")


def import_ossaudiodev():
    # OSS 仅在支持该扩展的平台构建；跳过只影响这些平台专属案例。
    return pytest.importorskip("ossaudiodev")


def test_ossaudiodev_error_alias_and_mode_validation_need_no_device():
    ossaudiodev = import_ossaudiodev()

    assert ossaudiodev.error is ossaudiodev.OSSAudioError
    with pytest.raises(ossaudiodev.OSSAudioError, match="mode must be"):
        ossaudiodev.open("/path/not/opened", "invalid")


def test_ossaudiodev_valid_mode_reports_missing_device_as_os_error(tmp_path):
    ossaudiodev = import_ossaudiodev()
    missing = tmp_path / "missing-dsp"

    with pytest.raises(OSError) as caught:
        ossaudiodev.open(str(missing), "w")

    assert caught.value.filename == str(missing)


def test_ossaudiodev_one_argument_open_uses_audiodev_environment(
    tmp_path,
    monkeypatch,
):
    ossaudiodev = import_ossaudiodev()
    missing = tmp_path / "configured-dsp"
    monkeypatch.setenv("AUDIODEV", str(missing))

    with pytest.raises(OSError) as caught:
        ossaudiodev.open("r")

    assert caught.value.filename == str(missing)


def test_ossaudiodev_openmixer_uses_mixerdev_environment(tmp_path, monkeypatch):
    ossaudiodev = import_ossaudiodev()
    missing = tmp_path / "configured-mixer"
    monkeypatch.setenv("MIXERDEV", str(missing))

    with pytest.raises(OSError) as caught:
        ossaudiodev.openmixer()

    assert caught.value.filename == str(missing)


def test_ossaudiodev_audio_formats_are_composable_driver_bitmasks():
    ossaudiodev = import_ossaudiodev()
    formats = [
        ossaudiodev.AFMT_MU_LAW,
        ossaudiodev.AFMT_A_LAW,
        ossaudiodev.AFMT_IMA_ADPCM,
        ossaudiodev.AFMT_U8,
        ossaudiodev.AFMT_S16_LE,
        ossaudiodev.AFMT_S16_BE,
        ossaudiodev.AFMT_S8,
        ossaudiodev.AFMT_U16_LE,
        ossaudiodev.AFMT_U16_BE,
    ]

    assert all(isinstance(value, int) for value in formats)
    assert len(set(formats)) == len(formats)
    supported = ossaudiodev.AFMT_U8 | ossaudiodev.AFMT_S16_LE
    assert supported & ossaudiodev.AFMT_U8
    assert not supported & ossaudiodev.AFMT_A_LAW

    if hasattr(ossaudiodev, "AFMT_S16_NE"):
        expected = (
            ossaudiodev.AFMT_S16_LE
            if sys.byteorder == "little"
            else ossaudiodev.AFMT_S16_BE
        )
        assert ossaudiodev.AFMT_S16_NE == expected


def test_ossaudiodev_mixer_controls_map_indexes_names_and_bitmasks():
    ossaudiodev = import_ossaudiodev()

    assert len(ossaudiodev.control_names) == len(ossaudiodev.control_labels)
    assert len(ossaudiodev.control_names) == ossaudiodev.SOUND_MIXER_NRDEVICES

    volume = ossaudiodev.SOUND_MIXER_VOLUME
    pcm = ossaudiodev.SOUND_MIXER_PCM
    assert isinstance(ossaudiodev.control_names[volume], str)
    assert isinstance(ossaudiodev.control_labels[pcm], str)

    available_controls = (1 << volume) | (1 << pcm)
    assert available_controls & (1 << volume)
    assert available_controls & (1 << pcm)


def test_ossaudiodev_import_is_a_real_extension_not_a_local_fallback():
    ossaudiodev = import_ossaudiodev()

    assert importlib.import_module("ossaudiodev") is ossaudiodev
    assert callable(ossaudiodev.open)
    assert callable(ossaudiodev.openmixer)
