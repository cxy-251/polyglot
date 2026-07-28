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
  go/
    language/
    standard_library/
    tooling_and_runtime/
  rust/
    tests/
      language/
      standard_library/
      tooling_and_runtime/
  julia/
    language/
    standard_library/
    tooling_and_runtime/
  r/
    language/
    standard_library/
    tooling_and_runtime/
  lua/
    language/
    standard_library/
    tooling_and_runtime/
```

课程文件使用 `test_NNN_topic.<ext>`。编号在每门语言内全局唯一、连续且稳定：

- Python `001`–`178`；
- C++ `001`–`160`；
- Node.js `001`–`107`；
- Go `001`–`128`；
- Rust `001`–`128`；
- Julia `001`–`128`；
- R `001`–`128`。
- Lua `001`–`128`。

语言主线承担基础语法、高级语义、数据模型、标准库、运行时与语言独有机制。Python
标准库、C++ 标准库、Node 核心模块和 npm 工作流、Go、Rust、Julia 与 R 的标准库和
工具链工作流始终留在这里。

## 横向概念对照

`concepts/` 使用“章节—主题—语言”三级结构，不收纳大型课程文件。顶层两位编号表示
稳定的概念章节，二级两位编号表示该章节内的具体对照主题：

```text
concepts/
  01_values_and_comparison/
    01_truthiness/
      python/test_01_core.py
      cpp/test_01_core.cpp
      nodejs/test_01_core.mjs
      go/test_01_core_test.go
      rust/test_01_core.rs
      julia/test_01_core.jl
      r/test_01_core.R
      lua/test_01_core.lua
    02_equality/
      python/test_01_core.py
      cpp/test_01_core.cpp
      nodejs/test_01_core.mjs
      go/test_01_core_test.go
      rust/test_01_core.rs
      julia/test_01_core.jl
      r/test_01_core.R
      lua/test_01_core.lua
  02_functions_and_calls/
    01_argument_passing/
      python/test_01_core.py
      cpp/test_01_core.cpp
      nodejs/test_01_core.mjs
      go/test_01_core_test.go
      rust/test_01_core.rs
      julia/test_01_core.jl
      r/test_01_core.R
      lua/test_01_core.lua
  03_errors_and_resources/
    01_resource_cleanup/
      python/test_01_core.py
      cpp/test_01_core.cpp
      nodejs/test_01_core.mjs
      go/test_01_core_test.go
      rust/test_01_core.rs
      julia/test_01_core.jl
      r/test_01_core.R
      lua/test_01_core.lua
```

当前横向课程已经完成 10 个章节、49 个主题：

| 章节 | 主题数 | 对照范围 |
|---|---:|---|
| `01_values_and_comparison` | 6 | 值、转换、空值、身份、排序与键语义 |
| `02_functions_and_calls` | 5 | 传参、作用域、闭包、调用绑定与适配 |
| `03_errors_and_resources` | 4 | 异常、错误链、契约与资源清理 |
| `04_collections_and_iteration` | 7 | 索引、迭代、失效、映射、集合、惰性与排序 |
| `05_objects_and_dispatch` | 6 | 构造、成员、继承、封装、协议与反射 |
| `06_text_binary_and_serialization` | 5 | Unicode、格式、正则、字节与序列化 |
| `07_modules_packages_and_loading` | 3 | 模块、包解析、初始化、缓存与动态加载 |
| `08_async_and_concurrency` | 5 | async、调度、取消、隔离、原子与同步 |
| `09_files_paths_and_streams` | 4 | 路径、文件、流、背压与子进程 |
| `10_time_locale_and_runtime` | 4 | 时钟、日历、区域化与运行时能力 |

49 个主题已经完成逐文件内容终审。终审逐项核对八门语言的共同问题、测试名称与断言、
锁定版本语义、边界与失败路径、状态隔离、迁移陷阱和直接关联课程；它表示当前案例经过
统一语义复核，不表示穷举所有语言输入或未来版本能力。24 个高复杂度主题已按独立子问题
使用多个测试文件，每门语言现有 73 个横向测试入口。

一个章节可以继续增加多个真实主题，不设固定主题总数，也不预建空目录。概念语言目录
使用连续的 `test_NN_name.<ext>` 局部编号；简单主题通常只有 `test_01_core`，内容增长到
确有独立查阅价值时才增加文件。主题可按需使用 `fixtures/` 或 `support/`，C++ 支持源会
自动链接到同一主题的测试目标。

每个测试文件通过 `polyglot-family` 和 `polyglot-concept` 声明所属章节与主题，并通过
`polyglot-related` 指向深入讲解该语言的完整课程文件。过长路径使用紧邻的
`polyglot-related+` 续行；两行共同构成一个真实仓库路径，不建立额外 JSON、YAML 或
Markdown 映射表。

没有对应能力时不编造等价机制。例如 C++ 容器没有通用真假协议，测试会断言容器不能
进入上下文布尔转换，并用注释说明必须显式查询 `empty()`；JavaScript 对象不能覆盖
`ToBoolean`，测试会证明转换钩子根本不会被调用；Go 条件只接受 `bool`，不会把零值、
空集合或自定义对象转换为真假。

## 在 `ohdev` 中执行

宿主机只负责阅读代码和发起 Docker 命令。Python、C++、Node.js、Go、Rust、Julia、R、
Lua 的
解释器、编译器和测试框架都只在 `ohdev` 中运行：

```text
./tools/run.sh
    ↓ docker exec ohdev
./tools/run-in-container.sh
```

环境检查区分当前工程与规划语言：

```bash
./tools/run.sh doctor
./tools/run.sh doctor planned
```

默认 `doctor` 强制验证 Python、C++、Node.js、Go、Rust、Julia、R、Lua；当前没有暂停中的
规划语言，`doctor planned` 会在完成 active 检查后明确显示空规划集合。

纵向课程验证：

```bash
./tools/run.sh python -q --timeout=30 -W error
./tools/run.sh cpp
./tools/run.sh nodejs
./tools/run.sh go
./tools/run.sh rust
./tools/run.sh julia
./tools/run.sh r
./tools/run.sh lua
```

横向概念验证：

```bash
./tools/run.sh concept 01_values_and_comparison/01_truthiness
./tools/run.sh family 01_values_and_comparison
./tools/run.sh concepts
./tools/run.sh list-concepts
```

`concept NN_family/NN_topic` 运行一个主题的全部语言；`family NN_family` 运行一个章节
中的全部主题；`concepts` 运行整个横向层；`list-concepts` 从目录实时列出章节、主题、
语言和测试文件数。C++ 课程与概念使用独立的 `/tmp` 构建目录和 CTest 标签，不会把
概念用例计入语言课程基线。

统一结构门禁：

```bash
./tools/run.sh check
```

它分别检查：

- 语言课程只位于声明的 `languages/` 路径，编号连续且有 `polyglot-covers`；
- 顶层章节使用连续的 `NN_family`，章节内主题使用连续的 `NN_topic`；
- 每个主题包含八门 active language，每门语言的 `test_NN_name` 编号连续且入口明确；
- `polyglot-family`、`polyglot-concept` 分别与章节和主题目录一致；
- `polyglot-related` 及可选续行指向同语言中真实存在的完整课程文件；
- 语言目录可以按需增加 `fixtures/` 或 `support/`；
- 仓库内未忽略文本每行不超过 120 个 Unicode 字符。

门禁只能证明结构契约，不能自动判断课程质量。概念是否真正回答同一问题，仍必须通过
共同问题矩阵、对应案例、断言和人工审阅确认。

## 当前验证基线

- Python 3.10.12：课程 `5025 passed, 39 skipped`；
- GCC/libstdc++ 11.4.0、C++20、GoogleTest 1.16.0：课程
  `1409 passed, 15 skipped`；
- Node.js 24.18.0：课程 `935 passed`；
- Go 1.26.5：课程 128 个文件、`133 passed`；
- Rust 1.97.1、edition 2024：课程 128 个文件、`128 passed, 1 ignored`，另有 1 个 doc test；
- Julia 1.12.6：课程 128 个文件、`488 passed`；
- R 4.6.1：课程 128 个文件、`128/128` 通过；离线 source package 的 build、install、
  check、installed tests 与 registered native code 工作流通过；
- Lua 5.5.0：课程 128 个文件、`128/128` 通过；官方源码 bootstrap、严格 C API 宿主与
  动态 C module 工作流通过；
- 横向课程 10 个章节、49 个已终审主题、24 个多文件主题；每门语言 73 个测试入口：
  Python `252 passed`、C++ `249 passed`、Node.js `255 passed`、Go `75 passed`、
  Rust `73 passed`、Julia `280 passed`、R `73/73`、Lua `73/73` 通过。

所有 skip 都必须说明实现能力、平台行为或可选依赖原因。准确工具链、官方资料、归档
校验值和实现提交记录在 `sources.lock`。

## 横向课程的维护准入

49 个主题构成当前完整横向课程。后续修改优先补强现有主题；增加主题或章节前先确认：

1. 优先选择现有稳定章节；同类主题在章节内递增编号，不机械创建新顶层编号；
2. 主题能用一句具体问题描述，而不是“类型”“对象”“标准库”这类大领域；
3. 至少两门语言存在可对照的输入、结果或缺失机制；
4. 各语言文件采用同一问题矩阵，差异通过断言或必要注释表达；
5. 案例保持精简并指回完整课程，不移动、裁剪或拆散语言课程文件。

只有出现无法归入现有十章的稳定问题域时才增加 family。新增语言时优先把它接入现有
49 个主题，并保留确实不存在对应机制的说明，不为追求语言齐全而伪造等价。

标准库默认只属于语言主线。文件系统、日期时间、并发等主题只有在真实问题值得比较时，
才另写一个小型概念测试；不会把整组标准库文件迁入 `concepts/`。

## 新对话从哪里开始

新对话先查看 Git 状态与最近提交，然后读取 `README.md`、`sources.lock` 和 `NEXT.md`。
`AGENTS.md` 是执行契约；`NEXT.md` 是唯一当前任务，不累积历史清单。

旧 checklist-first 实现截止于 commit `662e0d1`。需要查证历史时使用 `git show`，
不要把旧生成数据恢复到工作树。
