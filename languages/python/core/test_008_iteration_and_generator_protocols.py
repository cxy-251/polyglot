"""008｜迭代器、生成器与 ``yield from`` 协议的可执行示例。

iterable 能产生 iterator，iterator 则用 ``__next__`` 逐项推进并以
``StopIteration`` 表示耗尽。``for``、``iter``、``next`` 和 ``reversed``
都建立在这组协议或明确的历史序列 fallback 上。生成器把同一状态机写成含
``yield`` 的函数，并额外支持 ``send``、``throw``、``close`` 以及
``yield from`` 的双向委托。

内容基于 Python 3.10 For statement、Yield expressions、Generator-iterator
methods、Iterator types 和内置 iter/reversed。当前项目处于只编写、暂不执行
的阶段，本文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.statement.for python.statement.for-else
# polyglot-covers: python.builtin.iter python.builtin.next python.builtin.reversed
# polyglot-covers: python.protocol.__iter__ python.protocol.__next__
# polyglot-covers: python.protocol.__getitem__-iteration-fallback
# polyglot-covers: python.protocol.__reversed__ python.exception.StopIteration
# polyglot-covers: python.expression.yield python.expression.yield-from
# polyglot-covers: python.expression.generator-expression
# polyglot-covers: python.generator.send python.generator.throw
# polyglot-covers: python.generator.close python.exception.GeneratorExit

import pytest


class CountdownIterator:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        # iterator 必须返回自身，才能在已迭代一部分后继续交给 for/list 等入口。
        return self

    def __next__(self):
        if self.current < 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value


class Countdown:
    """可重复迭代的容器；每次请求都创建独立 iterator。"""

    def __init__(self, start):
        self.start = start

    def __iter__(self):
        return CountdownIterator(self.start)


def test_iterable_creates_iterators_while_iterator_returns_itself():
    """容器与 iterator 是不同角色，不应因都能传给 ``iter`` 而混淆。"""

    countdown = Countdown(2)
    first = iter(countdown)
    second = iter(countdown)

    assert first is not second
    assert iter(first) is first
    assert next(first) == 2
    assert next(first) == 1
    assert next(second) == 2

    # iterable 可以创建多条独立遍历；iterator 保存单条遍历的当前位置。把容器
    # 自身同时当 iterator 往往会让嵌套循环意外共享状态。


def test_next_uses_stop_iteration_or_returns_an_explicit_default():
    """``next`` 推进一项；耗尽时可抛异常，也可返回调用者提供的默认值。"""

    iterator = iter(["only"])

    assert next(iterator) == "only"
    assert next(iterator, "finished") == "finished"

    with pytest.raises(StopIteration):
        next(iterator)

    # 耗尽的 iterator 不会自动重置。next 的 default 也不写回任何状态；后续
    # 不带 default 的调用仍然抛 StopIteration。


def test_for_loop_repeatedly_calls_iterator_until_stop_iteration():
    """``for`` 隐式取得 iterator，并把每次 ``next`` 的值绑定给目标。"""

    visited = []

    for value in Countdown(3):
        visited.append(value)

    assert visited == [3, 2, 1, 0]


def test_for_else_runs_only_when_loop_finishes_without_break():
    """循环 ``else`` 表示“未被 break 提前终止”，不是普通条件的 else。"""

    events = []

    for value in [1, 2, 3]:
        if value == 2:
            events.append("found")
            break
    else:
        events.append("not-found")

    assert events == ["found"]

    for value in [1, 2, 3]:
        if value == 9:
            break
    else:
        events.append("not-found")

    assert events == ["found", "not-found"]


def test_two_argument_iter_calls_until_the_sentinel_value():
    """``iter(callable, sentinel)`` 将无参调用包装为 iterator。"""

    responses = ["header", "body", "", "unread"]

    def read_chunk():
        return responses.pop(0)

    chunks = list(iter(read_chunk, ""))

    assert chunks == ["header", "body"]
    assert responses == ["unread"]

    # sentinel 通过相等比较识别且不包含在输出中；一旦遇到它，callable 不会
    # 再被调用。读取固定块、消息队列等接口可用这种形式消除手写 while。


class LegacySequence:
    """只实现从零开始的 ``__getitem__``，展示历史迭代 fallback。"""

    def __init__(self, items):
        self.items = list(items)
        self.requested_indices = []

    def __getitem__(self, index):
        self.requested_indices.append(index)
        if index >= len(self.items):
            raise IndexError
        return self.items[index]


def test_iteration_falls_back_to_getitem_with_increasing_indices():
    """缺少 ``__iter__`` 时，旧式序列可由连续整数索引参与迭代。"""

    sequence = LegacySequence(["a", "b", "c"])

    assert list(sequence) == ["a", "b", "c"]
    assert sequence.requested_indices == [0, 1, 2, 3]

    # 最后一个越界请求必须抛 IndexError，迭代机制才知道结束。新的自定义容器
    # 应优先显式实现 __iter__；这个 fallback 主要解释旧协议兼容行为。


def test_setting_iter_to_none_explicitly_disables_sequence_fallback():
    """``__iter__ = None`` 表示不可迭代，不会继续尝试 ``__getitem__``。"""

    class DeliberatelyNotIterable(LegacySequence):
        __iter__ = None

    value = DeliberatelyNotIterable([1, 2, 3])

    with pytest.raises(TypeError):
        iter(value)

    assert value.requested_indices == []


class CustomReversed:
    def __init__(self, items):
        self.items = list(items)
        self.calls = []

    def __reversed__(self):
        self.calls.append("__reversed__")
        return iter(("custom", *self.items[::-1]))


def test_reversed_prefers_the_reversed_protocol():
    """类型可用 ``__reversed__`` 提供比通用索引 fallback 更合适的实现。"""

    values = CustomReversed([1, 2, 3])

    assert list(reversed(values)) == ["custom", 3, 2, 1]
    assert values.calls == ["__reversed__"]


class ReversibleSequenceFallback:
    def __init__(self, items):
        self.items = list(items)
        self.indices = []

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        self.indices.append(index)
        return self.items[index]


def test_reversed_falls_back_to_len_and_integer_getitem():
    """缺少 ``__reversed__`` 时，序列协议可从最后一个索引向前读取。"""

    values = ReversibleSequenceFallback(["a", "b", "c"])

    assert list(reversed(values)) == ["c", "b", "a"]
    assert values.indices == [2, 1, 0]


def test_calling_a_generator_function_does_not_execute_its_body_yet():
    """含 ``yield`` 的函数调用先创建 generator，首次推进才开始执行。"""

    events = []

    def stages():
        events.append("started")
        yield "syntax"
        events.append("resumed")
        yield "protocol"
        events.append("finished")

    generator = stages()

    assert events == []
    assert iter(generator) is generator

    assert next(generator) == "syntax"
    assert events == ["started"]

    assert next(generator) == "protocol"
    assert events == ["started", "resumed"]

    with pytest.raises(StopIteration):
        next(generator)

    assert events == ["started", "resumed", "finished"]

    with pytest.raises(StopIteration):
        next(generator)

    # generator 同时也是单次 iterator。耗尽后继续保持关闭状态，不会重新从
    # 函数开头执行；需要再次遍历时必须重新调用生成器函数。


def test_generator_expression_evaluates_outer_iterable_now_but_items_lazily():
    """生成器表达式立即取得最外层 iterable，转换工作则按需执行。"""

    events = []

    def source():
        events.append("source-created")
        return [1, 2, 3]

    def transform(value):
        events.append(("transformed", value))
        return value * 10

    values = (transform(value) for value in source())

    assert events == ["source-created"]
    assert next(values) == 10
    assert events == ["source-created", ("transformed", 1)]
    assert list(values) == [20, 30]

    # 常见坑：生成器表达式是惰性的，但不是“整条表达式什么都不做”。最外层
    # for 的 iterable 在创建 generator 时就求值，后续迭代和结果表达式才延迟。


def test_generator_expression_loop_variable_does_not_leak_outward():
    """生成器表达式拥有自己的隐式作用域，不覆盖外层同名变量。"""

    item = "outer"
    values = (item.upper() for item in ["a", "b"])

    assert list(values) == ["A", "B"]
    assert item == "outer"


def test_send_supplies_the_value_of_a_suspended_yield_expression():
    """``send`` 既恢复 generator，也让当前 ``yield`` 表达式得到一个值。"""

    def accumulator():
        total = 0
        while True:
            amount = yield total
            if amount is None:
                return total
            total += amount

    generator = accumulator()

    assert next(generator) == 0
    assert generator.send(5) == 5
    assert generator.send(3) == 8

    with pytest.raises(StopIteration) as finished:
        generator.send(None)

    assert finished.value.value == 8

    # send(value) 的返回值是 generator 下一次 yield 出来的值；子生成器的
    # return value 则放在最终 StopIteration.value 中，两者不是同一个方向。


def test_new_generator_must_be_started_with_next_or_send_none():
    """尚未运行到首个 ``yield`` 时，没有 yield 表达式可接收非 None 值。"""

    def receiver():
        received = yield "ready"
        yield received

    generator = receiver()

    with pytest.raises(TypeError):
        generator.send("too early")

    assert generator.send(None) == "ready"
    assert generator.send("now accepted") == "now accepted"


def test_throw_raises_at_the_suspension_point_and_can_be_handled():
    """``throw`` 把异常注入当前暂停位置，generator 可在内部捕获并继续。"""

    def resilient_worker():
        try:
            yield "ready"
        except ValueError as error:
            yield f"handled: {error}"
        yield "done"

    worker = resilient_worker()

    assert next(worker) == "ready"
    assert worker.throw(ValueError("bad input")) == "handled: bad input"
    assert next(worker) == "done"

    with pytest.raises(StopIteration):
        next(worker)


def test_close_injects_generator_exit_and_runs_cleanup():
    """``close`` 在暂停点抛 ``GeneratorExit``，从而执行清理逻辑。"""

    events = []

    def managed_resource():
        try:
            events.append("opened")
            yield "resource"
        except GeneratorExit:
            events.append("generator-exit")
            raise
        finally:
            events.append("closed")

    resource = managed_resource()

    assert next(resource) == "resource"
    resource.close()

    assert events == ["opened", "generator-exit", "closed"]

    with pytest.raises(StopIteration):
        next(resource)

    # 捕获 GeneratorExit 后应重新抛出或正常返回，不能再 yield 值；忽略关闭请求
    # 并继续产出会让 close 以 RuntimeError 失败。


def test_yield_from_delegates_send_and_captures_subgenerator_return_value():
    """``yield from`` 双向连接调用者和子生成器，并接收其 ``return``。"""

    def child():
        received = yield "child-ready"
        yield f"child-received:{received}"
        return 42

    def parent():
        child_result = yield from child()
        yield f"child-returned:{child_result}"

    generator = parent()

    assert next(generator) == "child-ready"
    assert generator.send("payload") == "child-received:payload"
    assert next(generator) == "child-returned:42"

    with pytest.raises(StopIteration):
        next(generator)

    # 手写 for value in child(): yield value 只能转发产出值；yield from 还负责
    # send/throw/close 通道，并把子生成器的 StopIteration.value 变成表达式值。


def test_explicit_stop_iteration_inside_generator_becomes_runtime_error():
    """生成器函数体不能用直接抛 ``StopIteration`` 伪装正常 ``return``。"""

    def incorrect_generator():
        yield "started"
        raise StopIteration("do not exit generators this way")

    generator = incorrect_generator()
    assert next(generator) == "started"

    with pytest.raises(RuntimeError, match="generator raised StopIteration") as error:
        next(generator)

    assert isinstance(error.value.__cause__, StopIteration)

    # Python 会把意外逸出的 StopIteration 转成 RuntimeError，避免它被外层
    # for 误判成正常耗尽。需要结束并携带结果时应写 return result。
