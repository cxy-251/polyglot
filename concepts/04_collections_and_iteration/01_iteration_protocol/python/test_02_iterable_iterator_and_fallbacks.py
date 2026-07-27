"""可迭代对象、迭代器与协议 fallback。

共同问题：容器与单次游标如何区分；每次取得迭代器是否共享状态；
缺少主要协议入口时是否存在兼容 fallback。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/python/language/test_008_iteration_and_generator_protocols.py


def test_iterator_returns_itself_but_container_returns_fresh_iterators():
    values = [1, 2]
    first = iter(values)
    second = iter(values)

    assert iter(first) is first
    assert first is not second
    assert next(first) == 1
    assert next(second) == 1


def test_iter_uses_legacy_getitem_fallback_until_index_error():
    calls = []

    class LegacySequence:
        def __getitem__(self, index):
            calls.append(index)
            if index >= 3:
                raise IndexError
            return index * 10

    assert list(LegacySequence()) == [0, 10, 20]
    assert calls == [0, 1, 2, 3]

    # Python 在没有 __iter__ 时可从整数索引 0 开始兼容旧序列；C++ range 和
    # JavaScript Symbol.iterator 没有对应的隐式索引 fallback。
