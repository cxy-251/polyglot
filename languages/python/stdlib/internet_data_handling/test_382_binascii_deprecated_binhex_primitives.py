"""382｜已弃用的 BinHex HQX/RLE 底层原语与 Incomplete。

Python 3.9 起 HQX/RLE 函数已弃用，但 3.10 仍保留供旧 BinHex 数据迁移。a2b_hqx 返回
``(data, done)``，冒号终止符才令 done 为真；RLE 的 0x90 是 repeat marker，孤立 marker 表示还
需更多输入并抛 Incomplete，而不是把损坏数据误报为一般编程错误。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.binascii.b2a_hqx
# polyglot-covers: python.binascii.a2b_hqx
# polyglot-covers: python.binascii.a2b-hqx-data-done-tuple
# polyglot-covers: python.binascii.rlecode_hqx
# polyglot-covers: python.binascii.rledecode_hqx
# polyglot-covers: python.binascii.hqx-rle-repeat-marker
# polyglot-covers: python.binascii.Incomplete
# polyglot-covers: python.binascii.incomplete-means-read-more-data
# polyglot-covers: python.binascii.hqx-primitives-deprecated-since-3.9

import binascii

import pytest


def test_hqx_ascii_conversion_reports_whether_the_end_marker_was_seen():
    payload = b"legacy-binhex"
    encoded = binascii.b2a_hqx(payload)
    decoded, done = binascii.a2b_hqx(encoded)
    assert decoded == payload
    assert done == 0

    decoded, done = binascii.a2b_hqx(encoded + b":")
    assert decoded == payload
    assert done == 1


def test_hqx_rle_round_trip_and_orphaned_marker_incomplete_error():
    payload = b"AAAAA\x90\x90BBBBBBBB"
    encoded = binascii.rlecode_hqx(payload)
    assert binascii.rledecode_hqx(encoded) == payload
    with pytest.raises(binascii.Incomplete):
        binascii.rledecode_hqx(b"orphan\x90")
    assert issubclass(binascii.Incomplete, Exception)
