"""367｜JSON 转换表、顺序保持与文本/二进制流 API。

JSON 的 object/array/null/boolean/number 分别映射到 Python dict/list/None/bool/int 或 float；tuple
编码后也变成 array，往返会得到 list。dumps/dump 始终产生或写入 str，load 则能从 text stream
或包含 UTF-8/16/32 的 binary stream 读取。对象成员顺序在底层容器有序时保持。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.dumps
# polyglot-covers: python.json.loads
# polyglot-covers: python.json.dump
# polyglot-covers: python.json.load
# polyglot-covers: python.json.python-json-conversion-table
# polyglot-covers: python.json.tuple-encodes-array-decodes-list
# polyglot-covers: python.json.output-is-str-not-bytes
# polyglot-covers: python.json.dump-requires-text-writer
# polyglot-covers: python.json.load-text-stream
# polyglot-covers: python.json.load-binary-stream
# polyglot-covers: python.json.object-order-preserved




import io
import json
import pytest
from decimal import Decimal
import math
import subprocess
import sys

def test_basic_python_hierarchy_round_trips_with_documented_type_conversions():
    value = {
        "nothing": None,
        "flags": (True, False),
        "numbers": [3, 2.5],
        "nested": {"name": "polyglot"},
    }
    encoded = json.dumps(value)
    assert isinstance(encoded, str)
    assert json.loads(encoded) == {
        "nothing": None,
        "flags": [True, False],
        "numbers": [3, 2.5],
        "nested": {"name": "polyglot"},
    }


def test_dump_writes_text_and_load_accepts_text_or_binary_streams():
    value = {"first": 1, "second": 2}
    text_stream = io.StringIO()
    assert json.dump(value, text_stream) is None
    assert text_stream.getvalue() == '{"first": 1, "second": 2}'

    text_stream.seek(0)
    assert json.load(text_stream) == value
    assert json.load(io.BytesIO(text_stream.getvalue().encode("utf-8"))) == value

    with pytest.raises(TypeError):
        json.dump(value, io.BytesIO())


def test_input_object_order_survives_encoding_and_decoding():
    value = {"z": 1, "a": 2, "m": 3}
    encoded = json.dumps(value)
    assert encoded == '{"z": 1, "a": 2, "m": 3}'
    assert list(json.loads(encoded)) == ["z", "a", "m"]


# 368｜ensure_ascii、indent、separators、sort_keys 与对象 key 规则。
#
# JSON object 的 key 必须是字符串；编码器会把 int/float/bool/None key 转成字符串，而其他类型默认
# 报错，skipkeys=True 则静默丢弃。这个转换使 ``loads(dumps(mapping))`` 不保证等于原 mapping。
# 格式选项只改变文本表示，不应被下游当成业务语义。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.ensure_ascii
# polyglot-covers: python.json.ensure-ascii-false-emits-unicode
# polyglot-covers: python.json.indent-int
# polyglot-covers: python.json.indent-string
# polyglot-covers: python.json.separators
# polyglot-covers: python.json.compact-separators-workflow
# polyglot-covers: python.json.sort_keys
# polyglot-covers: python.json.skipkeys
# polyglot-covers: python.json.invalid-dict-key-typeerror
# polyglot-covers: python.json.skipkeys-silently-discards-trap
# polyglot-covers: python.json.nonstring-keys-coerced-to-strings
# polyglot-covers: python.json.mapping-roundtrip-key-type-trap




def test_unicode_pretty_and_compact_representations_decode_to_the_same_value():
    value = {"城市": "深圳", "items": [1, 2]}
    escaped = json.dumps(value)
    readable = json.dumps(value, ensure_ascii=False)
    pretty = json.dumps(value, ensure_ascii=False, indent="\t", sort_keys=True)
    compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    assert "城市" not in escaped
    assert "\\u57ce\\u5e02" in escaped
    assert "城市" in readable
    assert '\n\t"城市"' in pretty
    assert compact == '{"城市":"深圳","items":[1,2]}'
    assert all(json.loads(text) == value for text in (escaped, readable, pretty, compact))


def test_sort_keys_makes_mapping_output_deterministic_for_comparable_keys():
    value = {"z": 1, "a": 2, "m": 3}
    assert json.dumps(value, sort_keys=True) == '{"a": 2, "m": 3, "z": 1}'
    assert json.dumps(value, indent=2).startswith('{\n  "z"')


def test_unsupported_keys_raise_or_are_silently_skipped():
    value = {("tuple",): "lost", "kept": 1}
    with pytest.raises(TypeError):
        json.dumps(value)
    assert json.loads(json.dumps(value, skipkeys=True)) == {"kept": 1}


def test_supported_nonstring_keys_do_not_round_trip_their_types():
    original = {1: "integer", None: "none", 2.5: "float"}
    # sort_keys 会先比较原 Python key；None 与数字不可排序，因此混合类型时不要顺带开启它。
    decoded = json.loads(json.dumps(original))
    assert decoded == {"1": "integer", "null": "none", "2.5": "float"}
    assert decoded != original


# 369｜default 扩展点、JSONEncoder 分块输出与循环引用检查。
#
# 未知类型会交给 default callable 或 JSONEncoder.default；实现无法识别的对象时必须调用 super，
# 让基类抛 TypeError，不能返回原对象再次形成循环。iterencode 产生若干 str chunk，适合逐块写入；
# 它并不提供消息 framing。默认循环检查会把自引用容器转成 ValueError，关闭后可能递归至崩溃。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.default-callback
# polyglot-covers: python.json.JSONEncoder
# polyglot-covers: python.json.JSONEncoder.default
# polyglot-covers: python.json.JSONEncoder.default-call-super-fallback
# polyglot-covers: python.json.JSONEncoder.encode
# polyglot-covers: python.json.JSONEncoder.iterencode
# polyglot-covers: python.json.iterencode-yields-str-chunks
# polyglot-covers: python.json.cls-custom-encoder
# polyglot-covers: python.json.check_circular
# polyglot-covers: python.json.circular-reference-valueerror
# polyglot-covers: python.json.disable-circular-check-recursion-trap




class ComplexEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, complex):
            return {"__complex__": True, "real": value.real, "imag": value.imag}
        return super().default(value)


def test_default_callable_and_encoder_subclass_convert_unknown_types():
    encoded_by_callback = json.dumps(
        {"number": 3 + 4j},
        default=lambda value: [value.real, value.imag],
    )
    assert json.loads(encoded_by_callback) == {"number": [3.0, 4.0]}

    encoded_by_class = json.dumps(3 + 4j, cls=ComplexEncoder, sort_keys=True)
    assert json.loads(encoded_by_class) == {
        "__complex__": True,
        "imag": 4.0,
        "real": 3.0,
    }
    with pytest.raises(TypeError):
        ComplexEncoder().encode(object())


def test_iterencode_chunks_join_to_the_same_document_as_encode():
    value = {"values": [1, 2, 3]}
    encoder = json.JSONEncoder(sort_keys=True)
    chunks = list(encoder.iterencode(value))
    assert chunks
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert "".join(chunks) == encoder.encode(value)


def test_circular_reference_check_reports_a_clear_error_before_recursion():
    recursive = []
    recursive.append(recursive)
    with pytest.raises(ValueError, match="Circular reference"):
        json.dumps(recursive)
    with pytest.raises(RecursionError):
        json.dumps(recursive, check_circular=False)


# 370｜object hooks 的分派优先级与数字解析类型。
#
# object_hook 在每个 object 完成后由内向外调用；object_pairs_hook 改收有序 pair 列表，并在两者
# 同时提供时具有优先级，因此能发现重复名称。parse_float/parse_int 收到原始数字 token 字符串，
# 可避免先经过二进制 float；parse_constant 只处理 NaN/Infinity 扩展，不处理 null/true/false。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.object_hook
# polyglot-covers: python.json.object-hook-inner-before-outer
# polyglot-covers: python.json.object_pairs_hook
# polyglot-covers: python.json.object-pairs-hook-preserves-duplicate-names
# polyglot-covers: python.json.object-pairs-hook-precedes-object-hook
# polyglot-covers: python.json.parse_float
# polyglot-covers: python.json.parse_int
# polyglot-covers: python.json.parse_constant
# polyglot-covers: python.json.parse-constant-nan-infinity-only
# polyglot-covers: python.json.decimal-number-decoding-workflow




def test_object_hook_replaces_inner_objects_before_their_parent_is_built():
    calls = []

    def hook(value):
        calls.append(value.copy())
        if value.get("type") == "point":
            return (value["x"], value["y"])
        return value

    decoded = json.loads(
        '{"name": "shape", "location": {"type": "point", "x": 2, "y": 3}}',
        object_hook=hook,
    )
    assert decoded == {"name": "shape", "location": (2, 3)}
    assert calls[0] == {"type": "point", "x": 2, "y": 3}
    assert calls[1] == decoded


def test_pairs_hook_sees_duplicates_and_suppresses_object_hook():
    object_calls = []
    pair_calls = []

    def pairs_hook(pairs):
        pair_calls.append(pairs)
        return pairs

    decoded = json.loads(
        '{"x": 1, "x": 2}',
        object_hook=lambda value: object_calls.append(value),
        object_pairs_hook=pairs_hook,
    )
    assert decoded == [("x", 1), ("x", 2)]
    assert pair_calls == [[("x", 1), ("x", 2)]]
    assert object_calls == []


def test_numeric_hooks_receive_lexemes_before_default_number_conversion():
    decoded = json.loads(
        '{"price": 1.10, "count": 7}',
        parse_float=Decimal,
        parse_int=lambda token: ("integer-token", token),
    )
    assert decoded == {
        "price": Decimal("1.10"),
        "count": ("integer-token", "7"),
    }

    seen = []
    assert json.loads("[NaN, Infinity, -Infinity]", parse_constant=seen.append) == [
        None,
        None,
        None,
    ]
    assert seen == ["NaN", "Infinity", "-Infinity"]
    assert json.loads("[null, true, false]", parse_constant=seen.append) == [None, True, False]


def test_parse_constant_can_reject_nonstandard_numeric_tokens():
    def reject(token):
        raise ValueError(f"non-standard number: {token}")

    with pytest.raises(ValueError, match="non-standard number: NaN"):
        json.loads("NaN", parse_constant=reject)


# 371｜JSONDecoder.raw_decode、strict 控制字符与结构化错误位置。
#
# decode/loads 要求输入只含一个完整文档；raw_decode 返回值和结束索引，适合由上层 framing 逻辑
# 从缓冲区取一个值，但它不会自动越过开头空白。strict=False 仅允许字符串中的 U+0000..U+001F
# 原始控制字符，不会放宽缺引号、尾逗号等其他语法。JSONDecodeError 保存原文和精确行列。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.JSONDecoder
# polyglot-covers: python.json.JSONDecoder.decode
# polyglot-covers: python.json.JSONDecoder.raw_decode
# polyglot-covers: python.json.raw-decode-returns-end-index
# polyglot-covers: python.json.raw-decode-does-not-skip-leading-whitespace
# polyglot-covers: python.json.JSONDecoder.strict
# polyglot-covers: python.json.strict-false-allows-control-characters
# polyglot-covers: python.json.JSONDecodeError
# polyglot-covers: python.json.JSONDecodeError.msg
# polyglot-covers: python.json.JSONDecodeError.doc
# polyglot-covers: python.json.JSONDecodeError.pos
# polyglot-covers: python.json.JSONDecodeError.lineno
# polyglot-covers: python.json.JSONDecodeError.colno
# polyglot-covers: python.json.trailing-data-error




def test_raw_decode_returns_the_first_value_and_exact_buffer_end_index():
    decoder = json.JSONDecoder()
    text = '{"a": 1} trailing'
    value, end = decoder.raw_decode(text)
    assert value == {"a": 1}
    assert end == len('{"a": 1}')
    assert text[end:] == " trailing"

    with pytest.raises(json.JSONDecodeError) as leading_error:
        decoder.raw_decode("  1")
    assert leading_error.value.pos == 0
    value, end = decoder.raw_decode("  1", idx=2)
    assert (value, end) == (1, 3)


def test_strict_false_only_relaxes_raw_control_characters_inside_strings():
    document = '"left\tright"'
    with pytest.raises(json.JSONDecodeError):
        json.loads(document)
    assert json.JSONDecoder(strict=False).decode(document) == "left\tright"
    with pytest.raises(json.JSONDecodeError):
        json.JSONDecoder(strict=False).decode('{"a": 1,}')


def test_decode_error_exposes_message_document_offset_line_and_column():
    document = '{"a": 1,}'
    with pytest.raises(json.JSONDecodeError) as raised:
        json.loads(document)
    error = raised.value
    assert isinstance(error, ValueError)
    assert error.msg == "Expecting property name enclosed in double quotes"
    assert error.doc == document
    assert error.pos == 8
    assert error.lineno == 1
    assert error.colno == 9

    with pytest.raises(json.JSONDecodeError, match="Extra data"):
        json.loads("1 2")


# 372｜NaN/Infinity、重复名称与顶层 scalar 的兼容性边界。
#
# 默认编码器/解码器接受 NaN 与无穷大，这是 JavaScript 风格扩展而非标准 JSON；互操作接口应在
# 编码侧 allow_nan=False，并在解码侧用 parse_constant 拒绝。重复成员默认保留最后值，可能掩盖
# 恶意字段；需要 object_pairs_hook 才能检测。RFC 7159 允许顶层 scalar，模块从不强制 object/array。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.allow_nan
# polyglot-covers: python.json.default-encodes-nan-infinity-extension
# polyglot-covers: python.json.default-decodes-nan-infinity-extension
# polyglot-covers: python.json.allow-nan-false-valueerror
# polyglot-covers: python.json.strict-number-decoding-parse-constant-workflow
# polyglot-covers: python.json.repeated-object-names-last-wins
# polyglot-covers: python.json.repeated-name-validation-trap
# polyglot-covers: python.json.top-level-scalar
# polyglot-covers: python.json.nan-not-equal-itself-trap




def test_default_nan_and_infinity_extensions_require_opt_in_for_interoperability():
    encoded = json.dumps([math.nan, math.inf, -math.inf])
    assert encoded == "[NaN, Infinity, -Infinity]"
    decoded = json.loads(encoded)
    assert math.isnan(decoded[0])
    assert decoded[1:] == [math.inf, -math.inf]
    assert decoded[0] != decoded[0]

    with pytest.raises(ValueError, match="Out of range float values"):
        json.dumps(math.nan, allow_nan=False)

    def reject(token):
        raise ValueError(token)

    with pytest.raises(ValueError, match="Infinity"):
        json.loads("Infinity", parse_constant=reject)


def test_duplicate_names_default_to_last_value_but_pairs_hook_can_reject_them():
    document = '{"role": "user", "role": "admin"}'
    assert json.loads(document) == {"role": "admin"}

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    with pytest.raises(ValueError, match="duplicate key: role"):
        json.loads(document, object_pairs_hook=unique_object)


@pytest.mark.parametrize(
    ("document", "expected"),
    [("null", None), ("true", True), ('"text"', "text"), ("42", 42)],
)
def test_top_level_value_may_be_a_scalar(document, expected):
    assert json.loads(document) == expected


# 373｜Unicode、UTF bytes 自动探测、BOM 差异与不可信输入限额。
#
# loads 接受 str、bytes、bytearray；二进制输入自动识别 UTF-8/16/32。str 开头的 U+FEFF 被视为
# 意外 BOM 而拒绝，UTF-8-SIG bytes 则在解码阶段剥离 BOM，这是输入类型造成的细微差异。模块不
# 限制文档大小或嵌套深度，服务必须在解析前实施自己的字节上限以防资源耗尽。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.loads-str-bytes-bytearray
# polyglot-covers: python.json.binary-input-utf8-utf16-utf32
# polyglot-covers: python.json.binary-input-encoding-autodetection
# polyglot-covers: python.json.str-leading-bom-valueerror
# polyglot-covers: python.json.utf8-sig-bytes-bom-stripped
# polyglot-covers: python.json.unpaired-surrogate-roundtrip
# polyglot-covers: python.json.untrusted-input-resource-exhaustion
# polyglot-covers: python.json.limit-input-size-before-parsing-workflow
# polyglot-covers: python.json.no-built-in-document-size-limit




@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
def test_binary_input_autodetects_supported_unicode_encodings(encoding):
    document = '{"城市": "深圳"}'
    encoded = document.encode(encoding)
    assert json.loads(encoded) == {"城市": "深圳"}
    assert json.loads(bytearray(encoded)) == {"城市": "深圳"}


def test_bom_handling_differs_between_an_already_decoded_str_and_bytes():
    with pytest.raises(ValueError, match="Unexpected UTF-8 BOM"):
        json.loads("\ufeff{}")
    assert json.loads(b"\xef\xbb\xbf{}") == {}


def test_unpaired_surrogate_is_preserved_but_may_not_interoperate():
    value = "\ud800"
    encoded = json.dumps(value)
    assert encoded == '"\\ud800"'
    assert json.loads(encoded) == value


def test_application_can_reject_large_untrusted_payload_before_json_parsing():
    def limited_loads(payload, max_bytes):
        raw = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
        if len(raw) > max_bytes:
            raise ValueError("JSON payload exceeds byte limit")
        return json.loads(raw)

    assert limited_loads('{"ok": true}', 32) == {"ok": True}
    with pytest.raises(ValueError, match="exceeds byte limit"):
        limited_loads('["large value"]', 8)


# 374｜JSON 不是 framed protocol，以及 JSON Lines 工作流。
#
# 连续对同一 stream 调用 dump 不会插入分隔符，两个合法值会黏成一个非法文档。若协议需要连续
# 记录，必须另定 framing；简单文本场景常用“一行一个紧凑 JSON”，逐行 loads。字符串内部换行会
# 被转义，所以不会破坏行边界，但生产方仍需约定空行与最大行长。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.not-a-framed-protocol
# polyglot-covers: python.json.repeated-dump-same-stream-invalid-document
# polyglot-covers: python.json.explicit-message-framing-required
# polyglot-covers: python.json.json-lines-workflow
# polyglot-covers: python.json.json-lines-one-value-per-line
# polyglot-covers: python.json.string-newline-escaped-within-line




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


# 375｜python -m json.tool 的验证、格式化与 JSON Lines 模式。
#
# json.tool 是标准库自带的命令行验证器。它成功时输出 pretty JSON，语法错误时非零退出并把位置
# 信息写到 stderr；--sort-keys 便于稳定 diff，--no-ensure-ascii 保留可读 Unicode，--json-lines
# 逐行处理独立文档。案例使用 sys.executable，确保调用的正是运行测试的 Python 3.10。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.json.tool
# polyglot-covers: python.json.tool-validates-and-pretty-prints
# polyglot-covers: python.json.tool-invalid-input-nonzero-exit
# polyglot-covers: python.json.tool-error-to-stderr
# polyglot-covers: python.json.tool-sort-keys
# polyglot-covers: python.json.tool-no-ensure-ascii
# polyglot-covers: python.json.tool-json-lines
# polyglot-covers: python.json.tool-compact
# polyglot-covers: python.json.tool-sys-executable-workflow



def run_json_tool(*arguments, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "json.tool", *map(str, arguments)],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_tool_validates_sorts_and_preserves_unicode_in_file_workflow(tmp_path):
    source = tmp_path / "input.json"
    target = tmp_path / "output.json"
    source.write_text('{"z": 1, "城市": "深圳"}', encoding="utf-8")

    completed = run_json_tool("--sort-keys", "--no-ensure-ascii", source, target)
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert json.loads(target.read_text(encoding="utf-8")) == {"z": 1, "城市": "深圳"}
    rendered = target.read_text(encoding="utf-8")
    assert rendered.index('"z"') < rendered.index('"城市"')
    assert "深圳" in rendered


def test_tool_reports_invalid_input_and_handles_json_lines_from_stdin():
    invalid = run_json_tool(input_text="{not json}")
    assert invalid.returncode != 0
    assert invalid.stdout == ""
    assert "line 1 column 2" in invalid.stderr

    lines = run_json_tool("--json-lines", "--compact", input_text='{"id": 1}\n{"id": 2}\n')
    assert lines.returncode == 0
    assert [json.loads(line) for line in lines.stdout.splitlines()] == [
        {"id": 1},
        {"id": 2},
    ]
