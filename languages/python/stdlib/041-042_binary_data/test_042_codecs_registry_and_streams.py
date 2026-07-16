"""042｜``codecs`` 注册表、错误策略、增量与流式编解码示例。

大多数 codec 在 ``str`` 与 ``bytes`` 之间转换，但 Python 还注册了 bytes-to-bytes
和 str-to-str 转换。``codecs`` 提供统一注册表与底层组件；普通文本最常用的入口仍是
``str.encode()``、``bytes.decode()`` 和内置 ``open()``。

codec search functions 与 error handlers 属于进程全局注册表。本文件会注销自定义
search function；没有 unregister API 的 error handler 放入短生命周期子进程，避免
污染整个 pytest 会话。
"""

# polyglot-covers: python.stdlib.codecs python.codecs.encode-decode
# polyglot-covers: python.codecs.lookup python.codecs.CodecInfo
# polyglot-covers: python.codecs.getencoder-getdecoder python.codecs.consumed
# polyglot-covers: python.codecs.error-handlers python.codecs.surrogateescape
# polyglot-covers: python.codecs.register_error python.codecs.lookup_error
# polyglot-covers: python.codecs.incremental-encoder python.codecs.incremental-decoder
# polyglot-covers: python.codecs.incremental-state python.codecs.final
# polyglot-covers: python.codecs.iterencode python.codecs.iterdecode
# polyglot-covers: python.codecs.stream-reader-writer python.codecs.open
# polyglot-covers: python.codecs.EncodedFile python.codecs.stream-ownership
# polyglot-covers: python.codecs.BOM python.codecs.utf-8-sig
# polyglot-covers: python.codecs.utf-16-endianness
# polyglot-covers: python.codecs.binary-transform python.codecs.text-transform
# polyglot-covers: python.codecs.register python.codecs.unregister

import codecs
import io
import subprocess
import sys

import pytest


def test_stateless_helpers_match_the_usual_text_and_bytes_methods():
    """对普通文本编码，codecs 的通用入口与类型专用方法产生相同结果。"""

    text = "价格 €"

    encoded = codecs.encode(text, "utf-8")
    decoded = codecs.decode(encoded, "utf-8")

    assert encoded == text.encode("utf-8")
    assert decoded == encoded.decode("utf-8") == text
    assert isinstance(encoded, bytes)
    assert isinstance(decoded, str)

    # codecs 的默认编码是 UTF-8，但协议代码仍应显式写出编码名称。
    assert codecs.encode("猫") == "猫".encode("utf-8")


def test_lookup_normalizes_aliases_and_returns_codec_info():
    """名称匹配不区分大小写，连字符、空格会规范化；结果描述 codec 的各组件。"""

    infos = [
        codecs.lookup("UTF-8"),
        codecs.lookup("utf_8"),
        codecs.lookup("utf 8"),
    ]

    assert all(isinstance(info, codecs.CodecInfo) for info in infos)
    assert {info.name for info in infos} == {"utf-8"}
    assert all(callable(info.encode) and callable(info.decode) for info in infos)
    assert all(info.incrementalencoder is not None for info in infos)
    assert all(info.incrementaldecoder is not None for info in infos)

    with pytest.raises(LookupError):
        codecs.lookup("polyglot-encoding-that-does-not-exist")


def test_low_level_encoder_and_decoder_report_consumed_input():
    """getencoder/getdecoder 返回底层函数；除了输出，还报告本次消费的输入长度。"""

    encoder = codecs.getencoder("utf-8")
    decoder = codecs.getdecoder("utf-8")

    encoded, consumed_characters = encoder("猫")
    decoded, consumed_bytes = decoder(encoded)

    assert encoded == b"\xe7\x8c\xab"
    assert consumed_characters == 1
    assert decoded == "猫"
    assert consumed_bytes == 3

    # codecs.encode/decode 是便利层，只返回 output，不暴露 consumed。
    assert codecs.encode("猫", "utf-8") == encoded
    assert codecs.decode(encoded, "utf-8") == decoded


def test_encoding_error_strategies_choose_between_failure_and_information_loss():
    """strict 保留失败信号；ignore/replace 会丢信息，转义策略则留下可读线索。"""

    text = "A猫B"

    with pytest.raises(UnicodeEncodeError):
        text.encode("ascii", errors="strict")

    assert text.encode("ascii", errors="ignore") == b"AB"
    assert text.encode("ascii", errors="replace") == b"A?B"
    assert text.encode("ascii", errors="backslashreplace") == b"A\\u732bB"
    assert text.encode("ascii", errors="xmlcharrefreplace") == b"A&#29483;B"
    assert text.encode("ascii", errors="namereplace") == (
        b"A\\N{CJK UNIFIED IDEOGRAPH-732B}B"
    )


def test_decoding_error_strategies_handle_invalid_source_bytes_differently():
    """解码 replace 使用 U+FFFD，backslashreplace 保留坏字节的十六进制表示。"""

    source = b"A\xffB"

    with pytest.raises(UnicodeDecodeError):
        source.decode("utf-8", errors="strict")

    assert source.decode("utf-8", errors="ignore") == "AB"
    assert source.decode("utf-8", errors="replace") == "A\ufffdB"
    assert source.decode("utf-8", errors="backslashreplace") == "A\\xffB"


def test_surrogateescape_round_trips_unknown_filesystem_style_bytes():
    """surrogateescape 把 0x80..0xff 暂存到低代理区，可用同一策略还原原字节。"""

    original = b"report-\xff.bin"
    decoded = original.decode("utf-8", errors="surrogateescape")

    assert decoded == "report-\udcff.bin"
    assert ord(decoded[7]) == 0xDCFF
    assert decoded.encode("utf-8", errors="surrogateescape") == original

    # 低代理字符不是可随意传播的普通 Unicode 标量，严格 UTF-8 会拒绝它。
    with pytest.raises(UnicodeEncodeError):
        decoded.encode("utf-8")


def test_custom_error_handler_is_registered_only_inside_a_child_process():
    """register_error 没有 unregister；子进程同时展示异常对象和继续位置协议。"""

    program = r'''
import codecs

calls = []

def bracket_codepoint(error):
    assert isinstance(error, UnicodeEncodeError)
    calls.append((error.start, error.end, error.object[error.start:error.end]))
    replacement = f"<U+{ord(error.object[error.start]):04X}>"
    return replacement, error.end

name = "polyglot_bracket_codepoint"
codecs.register_error(name, bracket_codepoint)
assert codecs.lookup_error(name) is bracket_codepoint
assert "A猫B".encode("ascii", errors=name) == b"A<U+732B>B"
assert calls == [(1, 2, "猫")]
print("isolated-error-handler-ok")
'''

    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "isolated-error-handler-ok"


def test_incremental_decoder_buffers_a_multibyte_character_between_chunks():
    """无状态 decode 会拒绝半个字符；同一个 incremental decoder 会保存尾部字节。"""

    decoder_type = codecs.getincrementaldecoder("utf-8")
    decoder = decoder_type(errors="strict")

    first_output = decoder.decode(b"A\xe7", final=False)
    buffered_bytes, state_number = decoder.getstate()

    assert first_output == "A"
    assert buffered_bytes == b"\xe7"
    assert state_number == 0

    # state 可移交给同类型 decoder，例如暂停流读取后恢复。
    resumed = decoder_type(errors="strict")
    resumed.setstate((buffered_bytes, state_number))
    assert resumed.decode(b"\x8c\xabB", final=True) == "猫B"
    assert resumed.getstate() == (b"", 0)


def test_incremental_decoder_final_flushes_or_reports_incomplete_input():
    """final=False 允许等待下一块；流结束时 final=True 必须处理仍未闭合的字节序列。"""

    decoder_type = codecs.getincrementaldecoder("utf-8")
    strict_decoder = decoder_type(errors="strict")

    assert strict_decoder.decode(b"\xe7", final=False) == ""
    with pytest.raises(UnicodeDecodeError):
        strict_decoder.decode(b"", final=True)

    replacing_decoder = decoder_type(errors="replace")
    assert replacing_decoder.decode(b"\xe7", final=False) == ""
    assert replacing_decoder.decode(b"", final=True) == "\ufffd"


def test_incremental_decoder_reset_discards_buffered_partial_input():
    """reset 回到初始状态；未输出的残缺输入会被明确丢弃，不能事后恢复。"""

    decoder = codecs.getincrementaldecoder("utf-8")()
    assert decoder.decode(b"\xe7", final=False) == ""
    assert decoder.getstate()[0] == b"\xe7"

    assert decoder.reset() is None
    assert decoder.getstate() == (b"", 0)
    assert decoder.decode(b"A", final=True) == "A"


def test_utf8_sig_incremental_encoder_writes_the_bom_only_once_per_state():
    """stateful utf-8-sig encoder 只在首个输出前加 BOM；reset 后开始一条新流。"""

    encoder = codecs.getincrementalencoder("utf-8-sig")()
    first = encoder.encode("A", final=False)
    second = encoder.encode("猫", final=True)

    assert first.startswith(codecs.BOM_UTF8)
    assert not second.startswith(codecs.BOM_UTF8)
    assert first + second == "A猫".encode("utf-8-sig")

    assert encoder.reset() is None
    assert encoder.encode("B", final=True).startswith(codecs.BOM_UTF8)


def test_iterencode_and_iterdecode_preserve_state_across_iterable_chunks():
    """迭代器便利函数内部复用 incremental codec，chunk 不必落在字符边界。"""

    encoded_chunks = list(codecs.iterencode(iter(["你", "好"]), "utf-8"))
    assert b"".join(encoded_chunks) == "你好".encode("utf-8")
    assert all(isinstance(chunk, bytes) for chunk in encoded_chunks)

    source = "你好".encode("utf-8")
    split_bytes = [source[:1], source[1:4], source[4:]]
    decoded_chunks = list(codecs.iterdecode(iter(split_bytes), "utf-8"))

    assert "".join(decoded_chunks) == "你好"
    assert all(isinstance(chunk, str) for chunk in decoded_chunks)


def test_stream_reader_and_writer_wrap_a_binary_stream():
    """getwriter/getreader 让同一个 BytesIO 分别接收 str、返回 str，底层仍保存 bytes。"""

    binary_stream = io.BytesIO()
    writer = codecs.getwriter("utf-8")(binary_stream)

    assert writer.write("第一行") is None
    writer.writelines(["\n", "第二行"])
    writer.flush()
    assert binary_stream.getvalue() == "第一行\n第二行".encode("utf-8")

    binary_stream.seek(0)
    reader = codecs.getreader("utf-8")(binary_stream)
    assert reader.readline() == "第一行\n"
    assert reader.read() == "第二行"


def test_codecs_open_uses_an_encoded_binary_file_without_newline_translation(tmp_path):
    """Python 3.10 仍支持 codecs.open；普通文本文件通常应优先使用内置 open。"""

    path = tmp_path / "legacy-codecs-open.txt"

    with codecs.open(path, mode="w", encoding="utf-8") as stream:
        assert stream.write("甲\n乙") is None

    assert path.read_bytes() == "甲\n乙".encode("utf-8")

    with codecs.open(path, mode="r", encoding="utf-8") as stream:
        assert stream.read() == "甲\n乙"

    # codecs.open 的底层始终加 binary mode，也没有内置 open 的 newline 参数。


def test_encoded_file_transcodes_bytes_between_data_and_file_encodings():
    """EncodedFile 的调用面仍是 bytes；它在 data_encoding 与落盘编码间透明转码。"""

    original = io.BytesIO()
    recoder = codecs.EncodedFile(
        original,
        data_encoding="utf-8",
        file_encoding="utf-16-le",
    )

    recoder.write("你好".encode("utf-8"))
    recoder.flush()
    assert original.getvalue() == "你好".encode("utf-16-le")

    stored = io.BytesIO("再见".encode("utf-16-le"))
    reader = codecs.EncodedFile(
        stored,
        data_encoding="utf-8",
        file_encoding="utf-16-le",
    )
    assert reader.read() == "再见".encode("utf-8")

    # StreamRecoder 关闭时也会关闭传入的原始流；读取完所需值后显式释放。
    recoder.close()
    reader.close()
    assert original.closed and stored.closed


def test_closing_encoded_file_closes_the_original_stream():
    """StreamRecoder 拥有传入流的关闭责任；调用方不能假设 wrapper 关闭后仍可复用。"""

    original = io.BytesIO()
    recoder = codecs.EncodedFile(original, "utf-8", "utf-16-le")

    recoder.close()

    assert recoder.closed
    assert original.closed


def test_utf8_sig_consumes_only_an_optional_bom_at_the_start():
    """UTF-8 不要求 BOM；utf-8-sig 写时添加、读时跳过开头的 UTF-8 signature。"""

    signed = "data".encode("utf-8-sig")

    assert codecs.BOM_UTF8 == b"\xef\xbb\xbf"
    assert signed == codecs.BOM_UTF8 + b"data"
    assert signed.decode("utf-8-sig") == "data"
    assert b"data".decode("utf-8-sig") == "data"

    # 普通 utf-8 不把这三个字节当签名，解码后会保留 U+FEFF。
    assert signed.decode("utf-8") == "\ufeffdata"


def test_utf16_generic_and_explicit_endian_codecs_treat_bom_differently():
    """utf-16 用 BOM 选择字节序；utf-16-le/be 固定字节序且不会自动去掉 BOM。"""

    generic = "A".encode("utf-16")
    little_endian = "A".encode("utf-16-le")
    big_endian = "A".encode("utf-16-be")

    assert generic.startswith(codecs.BOM_UTF16)
    assert little_endian == b"A\x00"
    assert big_endian == b"\x00A"
    assert (codecs.BOM_UTF16_LE + little_endian).decode("utf-16") == "A"
    assert (codecs.BOM_UTF16_BE + big_endian).decode("utf-16") == "A"

    # 显式 endian codec 把 BOM 当普通 U+FEFF 数据，而不是字节序控制标记。
    assert (codecs.BOM_UTF16_LE + little_endian).decode("utf-16-le") == "\ufeffA"
    assert (codecs.BOM_UTF16_BE + big_endian).decode("utf-16-be") == "\ufeffA"

    expected_native_bom = (
        codecs.BOM_UTF16_LE if sys.byteorder == "little" else codecs.BOM_UTF16_BE
    )
    assert codecs.BOM == codecs.BOM_UTF16 == expected_native_bom


def test_binary_transform_maps_bytes_to_bytes_and_keeps_its_own_framing():
    """base64_codec 不是文本编码；它接收 bytes-like 并按 MIME 形式附带结尾换行。"""

    source = b"binary\x00data"
    encoded = codecs.encode(memoryview(source), "base64_codec")
    decoded = codecs.decode(encoded, "base64_codec")

    assert isinstance(encoded, bytes)
    assert encoded.endswith(b"\n")
    assert decoded == source
    assert isinstance(decoded, bytes)

    with pytest.raises(LookupError):
        source.decode("base64_codec")


def test_text_transform_maps_text_to_text_not_text_to_bytes():
    """rot_13 返回 str；它通过 codecs 通用入口使用，不属于 str.encode 的文本编码。"""

    transformed = codecs.encode("Hello, Python!", "rot_13")

    assert transformed == "Uryyb, Clguba!"
    assert isinstance(transformed, str)
    assert codecs.decode(transformed, "rot_13") == "Hello, Python!"

    with pytest.raises(LookupError):
        "Hello".encode("rot_13")


def test_iter_helpers_enforce_text_encoder_and_bytes_decoder_boundaries():
    """iterencode 要求输入 text；iterdecode 要求输入 bytes，不能机械套用任意 codec。"""

    with pytest.raises(TypeError):
        list(codecs.iterencode([b"binary"], "base64_codec"))

    with pytest.raises(TypeError):
        list(codecs.iterdecode(["Uryyb"], "rot_13"))


def test_custom_codec_search_function_is_normalized_cached_and_unregistered():
    """search function 返回 CodecInfo 或 None；unregister 同时清 cache，恢复全局状态。"""

    seen_names = []
    utf8_info = codecs.lookup("utf-8")

    def search_function(normalized_name):
        seen_names.append(normalized_name)
        if normalized_name == "polyglot_utf8_alias":
            return utf8_info
        return None

    codecs.register(search_function)
    try:
        alias_info = codecs.lookup("Polyglot UTF8-Alias")
        assert isinstance(alias_info, codecs.CodecInfo)
        assert alias_info.name == "utf-8"
        assert codecs.encode("猫", "polyglot_utf8_alias") == b"\xe7\x8c\xab"
        assert "polyglot_utf8_alias" in seen_names
    finally:
        # Python 3.10 新增 unregister；即使中途断言失败也必须撤销进程全局注册。
        codecs.unregister(search_function)

    with pytest.raises(LookupError):
        codecs.lookup("polyglot_utf8_alias")
