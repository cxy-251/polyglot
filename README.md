# Polyglot：纵向课程与横向对照

> Polyglot 通过可执行测试，对照学习不同语言如何解决相同问题，理解它们的共同概念、
> 语义差异、底层机制和迁移陷阱。

仓库采用三个明确分层：

1. `languages/` 承载语言语义、标准库和真实开发工作流；
2. `concepts/` 承载围绕共同问题编写的精简横向对照；
3. `harness/` 与 `tools/` 承载工具链、runner、bootstrap、版本锁、环境隔离和构建集成。

同一语义可以在两层出现少量重复。语言课程负责讲深、讲全；概念测试只保留比较所需的
代表案例。仅验证仓库配置或执行环境的内容不计入语言课程。

九门 active language 集合已经冻结，不再增加第十门语言。Ruby、Lua、R、Julia、Rust、
Go、Node.js、C++、Python 已按此顺序完成文件级语义审计；项目进入维护阶段。文件数量
只描述审计后的真实课程结构，不作为未来必须维持的完整性指标。

## 纵向语言课程

纵向课程目标是让读者只沿一个语言目录理解该语言：

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
  ruby/
    language/
    standard_library/
    tooling_and_runtime/
```

课程文件使用 `test_NNN_topic.<ext>`。编号在每门语言内全局唯一且稳定；合并或删除后
允许空缺，不批量重排。审计后课程文件数与编号范围为：

- Python：178 个，`001`–`178`；C++：160 个，`001`–`160`；
- Node.js：103 个，`001`–`107`；Go：65 个，`009`–`127`；
- Rust：60 个，`009`–`124`；Julia：71 个，`002`–`127`；
- R：56 个，`009`–`126`；Lua：61 个，`002`–`122`；
- Ruby：74 个，`002`–`120`。

语言主线承担基础语法、高级语义、数据模型、标准库、运行时接口与语言独有机制。
固定安装路径、归档校验值、runner 参数、临时目录布局和容器配置属于 harness，不作为
语言知识或课程完成度。

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
      ruby/test_01_core.rb
    02_equality/
      python/test_01_core.py
      cpp/test_01_core.cpp
      nodejs/test_01_core.mjs
      go/test_01_core_test.go
      rust/test_01_core.rs
      julia/test_01_core.jl
      r/test_01_core.R
      lua/test_01_core.lua
      ruby/test_01_core.rb
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
      ruby/test_01_core.rb
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

横向层审计后保留 10 个章节、49 个主题：

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

审计逐 topic 核对共同问题、语言差异、失败边界和真实关联课程。最终 441 个语言实现使用
613 个横向测试入口：Python 72、C++ 70、Node.js 70、Go 64、Rust 67、Julia 65、R 67、
Lua 66、Ruby 72。不同数量正是独立问题分层的结果，不再要求机械同构。

一个章节可以继续增加多个真实主题，不设固定主题总数，也不预建空目录。概念语言目录
使用稳定且唯一的 `test_NN_name.<ext>` 局部编号，删除后允许空缺。不同语言可以使用不同
文件数量和 stem；简单主题通常只有一个文件，存在真正独立的失败边界、生命周期或并发协议
时才拆分。主题可按需使用 `fixtures/` 或 `support/`。

每个测试文件通过 `polyglot-family` 和 `polyglot-concept` 声明所属章节与主题，并通过
`polyglot-related` 指向深入讲解该语言的课程文件。过长路径使用紧邻的
`polyglot-related+` 续行；结构门禁只验证两行组成的路径真实存在，路径存在本身不证明
教学相关性，关联内容仍需人工语义审计。

没有对应能力时不编造等价机制。例如 C++ 容器没有通用真假协议，测试会断言容器不能
进入上下文布尔转换，并用注释说明必须显式查询 `empty()`；JavaScript 对象不能覆盖
`ToBoolean`，测试会证明转换钩子根本不会被调用；Go 条件只接受 `bool`，不会把零值、
空集合或自定义对象转换为真假。

## Harness 与集成验证

`harness/<language>/` 用于该语言的 bootstrap、精确版本、runner 隔离、离线 package
工程、原生扩展构建和仓库集成测试；`tools/` 保留跨语言统一入口及共享实现。harness
测试不使用 `test_NNN_topic` 课程编号，不声明 `polyglot-covers`，也不计入纵向课程结果。

package、FFI、编译和代码加载仍可在纵向课程中讲解其语言接口与语义；官方归档 SHA、
固定安装路径、容器命令、仓库 fixture 布局和环境变量清理已经移入 harness。九门语言
均有独立 harness 入口，课程结果不再包含工程配置验证。

## 在 `ohdev` 中执行

宿主机只负责阅读代码和发起 Docker 命令。Python、C++、Node.js、Go、Rust、Julia、R、
Lua、Ruby 的解释器、编译器和测试框架都只在 `ohdev` 中运行：

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

默认 `doctor` 强制验证 Python、C++、Node.js、Go、Rust、Julia、R、Lua、Ruby；当前没有
暂停中的规划语言，`doctor planned` 会在完成 active 检查后明确显示空规划集合。

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
./tools/run.sh ruby
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

- 语言课程只位于声明路径，编号格式正确且唯一，并有 `polyglot-covers`；
- 顶层章节和主题使用稳定的编号格式且编号唯一，允许空缺；
- 每个主题至少包含两门实际参与语言，不要求语言间文件数量或 stem 相同；
- `polyglot-family`、`polyglot-concept` 分别与章节和主题目录一致；
- `polyglot-related` 及可选续行指向同语言中真实存在的课程文件；
- 语言目录可以按需增加 `fixtures/` 或 `support/`；
- 仓库内未忽略文本每行不超过 120 个 Unicode 字符。

门禁只能证明结构完整性，不能从编号、文件数量、执行通过或关联路径存在推导课程质量。
概念是否真正回答同一问题，仍必须通过共同问题矩阵、对应案例、断言和人工审阅确认。

## 语义审计完成结果

决策统计以审计开始前的稳定课程编号为基准：“保留”表示同编号内容未改，“纠错”包含
扩充和重命名，“合并”表示教学问题被保留课程吸收，“移动”表示工程问题转入 harness，
“删除”表示不再具有课程价值；“横删”单列横向重复入口。

| 语言 | 保留 | 纠错 | 合并 | 移动 | 删除 | 横删 | 最终纵向 | 最终横向 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ruby | 23 | 51 | 44 | 9 | 1 | 1 | 74 | 72 |
| Lua | 3 | 58 | 61 | 5 | 1 | 7 | 61 | 66 |
| R | 8 | 48 | 63 | 9 | 0 | 6 | 56 | 67 |
| Julia | 9 | 62 | 49 | 8 | 0 | 8 | 71 | 65 |
| Rust | 13 | 47 | 49 | 8 | 11 | 6 | 60 | 67 |
| Go | 14 | 51 | 51 | 12 | 0 | 9 | 65 | 64 |
| Node.js | 100 | 3 | 0 | 4 | 0 | 3 | 103 | 70 |
| C++ | 118 | 42 | 0 | 0 | 0 | 3 | 160 | 70 |
| Python | 170 | 8 | 0 | 0 | 0 | 1 | 178 | 72 |

最终验证结果：Python `5025 passed, 39 skipped`；C++ `1409 passed, 15 skipped`；
Node.js `900 passed`；Go `115 passed`；Rust `97 passed`；Julia、R、Lua、Ruby 分别为
`71/71`、`56/56`、`61/61`、`74/74` 个课程文件通过。九个 harness、49 个精确 topic、
10 个 family、完整 concepts、版本检查、概念清单、结构门禁和 `git diff --check` 均通过。

## 审计前执行快照

下列结果仅说明审计开始前代码能够执行，不是内容审查完成声明，也不是必须维持的数量：

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
- CRuby 4.0.6：课程 128 个文件、`128/128` 通过；官方源码 bootstrap、隔离 RubyGems、
  Bundler、Rake、Ruby Box/Ractor 能力检查和公共 C Extension 工作流通过；
- 横向课程审计前有 10 个章节、49 个主题、24 个多文件主题；每门语言 73 个测试入口：
  Python `252 passed`、C++ `249 passed`、Node.js `255 passed`、Go `75 passed`、
  Rust `73 passed`、Julia `280 passed`、R `73/73`、Lua `73/73`、Ruby `73/73` 通过。

所有 skip 都必须说明实现能力、平台行为或可选依赖原因。准确工具链、官方资料、归档
校验值和实现提交记录在 `sources.lock`。

## 横向课程维护

49 个主题构成当前已审课程。修改优先补强、合并、纠错或删除现有主题；增加主题或章节前
先确认：

1. 优先选择现有稳定章节；同类主题在章节内递增编号，不机械创建新顶层编号；
2. 主题能用一句具体问题描述，而不是“类型”“对象”“标准库”这类大领域；
3. 至少两门语言存在可对照的输入、结果或缺失机制；
4. 各语言回答同一观察问题，但文件数量和组织方式可以不同；
5. 案例保持精简并指回真正支撑断言的课程，不复制纵向大测试。

只有出现无法归入现有十章的稳定问题域时才增加 family。语言集合保持冻结；不存在对应
机制时说明缺失、替代模型或不可比较边界，不为追求目录齐全而伪造等价。

标准库默认只属于语言主线。文件系统、日期时间、并发等主题只有在真实问题值得比较时，
才另写一个小型概念测试；不会把整组标准库文件迁入 `concepts/`。

## 新对话从哪里开始

新对话先查看 Git 状态与最近提交，然后读取 `README.md`、`sources.lock` 和 `NEXT.md`。
`AGENTS.md` 是执行契约；`NEXT.md` 记录当前维护任务或已完成状态，不累积历史清单。

旧 checklist-first 实现截止于 commit `662e0d1`。需要查证历史时使用 `git show`，
不要把旧生成数据恢复到工作树。
