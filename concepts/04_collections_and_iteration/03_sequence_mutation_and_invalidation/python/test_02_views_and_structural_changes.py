"""视图、复制与结构修改边界。

共同问题：派生对象是独立副本还是共享视图；哪些修改保持现有游标有效；
安全删除循环应基于什么稳定观察。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/python/builtins/test_022_binary_sequences.py
# polyglot-related: languages/python/builtins/test_024_mapping_dict.py


def test_list_slice_is_copy_but_memoryview_is_shared():
    values = [1, 2, 3]
    copied = values[1:]
    storage = bytearray(b"abc")
    view = memoryview(storage)[1:]

    copied[0] = 9
    view[0] = ord("z")

    assert values == [1, 2, 3]
    assert storage == bytearray(b"azc")
    view.release()


def test_dictionary_value_replacement_keeps_size_iterator_usable():
    mapping = {"a": 1, "b": 2}
    iterator = iter(mapping)

    assert next(iterator) == "a"
    mapping["b"] = 20

    assert list(iterator) == ["b"]
    assert mapping["b"] == 20

    # CPython 的 dict iterator 检测 size 变化；替换已有值不改变键集合。业务代码仍不应
    # 把实现的遍历次序细节推广成所有映射迭代器的修改契约。


def test_collect_then_delete_uses_a_stable_key_snapshot():
    mapping = {"keep": 1, "drop": 0}
    keys_to_delete = [key for key, value in mapping.items() if value == 0]

    for key in keys_to_delete:
        del mapping[key]

    assert mapping == {"keep": 1}
