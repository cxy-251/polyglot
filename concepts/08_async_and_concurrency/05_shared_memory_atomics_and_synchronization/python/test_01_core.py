"""共享内存、原子操作与同步。

共同问题：并发工作如何共享状态；互斥和条件通知保证什么；是否提供原子读改写；
消息传递与共享内存的边界在哪里。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/python/stdlib/088-094_concurrent_execution/
# polyglot-related+: test_088_threading_complete_threads_locks_coordination_introspection_and_low_level_api.py

import multiprocessing
import threading


def _increment_shared_value(value, lock):
    with lock:
        value.value += 1


def test_lock_protects_a_shared_thread_counter():
    counter = [0]
    lock = threading.Lock()

    def increment():
        for _ in range(500):
            with lock:
                counter[0] += 1

    workers = [threading.Thread(target=increment) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert counter == [1000]


def test_condition_wait_uses_a_predicate_and_notification():
    condition = threading.Condition()
    ready = False
    observations = []

    def observe():
        with condition:
            condition.wait_for(lambda: ready)
            observations.append("ready")

    worker = threading.Thread(target=observe)
    worker.start()
    with condition:
        ready = True
        condition.notify()
    worker.join()

    assert observations == ["ready"]


def test_processes_require_explicit_shared_storage_and_locking():
    context = multiprocessing.get_context("fork")
    value = context.Value("i", 0, lock=False)
    lock = context.Lock()
    workers = [
        context.Process(target=_increment_shared_value, args=(value, lock))
        for _ in range(2)
    ]

    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert [worker.exitcode for worker in workers] == [0, 0]
    assert value.value == 2


def test_lock_defines_the_atomic_boundary_for_a_compound_update():
    value = [0]
    lock = threading.Lock()

    with lock:
        before = value[0]
        value[0] = before + 1

    assert value == [1]

    # CPython 3.10 的 GIL 是解释器执行机制，不是用户数据的读改写契约；锁明确覆盖
    # 读取、计算和写回，代码也不会依赖不存在的“原子整数”API 名称。
