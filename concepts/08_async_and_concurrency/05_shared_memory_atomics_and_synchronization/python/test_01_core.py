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


def test_python_has_no_language_level_atomic_number_type():
    assert not hasattr(threading, "AtomicInteger")

    # 锁是这里可移植的复合操作边界；不要把 GIL 当作用户数据的通用原子性契约。
