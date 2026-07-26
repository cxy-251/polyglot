"""线程、Worker 与进程隔离。

共同问题：并发工作运行在哪里；参数如何进入工作单元；调用方如何等待结果；
工作单元是否共享对象、地址空间或运行时状态。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/python/language/test_015_async_functions_and_protocols.py

import multiprocessing
import os
import threading


def _send_process_observation(connection, value):
    connection.send((os.getpid(), value + 1))
    connection.close()


def test_thread_runs_in_same_process_and_join_waits_for_completion():
    observations = []
    worker = threading.Thread(target=lambda: observations.append(os.getpid()))

    worker.start()
    worker.join()

    assert observations == [os.getpid()]
    assert not worker.is_alive()


def test_thread_arguments_reference_the_same_mutable_object():
    values = []
    worker = threading.Thread(target=values.append, args=(42,))

    worker.start()
    worker.join()

    assert values == [42]


def test_process_has_a_distinct_pid_and_returns_data_through_ipc():
    context = multiprocessing.get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    worker = context.Process(target=_send_process_observation, args=(sender, 41))

    worker.start()
    sender.close()
    child_pid, result = receiver.recv()
    receiver.close()
    worker.join()

    assert worker.exitcode == 0
    assert child_pid != os.getpid()
    assert result == 42


def test_process_memory_is_not_the_callers_object_graph():
    context = multiprocessing.get_context("fork")
    values = []
    worker = context.Process(target=values.append, args=(42,))

    worker.start()
    worker.join()

    assert worker.exitcode == 0
    assert values == []

    # fork 初始内容来自快照；子进程修改不会写回父进程，跨进程结果必须显式传输或共享。
