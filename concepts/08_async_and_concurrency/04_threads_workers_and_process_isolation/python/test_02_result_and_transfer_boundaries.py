"""并发结果、异常与数据传输边界。

共同问题：工作单元失败如何回到调用方；普通对象是共享、复制还是序列化；
所有者如何确认工作单元已经结束。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/python/stdlib/088-094_concurrent_execution/
# polyglot-related+: test_092_concurrent_futures_complete_states_waiting_thread_and_process_pools.py

from concurrent.futures import ThreadPoolExecutor
import multiprocessing

import pytest


def _mutate_and_send(connection, payload):
    payload.append(3)
    connection.send(payload)
    connection.close()


def test_thread_pool_future_rethrows_worker_exception_to_owner():
    failure = RuntimeError("worker failed")

    def fail():
        raise failure

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(fail)

        with pytest.raises(RuntimeError) as caught:
            result.result()

    assert caught.value is failure


def test_process_pipe_serializes_value_instead_of_sharing_list_identity():
    context = multiprocessing.get_context("fork")
    original = [1, 2]
    receiver, sender = context.Pipe(duplex=False)
    worker = context.Process(target=_mutate_and_send, args=(sender, original))

    worker.start()
    sender.close()
    transferred = receiver.recv()
    receiver.close()
    worker.join()

    assert worker.exitcode == 0
    assert transferred == [1, 2, 3]
    assert original == [1, 2]

    # fork 初始内存快照与 Pipe pickle 都不共享 list identity；需要共享状态时必须选用
    # multiprocessing.Value/Array/shared_memory 并定义同步。
