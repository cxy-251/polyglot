# Current Task

ID: `python.core.imports-modules-and-packages`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 import 语句、module object、package/relative import 与导入缓存测试套，使用 pytest ``tmp_path`` 构造隔离的小型模块树，讲清导入执行、名字绑定、``sys.modules`` 和 reload 的真实语义。

## Covers

- ``import module``、``import module as alias``、``from module import name`` 的绑定差异；
- ``import package.submodule`` 默认绑定顶层 package；
- module 的 ``__name__``、``__package__``、``__spec__``、``__file__``；
- 首次 import 执行模块代码，后续 import 复用 ``sys.modules`` 同一对象；
- 从 ``sys.modules`` 删除后再次 import 创建新 module 并重新执行；
- ``importlib.import_module()`` 返回指定子模块；
- ``__import__()`` 默认返回顶层包，``fromlist`` 改变返回对象；
- package ``__init__.py``、绝对导入与显式相对导入；
- 相对导入依赖正确 ``__package__`` 上下文，不能在普通顶层模块任意使用；
- ``__all__`` 控制 star import，未定义时默认排除下划线名称；
- ``importlib.reload()`` 重新执行但复用 module object/dict，旧名称可能残留；
- 导入失败、部分初始化 module 与循环 import 的诊断边界；
- ``if __name__ == "__main__"`` 区分导入和脚本执行。

## Common Pitfalls To Explain

- 以为重复 import 会重复执行模块顶层副作用；
- 以为 ``import a.b`` 直接在局部绑定名称 ``b``；
- 修改已导入 module 文件后只调用 import，忽略缓存；
- 把 reload 当成全新干净命名空间；
- 使用隐式相对导入或在缺少 package context 时写相对导入；
- star import 造成来源不明的名字覆盖；
- 循环 import 在模块尚未完成初始化时读取对方属性。

## Target File

`languages/python/core/test_018_imports_modules_and_packages.py`

## Official Sources

- https://docs.python.org/3.10/reference/simple_stmts.html#the-import-statement
- https://docs.python.org/3.10/reference/import.html
- https://docs.python.org/3.10/reference/datamodel.html#modules
- https://docs.python.org/3.10/library/importlib.html
- https://docs.python.org/3.10/library/functions.html#__import__
- https://docs.python.org/3.10/library/runpy.html

## Authoring Requirements

- 使用 pytest ``tmp_path`` / ``monkeypatch`` 隔离临时模块，不写真实用户目录；
- 每个临时 module/package 使用独特名称，并在结束时清理相关 ``sys.modules`` 条目；
- 使用必要而详细的中文注释解释执行、绑定、缓存与相对导入上下文；
- 案例保持正常、具体、可复用，不做完整 import hook/finders/loaders 实现；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--017 共十七个 Python 核心测试套已完成首轮编写；最新的 017 覆盖普通/链式/解包/带注解赋值、容器 display、comprehension 求值顺序和 assignment expression。全部文件按照用户要求尚未运行。下一步直接编写 018 import、module 与 package；不要先运行 pytest。
