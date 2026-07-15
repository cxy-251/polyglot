"""135｜wave、aifc、sunau 与 chunk 的音频容器工作流。

前三个模块共享参数、帧和位置接口，但各容器能力不同。
chunk 展示这些容器背后的 IFF 分块边界、填充和游标规则。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.wave python.wave.open-file-and-file-object
# polyglot-covers: python.wave.Wave_write-setparams python.wave.writeframes
# polyglot-covers: python.wave.writeframesraw python.wave.seekable-header-patching
# polyglot-covers: python.wave.unseekable-output-nframes-contract
# polyglot-covers: python.wave.Wave_read-getparams python.wave.readframes
# polyglot-covers: python.wave.tell-setpos-rewind python.wave.markers-compatibility
# polyglot-covers: python.wave.file-object-ownership python.wave.parameter-lock
# polyglot-covers: python.wave.Error python.wave.pcm-only
# polyglot-covers: python.stdlib.aifc python.aifc.AIFF-vs-AIFC
# polyglot-covers: python.aifc.setparams python.aifc.markers
# polyglot-covers: python.aifc.marker-name-bytes python.aifc.stream-ownership
# polyglot-covers: python.aifc.read-write-position python.aifc.ULAW-roundtrip
# polyglot-covers: python.aifc.context-manager python.aifc.Error
# polyglot-covers: python.stdlib.sunau python.sunau.header-and-encoding-constants
# polyglot-covers: python.sunau.linear-read-write python.sunau.ULAW-conversion
# polyglot-covers: python.sunau.params-position-markers python.sunau.Error
# polyglot-covers: python.stdlib.chunk python.chunk.big-and-little-endian-sizes
# polyglot-covers: python.chunk.alignment-padding python.chunk.inclheader
# polyglot-covers: python.chunk.read-seek-tell-skip python.chunk.nested-chunks
# polyglot-covers: python.chunk.nonseekable-forward-skip python.chunk.close-ownership

from io import BytesIO
import struct

import aifc
import audioop
import chunk
import sunau
import wave
import pytest


def pack_native_i16(*samples):
    return struct.pack(f"={len(samples)}h", *samples)


class UnseekableSink:
    """保留输出字节，但明确拒绝 wave 用来回补头部的定位操作。"""

    def __init__(self):
        self.data = bytearray()
        self.flush_count = 0

    def write(self, data):
        self.data.extend(data)
        return len(data)

    def tell(self):
        raise OSError("cannot seek")

    def seek(self, *args):
        raise OSError("cannot seek")

    def flush(self):
        self.flush_count += 1


class ReadOnlyStream:
    """只有 read 的流，用于触发 chunk 的向前读取式 skip。"""

    def __init__(self, data):
        self._source = BytesIO(data)

    def read(self, size=-1):
        return self._source.read(size)


class NonClosingBytesIO(BytesIO):
    """aifc 总会关闭传入流；测试替身保留最终容器字节供断言。"""

    def __init__(self):
        super().__init__()
        self.close_calls = 0

    def close(self):
        self.close_calls += 1


def make_wave_bytes(frames, *, channels=1, width=2, rate=8000):
    target = BytesIO()
    with wave.open(target, "wb") as writer:
        writer.setparams(
            (channels, width, rate, 0, "NONE", "not compressed")
        )
        writer.writeframes(frames)
    return target.getvalue()


def test_wave_seekable_round_trip_exposes_named_parameters_and_frames():
    frames = pack_native_i16(-1000, 0, 1000)
    payload = make_wave_bytes(frames)

    assert payload[:4] == b"RIFF"
    assert payload[8:12] == b"WAVE"

    with wave.open(BytesIO(payload), "rb") as reader:
        params = reader.getparams()
        assert params.nchannels == 1
        assert params.sampwidth == 2
        assert params.framerate == 8000
        assert params.nframes == 3
        assert params.comptype == "NONE"
        assert params.compname == "not compressed"
        assert reader.readframes(2) == frames[:4]
        assert reader.tell() == 2
        assert reader.readframes(20) == frames[4:]


def test_wave_position_methods_use_frame_offsets_not_byte_offsets():
    frames = pack_native_i16(10, 20, 30, 40)

    with wave.open(BytesIO(make_wave_bytes(frames)), "rb") as reader:
        reader.setpos(2)
        assert reader.tell() == 2
        assert reader.readframes(1) == frames[4:6]

        reader.rewind()
        assert reader.tell() == 0
        assert reader.readframes(1) == frames[:2]

        with pytest.raises(wave.Error, match="position not in range"):
            reader.setpos(5)


def test_wave_marker_methods_are_only_aifc_compatibility_stubs():
    with wave.open(BytesIO(make_wave_bytes(b"\x00\x00")), "rb") as reader:
        assert reader.getmarkers() is None
        with pytest.raises(wave.Error, match="no marks"):
            reader.getmark(1)


def test_wave_does_not_close_a_file_object_owned_by_the_caller():
    target = BytesIO()

    with wave.open(target, "wb") as writer:
        writer.setparams((1, 1, 8000, 1, "NONE", "not compressed"))
        writer.writeframes(b"\x80")

    # 传入路径时由 wave 管理文件；传入流时，生命周期仍属于调用方。
    assert target.closed is False
    assert target.getvalue().startswith(b"RIFF")


def test_wave_rejects_compression_and_parameter_changes_after_data():
    target = BytesIO()
    writer = wave.open(target, "wb")

    with pytest.raises(wave.Error, match="unsupported compression type"):
        writer.setcomptype("ULAW", "u-law")

    writer.setparams((1, 1, 8000, 1, "NONE", "not compressed"))
    writer.writeframesraw(b"\x80")

    with pytest.raises(wave.Error, match="cannot change parameters"):
        writer.setframerate(16000)
    writer.close()


def test_wave_writeframes_patches_seekable_header_to_actual_frame_count():
    target = BytesIO()
    with wave.open(target, "wb") as writer:
        writer.setparams((1, 2, 8000, 99, "NONE", "not compressed"))
        writer.writeframes(pack_native_i16(1, 2, 3))

    with wave.open(BytesIO(target.getvalue()), "rb") as reader:
        assert reader.getnframes() == 3


def test_wave_unseekable_raw_output_succeeds_when_nframes_is_exact():
    sink = UnseekableSink()
    frames = pack_native_i16(1, 2, 3)

    with wave.open(sink, "wb") as writer:
        writer.setparams((1, 2, 8000, 3, "NONE", "not compressed"))
        writer.writeframesraw(frames)

    assert sink.flush_count == 1
    with wave.open(BytesIO(bytes(sink.data)), "rb") as reader:
        assert reader.getnframes() == 3
        assert reader.readframes(3) == frames


def test_wave_unseekable_output_cannot_patch_an_incorrect_declared_size():
    sink = UnseekableSink()
    writer = wave.open(sink, "wb")
    writer.setparams((1, 2, 8000, 4, "NONE", "not compressed"))
    writer.writeframesraw(pack_native_i16(1, 2))

    # writeframesraw 不改头；close 发现数量不符后必须回头修补，因而失败。
    with pytest.raises(OSError, match="cannot seek"):
        writer.close()


def test_aiff_path_suffix_selects_aiff_and_preserves_markers(tmp_path):
    path = tmp_path / "lesson.aiff"
    frames = pack_native_i16(-20, 0, 20)

    with aifc.open(str(path), "wb") as writer:
        writer.setparams(
            (1, 2, 8000, 3, b"NONE", b"not compressed")
        )
        writer.setmark(1, 1, b"middle")
        writer.writeframes(frames)

    payload = path.read_bytes()
    assert payload[:4] == b"FORM"
    assert payload[8:12] == b"AIFF"

    with aifc.open(str(path), "rb") as reader:
        assert reader.getparams().nframes == 3
        assert reader.getcomptype() == b"NONE"
        assert reader.getmarkers() == [(1, 1, b"middle")]
        assert reader.getmark(1) == (1, 1, b"middle")
        assert reader.readframes(3) == frames


def test_aifc_marker_id_is_unique_and_marker_arguments_are_validated():
    target = NonClosingBytesIO()
    writer = aifc.open(target, "wb")
    writer.aiff()
    writer.setparams((1, 1, 8000, 1, b"NONE", b"not compressed"))
    writer.setmark(1, 0, b"start")
    writer.setmark(1, 1, b"replacement")

    assert writer.getmarkers() == [(1, 1, b"replacement")]
    with pytest.raises(aifc.Error):
        writer.setmark(0, 0, b"bad id")
    with pytest.raises(aifc.Error):
        writer.setmark(2, -1, b"bad position")
    # Python 3.10 的实现要求 marker 名称是 bytes，不会隐式编码文本。
    with pytest.raises(aifc.Error, match="marker name must be bytes"):
        writer.setmark(2, 0, "text name")

    writer.writeframes(b"\x00")
    writer.close()


def test_aifc_reader_supports_frame_position_rewind_and_missing_mark_error():
    target = NonClosingBytesIO()
    frames = b"\x01\x02\x03"
    with aifc.open(target, "wb") as writer:
        writer.aiff()
        writer.setparams((1, 1, 8000, 3, b"NONE", b"not compressed"))
        writer.writeframes(frames)

    with aifc.open(BytesIO(target.getvalue()), "rb") as reader:
        reader.setpos(1)
        assert reader.tell() == 1
        assert reader.readframes(1) == b"\x02"
        reader.rewind()
        assert reader.readframes(3) == frames
        with pytest.raises(aifc.Error):
            reader.getmark(99)


def test_aifc_ulaw_container_decodes_back_to_linear_samples():
    linear = pack_native_i16(-10000, -1000, 0, 1000, 10000)
    target = NonClosingBytesIO()

    with aifc.open(target, "wb") as writer:
        writer.aifc()
        writer.setparams(
            (1, 2, 8000, 5, b"ULAW", b"CCITT G.711 u-law")
        )
        writer.writeframes(linear)

    payload = target.getvalue()
    assert target.close_calls == 1
    assert payload[8:12] == b"AIFC"
    with aifc.open(BytesIO(payload), "rb") as reader:
        decoded = reader.readframes(5)
        assert reader.getcomptype() == b"ULAW"
        assert reader.getsampwidth() == 2

    difference = audioop.add(decoded, audioop.mul(linear, 2, -1), 2)
    assert len(decoded) == len(linear)
    assert audioop.rms(difference, 2) < 400


def test_sunau_linear_round_trip_exposes_header_constants_and_params():
    frames = b"\x00\x01\xff\xff\x01\x00"
    target = BytesIO()

    with sunau.open(target, "wb") as writer:
        writer.setparams((1, 2, 8000, 3, "NONE", "not compressed"))
        writer.writeframes(frames)

    payload = target.getvalue()
    assert payload[:4] == b".snd"
    assert int.from_bytes(payload[:4], "big") == sunau.AUDIO_FILE_MAGIC

    with sunau.open(BytesIO(payload), "rb") as reader:
        params = reader.getparams()
        assert params[:4] == (1, 2, 8000, 3)
        assert params.comptype == "NONE"
        assert reader.readframes(3) == frames


def test_sunau_position_and_marker_compatibility_follow_common_interface():
    target = BytesIO()
    with sunau.open(target, "wb") as writer:
        writer.setparams((1, 1, 8000, 3, "NONE", "not compressed"))
        writer.writeframes(b"abc")

    with sunau.open(BytesIO(target.getvalue()), "rb") as reader:
        reader.setpos(1)
        assert reader.tell() == 1
        assert reader.readframes(1) == b"b"
        reader.rewind()
        assert reader.readframes(1) == b"a"
        assert reader.getmarkers() is None
        with pytest.raises(sunau.Error, match="no marks"):
            reader.getmark(1)


def test_sunau_ulaw_writer_compresses_and_reader_returns_linear_audio():
    linear = pack_native_i16(-10000, 0, 10000)
    target = BytesIO()

    with sunau.open(target, "wb") as writer:
        writer.setparams(
            (1, 2, 8000, 3, "ULAW", "CCITT G.711 u-law")
        )
        writer.writeframes(linear)

    with sunau.open(BytesIO(target.getvalue()), "rb") as reader:
        decoded = reader.readframes(3)
        assert reader.getcomptype() == "ULAW"
        assert reader.getsampwidth() == 2

    difference = audioop.add(decoded, audioop.mul(linear, 2, -1), 2)
    assert len(decoded) == len(linear)
    assert audioop.rms(difference, 2) < 400


def test_sunau_supported_header_encodings_are_distinct_from_output_codecs():
    readable_encodings = {
        sunau.AUDIO_FILE_ENCODING_MULAW_8,
        sunau.AUDIO_FILE_ENCODING_LINEAR_8,
        sunau.AUDIO_FILE_ENCODING_LINEAR_16,
        sunau.AUDIO_FILE_ENCODING_LINEAR_24,
        sunau.AUDIO_FILE_ENCODING_LINEAR_32,
        sunau.AUDIO_FILE_ENCODING_ALAW_8,
    }
    assert len(readable_encodings) == 6

    writer = sunau.open(BytesIO(), "wb")
    with pytest.raises(sunau.Error, match="unknown compression type"):
        writer.setcomptype("ALAW", "CCITT G.711 A-law")
    writer.setparams((1, 1, 8000, 0, "NONE", "not compressed"))
    writer.close()


def make_chunk(name, payload, *, byteorder="big", inclheader=False):
    size = len(payload) + (8 if inclheader else 0)
    encoded_size = size.to_bytes(4, byteorder)
    padding = b"\x00" if len(payload) % 2 else b""
    return name + encoded_size + payload + padding


def test_chunk_reads_only_its_payload_and_consumes_alignment_padding():
    source = BytesIO(
        make_chunk(b"ODD!", b"abc") + make_chunk(b"NEXT", b"data")
    )
    first = chunk.Chunk(source)

    assert first.getname() == b"ODD!"
    assert first.getsize() == 3
    assert first.isatty() is False
    assert first.read(2) == b"ab"
    assert first.tell() == 2
    assert first.read(20) == b"c"
    assert first.read() == b""

    # 读取到块尾时，奇数长度后的填充字节也会被消费。
    second = chunk.Chunk(source)
    assert second.getname() == b"NEXT"
    assert second.read() == b"data"
    with pytest.raises(EOFError):
        chunk.Chunk(source)


def test_chunk_seek_and_close_are_relative_and_leave_underlying_file_open():
    source = BytesIO(
        make_chunk(b"ONE!", b"abcdef") + make_chunk(b"TWO!", b"xy")
    )
    first = chunk.Chunk(source)
    first.seek(2)
    assert first.tell() == 2
    assert first.read(2) == b"cd"
    first.seek(-1, 1)
    assert first.read(1) == b"d"

    first.close()
    assert source.closed is False
    second = chunk.Chunk(source)
    assert second.getname() == b"TWO!"


def test_chunk_supports_little_endian_sizes_and_header_inclusive_sizes():
    little = chunk.Chunk(
        BytesIO(make_chunk(b"data", b"abcd", byteorder="little")),
        bigendian=False,
    )
    assert little.getsize() == 4
    assert little.read() == b"abcd"

    inclusive = chunk.Chunk(
        BytesIO(make_chunk(b"FORM", b"body", inclheader=True)),
        inclheader=True,
    )
    assert inclusive.getsize() == 4
    assert inclusive.read() == b"body"


def test_chunk_can_contain_another_chunk_without_crossing_outer_boundary():
    inner_bytes = make_chunk(b"DATA", b"payload")
    outer = chunk.Chunk(BytesIO(make_chunk(b"FORM", inner_bytes)))
    inner = chunk.Chunk(outer)

    assert outer.getname() == b"FORM"
    assert inner.getname() == b"DATA"
    assert inner.read() == b"payload"
    assert outer.read() == b""


def test_chunk_nonseekable_skip_reads_forward_to_next_aligned_chunk():
    stream = ReadOnlyStream(
        make_chunk(b"SKIP", b"abc") + make_chunk(b"KEEP", b"ok")
    )
    skipped = chunk.Chunk(stream)
    skipped.skip()

    kept = chunk.Chunk(stream)
    assert kept.getname() == b"KEEP"
    assert kept.read() == b"ok"
