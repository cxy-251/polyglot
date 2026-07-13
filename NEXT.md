# Current Task

ID: `python.core.decorators-and-metaclasses`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 函数/类装饰器与元类测试套，展示装饰器表达式求值和应用顺序、包装函数元数据、class 创建流水线、``__prepare__`` / metaclass ``__new__`` / ``__init__`` / ``__call__`` 以及元类选择与冲突。

## Covers

- 函数装饰器接收并替换函数对象；
- 多层装饰器表达式从上到下求值、从下到上应用；
- 带参数 decorator factory 的配置时机；
- 包装器转发 ``*args`` / ``**kwargs`` 与返回值/异常；
- ``functools.wraps`` / ``update_wrapper`` 保留名称、文档、注解和 ``__wrapped__``；
- 类装饰器在类创建后接收并替换类对象；
- ``type(name, bases, namespace)`` 动态创建类；
- metaclass ``__prepare__`` 提供类体命名空间；
- metaclass ``__new__`` 与 ``__init__`` 创建/初始化类对象；
- metaclass ``__call__`` 包围实例的 ``__new__`` / ``__init__``；
- 派生类的元类必须兼容所有基类元类，以及元类冲突；
- 类关键字流向 metaclass 与 ``__init_subclass__`` 的边界；
- decorator/metaclass 中返回错误对象导致绑定语义改变的风险。

## Common Pitfalls To Explain

- 以为多装饰器按书写顺序从上到下包裹；
- wrapper 忘记 return 原函数结果或不接受完整参数；
- 不用 ``functools.wraps`` 导致名称、文档、签名跟踪信息丢失；
- decorator factory 在定义时执行而非每次调用时执行；
- metaclass ``__new__`` 忘记调用/返回 ``super().__new__``；
- 把 metaclass ``__call__`` 与实例 ``__call__`` 混为一谈；
- 多继承时忽略元类兼容关系。

## Target File

`languages/python/core/test_013_decorators_and_metaclasses.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#function-definitions
- https://docs.python.org/3.10/reference/compound_stmts.html#class-definitions
- https://docs.python.org/3.10/reference/datamodel.html#customizing-class-creation
- https://docs.python.org/3.10/library/functools.html#functools.wraps
- https://docs.python.org/3.10/library/functions.html#type

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释定义时求值、替换关系和 class 创建顺序；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--012 共十二个 Python 核心测试套已完成首轮编写；最新的 012 覆盖名字绑定、LEGB、global/nonlocal、编译期作用域判定、closure cell、comprehension/class scope 和 locals/globals。全部文件按照用户要求尚未运行。下一步直接编写 013 装饰器与元类；不要先运行 pytest。
