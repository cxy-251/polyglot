"""247｜``SharedMemoryManager`` ownership、managed blocks/lists 与 automatic unlink。

SharedMemoryManager 启动专用 process 跟踪由它创建的 blocks。context exit 会对所有 tracked
SharedMemory/ShareableList backing blocks 调 unlink，再关闭 manager；这适合集中 ownership，
避免多个 worker 争抢谁最后 unlink。返回对象仍是直接 shared-memory handle，不是 RPC proxy。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.managers.SharedMemoryManager
# polyglot-covers: python.multiprocessing.SharedMemoryManager.start
# polyglot-covers: python.multiprocessing.SharedMemoryManager.shutdown
# polyglot-covers: python.multiprocessing.SharedMemoryManager-context-manager
# polyglot-covers: python.multiprocessing.SharedMemoryManager.SharedMemory
# polyglot-covers: python.multiprocessing.SharedMemoryManager.ShareableList
# polyglot-covers: python.multiprocessing.SharedMemoryManager-tracks-lifecycle
# polyglot-covers: python.multiprocessing.SharedMemoryManager-automatic-unlink
# polyglot-covers: python.multiprocessing.SharedMemoryManager-direct-memory-handle

from multiprocessing.managers import SharedMemoryManager
from multiprocessing import shared_memory

import pytest


def test_manager_context_creates_direct_handles_and_unlinks_them_on_exit():
    """先 close 当前 process handles；manager exit 负责唯一的 unlink ownership。"""

    with SharedMemoryManager() as manager:
        block = manager.SharedMemory(size=16)
        values = manager.ShareableList([1, 2, 3])
        block_name = block.name
        list_name = values.shm.name

        block.buf[:4] = b"data"
        values[1] = 20

        assert bytes(block.buf[:4]) == b"data"
        assert list(values) == [1, 20, 3]
        assert isinstance(block, shared_memory.SharedMemory)
        assert isinstance(values, shared_memory.ShareableList)

        block.close()
        values.shm.close()

    with pytest.raises(FileNotFoundError):
        shared_memory.SharedMemory(name=block_name)
    with pytest.raises(FileNotFoundError):
        shared_memory.ShareableList(name=list_name)


def test_explicit_start_and_shutdown_release_all_tracked_blocks():
    """不用 with 时必须把 shutdown 放在 finally；它同时停止 manager child。"""

    manager = SharedMemoryManager()
    manager.start()
    block = manager.SharedMemory(size=8)
    name = block.name

    try:
        block.buf[:] = b"12345678"
        assert bytes(block.buf) == b"12345678"
        block.close()
    finally:
        manager.shutdown()

    with pytest.raises(FileNotFoundError):
        shared_memory.SharedMemory(name=name)
