# Polyglot：纵向课程与横向对照

> Polyglot 通过可执行测试，对照学习不同语言如何解决相同问题，理解它们的共同概念、
> 语义差异、底层机制和迁移陷阱。

仓库提供两个相互独立的学习产品：

1. `languages/` 是每门语言完整、连续的纵向课程；
2. `concepts/` 是围绕具体共同问题编写的精简横向对照。

同一语义可以在两层出现少量重复。语言课程负责讲深、讲全；概念测试只保留比较所需的
代表案例。现有完整测试不会为了避免重复而迁出语言主线。

## 纵向语言课程

只沿一个语言目录即可完整学习该语言：

```text
languages/
  python/
    language/
    builtins/
    stdlib/
  cpp/
    language/
    standard_library/
  nodejs/
    language/
    node_core/
    npm_and_package_workflows/
```

课程文件使用 `test_NNN_topic.<ext>`。编号在每门语言内全局唯一、连续且稳定：

- Python `001`–`178`；
- C++ `001`–`160`；
- Node.js `001`–`107`。

语言主线承担基础语法、高级语义、数据模型、标准库、运行时与语言独有机制。Python
标准库、C++ 标准库、Node 核心模块和 npm 工作流始终留在这里。

## 横向概念对照

`concepts/` 使用“章节—主题—语言”三级结构，不收纳大型课程文件。顶层两位编号表示
稳定的概念章节，二级两位编号表示该章节内的具体对照主题：

```text
concepts/
  01_values_and_comparison/
    01_truthiness/
      python/test_truthiness.py
      cpp/test_truthiness.cpp
      nodejs/test_truthiness.mjs
    02_equality/
      python/test_equality.py
      cpp/test_equality.cpp
      nodejs/test_equality.mjs
  02_functions_and_calls/
    01_argument_passing/
      python/test_argument_passing.py
      cpp/test_argument_passing.cpp
      nodejs/test_argument_passing.mjs
  03_errors_and_resources/
    01_resource_cleanup/
      python/test_resource_cleanup.py
      cpp/test_resource_cleanup.cpp
      nodejs/test_resource_cleanup.mjs
```

一个章节可以逐步增加多个主题，不设固定的主题总数。顶层预计稳定在约 10–15 个章节；
只有出现首个真实主题时才创建章节，不预建空目录。当前三个章节包含四个主题：

- `truthiness`：零、空文本、空集合、空值、自定义对象和逻辑运算结果；
- `equality`：数值转换、NaN、负零、集合内容、对象身份和自定义值语义；
- `argument_passing`：调用参数数量、对象修改与重新绑定、默认值求值和灵活参数；
- `resource_cleanup`：正常与异常退出、逆序清理、触发机制、异常抑制和清理错误。

概念测试使用局部名称，不占用语言课程编号。每个文件通过 `polyglot-family` 和
`polyglot-concept` 声明所属章节与主题，并通过 `polyglot-related` 指向深入讲解该语言
的完整课程文件，不建立额外 JSON、YAML 或 Markdown 映射表。

没有对应能力时不编造等价机制。例如 C++ 容器没有通用真假协议，测试会断言容器不能
进入上下文布尔转换，并用注释说明必须显式查询 `empty()`；JavaScript 对象不能覆盖
`ToBoolean`，测试会证明转换钩子根本不会被调用。

## 在 `ohdev` 中执行

宿主机只负责阅读代码和发起 Docker 命令。Python、C++、Node.js 的解释器、编译器和
测试框架都只在 `ohdev` 中运行：

```text
./tools/run.sh
    ↓ docker exec ohdev
./tools/run-in-container.sh
```

纵向课程验证：

```bash
./tools/run.sh python -q --timeout=30 -W error
./tools/run.sh cpp
./tools/run.sh nodejs
```

横向概念验证：

```bash
./tools/run.sh concept 01_values_and_comparison/01_truthiness
./tools/run.sh family 01_values_and_comparison
./tools/run.sh concepts
```

`concept NN_family/NN_topic` 运行一个主题的全部语言；`family NN_family` 运行一个章节
中的全部主题；`concepts` 运行整个横向层。C++ 课程与概念使用独立的 `/tmp` 构建目录
和 CTest 标签，不会把概念用例计入语言课程基线。

统一结构门禁：

```bash
./tools/run.sh check
```

它分别检查：

- 语言课程只位于声明的 `languages/` 路径，编号连续且有 `polyglot-covers`；
- 顶层章节使用连续的 `NN_family`，章节内主题使用连续的 `NN_topic`；
- 每个主题至少包含两门语言，并使用唯一的顶层 `test_<topic>` 测试入口；
- `polyglot-family`、`polyglot-concept` 分别与章节和主题目录一致；
- `polyglot-related` 指向同语言中真实存在的完整课程文件；
- 语言目录可以按需增加 `fixtures/` 或 `support/`；
- 仓库内未忽略文本每行不超过 120 个 Unicode 字符。

门禁只能证明结构契约，不能自动判断课程质量。概念是否真正回答同一问题，仍必须通过
共同问题矩阵、对应案例、断言和人工审阅确认。

## 当前验证基线

- Python 3.10.12：课程 `5025 passed, 39 skipped`；
- GCC/libstdc++ 11.4.0、C++20、GoogleTest 1.16.0：课程
  `1409 passed, 15 skipped`；
- Node.js 24.18.0：课程 `935 passed`；
- 三个横向章节、四个主题：Python `16 passed`、C++ `15 passed`、Node.js `16 passed`。

所有 skip 都必须说明实现能力、平台行为或可选依赖原因。准确工具链、官方资料、归档
校验值和实现提交记录在 `sources.lock`。

## 新概念的准入条件

增加概念前先确认：

1. 先选择稳定章节；同类主题在章节内递增编号，不消耗新的顶层编号；
2. 主题能用一句具体问题描述，而不是“类型”“对象”“标准库”这类大领域；
3. 至少两门语言存在可对照的输入、结果或缺失机制；
4. 各语言文件采用同一问题矩阵，差异通过断言或必要注释表达；
5. 案例保持精简并指回完整课程，不移动、裁剪或拆散语言课程文件。

标准库默认只属于语言主线。文件系统、日期时间、并发等主题只有在真实问题值得比较时，
才另写一个小型概念测试；不会把整组标准库文件迁入 `concepts/`。

## 新对话从哪里开始

新对话先查看 Git 状态与最近提交，然后读取 `README.md`、`sources.lock` 和 `NEXT.md`。
`AGENTS.md` 是执行契约；`NEXT.md` 是唯一当前任务，不累积历史清单。

旧 checklist-first 实现截止于 commit `662e0d1`。需要查证历史时使用 `git show`，
不要把旧生成数据恢复到工作树。
