"""122｜``LZMACompressor``/``LZMADecompressor`` 增量状态与 stream 接续。

和 bz2 相同，compressor 只能 finish-flush 一次；decompressor 依靠 ``needs_input`` 拉取
buffered output，一次只处理一个 stream。``check`` 可能在读到足够 header 前为 UNKNOWN，
transport 结束时还必须检查 ``eof``，否则 truncated stream 可能被当成成功。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import lzma

import pytest


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
