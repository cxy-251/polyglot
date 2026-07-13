# Current Task

ID: `python.core.attribute-access-and-descriptors`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 属性访问与描述符协议测试套，把点号访问、内置属性函数、实例/类命名空间和 descriptor 分派连接到对应特殊方法，并清楚展示 data descriptor、实例属性与 non-data descriptor 的优先级。

## Covers

- 实例属性、类属性、实例遮蔽与删除后回退；
- ``getattr()``、``setattr()``、``delattr()``、``hasattr()``；
- ``__getattribute__()`` 拦截所有读取，``__getattr__()`` 只处理正常查找失败；
- ``__setattr__()``、``__delattr__()`` 与使用 ``object`` 基础实现避免递归；
- ``__get__()``、``__set__()``、``__delete__()``、``__set_name__()``；
- data descriptor > instance dictionary > non-data descriptor > class variable 的查找优先级；
- 函数作为 non-data descriptor 形成绑定方法；
- ``property`` 的 getter/setter/deleter 正常工作流；
- ``__slots__`` 对实例存储和 ``__dict__`` 的影响；
- 属性钩子中吞掉或误用 ``AttributeError`` 的常见后果。

## Common Pitfalls To Explain

- 在 ``__getattribute__`` 或 ``__setattr__`` 中再次使用普通点号访问导致无限递归；
- 以为 ``__getattr__`` 会在每次属性读取时调用；
- 以为实例属性总能遮蔽类上的 descriptor；
- 让 property getter 内部意外抛出 ``AttributeError``，导致 ``hasattr`` 把真实错误当成“不存在”；
- 以为定义 ``__slots__`` 后所有继承层级都自动禁止 ``__dict__``。

## Target File

`languages/python/core/test_attribute_access_and_descriptors.py`

## Official Sources

- https://docs.python.org/3.10/reference/expressions.html#attribute-references
- https://docs.python.org/3.10/reference/datamodel.html#customizing-attribute-access
- https://docs.python.org/3.10/reference/datamodel.html#implementing-descriptors
- https://docs.python.org/3.10/howto/descriptor.html
- https://docs.python.org/3.10/library/functions.html#getattr
- https://docs.python.org/3.10/library/functions.html#property

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释属性查找优先级和常见坑；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

真假值、比较、二元运算、一元与转换、订阅切片、函数调用共六个测试套已完成首轮编写，但按照用户要求尚未运行。下一步直接编写属性访问与描述符测试套；不要先运行 pytest。
