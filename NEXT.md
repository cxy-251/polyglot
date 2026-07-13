# Current Task

ID: `python.core.representation-formatting-and-hashing`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 对象表示、格式化、字节转换与哈希协议测试套，把 ``repr`` / ``str`` / ``ascii`` / ``format`` / f-string / ``bytes`` / ``hash`` 连接到对应特殊方法，并讲清相等性与稳定哈希的约束。

## Covers

- ``__repr__()``、``repr()`` 与无 ``__str__`` 时的字符串 fallback；
- ``__str__()`` 面向用户显示与 ``str()``；
- ``ascii()`` 对 ``repr`` 中非 ASCII 字符进行转义；
- ``__format__()``、``format()`` 和 f-string format spec；
- f-string ``!s`` / ``!r`` / ``!a`` 转换先于格式化；
- f-string debug ``value=`` 语法；
- ``__bytes__()`` 与 ``bytes()``；
- 表示/格式化特殊方法必须返回严格的 str/bytes 类型；
- ``__hash__()`` 与 ``hash()``；
- 相等对象必须具有相同 hash；
- 覆盖 ``__eq__`` 后默认变为不可哈希，以及显式不可哈希 ``__hash__ = None``；
- 基于可变字段计算 hash 会破坏 dict/set 查找；
- 自定义不可变值对象同时实现 eq/hash 的正常键工作流。

## Common Pitfalls To Explain

- 认为 ``__repr__`` 必须能被 eval，或在表示中泄漏敏感信息；
- 只实现 ``__str__`` 导致容器仍显示默认 repr；
- 在 ``__format__`` 中忽略空 spec 或擅自接受未知 spec；
- 以为 f-string ``!r`` 仍调用原对象的 ``__format__``；
- ``__repr__`` / ``__str__`` 返回非字符串；
- 定义值相等却沿用身份哈希；
- 把参与 hash 的字段设为可变。

## Target File

`languages/python/core/test_014_representation_formatting_and_hashing.py`

## Official Sources

- https://docs.python.org/3.10/reference/datamodel.html#object.__repr__
- https://docs.python.org/3.10/reference/datamodel.html#object.__format__
- https://docs.python.org/3.10/reference/datamodel.html#object.__hash__
- https://docs.python.org/3.10/reference/lexical_analysis.html#formatted-string-literals
- https://docs.python.org/3.10/library/functions.html#repr
- https://docs.python.org/3.10/library/functions.html#format

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释转换顺序、严格返回类型和 hash 不变量；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--013 共十三个 Python 核心测试套已完成首轮编写；最新的 013 覆盖 decorator 求值/应用、wraps、class decorator、动态 type、metaclass 创建/调用流水线、class keyword 与元类选择冲突。全部文件按照用户要求尚未运行。下一步直接编写 014 表示、格式化与哈希协议；不要先运行 pytest。
