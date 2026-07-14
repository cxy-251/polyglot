"""116｜``zlib`` incremental object、flush、remainder 与预置字典。

streaming compressor/decompressor 带可变状态：每次输出都要按顺序拼接；``Z_FINISH``/
``flush()`` 后对象不可复用。``unused_data`` 是完整 stream 之后的外层数据，
``unconsumed_tail`` 则是 max_length 暂未处理的压缩输入，两者不可混淆。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import copy
import zlib

import pytest


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
