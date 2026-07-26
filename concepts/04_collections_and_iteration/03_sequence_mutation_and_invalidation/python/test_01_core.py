"""序列修改与失效。

共同问题：修改容器后迭代器和视图是否仍有效；遍历期间修改会发生什么；
哪些结构能检测不安全的结构变化。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/python/builtins/test_023_general_sequence_types.py
# polyglot-related: languages/python/builtins/test_024_mapping_dict.py

import pytest


def test_list_iterator_observes_appends_because_it_tracks_an_index():
    values = [1, 2]
    iterator = iter(values)

    assert next(iterator) == 1
    values.append(3)
    assert list(iterator) == [2, 3]

    # 结果虽有定义，遍历时修改 list 往往跳过或重复业务元素，不应当作通用工作流。


def test_dictionary_iterator_rejects_size_change():
    mapping = {"a": 1}
    iterator = iter(mapping)
    assert next(iterator) == "a"

    mapping["b"] = 2

    with pytest.raises(RuntimeError, match="changed size"):
        next(iterator)


def test_memoryview_shares_bytes_and_blocks_resizing_exporter():
    storage = bytearray(b"abc")
    view = memoryview(storage)

    view[0] = ord("z")
    assert storage == bytearray(b"zbc")

    with pytest.raises(BufferError):
        storage.append(ord("d"))

    view.release()
    storage.append(ord("d"))
    assert storage == bytearray(b"zbcd")


def test_copy_before_mutation_provides_a_stable_iteration_snapshot():
    values = [1, 2, 3]

    for value in values.copy():
        if value % 2:
            values.remove(value)

    assert values == [2]

