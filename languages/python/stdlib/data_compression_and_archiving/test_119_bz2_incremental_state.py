"""119｜``BZ2Compressor``/``BZ2Decompressor`` 的增量状态机。

incremental compressor 必须 flush 才形成完整 stream，且 flush 后不可复用。decompressor
没有 flush；``needs_input=False`` 表示内部仍有 output，应以 ``b''`` 继续拉取。它一次只
处理一个 stream，末尾内容进入 ``unused_data``，需要新 decompressor 接续。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import bz2

import pytest


def test_incremental_compressor_concatenates_outputs_and_flush():
    """compress 可返回空 bytes；所有输出按调用顺序加上最终 flush 才是完整 stream。"""

    chunks = [b"first" * 100, b"second" * 100, b"third" * 100]
    compressor = bz2.BZ2Compressor(compresslevel=5)
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
