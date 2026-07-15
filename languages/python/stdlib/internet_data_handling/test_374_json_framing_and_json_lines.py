"""374｜JSON 不是 framed protocol，以及 JSON Lines 工作流。

连续对同一 stream 调用 dump 不会插入分隔符，两个合法值会黏成一个非法文档。若协议需要连续
记录，必须另定 framing；简单文本场景常用“一行一个紧凑 JSON”，逐行 loads。字符串内部换行会
被转义，所以不会破坏行边界，但生产方仍需约定空行与最大行长。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.not-a-framed-protocol
# polyglot-covers: python.json.repeated-dump-same-stream-invalid-document
# polyglot-covers: python.json.explicit-message-framing-required
# polyglot-covers: python.json.json-lines-workflow
# polyglot-covers: python.json.json-lines-one-value-per-line
# polyglot-covers: python.json.string-newline-escaped-within-line

import io
import json

import pytest


def test_repeated_dump_calls_concatenate_values_without_a_frame():
    stream = io.StringIO()
    json.dump({"id": 1}, stream)
    json.dump({"id": 2}, stream)
    assert stream.getvalue() == '{"id": 1}{"id": 2}'
    with pytest.raises(json.JSONDecodeError, match="Extra data"):
        json.loads(stream.getvalue())


def test_json_lines_adds_an_explicit_record_boundary():
    records = [
        {"id": 1, "message": "first"},
        {"id": 2, "message": "contains\nnewline"},
    ]
    document = "\n".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        for record in records
    )
    assert document.count("\n") == 1
    assert "\\n" in document.splitlines()[1]
    assert [json.loads(line) for line in document.splitlines()] == records
