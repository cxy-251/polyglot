# Polyglot：通过可执行测试进行跨语言学习

> Polyglot 通过可执行测试，对照学习不同语言如何解决相同问题，理解它们的共同概念、
> 语义差异、底层机制和迁移陷阱。

仓库当前用 Python、C++ 和 Node.js 建立跨语言框架；Julia、R、Go 和 Rust 保留在规划
范围内，但在前三门语言的框架稳定前暂停扩展。项目的完成指标不是文件数量，而是同一
问题能否被并排阅读、真实语义是否得到断言验证、语言经验能否安全迁移。

测试代码是主要内容。能用代码和断言表达的语义直接写在测试中；编译期错误、未定义行为、
实现差异和平台限制使用必要注释或 skip 表达。仓库不维护大型 Markdown/JSON checklist、
对象快照、数据库快照或 `chatgpt-sources/`。

## 组织方式

仓库采用“共同概念 + 各语言完整路径”的混合结构：

```text
concepts/
  01_values_types_conversions_and_equality/
    python/
    cpp/
    nodejs/
  02_bindings_scope_and_lifetime/
  ...
  10_modules_code_loading_and_packages/

languages/
  python/
    language_specific/
    stdlib/
  cpp/
    language_specific/
    standard_library/
  nodejs/
    language_specific/
    node_core/
    npm_and_package_workflows/
```

`concepts/` 围绕共同问题组织测试，例如真假值、作用域、函数调用、对象分派、资源清理
和模块加载。同一目录中的测试解决相近问题，但不暗示语法或语义相同；代表测试顶部的
“跨语言迁移提示”指出最容易误套经验的边界。

共同概念不要求三门语言齐全。只有两门语言存在真实对照价值时也可以建立概念；缺少合理
对应项时保持缺席。模板元编程、C++ 值类别等特有机制留在
`languages/<language>/language_specific/`，标准库、Node 核心模块和 npm 工作流继续留在
各语言目录中，保证每门语言仍有完整的独立学习路径。

测试编号仍属于语言，而不是概念。Python `001`–`178`、C++ `001`–`160`、Node.js
`001`–`107` 分别在 `concepts/` 和对应 `languages/` 目录之间保持全局唯一、连续和稳定；
三门语言的相同编号不要求表达相同概念。

## 当前基线

- Python 3.10：178 个测试文件；锁定解释器为 Python 3.10.12；严格全量基线为
  `5025 passed, 39 skipped`。
- C++20：160 个测试文件；GCC/libstdc++ 11.4.0、CMake 3.22.1、GoogleTest 1.16.0；
  全量基线为 `1409 passed, 15 skipped`。
- Node.js：107 个测试文件；Node.js 24.18.0、ECMAScript 2025、ECMA-402 12th edition、
  npm 11.16.0；全量基线为 `935 passed`。

所有 skip 都必须说明平台、实现能力或可选依赖原因。准确版本、官方资料、归档校验值和
实现提交记录在 `sources.lock`。

## 新对话从哪里开始

新对话按顺序查看 Git 状态和最近提交，然后读取：

```text
README.md
sources.lock
NEXT.md
```

`AGENTS.md` 是执行契约；`NEXT.md` 是唯一的当前任务入口，只保存一项可接续工作。历史
决策由 Git 提交保留，不在交接文件中累积任务清单。

## 在容器中执行

宿主机只用于阅读代码和发起 Docker 命令，不直接运行任何目标语言的解释器、编译器或
测试框架：

```text
./tools/run.sh
    ↓ docker exec ohdev
./tools/run-in-container.sh
    ↓ pytest / CMake + CTest / node:test
```

常用命令：

```bash
./tools/run.sh doctor
./tools/run.sh check
./tools/run.sh python -q --timeout=30 -W error
./tools/run.sh cpp
./tools/run.sh nodejs
```

`./tools/run.sh check` 在 `ohdev` 中验证允许的目录结构、`polyglot-covers` 标记、各语言
连续且唯一的编号、共同概念至少包含两门语言，以及仓库内未忽略文本每行不超过 120 个
Unicode 字符。修改测试时先运行受影响范围，再运行对应语言全量；只有两者都通过才能
保持 verified 状态。

Python 与 Node.js 的单文件命令直接使用当前路径，例如：

```bash
./tools/run.sh python \
  concepts/01_values_types_conversions_and_equality/python/test_001_truth_value_testing.py

./tools/run.sh nodejs \
  concepts/01_values_types_conversions_and_equality/nodejs/test_001_primitive_values_numeric_models_and_equality.mjs
```

C++ 可用 CTest 正则按目标名筛选：

```bash
./tools/run.sh cpp -R '^test_001_'
```

主机阅读 C++ 使用仓库根目录的 `.clangd`；它同时匹配 `concepts/*/cpp/` 与
`languages/cpp/`，提供跳转、补全和静态诊断，但不改变编译只在 `ohdev` 中执行的边界。

## 新内容如何归类

开始移动或新增内容前先回答三个问题：

1. 它是否在回答一个语言无关的共同问题？
2. 至少两门语言之间是否存在值得解释的真实对应关系或迁移陷阱？
3. 放在同一目录是否会帮助比较，而不是制造“看起来相似”的假等价？

三个答案都成立时进入 `concepts/`；否则进入对应语言的特有机制、标准库、核心模块或
包工作流目录。先审计已有测试再建立目录，不预建空分类，不为达到数量或语言齐全而迁移。
移动优先使用 `git mv`，保留原编号、覆盖标记、断言、注释和可追踪历史。

## 历史

旧 checklist-first 实现截止于 commit `662e0d1`。需要查证历史判断时使用
`git show 662e0d1:<path>`，不要把旧生成数据恢复到当前工作树。
