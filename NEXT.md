# Current Task

ID: `python.core.classes-construction-and-inheritance`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 类定义、实例构造与继承测试套，连接类体命名空间、``__new__`` / ``__init__``、方法绑定、``super()``、MRO 和类级扩展钩子，并展示多继承中协作式调用的真实约束。

## Covers

- ``class`` 语句执行类体并创建独立命名空间；
- 实例、类、``type()``、``isinstance()``、``issubclass()`` 的关系；
- ``__new__()`` 创建实例、``__init__()`` 初始化既有实例；
- ``__new__`` 返回其他类型时跳过当前类的 ``__init__``；
- 不可变内置类型子类在 ``__new__`` 中处理构造值；
- 实例方法、``@classmethod``、``@staticmethod`` 的绑定差异；
- 单继承方法覆盖与 ``super()``；
- C3 MRO 与菱形继承；
- 使用一致关键字参数和 ``super()`` 的协作式多继承；
- 硬编码父类调用导致菱形重复/漏调用的风险；
- ``__init_subclass__()`` 的类创建钩子与关键字消费；
- 双下划线名称改写的用途与边界。

## Common Pitfalls To Explain

- 把 ``__init__`` 当成创建对象的方法并尝试返回实例；
- 覆盖 ``__new__`` 时忘记返回实例；
- 把 ``super()`` 理解成“固定父类”而忽略它沿 MRO 的动态含义；
- 多继承中方法签名不协作，造成参数无法继续传递；
- 依赖双下划线名称改写实现安全或真正私有；
- 在 ``__init_subclass__`` 中不消费自定义关键字就直接传给 object。

## Target File

`languages/python/core/test_011_classes_construction_and_inheritance.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#class-definitions
- https://docs.python.org/3.10/reference/datamodel.html#customizing-instance-and-subclass-checks
- https://docs.python.org/3.10/reference/datamodel.html#object.__new__
- https://docs.python.org/3.10/reference/datamodel.html#object.__init_subclass__
- https://docs.python.org/3.10/library/functions.html#super
- https://docs.python.org/3.10/howto/mro.html

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释构造阶段、绑定方式、MRO 和协作约束；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--010 共十个 Python 核心测试套已完成首轮编写；最新的 010 覆盖 with 展开、异常三元组、选择性抑制、enter/target 失败、多个管理器、非局部跳转和类型级特殊方法查找。全部文件按照用户要求尚未运行。下一步直接编写 011 类构造与继承；不要先运行 pytest。
