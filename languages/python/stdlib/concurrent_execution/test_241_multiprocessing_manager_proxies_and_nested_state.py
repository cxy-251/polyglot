"""241｜``multiprocessing.Manager`` server process、proxy semantics 与 nested state。

Manager referent 活在独立 server process，调用 proxy method 会 IPC；可支持任意 picklable
类型和远端共享，但通常慢于 shared memory。普通 mutable object 嵌在 proxy container 中时，
取出后原地修改只改本地 copy；要重新赋值，或从一开始嵌套另一个 managed proxy。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Manager
# polyglot-covers: python.multiprocessing.managers.SyncManager
# polyglot-covers: python.multiprocessing.manager-context-manager
# polyglot-covers: python.multiprocessing.manager-server-process
# polyglot-covers: python.multiprocessing.manager-list
# polyglot-covers: python.multiprocessing.manager-dict
# polyglot-covers: python.multiprocessing.manager-Namespace
# polyglot-covers: python.multiprocessing.manager-Queue
# polyglot-covers: python.multiprocessing.manager-Event
# polyglot-covers: python.multiprocessing.manager-Value
# polyglot-covers: python.multiprocessing.manager-Array
# polyglot-covers: python.multiprocessing.proxy-picklable
# polyglot-covers: python.multiprocessing.proxy-str-vs-repr
# polyglot-covers: python.multiprocessing.proxy-getvalue-copy
# polyglot-covers: python.multiprocessing.proxy-equality-trap
# polyglot-covers: python.multiprocessing.proxy-nested-regular-mutable-trap
# polyglot-covers: python.multiprocessing.nested-proxies
# polyglot-covers: python.multiprocessing.proxy-thread-safety-caveat

import multiprocessing


def _mutate_manager_proxies(shared_list, shared_dict, namespace, work, ready):
    shared_list.append("child")
    shared_dict["answer"] = 42
    namespace.owner = "child"
    work.put("message")
    ready.set()


def test_sync_manager_proxies_can_be_passed_to_spawned_process():
    """proxy 自身可 pickle；method call 在 manager server 执行而非复制整个 referent。"""

    context = multiprocessing.get_context("spawn")
    with multiprocessing.Manager() as manager:
        shared_list = manager.list(["parent"])
        shared_dict = manager.dict()
        namespace = manager.Namespace()
        work = manager.Queue()
        ready = manager.Event()
        number = manager.Value("i", 7)
        numbers = manager.Array("i", [1, 2, 3])
        process = context.Process(
            target=_mutate_manager_proxies,
            args=(shared_list, shared_dict, namespace, work, ready),
        )

        process.start()
        assert ready.wait(timeout=5)
        assert work.get(timeout=5) == "message"
        process.join(timeout=5)

        assert process.exitcode == 0
        assert list(shared_list) == ["parent", "child"]
        assert dict(shared_dict) == {"answer": 42}
        assert namespace.owner == "child"
        assert number.value == 7
        assert list(numbers) == [1, 2, 3]
        process.close()


def test_proxy_str_represents_referent_but_repr_and_equality_are_proxy_level():
    """显式 list(proxy) 或 _getvalue 才得到普通 list；不要依赖 proxy == referent。"""

    with multiprocessing.Manager() as manager:
        proxy = manager.list([1, 2, 3])

        assert str(proxy) == "[1, 2, 3]"
        assert "ListProxy" in repr(proxy)
        assert proxy != [1, 2, 3]

        snapshot = proxy._getvalue()
        assert snapshot == [1, 2, 3]
        snapshot.append(4)
        assert list(proxy) == [1, 2, 3]


def test_regular_mutable_nested_in_proxy_requires_reassignment():
    """list proxy 的 __getitem__ pickle 出 dict copy；本地原地修改不会自动通知 manager。"""

    with multiprocessing.Manager() as manager:
        outer = manager.list([{"count": 0}])

        local_copy = outer[0]
        local_copy["count"] = 1
        assert outer[0] == {"count": 0}

        outer[0] = local_copy
        assert outer[0] == {"count": 1}


def test_nested_managed_proxy_propagates_inner_mutation():
    """referent 可以保存另一个 picklable proxy；inner method call 直接到 inner referent。"""

    with multiprocessing.Manager() as manager:
        inner = manager.dict(count=0)
        outer = manager.list([inner])

        inner["count"] = 2

        assert outer[0]["count"] == 2
        outer[0]["count"] = 3
        assert inner["count"] == 3
