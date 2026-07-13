# Current Task

ID: `python.builtins.introspection-and-attribute-functions`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 对象身份、类型检查、可调用判断、属性访问和内省类内置函数测试套，集中展示 `object`、`id`、`type`、`isinstance` / `issubclass`、`callable`、`getattr` / `hasattr` / `setattr` / `delattr`、`vars` / `dir`，并补充 `property` / `classmethod` / `staticmethod` 的实际类接口用法。

## Covers

- `object()` 作为唯一 sentinel、默认 identity equality/hash 和无实例属性；
- `id()` 与 `is` 的关系、别名/相等对象差异和仅限对象生命周期的保证；
- `type(obj)` 精确类型与 `isinstance()` 继承判断的区别；
- `isinstance` / `issubclass` 接受类型 tuple 和 Python 3.10 union type；
- `callable()` 对函数、类、实现 `__call__` 的实例，以及“可调用不等于无参可调用”；
- `getattr()` 默认值、动态属性名和 `AttributeError`；
- `hasattr()` 会执行属性访问、只把 `AttributeError` 当作不存在；
- `setattr()` / `delattr()` 与描述符/动态名字；
- `vars()` 的无参数形式、实例 `__dict__`、类 mappingproxy 和 slots 边界；
- `dir()` 的排序、定制 `__dir__` 和“便于交互而非完整权威清单”的定位；
- property getter/setter/deleter 和验证；
- classmethod 接收实际子类并适合作为替代构造器；
- staticmethod 不绑定 self/cls 的命名空间工具语义；
- 与 007/011/013 已有描述符、类构造、super/metaclass 内容交叉引用而不机械重写。

## Common Pitfalls To Explain

- 用 `type(x) is Base` 拒绝合法子类，而本意是接受协议/继承关系；
- 把 `id()` 当永久业务 ID、内存地址或跨进程标识；
- 认为 `callable(x)` 保证 `x()` 无参数调用成功；
- 认为 `hasattr()` 无副作用或会吞掉属性代码中的任意异常；
- 修改 `vars()` / `locals()` 结果并期待局部变量可靠改变；
- 把 `dir()` 当对象所有动态属性的完整机器清单；
- 忘记 classmethod 在子类上接收子类，而 staticmethod 不接收隐式参数。

## Target File

`languages/python/builtins/test_027_introspection_and_attribute_functions.py`

## Official Sources

- https://docs.python.org/3.10/library/functions.html#object
- https://docs.python.org/3.10/library/functions.html#id
- https://docs.python.org/3.10/library/functions.html#type
- https://docs.python.org/3.10/library/functions.html#isinstance
- https://docs.python.org/3.10/library/functions.html#issubclass
- https://docs.python.org/3.10/library/functions.html#callable
- https://docs.python.org/3.10/library/functions.html#getattr
- https://docs.python.org/3.10/library/functions.html#hasattr
- https://docs.python.org/3.10/library/functions.html#setattr
- https://docs.python.org/3.10/library/functions.html#delattr
- https://docs.python.org/3.10/library/functions.html#vars
- https://docs.python.org/3.10/library/functions.html#dir
- https://docs.python.org/3.10/library/functions.html#property
- https://docs.python.org/3.10/library/functions.html#classmethod
- https://docs.python.org/3.10/library/functions.html#staticmethod

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释解释 identity/业务 ID、精确类型/继承、属性访问副作用；
- 自定义类只实现当前内省行为所需的最小接口；
- 与 002、007、011、013 的协议与类机制文件避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--026 位于 `builtins/`，编号在整个 Python 树全局连续。026 迭代与聚合内置函数已完成首轮编写，尚未运行。下一步直接编写 027 内省与属性内置函数；不要先运行 pytest。
