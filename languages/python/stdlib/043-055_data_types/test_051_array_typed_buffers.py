"""051｜``array`` 同质数值序列、机器字节表示与 buffer protocol 示例。

``array.array`` 像可变 list 一样支持索引、切片和常见序列操作，但 typecode 固定了
元素对应的 C 类型。``itemsize`` 与原始字节布局受机器架构影响，所以可移植代码应
读取元数据并做同类型往返，不应硬编码本机地址、字节序或 C long 的宽度。

array 也直接导出可写 buffer；memoryview 存活期间可以原地改元素，但不能调整底层
数组长度。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.array.typecodes python.array.itemsize
# polyglot-covers: python.array.constructor python.array.type-constraint
# polyglot-covers: python.array.integer-overflow python.array.sequence-operations
# polyglot-covers: python.array.slicing python.array.slice-assignment
# polyglot-covers: python.array.concatenation python.array.repetition
# polyglot-covers: python.array.append python.array.extend python.array.insert
# polyglot-covers: python.array.pop python.array.remove python.array.reverse
# polyglot-covers: python.array.count python.array.index-range-python310
# polyglot-covers: python.array.fromlist-atomic python.array.tolist
# polyglot-covers: python.array.tobytes python.array.frombytes
# polyglot-covers: python.array.tofile python.array.fromfile python.array.partial-eof
# polyglot-covers: python.array.byteswap python.array.machine-representation
# polyglot-covers: python.array.unicode-typecode python.array.deprecated-u
# polyglot-covers: python.array.buffer-info python.array.buffer-protocol
# polyglot-covers: python.array.memoryview-write-through python.array.export-resize
# polyglot-covers: python.array.repr-roundtrip

from array import array
from array import typecodes
from io import BytesIO

import pytest


def test_typecodes_are_available_but_actual_item_sizes_are_runtime_metadata():
    """类型码集合由模块公布；除文档最小值外，实际 C 宽度应从 itemsize 获取。"""

    minimum_sizes = {
        "b": 1,
        "B": 1,
        "u": 2,
        "h": 2,
        "H": 2,
        "i": 2,
        "I": 2,
        "l": 4,
        "L": 4,
        "q": 8,
        "Q": 8,
        "f": 4,
        "d": 8,
    }

    assert set(minimum_sizes) <= set(typecodes)
    for typecode, minimum in minimum_sizes.items():
        assert array(typecode).itemsize >= minimum

    with pytest.raises(ValueError, match="bad typecode"):
        array("z")


def test_constructor_accepts_typed_values_iterables_or_matching_raw_bytes():
    """普通 iterable 按元素转换；bytes-like initializer 则按本机机器值解释。"""

    from_list = array("i", [1, 2, 3])
    from_generator = array("i", (value * 10 for value in range(1, 4)))
    from_bytes = array("i", from_list.tobytes())

    assert from_list.tolist() == [1, 2, 3]
    assert from_generator.tolist() == [10, 20, 30]
    assert from_bytes == from_list
    assert from_bytes.typecode == "i"


def test_integer_array_rejects_wrong_python_types_and_out_of_range_values():
    """array 不像 list 接受混合类型；整数还必须落入当前 C signed int 的范围。"""

    values = array("i", [1])
    signed_bits = values.itemsize * 8
    maximum = (1 << (signed_bits - 1)) - 1

    with pytest.raises(TypeError):
        values.append(1.5)
    with pytest.raises(OverflowError):
        values.append(maximum + 1)

    assert values.tolist() == [1]


def test_indexing_and_slicing_preserve_values_and_array_typecode():
    """单项索引返回 Python 标量；切片返回独立的同 typecode array，而不是 list。"""

    values = array("i", [10, 20, 30, 40])
    subset = values[1:3]

    assert values[-1] == 40
    assert isinstance(subset, array)
    assert subset.typecode == "i"
    assert subset.tolist() == [20, 30]

    subset[0] = 99
    assert values.tolist() == [10, 20, 30, 40]


def test_slice_assignment_requires_an_array_with_the_exact_same_typecode():
    """即使 list 元素都是 int 也不能赋给 slice；替换值必须是相同 typecode array。"""

    values = array("i", [1, 2, 3, 4])
    values[1:3] = array("i", [20, 30, 40])

    assert values.tolist() == [1, 20, 30, 40, 4]

    with pytest.raises(TypeError):
        values[1:2] = [99]
    with pytest.raises(TypeError):
        values[1:2] = array("l", [99])


def test_concatenation_requires_matching_typecodes_and_multiplication_repeats():
    """加法是序列拼接、乘法是重复，不是逐元素数值运算；不同 typecode 不能拼接。"""

    left = array("i", [1, 2])
    right = array("i", [3])

    assert (left + right).tolist() == [1, 2, 3]
    assert (left * 2).tolist() == [1, 2, 1, 2]

    with pytest.raises(TypeError):
        left + array("l", [3])


def test_mutating_sequence_methods_follow_list_like_positions_and_returns():
    """append/extend/insert 原地修改；pop 返回元素，remove 只删除首个匹配值。"""

    values = array("i", [2, 3, 2])

    assert values.append(4) is None
    assert values.extend([5, 6]) is None
    assert values.insert(0, 1) is None
    assert values.tolist() == [1, 2, 3, 2, 4, 5, 6]

    assert values.pop() == 6
    assert values.remove(2) is None
    assert values.tolist() == [1, 3, 2, 4, 5]

    assert values.reverse() is None
    assert values.tolist() == [5, 4, 2, 3, 1]
    assert values.count(3) == 1


def test_index_accepts_start_and_stop_ranges_in_python_310():
    """3.10 的 array.index 与 list.index 一样支持半开 start/stop 子范围。"""

    values = array("i", [1, 2, 1, 2, 1])

    assert values.index(1) == 0
    assert values.index(1, 1) == 2
    assert values.index(2, 2, 4) == 3

    with pytest.raises(ValueError, match="not in array"):
        values.index(1, 1, 2)


def test_fromlist_rolls_back_all_appends_when_any_item_has_wrong_type():
    """fromlist 明确提供失败原子性；类型错误不会留下此前已成功转换的前缀。"""

    values = array("i", [1])

    with pytest.raises(TypeError):
        values.fromlist([2, 3, "wrong", 4])

    assert values.tolist() == [1]


def test_tolist_returns_an_independent_plain_list():
    """tolist 复制为普通 list；之后任一侧改变都不会同步到另一侧。"""

    values = array("d", [1.5, 2.5])
    copied = values.tolist()

    assert copied == [1.5, 2.5]
    copied.append(3.5)
    values[0] = 9.5

    assert copied == [1.5, 2.5, 3.5]
    assert values.tolist() == [9.5, 2.5]


def test_tobytes_and_frombytes_round_trip_native_machine_representation():
    """原始 bytes 依赖本机表示；同 typecode 往返可恢复值，长度由 itemsize 决定。"""

    original = array("i", [1, -2, 300])
    payload = original.tobytes()
    restored = array("i")

    assert bytes(original) == payload
    assert len(payload) == len(original) * original.itemsize
    assert restored.frombytes(payload) is None
    assert restored == original


def test_frombytes_requires_a_whole_number_of_machine_items():
    """字节数若不是 itemsize 的整数倍，最后半个机器值没有可解释语义。"""

    values = array("i", [1])
    incomplete = b"\x00" * (values.itemsize - 1)

    with pytest.raises(ValueError, match="multiple of item size"):
        values.frombytes(incomplete)

    assert values.tolist() == [1]


def test_tofile_and_fromfile_round_trip_through_a_temporary_binary_file(tmp_path):
    """文件保存的是机器值而非自描述格式；读取端必须提前知道相同 typecode 和数量。"""

    path = tmp_path / "samples.bin"
    original = array("d", [1.25, -2.5, 3.75])

    with path.open("wb") as file:
        assert original.tofile(file) is None

    restored = array("d")
    with path.open("rb") as file:
        assert restored.fromfile(file, 3) is None

    assert restored == original
    assert path.stat().st_size == len(original) * original.itemsize


def test_fromfile_raises_eoferror_but_keeps_whole_items_that_were_available():
    """请求数量超过文件内容时不是事务失败：完整读取到的前缀已经追加，然后才抛错。"""

    available = array("H", [10, 20])
    target = array("H", [1])
    stream = BytesIO(available.tobytes())

    with pytest.raises(EOFError):
        target.fromfile(stream, 3)

    assert target.tolist() == [1, 10, 20]


def test_byteswap_reverses_each_item_bytes_and_is_its_own_inverse():
    """byteswap 逐个元素反转字节，适配不同 endian 数据；调用两次恢复原表示。"""

    values = array("H", [0x0102, 0x0A0B])
    original = values.tobytes()
    width = values.itemsize
    expected = b"".join(
        original[offset : offset + width][::-1]
        for offset in range(0, len(original), width)
    )

    assert values.byteswap() is None
    assert values.tobytes() == expected

    values.byteswap()
    assert values.tobytes() == original
    assert values.tolist() == [0x0102, 0x0A0B]


def test_unicode_array_round_trips_text_but_u_typecode_is_deprecated():
    """3.10 仍支持 wchar_t 的 'u' 与专用方法，但新设计不应依赖这个弃用 typecode。"""

    values = array("u", "你好")

    assert values.typecode == "u"
    assert values.tounicode() == "你好"
    assert values.fromunicode("!") is None
    assert values.tounicode() == "你好!"

    with pytest.raises(ValueError):
        array("i").fromunicode("text")
    with pytest.raises(ValueError):
        array("i").tounicode()


def test_buffer_info_reports_address_and_element_count_not_byte_count():
    """buffer_info 的 length 是元素数；低层地址在改变长度后可能失效，新代码优先 buffer。"""

    values = array("i", [10, 20, 30])
    address, length = values.buffer_info()

    assert isinstance(address, int)
    assert address != 0
    assert length == len(values) == 3
    assert length * values.itemsize == len(values.tobytes())


def test_memoryview_exposes_writable_zero_copy_elements_and_buffer_metadata():
    """memoryview 直接引用 array 存储；元素写入立即反映到底层，不产生 list 副本。"""

    values = array("i", [1, 2, 3])
    view = memoryview(values)

    assert view.readonly is False
    assert view.itemsize == values.itemsize
    assert view.nbytes == len(values) * values.itemsize
    assert view.tolist() == [1, 2, 3]

    view[1] = 20
    assert values.tolist() == [1, 20, 3]
    view.release()


def test_exported_memoryview_blocks_resizing_until_it_is_released():
    """活动 buffer 保存地址和形状；允许等长赋值，但 append 等重新分配操作会被拒绝。"""

    values = array("i", [1, 2, 3])
    view = memoryview(values)

    values[0] = 10
    assert view[0] == 10

    with pytest.raises(BufferError):
        values.append(4)

    view.release()
    values.append(4)
    assert values.tolist() == [10, 2, 3, 4]


def test_repr_can_reconstruct_same_array_when_array_name_is_available():
    """repr 带 typecode 和 initializer；在明确提供 array 名称的受控命名空间可往返。"""

    values = array("l", [1, 2, 3])
    restored = eval(repr(values), {"array": array})

    assert restored == values
    assert restored.typecode == values.typecode
    assert restored is not values
