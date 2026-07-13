# Current Task

ID: `python.builtins.boolean-and-integer-types`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 ``bool`` 与 ``int`` 内置类型测试套，在已有真假协议/运算符分派基础上集中展示构造、字面量、任意精度、整数专用方法、字节转换和 bool/int 继承关系中的真实陷阱。

## Covers

- ``True`` / ``False`` 单例、``bool`` 是 ``int`` 子类但语义用途不同；
- bool 的数值相等/hash/算术行为及作为 dict key 与 0/1 的碰撞；
- 十进制、二/八/十六进制字面量和下划线分组；
- int 任意精度与 ``sys.maxsize`` 不是最大整数；
- ``int()`` 从整数、float、字符串、bytes/bytearray 构造；
- 字符串正负号、空白、下划线、显式 base 与 ``base=0`` 前缀推断；
- float 转 int 向零截断，NaN/Infinity 转换失败；
- ``bit_length()``、``bit_count()``、``as_integer_ratio()``；
- ``to_bytes()`` / ``from_bytes()`` 的 byteorder、length、signed；
- 字节长度不足的 ``OverflowError`` 与 signed 误用；
- 整数 ``real`` / ``imag`` / ``numerator`` / ``denominator`` / ``conjugate()``；
- 负移位、除零和无效 base 等异常边界；
- ``int`` 不可变性与构造已有精确 int 时的对象复用边界。

## Common Pitfalls To Explain

- 在业务数据中利用 ``True == 1``，导致 dict/set 键碰撞；
- 把 ``sys.maxsize`` 当作 Python int 上限；
- 混淆 floor division 与 int(float) 的向零截断；
- 使用 ``base=0`` 解析带前导零但无合法前缀的字符串；
- 忘记 ``to_bytes`` 默认 unsigned，负数必须 ``signed=True``；
- 按字符数而不是数值位宽估算字节长度；
- 依赖小整数缓存或 ``int(existing) is existing`` 作为语言语义。

## Target File

`languages/python/core/test_019_boolean_and_integer_types.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#boolean-values
- https://docs.python.org/3.10/library/stdtypes.html#numeric-types-int-float-complex
- https://docs.python.org/3.10/library/stdtypes.html#additional-methods-on-integer-types
- https://docs.python.org/3.10/library/functions.html#int
- https://docs.python.org/3.10/reference/lexical_analysis.html#integer-literals
- https://docs.python.org/3.10/library/sys.html#sys.maxsize

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释数值语义、解析规则和字节边界；
- 与 001/003/004 已覆盖的通用协议分派避免机械重复，必要时通过注释交叉说明；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 共十八个 Python 测试套已完成首轮编写；最新的 018 覆盖 import 绑定、module/package 元数据、sys.modules 缓存、relative/star import、reload、失败/循环导入和 main guard。全部文件按照用户要求尚未运行。下一步直接编写 019 bool/int 内置类型；不要先运行 pytest。
