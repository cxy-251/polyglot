"""022｜``bytes``、``bytearray`` 与 ``memoryview`` 二进制序列示例。

bytes 是不可变字节值，bytearray 是可变字节缓冲区，memoryview 则在 buffer
protocol 上创建通常不复制数据的结构化视图。三者都处理 0--255 的字节，而不是
Unicode 文本；编码和解码必须显式跨越 str/bytes 边界。

通用订阅协议已在 005、str 编码入口已在 021 展示；本文件聚焦二进制类型自身。
内容基于 Python 3.10 Binary Sequence Types 和 Memory Views；当前文件尚未经过
pytest 验证。
"""

# polyglot-covers: python.type.bytes python.type.bytearray python.type.memoryview
# polyglot-covers: python.literal.bytes python.builtin.bytes python.builtin.bytearray
# polyglot-covers: python.builtin.memoryview python.bytes.decode python.bytes.hex
# polyglot-covers: python.bytes.fromhex python.bytes.binary-methods
# polyglot-covers: python.bytes.percent-formatting python.bytearray.mutation
# polyglot-covers: python.memoryview.metadata python.memoryview.cast
# polyglot-covers: python.memoryview.release python.buffer.export-resize-boundary

import pytest


def test_bytes_literals_use_ascii_source_characters_and_byte_escapes():
    """bytes 字面量可直接写 ASCII，其他字节用十六进制等转义表示。"""

    header = b"HTTP/1.1\r\n"
    payload = b"\x00\x7f\xff"

    assert header.endswith(b"\r\n")
    assert list(payload) == [0, 127, 255]
    assert b"A" == b"\x41"
    assert rb"\x41" == b"\\x41"

    with pytest.raises(SyntaxError):
        compile("value = b'咖啡'", "<bytes-literal>", "exec")

    # 字面量源码中的非 ASCII 字符被拒绝；实际文本应先成为 str，再按协议编码。


def test_bytes_constructor_distinguishes_length_iterable_buffer_and_text():
    """bytes 的参数类型决定构造语义，单个 int 表示零字节数量。"""

    assert bytes() == b""
    assert bytes(4) == b"\x00\x00\x00\x00"
    assert bytes([65, 66, 255]) == b"AB\xff"
    assert bytes(bytearray(b"mutable")) == b"mutable"
    assert bytes("咖啡", encoding="utf-8") == b"\xe5\x92\x96\xe5\x95\xa1"
    assert bytearray(3) == bytearray(b"\x00\x00\x00")
    assert bytearray("café", encoding="utf-8") == bytearray(b"caf\xc3\xa9")

    # 常见坑：bytes(4) 不是 b"4"；需要十进制文本时应显式 str(4).encode(...)。
    assert str(4).encode("ascii") == b"4"

    with pytest.raises(ValueError):
        bytes([256])

    with pytest.raises(TypeError):
        bytes("text")


def test_binary_indexing_returns_int_while_slicing_preserves_sequence_type():
    """单个字节用 0--255 整数表示，切片仍是二进制序列。"""

    immutable = b"A\xffC"
    mutable = bytearray(immutable)

    assert immutable[0] == 65
    assert immutable[-2] == 255
    assert immutable[0:1] == b"A"
    assert mutable[0] == 65
    assert mutable[0:1] == bytearray(b"A")
    assert 255 in immutable
    assert b"\xffC" in immutable

    # 这与 str[0] 返回长度 1 的 str 不同；需要 bytes 时要显式切片或 bytes([n])。


def test_bytes_is_immutable_and_bytearray_supports_in_place_byte_updates():
    """bytearray 的索引写入接收整数，切片写入接收 bytes-like iterable。"""

    immutable = b"abcd"

    with pytest.raises(TypeError):
        immutable[0] = 65

    mutable = bytearray(immutable)
    mutable[0] = ord("A")
    mutable[1:3] = b"XYZ"

    assert mutable == bytearray(b"AXYZd")

    with pytest.raises(ValueError):
        mutable[0] = 256


def test_bytearray_mutating_methods_manage_a_binary_buffer():
    """append/insert 接收单字节整数，extend 接收字节 iterable。"""

    data = bytearray(b"ac")
    data.insert(1, ord("b"))
    data.append(ord("d"))
    data.extend(b"ef")

    assert data == bytearray(b"abcdef")
    assert data.pop() == ord("f")
    data.remove(ord("b"))
    data.reverse()

    assert data == bytearray(b"edca")

    data.clear()
    assert data == bytearray()


def test_non_mutating_bytearray_methods_return_new_values():
    """bytearray 可变不代表它的每个类似 str 的方法都会原地修改。"""

    original = bytearray(b"hello")
    upper = original.upper()
    replaced = original.replace(b"h", b"y")

    assert original == bytearray(b"hello")
    assert upper == bytearray(b"HELLO")
    assert replaced == bytearray(b"yello")
    assert upper is not original

    # 若需要修改原缓冲区，要做切片赋值或把返回值重新绑定，不能忽略方法返回值。


def test_decode_round_trip_and_error_policy_are_explicit():
    """decode 按指定字符编码解释 bytes；无效序列的策略决定是否丢失信息。"""

    encoded = b"caf\xc3\xa9"

    assert encoded.decode("utf-8") == "café"
    assert encoded.decode("utf-8").encode("utf-8") == encoded

    invalid = b"name=\xff"
    with pytest.raises(UnicodeDecodeError):
        invalid.decode("utf-8")

    assert invalid.decode("utf-8", errors="replace") == "name=�"
    assert invalid.decode("utf-8", errors="ignore") == "name="

    # replace 可保留“此处损坏”的证据；ignore 会静默删除字节，通常不适合协议校验。


def test_utf8_bom_handling_depends_on_the_selected_codec():
    """UTF-8 BOM 是实际字节；utf-8-sig codec 才会在开头消费它。"""

    payload = b"\xef\xbb\xbfheader"

    assert payload.decode("utf-8") == "\ufeffheader"
    assert payload.decode("utf-8-sig") == "header"

    # 不应对任意数据手工 strip BOM 字节；codec 才理解它只在流开头的语义。


def test_hex_and_fromhex_provide_readable_lossless_binary_text():
    """hex 展示每个字节，fromhex 忽略 ASCII 空白并还原二进制值。"""

    payload = b"\x00\xab\xff"

    assert payload.hex() == "00abff"
    assert payload.hex(" ") == "00 ab ff"
    assert bytes.fromhex("00 ab\nff") == payload
    assert bytearray.fromhex("00abff") == bytearray(payload)

    with pytest.raises(ValueError):
        bytes.fromhex("not hex")

    # hex 文本每个字节固定两位，适合日志/夹具；它不是字符编码，不应用 decode 解析。


def test_binary_search_split_partition_and_join_use_bytes_like_tokens():
    """常用文本形方法也存在于二进制序列，但参数和结果仍是 bytes。"""

    payload = b"one,two,,three"

    assert payload.find(b"two") == 4
    assert payload.index(b"three") == 9
    assert payload.count(b",") == 3
    assert payload.split(b",") == [b"one", b"two", b"", b"three"]
    assert payload.partition(b",") == (b"one", b",", b"two,,three")
    assert b"|".join([b"one", b"two"]) == b"one|two"

    with pytest.raises(TypeError):
        payload.find("two")


def test_binary_prefix_cleanup_and_translation_remain_byte_oriented():
    """边界标记和逐字节映射不会进行 Unicode 解释。"""

    framed = b"HDR:payload\r\n"
    assert framed.removeprefix(b"HDR:").removesuffix(b"\r\n") == b"payload"

    table = bytes.maketrans(b"abc", b"ABC")
    assert b"cab!".translate(table, delete=b"!") == b"CAB"

    # maketrans 的两个参数必须等长，并由此生成完整 256 项翻译表；translate 的
    # delete 参数再删除列出的原始字节。


def test_binary_case_and_classification_methods_are_ascii_only():
    """bytes 方法只理解 ASCII 字节，不把高位字节解码成 Unicode 字符。"""

    assert b"hello\xe9".upper() == b"HELLO\xe9"
    assert b"ABC".isupper()
    assert b"abc".isalpha()
    assert not b"\xe9".isalpha()
    assert b"123".isdigit()
    assert not b"\xb2".isdigit()
    assert b" \t\r\n".isspace()
    assert b"plain".isascii()
    assert not b"\xff".isascii()

    # 若字节代表文本，应先用正确 codec 解码，再使用 str 的 Unicode 分类方法。


def test_percent_formatting_builds_bytes_without_crossing_into_str():
    """bytes 的 printf 风格格式化适合小型二进制协议片段。"""

    message = b"%b=%04d; hex=%02x" % (b"items", 7, 255)

    assert message == b"items=0007; hex=ff"
    assert not hasattr(bytes, "format")

    with pytest.raises(TypeError):
        b"%b" % "text"

    # `%b` 需要 bytes-like 对象（或 __bytes__ 协议），不会替调用者猜 str 编码。


def test_bytes_are_hashable_but_bytearray_is_not():
    """内容相等不改变可变对象不能作为 hash key 的原则。"""

    immutable = b"abc"
    mutable = bytearray(b"abc")

    assert immutable == mutable
    assert {immutable: "value"}[b"abc"] == "value"

    with pytest.raises(TypeError):
        hash(mutable)


def test_memoryview_exposes_buffer_metadata_without_copying_contents():
    """一维 bytearray 视图通常按 unsigned byte（B）解释。"""

    source = bytearray(b"abcd")
    view = memoryview(source)

    assert view.obj is source
    assert view.format == "B"
    assert view.itemsize == 1
    assert view.ndim == 1
    assert view.shape == (4,)
    assert view.strides == (1,)
    assert view.nbytes == 4
    assert view.readonly is False
    assert view.tolist() == [97, 98, 99, 100]
    assert view.tobytes() == b"abcd"


def test_memoryview_slice_shares_storage_with_mutable_exporter():
    """视图切片不是 bytearray 副本，写入会反映到原缓冲区。"""

    source = bytearray(b"abcd")
    view = memoryview(source)
    middle = view[1:3]

    middle[:] = b"XY"

    assert source == bytearray(b"aXYd")
    assert view.tobytes() == b"aXYd"
    assert middle.tobytes() == b"XY"

    # 共享很适合解析大缓冲区，也意味着 API 边界若需要隔离就应显式调用 bytes(view)。


def test_memoryview_of_bytes_is_read_only():
    """memoryview 是否可写由底层 exporter 决定，而不是由视图构造器决定。"""

    view = memoryview(b"abc")

    assert view.readonly is True

    with pytest.raises(TypeError):
        view[0] = ord("A")

    assert view.tobytes() == b"abc"


def test_memoryview_cast_changes_element_format_or_shape_not_underlying_bytes():
    """cast 重新解释同一段连续内存，字节总数必须与新布局一致。"""

    source = bytearray(range(8))
    byte_view = memoryview(source)
    word_view = byte_view.cast("I")
    matrix = byte_view.cast("B", shape=[2, 4])

    assert word_view.itemsize == 4
    assert word_view.shape == (2,)
    assert word_view.nbytes == 8
    assert matrix.ndim == 2
    assert matrix.shape == (2, 4)
    assert matrix.strides == (4, 1)
    assert matrix[1, 3] == 7

    with pytest.raises(TypeError):
        memoryview(bytearray(3)).cast("I")

    # `I` 使用本机原生格式；跨机器协议不要用其数值结果猜端序，应使用 struct 等
    # 明确声明字节序的标准库工具。


def test_non_contiguous_view_reports_logical_nbytes_and_can_copy_to_bytes():
    """带步长切片可不连续；nbytes 统计可访问元素占用的逻辑字节。"""

    view = memoryview(b"abcdef")[::2]

    assert view.tolist() == [97, 99, 101]
    assert view.nbytes == 3
    assert view.strides == (2,)
    assert view.c_contiguous is False
    assert view.tobytes() == b"ace"


def test_exported_memoryview_prevents_bytearray_resizing_until_release():
    """视图依赖原缓冲区地址和布局，导出期间只能等长改写。"""

    source = bytearray(b"abc")
    view = memoryview(source)

    view[0] = ord("A")
    assert source == bytearray(b"Abc")

    with pytest.raises(BufferError):
        source.append(ord("d"))

    view.release()
    source.append(ord("d"))
    assert source == bytearray(b"Abcd")


def test_memoryview_context_manager_releases_the_view_on_exit():
    """with memoryview(...) 保证离开作用域时 release。"""

    source = bytearray(b"abc")

    with memoryview(source) as view:
        assert view[0] == ord("a")
        view[0] = ord("A")

    assert source == bytearray(b"Abc")

    with pytest.raises(ValueError, match="released memoryview"):
        view[0]


def test_only_eligible_read_only_memoryviews_are_hashable():
    """一维只读 B/b/c 视图按其字节内容 hash；可写视图不能 hash。"""

    readonly = memoryview(b"abc")
    writable = memoryview(bytearray(b"abc"))

    assert readonly == memoryview(b"abc")
    assert hash(readonly) == hash(b"abc")

    with pytest.raises(ValueError):
        hash(writable)

    # 即使当前内容不变，可写 exporter 后续仍能改变相等关系，所以不能成为稳定键。
