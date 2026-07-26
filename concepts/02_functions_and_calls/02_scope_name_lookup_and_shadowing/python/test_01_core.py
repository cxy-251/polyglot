"""作用域、名称查找与遮蔽。

共同问题：块是否创建作用域；内层绑定如何遮蔽外层名称；函数如何修改外层状态；
读取尚未初始化的局部名称在何处失败。
"""

# polyglot-family: functions_and_calls
# polyglot-concept: scope_name_lookup_and_shadowing
# polyglot-related: languages/python/language/test_012_names_scopes_and_closures.py

import pytest


module_label = "module"


def test_if_block_does_not_create_a_python_scope():
    if True:
        block_value = "visible"

    assert block_value == "visible"


def test_local_binding_shadows_global_without_changing_it():
    def read_local():
        module_label = "local"
        return module_label

    assert read_local() == "local"
    assert module_label == "module"


def test_global_and_nonlocal_choose_an_existing_outer_binding():
    state = "outer"

    def update_nonlocal():
        nonlocal state
        state = "changed"

    update_nonlocal()
    assert state == "changed"

    # `global` 指模块命名空间，`nonlocal` 指最近的封闭函数绑定；C++/JavaScript 没有同一组声明。


def test_assignment_makes_a_name_local_for_the_whole_function_body():
    value = "outer"

    def invalid_read_then_assign():
        result = value
        value = "local"
        return result

    with pytest.raises(UnboundLocalError):
        invalid_read_then_assign()


def test_comprehension_target_does_not_leak_into_enclosing_scope():
    item = "outside"
    values = [item * 2 for item in range(3)]

    assert values == [0, 2, 4]
    assert item == "outside"

