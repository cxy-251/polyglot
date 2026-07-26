"""闭包捕获与生命周期。

共同问题：闭包捕获绑定还是值；循环创建的函数看到哪个变量；捕获状态能否修改；
外层调用结束后状态是否仍存活。
"""

# polyglot-family: functions_and_calls
# polyglot-concept: closures_capture_and_lifetime
# polyglot-related: languages/python/language/test_012_names_scopes_and_closures.py


def test_closure_keeps_enclosing_state_alive_after_return():
    def make_counter():
        count = 0

        def increment():
            nonlocal count
            count += 1
            return count

        return increment

    counter = make_counter()

    assert counter() == 1
    assert counter() == 2


def test_loop_closures_share_one_late_bound_name():
    functions = [lambda: index for index in range(3)]

    assert [function() for function in functions] == [2, 2, 2]


def test_default_argument_can_snapshot_each_iteration_value():
    functions = [lambda index=index: index for index in range(3)]

    assert [function() for function in functions] == [0, 1, 2]


def test_each_factory_call_creates_an_independent_cell():
    def make_box(initial):
        value = initial

        def exchange(replacement):
            nonlocal value
            previous = value
            value = replacement
            return previous

        return exchange

    first = make_box("a")
    second = make_box("x")

    assert first("b") == "a"
    assert first("c") == "b"
    assert second("y") == "x"

