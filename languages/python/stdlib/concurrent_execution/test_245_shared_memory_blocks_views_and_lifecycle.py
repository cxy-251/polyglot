"""245｜``SharedMemory`` create/attach、memoryview alias 与 close/unlink lifecycle。

SharedMemory 用 name 让不同 process attach 同一 volatile bytes。``close`` 只关闭本 object
handle，``unlink`` 才请求销毁全局 block，而且所有参与者中只调用一次。``buf`` 是 live
memoryview，close 前必须释放外部 view；否则 exported pointers 会触发 BufferError。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.shared_memory
# polyglot-covers: python.multiprocessing.shared_memory.SharedMemory
# polyglot-covers: python.multiprocessing.SharedMemory-create
# polyglot-covers: python.multiprocessing.SharedMemory-attach-by-name
# polyglot-covers: python.multiprocessing.SharedMemory-generated-name
# polyglot-covers: python.multiprocessing.SharedMemory-size
# polyglot-covers: python.multiprocessing.SharedMemory-buf
# polyglot-covers: python.multiprocessing.SharedMemory-memoryview-alias
# polyglot-covers: python.multiprocessing.SharedMemory-close
# polyglot-covers: python.multiprocessing.SharedMemory-unlink-once
# polyglot-covers: python.multiprocessing.SharedMemory-close-does-not-unlink
# polyglot-covers: python.multiprocessing.SharedMemory-duplicate-name-error
# polyglot-covers: python.multiprocessing.SharedMemory-missing-attach-error
# polyglot-covers: python.multiprocessing.SharedMemory-release-exported-views

import multiprocessing
from multiprocessing import shared_memory

import pytest


def _modify_named_shared_memory(name):
    attached = shared_memory.SharedMemory(name=name)
    try:
        attached.buf[:5] = b"child"
    finally:
        attached.close()


def test_two_attachments_alias_same_bytes_and_size_is_ignored_on_attach():
    """request 16 bytes，实际 size 可因 page allocation 更大；attach 的 size=1 被忽略。"""

    owner = shared_memory.SharedMemory(create=True, size=16)
    attached = None
    try:
        assert isinstance(owner.name, str)
        assert owner.name
        assert owner.size >= 16
        assert isinstance(owner.buf, memoryview)

        owner.buf[:5] = b"hello"
        attached = shared_memory.SharedMemory(
            name=owner.name,
            create=False,
            size=1,
        )
        assert attached.size == owner.size
        assert bytes(attached.buf[:5]) == b"hello"

        attached.buf[:5] = b"world"
        assert bytes(owner.buf[:5]) == b"world"
    finally:
        if attached is not None:
            attached.close()
        owner.unlink()
        owner.close()


def test_spawned_process_attaches_by_name_and_mutates_without_pickle_copy():
    """child 只接收短 name；payload 不经过 Pipe/Queue serialization。"""

    owner = shared_memory.SharedMemory(create=True, size=8)
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=_modify_named_shared_memory, args=(owner.name,))

    try:
        owner.buf[:5] = b"start"
        process.start()
        process.join(timeout=5)

        assert process.exitcode == 0
        assert bytes(owner.buf[:5]) == b"child"
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        process.close()
        owner.unlink()
        owner.close()


def test_close_drops_one_handle_but_existing_attachment_keeps_block_accessible():
    """最后由仍存活的 attachment unlink；不要把 close 当作全局 delete。"""

    owner = shared_memory.SharedMemory(create=True, size=4)
    name = owner.name
    attached = shared_memory.SharedMemory(name=name)
    owner.buf[:] = b"data"

    owner.close()
    try:
        assert bytes(attached.buf) == b"data"
        third = shared_memory.SharedMemory(name=name)
        third.close()
    finally:
        attached.unlink()
        attached.close()

    with pytest.raises(FileNotFoundError):
        shared_memory.SharedMemory(name=name)


def test_duplicate_name_and_nonpositive_create_size_are_rejected():
    """create=True 是 exclusive allocation；已有 name 不会被悄悄复用或覆盖。"""

    owner = shared_memory.SharedMemory(create=True, size=1)
    try:
        with pytest.raises(FileExistsError):
            shared_memory.SharedMemory(name=owner.name, create=True, size=1)
    finally:
        owner.unlink()
        owner.close()

    with pytest.raises(ValueError, match="size must be a positive number"):
        shared_memory.SharedMemory(create=True, size=0)


def test_external_memoryview_must_be_released_before_shared_memory_close():
    """切片 view 也导出 pointer；release 后 SharedMemory.close 才能安全 unmap。"""

    owner = shared_memory.SharedMemory(create=True, size=8)
    view = owner.buf[2:6]

    try:
        view[:] = b"view"
        assert bytes(owner.buf) == b"\x00\x00view\x00\x00"
        with pytest.raises(BufferError, match="exported pointers"):
            owner.close()
    finally:
        view.release()
        owner.unlink()
        owner.close()
