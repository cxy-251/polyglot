"""246｜``ShareableList`` supported scalars、fixed layout、capacity 与 name attachment。

ShareableList 把有限 scalar types 直接编码进 shared memory，长度固定且不支持 slice 产生
新 list。元素可换类型，但 str/bytes 不能超过该 slot 初始化时预留容量。按 name attach 或
pickle round trip 得到的是同一 backing block 的新 handle，不是 list snapshot。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.shared_memory.ShareableList
# polyglot-covers: python.multiprocessing.ShareableList-supported-types
# polyglot-covers: python.multiprocessing.ShareableList-index-assignment
# polyglot-covers: python.multiprocessing.ShareableList-type-change
# polyglot-covers: python.multiprocessing.ShareableList-fixed-length
# polyglot-covers: python.multiprocessing.ShareableList-no-slicing
# polyglot-covers: python.multiprocessing.ShareableList-slot-capacity
# polyglot-covers: python.multiprocessing.ShareableList.count
# polyglot-covers: python.multiprocessing.ShareableList.index
# polyglot-covers: python.multiprocessing.ShareableList.format
# polyglot-covers: python.multiprocessing.ShareableList.shm
# polyglot-covers: python.multiprocessing.ShareableList-attach-by-name
# polyglot-covers: python.multiprocessing.ShareableList-pickle-preserves-alias
# polyglot-covers: python.multiprocessing.ShareableList-cleanup

import pickle
from multiprocessing import shared_memory

import pytest


def test_shareable_list_preserves_supported_scalar_types_and_mutation():
    """bool 必须保持 bool 而不是 int；None 也有专门 encoding。"""

    values = shared_memory.ShareableList(
        ["text", b"bytes", -2.5, 7, None, True]
    )
    try:
        assert list(values) == ["text", b"bytes", -2.5, 7, None, True]
        assert [type(value) for value in values] == [
            str,
            bytes,
            float,
            int,
            type(None),
            bool,
        ]

        values[2] = "ice"
        values[3] = 42
        assert list(values)[2:4] == ["ice", 42]
        assert values.count(42) == 1
        assert values.index(True) == 5
        assert isinstance(values.format, str)
        assert values.shm.name
    finally:
        values.shm.unlink()
        values.shm.close()


def test_length_is_fixed_and_unsupported_values_or_slices_fail():
    """API 是 list-like 而非完整 list；没有 append，slice 也不创建新 ShareableList。"""

    values = shared_memory.ShareableList([1, 2, 3])
    try:
        assert len(values) == 3
        with pytest.raises(AttributeError):
            values.append(4)
        with pytest.raises(TypeError):
            _ = values[:]
        with pytest.raises(TypeError, match="type"):
            values[0] = {"not": "supported"}
    finally:
        values.shm.unlink()
        values.shm.close()


def test_string_or_bytes_replacement_cannot_exceed_slot_capacity():
    """slot 由初始 value 规划；写入失败后旧 value 保持不变。"""

    values = shared_memory.ShareableList(["short", b"bytes"])
    try:
        values[0] = "tiny"
        with pytest.raises(ValueError, match="exceeds available storage"):
            values[0] = "this replacement is much longer than the slot"
        assert values[0] == "tiny"

        with pytest.raises(ValueError, match="exceeds available storage"):
            values[1] = b"a much longer byte string"
        assert values[1] == b"bytes"
    finally:
        values.shm.unlink()
        values.shm.close()


def test_name_attachment_and_pickle_round_trip_alias_same_backing_block():
    """每个 attachment 都 close local handle，但全局 unlink 只由 owner 做一次。"""

    owner = shared_memory.ShareableList([0, 1, 2])
    attached = shared_memory.ShareableList(name=owner.shm.name)
    deserialized = pickle.loads(pickle.dumps(owner))

    try:
        attached[0] = 10
        deserialized[1] = 20

        assert list(owner) == [10, 20, 2]
        assert list(attached) == [10, 20, 2]
        assert list(deserialized) == [10, 20, 2]
    finally:
        attached.shm.close()
        deserialized.shm.close()
        owner.shm.unlink()
        owner.shm.close()
