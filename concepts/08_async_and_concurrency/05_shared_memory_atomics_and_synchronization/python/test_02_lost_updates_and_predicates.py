"""丢失更新、条件谓词与同步边界。

共同问题：运行时锁是否自动保护复合操作；条件通知能否替代状态谓词；
发布数据需要哪一个明确同步点。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/python/stdlib/088-094_concurrent_execution/
# polyglot-related+: test_088_threading_complete_threads_locks_coordination_introspection_and_low_level_api.py

import threading


def test_coordinated_read_then_write_loses_an_update_without_a_lock():
    value = [0]
    both_read = threading.Barrier(2)

    def increment():
        observed = value[0]
        both_read.wait()
        value[0] = observed + 1

    workers = [threading.Thread(target=increment) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert value == [1]

    # Barrier 强制两个线程先读同一个旧值再写回；即使 CPython 有 GIL，跨多个操作的
    # 读改写仍会丢失更新。生产代码应以 Lock 包围完整不变量。


def test_condition_rechecks_false_notification_before_proceeding():
    condition = threading.Condition()
    ready = False
    first_check = threading.Event()
    second_check = threading.Event()
    checks = 0
    events = []

    def predicate():
        nonlocal checks
        checks += 1
        if checks == 1:
            first_check.set()
        elif checks == 2:
            second_check.set()
        return ready

    def observe():
        with condition:
            condition.wait_for(predicate)
            events.append("ready")

    worker = threading.Thread(target=observe)
    worker.start()
    first_check.wait()

    with condition:
        condition.notify()
    second_check.wait()
    assert events == []

    with condition:
        ready = True
        condition.notify()
    worker.join()

    assert events == ["ready"]
    assert checks >= 3
