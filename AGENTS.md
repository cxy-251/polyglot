# Agent Contract

这个仓库必须让全新对话只依靠工作树继续，不依赖以前的聊天记录。

## 开始工作

每场对话只执行一次：

1. 查看 `git status --short` 和最近的 Git commit。
2. 阅读 `README.md`、`sources.lock` 和 `NEXT.md`。
3. 只把 `NEXT.md` 作为当前任务入口，不寻找或创建完整任务清单。
4. 先阅读任务列出的官方资料、目标文件和已有课程，再修改代码。
5. 工作中断时，把准确剩余步骤写入 `NEXT.md` 的 `Handoff`。

上下文压缩、自动续写和同一 goal 内的阶段提交不算新对话；文件未被外部修改时，不要
反复读取启动文件。

## 项目目标

> Polyglot 通过可执行测试，对照学习不同语言如何解决相同问题，理解它们的共同概念、
> 语义差异、底层机制和迁移陷阱。

Python、C++、Node.js、Go、Rust、Julia、R、Lua 和 Ruby 是冻结的九门 active language，
不再增加第十门语言。现有课程正在按文件进行语义审计；审计前的文件数、测试数和 topic 数
只表示可执行快照，不表示课程完整或内容终审完成。

测试代码是主要产品。不要建立大型 Markdown/JSON checklist、Dash 对象快照、数据库
快照、完整覆盖清单或 `chatgpt-sources/`。

## 双轴学习结构

### 纵向课程：`languages/`

`languages/` 必须让读者只沿一门语言目录就能完整学习：

```text
languages/python/{language,builtins,stdlib}/
languages/cpp/{language,standard_library}/
languages/nodejs/{language,node_core,npm_and_package_workflows}/
languages/go/{language,standard_library,tooling_and_runtime}/
languages/rust/tests/{language,standard_library,tooling_and_runtime}/
languages/julia/{language,standard_library,tooling_and_runtime}/
languages/r/{language,standard_library,tooling_and_runtime}/
languages/lua/{language,standard_library,tooling_and_runtime}/
languages/ruby/{language,standard_library,tooling_and_runtime}/
```

语言主线只保留语言语义、标准库契约和真实开发工作流。仅验证工具链版本、runner 参数、
仓库路径、环境隔离、bootstrap、临时目录布局或当前容器配置的测试移入 `harness/`；
共享执行实现继续位于 `tools/`。

课程文件使用 `test_NNN_topic.<ext>`；`NNN` 在同一语言内全局唯一且稳定。合并或删除后
允许编号空缺，不批量重排剩余文件；新文件使用当前最大编号的下一个值。每个课程文件
保留稳定的 `polyglot-covers` 标记，审计合并时同步处理重复或失效的覆盖声明。

### 横向对照：`concepts/`

`concepts/NN_family/NN_topic/` 是独立编写的精简对照层，不收纳原课程大文件。顶层
两位编号表示稳定章节，二级两位编号表示章节内的具体主题。一个主题只回答一个明确问题；
至少两门语言存在真实对照价值时才建立，不要求机械补齐所有语言。

当前 10 个章节和 49 个主题是审计输入，不是必须维持的质量指标。主题总数不设固定值，
也不预建空目录；合并、重命名或删除无效主题必须先给出明确语义依据并同步修改各语言、
运行入口和门禁。

每个语言子目录使用稳定且唯一的局部测试编号；不同语言可以使用不同数量和不同 stem：

```text
concepts/01_values_and_comparison/01_truthiness/python/test_01_core.py
concepts/01_values_and_comparison/01_truthiness/cpp/test_01_core.cpp
concepts/01_values_and_comparison/01_truthiness/nodejs/test_01_core.mjs
concepts/01_values_and_comparison/01_truthiness/go/test_01_core_test.go
concepts/01_values_and_comparison/01_truthiness/rust/test_01_core.rs
concepts/01_values_and_comparison/01_truthiness/julia/test_01_core.jl
concepts/01_values_and_comparison/01_truthiness/lua/test_01_core.lua
concepts/01_values_and_comparison/01_truthiness/ruby/test_01_core.rb
```

概念测试必须：

- 在顶部用两三行列出共同问题矩阵；
- 使用 `polyglot-family: <name>`，名称与顶层章节一致；
- 使用 `polyglot-concept: <name>`，名称与主题目录一致；
- 使用 `polyglot-related: languages/<language>/...` 指向真实完整课程；
- 围绕相同输入类别和观察点组织断言；
- 对缺失机制、编译期非法、未定义行为或规范差异使用必要注释；
- 只复制比较所需的最小代表案例，不复刻完整课程。

概念局部文件使用 `test_NN_name.<ext>`，编号在当前 topic 的当前语言中稳定且唯一，删除
文件后允许空缺；不使用语言课程编号、不声明 `polyglot-covers`、不计入语言课程文件数。
简单主题优先一个文件；只有内容已形成可独立查阅的子问题时才增加文件。语言目录允许
按需增加 `fixtures/` 或 `support/`，不得把普通辅助代码伪装成额外测试入口。

关联课程路径超过行宽时写成 `polyglot-related: <directory>/` 与紧邻的
`polyglot-related+: <filename>`；结构门禁只拼接并验证路径完整性。路径存在不证明课程
真正支撑当前断言，语义相关性必须在文件级审计中人工确认。

标准库默认留在语言主线。只有具体问题值得比较时才另写精简概念测试；禁止把一组标准库
课程文件整体迁入 `concepts/`。

## 通用内容规范

- 案例展示正常用法、高阶语义、隐式机制、实际工作流和真实陷阱。
- 新增或修改 topic 前先对齐实际参与语言的共同问题、输入类别和观察点；缺失机制不强行等价。
- 九门 active language 集合已经冻结；不得增加新语言或为了齐全机械补写概念实现。
- 九门语言优先回答同一问题，不要求代码外形一致，也不把缺失机制包装成相似 API。
- 测试名称只描述断言真正证明的范围，不把锁定实现观察写成语言普遍保证。
- 测试必须可独立运行且不依赖执行顺序；修改全局或进程状态时可靠恢复。
- 可执行的能力和边界使用真实断言或编译期检测，不以空 `SUCCEED()` 代替。
- 能执行的差异使用断言；不能安全执行的内容使用特性检测、类型检查、skip 或注释。
- 中文注释解释分派、求值顺序、生命周期、返回语义、版本差异和迁移陷阱，不逐行复述。
- 每行按 Unicode 字符数不超过 120，编写时主动换行。
- 单文件只承载一个连贯主题；内容形成可独立查阅的协议、边界或迁移问题时才使用多文件
  结构，数百行本身不是拆分理由。
- 不足 100 行的相邻同类课程文件是复查合并信号；合并保留覆盖 ID 和教学案例。
- “覆盖全面”指正常语义、协议入口、关键 fallback、常用工作流和真实陷阱，不制造
  穷举式输入或类型组合矩阵。
- 不依赖公网、sleep、真实用户目录或持久机器状态；临时资源写入 `/tmp/polyglot-*`
  或测试框架临时目录并可靠清理。

## 语义审计与分层

每个课程文件必须作出 `保留、扩充、合并、移动、删除、纠错` 六种决定之一并直接落实，
不提交大型 checklist 或生成式 inventory。保留文件必须有明确且足够重要的教学问题，
标题与断言范围一致；在有意义时覆盖边界、失败路径和迁移陷阱，并区分规范保证、标准库
契约、锁定版本行为和明确标注的实现观察。

相邻短文件共同回答同一问题时合并；仅有少量直接 API happy path、仓库配置断言或机器
状态观察的文件不能独立充当课程。纵向层负责完整讲解，横向层只保留比较所需的最小案例。
审计顺序固定为 Ruby、Lua、R、Julia、Rust、Go、Node.js、C++、Python；每次只处理一门，
完成该语言纵向、相关横向、10 个 family、完整 concepts 和结构门禁后再进入下一门。

`harness/<language>/` 承载该语言的 bootstrap、版本锁、runner 隔离、构建工程和仓库集成
测试；`tools/` 承载共享入口及实现。harness 测试可以执行，但不声明 `polyglot-covers`，
不计入语言课程完成度。语言课程可讲解 package、FFI 或构建接口的语义，固定安装路径、
归档校验值和容器行为必须留在 harness。

## 运行与门禁

宿主机不运行目标语言工具。所有解释器、编译器和测试框架位于 `ohdev`，统一入口为
`./tools/run.sh`。

纵向课程：

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

横向概念：

```bash
./tools/run.sh concept 01_values_and_comparison/01_truthiness
./tools/run.sh family 01_values_and_comparison
./tools/run.sh concepts
./tools/run.sh list-concepts
```

环境检查：

```bash
./tools/run.sh doctor
./tools/run.sh doctor planned
```

默认 `doctor` 强制检查九门 active language；当前没有暂停中的规划语言，
`doctor planned` 在 active 检查后报告空规划集合。

结构门禁：

```bash
./tools/run.sh check
```

门禁分别验证语言路径、编号格式与唯一性、覆盖标记存在、章节与主题格式、至少两门实际
参与语言、`polyglot-family`、`polyglot-concept`、关联路径完整性和 Unicode 120 字符行宽。
编号允许稳定空缺，不要求语言间文件数量或 stem 相同。门禁不能替代人工语义审阅，也
不能从 `polyglot-related` 路径存在推导教学相关性。

修改测试时先跑受影响课程或单个概念，再跑对应全量。只有两者都通过才能称为 verified。

## 审计前执行快照

以下数字只记录审计开始前代码可执行状态，不是必须维持的课程数量或内容完成声明：

- Python 3.10：审计前编号 `001`–`178`；Python 3.10.12；`5025 passed, 39 skipped`。
- C++20：审计前编号 `001`–`160`；GCC/libstdc++ 11.4.0、CMake 3.22.1、
  GoogleTest 1.16.0；`1409 passed, 15 skipped`。
- Node.js：审计前编号 `001`–`107`；Node.js 24.18.0、ECMAScript 2025、
  ECMA-402 12th edition、npm 11.16.0；`935 passed`。
- Go：审计前 128 个测试文件；Go 1.26.5；`133 passed`。
- Rust：审计前 128 个测试文件；Rust 1.97.1、edition 2024；`128 passed, 1 ignored`，
  另有 1 个 doc test。
- Julia、R、Lua、Ruby：审计前各 128 个测试文件；锁定版本全量执行通过。
- 横向层审计前有 10 个章节、49 个主题、24 个多文件主题，每门语言 73 个测试入口；
  执行快照为
  Python `252 passed`、C++ `249 passed`、Node.js `255 passed`、Go `75 passed`、
  Rust `73 passed`、Julia `280 passed`、R `73/73`、Lua `73/73`、Ruby `73/73` 通过。

所有 skip 必须说明实现能力、平台行为或可选依赖原因。工具链和资料版本见
`sources.lock`。

## 内容来源

Python 来源优先级：

1. Python Language Reference；
2. Python Data Model；
3. Built-in Functions / Built-in Types；
4. Python Standard Library Reference；
5. 仅补充版本演进或设计背景的 PEP。

C++ 来源优先级：

1. ISO/IEC 14882:2020 与对应 WG21 工作草案；
2. WG21 提案、缺陷报告和编辑报告；
3. GCC 11.4 与 libstdc++ 11.4 手册；
4. C++ Core Guidelines；
5. 只决定构建行为的 CMake 与 GoogleTest 官方文档。

Node.js 来源优先级：

1. ECMA-262 16th edition；
2. ECMA-402 12th edition；
3. Node.js 24.18.0 API 文档与对应源码；
4. Node.js 官方指南；
5. 仅补充演进和实现差异的 TC39 提案、Node.js issue 与变更记录。

Go 来源优先级：

1. Go Language Specification 与 Memory Model；
2. Go 1.26 release notes、标准库文档和源码；
3. Go Modules Reference 与 `go` command 文档；
4. Effective Go 只补充惯用写法，不覆盖规范语义。

Rust 来源优先级：

1. Rust Reference 与 edition 2024 规则；
2. Rust 1.97.1 标准库文档与对应源码；
3. Cargo Reference、rustc book 与 rustdoc book；
4. Rustonomicon 只补充 unsafe 边界，不覆盖 Reference 语义。

Julia 来源优先级：

1. Julia 1.12 Manual；
2. Julia 1.12 Standard Library；
3. Pkg documentation 与 Julia 1.12.6 对应源码；
4. 开发者文档只补充明确标注的实现观察，不覆盖 Manual 语义。

R 来源优先级：

1. R Language Definition 4.6.1；
2. R 4.6.1 base、recommended packages 与标准工具文档；
3. Writing R Extensions、R Installation and Administration；
4. R Internals 只补充明确标注的实现观察，不覆盖语言接口保证。

Lua 来源优先级：

1. Lua 5.5 Reference Manual；
2. Lua 5.5.0 官方源码包内 README、Makefile 与头文件；
3. Lua 5.5.0 对应源码只补充明确标注的实现观察，不覆盖 Reference Manual 的语义保证；
4. LuaJIT、旧版 Lua、LuaRocks 与宿主引擎文档不决定本课程语义。

Ruby 来源优先级：

1. Ruby 4.0 语法、核心类与标准库官方文档；
2. Ruby 4.0.6 release、官方源码归档和公开头文件；
3. RubyGems guides、Bundler manual 与 Rake 官方文档；
4. CRuby C API 与扩展文档；
5. CRuby 4.0.6 对应源码只补充明确标注的实现观察，不覆盖 Ruby 接口语义。

Dash、MDN、cppreference 和 Test262 可以帮助定位主题或发现遗漏，但不作为语义争议的
最终依据，也不决定目录结构。

## 语言测试边界

Python 使用 pytest；自定义协议类型保持最小，文件案例使用 pytest 临时目录。

C++ 使用 C++20、GoogleTest 和 CTest；GoogleTest 来自 `ohdev`，不复制依赖、不使用
FetchContent。测试目标启用 `-Wall -Wextra -Wpedantic -Werror`。不执行未定义行为；
优先使用 `requires`、type traits、`static_assert`、受控编译检查和必要注释。

Node.js 使用内置 `node:test` 和 ESM `.mjs`；普通测试不安装 npm 依赖。修改进程级状态
时用 `t.after()` 或 `try/finally` 恢复；网络只监听回环动态端口；异步测试等待明确事件
或 Promise，不用时间延迟猜测完成。

Go 使用标准 `testing`，执行时固定 `-count=1`，所有源码通过 `gofmt` 和 `go vet`。编译期
非法语义使用 `go/parser`、`go/types` 或隔离临时 module；并发测试使用 channel、
WaitGroup、context 或条件 predicate 建立明确同步，不用 `sleep` 猜测调度。网络只使用
loopback、`httptest` 或内存连接；全局状态、环境、cwd 和临时资源必须恢复。

Rust 使用 edition 2024、标准 `libtest` 与 Cargo；普通课程不引入第三方 crate。所有源码
通过 `rustfmt` 和 Clippy `-D warnings`；编译期非法语义使用隔离临时 crate 与真实 `rustc`
诊断。并发测试使用 channel、Barrier、Condvar 或显式轮询协议，不用 `sleep` 猜测调度；
unsafe 只在解释安全抽象边界时使用，并用可执行不变量约束。

Julia 使用 1.12.6、标准库 `Test`；普通课程不引入第三方 package。执行固定
`--startup-file=no`、`--history-file=no`、`--depwarn=error`、`--check-bounds=yes`，
并使用独立 `JULIA_DEPOT_PATH`。并发测试使用 Task、Channel、Event、Condition 或显式
predicate，不用 `sleep` 猜测调度；FFI 与 unsafe 测试用 `GC.@preserve` 和拥有对象约束生命周期。

R 使用 4.6.1、base `stopifnot` 与随 R 发行的标准工具；普通课程不安装第三方 CRAN package。
每个文件使用独立 `Rscript --vanilla` 进程、`R_LIBS_USER`、`R_USER` 与临时目录，并检查
options、环境变量、cwd、locale、library/search path、connections、sink、graphics device 和
random state 泄漏。并发测试按 fork/PSOCK 进程模型建立显式收集与清理，不描述成共享内存线程；
package 与 FFI 测试只构建仓库内本地 fixture，不访问公网。

Lua 使用 5.5.0、仓库内最小断言库和每文件独立解释器进程；执行清除所有 `LUA_INIT`、
`LUA_PATH` 与 `LUA_CPATH` 版本变量，并用 `lua -E` 和受控 repository/module path。
C API 宿主与 C module 使用锁定头文件和静态库，以 C11、`-Wall -Wextra -Wpedantic -Werror`
构建到 `/tmp`；coroutine 只描述为 cooperative control flow，不伪装成线程或 async runtime。

Ruby 使用 CRuby 4.0.6、仓库内最小断言库和每文件独立解释器进程；执行清除 `RUBYOPT`、
`RUBYLIB`、RubyGems 与 Bundler 用户设置，并隔离 `HOME`、gem path、bundle path 和临时目录。
普通课程只使用随 CRuby 发行的标准库与 default gem；包工作流仅构建仓库内 source gem，
使用 `--local` 和 path dependency，不访问公网。Thread、Fiber 与 Ractor 按真实共享、
协作和隔离模型说明；同步使用 Queue、Mutex、ConditionVariable 或显式 predicate，不用
sleep 猜测完成。C Extension 只使用锁定公开头文件，以 C11、`-Wall -Wextra -Werror` 构建；
CRuby 4 公开头文件会触发 GCC pedantic 诊断，因此不叠加 `-Wpedantic`，也不依赖 private header。

## 单任务接续与 Git

`NEXT.md` 始终只包含一个任务：`ready` 表示可开始，`in_progress` 必须写清剩余步骤，
`blocked` 必须写证据和解除条件。只有准备暂停、blocked、用户要求交接或 goal 完成时
更新它；Git 历史保存已经发生的过程。

默认完成一个连贯改动后做一个本地提交。大规模移动、概念内容、运行器和文档尽量分开。
默认不得 push、创建远程分支或 PR；只有用户明确授权当前任务时才执行。禁止 force push
和整体 squash，保留工作树中的用户改动。

语言集合已经冻结，现有 49 个 topic 正在接受语义审计。优先修正、合并或删除无效主题；
新增共同问题优先归入现有 family，只有无法归类的稳定问题域才建立新 family。不要为了
维持旧统计补文件，也不要把一次具体任务机械转换成一个新 topic。

旧 checklist-first 实现截止于 commit `662e0d1`。查证历史时使用 `git show`，不要恢复
旧生成数据。
