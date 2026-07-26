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

当前用 Python、C++ 和 Node.js 建立双轴学习结构；Julia、R、Go 和 Rust 保留在规划
范围，但暂停新增语言，直到 `NEXT.md` 明确改变阶段。

测试代码是主要产品。不要建立大型 Markdown/JSON checklist、Dash 对象快照、数据库
快照、完整覆盖清单或 `chatgpt-sources/`。

## 双轴学习结构

### 纵向课程：`languages/`

`languages/` 必须让读者只沿一门语言目录就能完整学习：

```text
languages/python/{language,builtins,stdlib}/
languages/cpp/{language,standard_library}/
languages/nodejs/{language,node_core,npm_and_package_workflows}/
```

现有详细测试、标准库和运行时工作流始终留在语言主线。不要为了建立概念对照而移动、
裁剪或拆散课程文件。

课程文件使用 `test_NNN_topic.<ext>`；`NNN` 在同一语言内全局唯一、连续且稳定。新文件
使用当前最大编号的下一个值，不批量重排已提交编号。每个课程文件保留稳定的
`polyglot-covers` ID。

### 横向对照：`concepts/`

`concepts/NN_family/NN_topic/` 是独立编写的精简对照层，不收纳原课程大文件。顶层
两位编号表示稳定章节，二级两位编号表示章节内的具体主题。一个主题只回答一个明确问题；
至少两门语言存在真实对照价值时才建立，不要求机械补齐所有语言。

顶层预计保持约 10–15 个章节，不要求预先确定精确数量；主题总数不设固定上限。只有
出现首个主题时才创建章节，不预建空目录。同类新主题在已有章节内递增编号。

每个语言子目录默认只有一个局部命名测试：

```text
concepts/01_values_and_comparison/01_truthiness/python/test_truthiness.py
concepts/01_values_and_comparison/01_truthiness/cpp/test_truthiness.cpp
concepts/01_values_and_comparison/01_truthiness/nodejs/test_truthiness.mjs
```

概念测试必须：

- 在顶部用两三行列出共同问题矩阵；
- 使用 `polyglot-family: <name>`，名称与顶层章节一致；
- 使用 `polyglot-concept: <name>`，名称与目录和文件一致；
- 使用 `polyglot-related: languages/<language>/...` 指向真实完整课程；
- 围绕相同输入类别和观察点组织断言；
- 对缺失机制、编译期非法、未定义行为或规范差异使用必要注释；
- 只复制比较所需的最小代表案例，不复刻完整课程。

概念局部文件名不使用语言课程编号，不声明 `polyglot-covers`，不计入语言课程文件数。
测试入口保持唯一的 `test_<topic>`；语言目录允许按需增加 `fixtures/` 或 `support/`。
少量语义重复是双轴设计的一部分，不要以“去重”为理由重新移动课程文件。

标准库默认留在语言主线。只有具体问题值得比较时才另写精简概念测试；禁止把一组标准库
课程文件整体迁入 `concepts/`。

## 通用内容规范

- 案例展示正常用法、高阶语义、隐式机制、实际工作流和真实陷阱。
- 能执行的差异使用断言；不能安全执行的内容使用特性检测、类型检查、skip 或注释。
- 中文注释解释分派、求值顺序、生命周期、返回语义、版本差异和迁移陷阱，不逐行复述。
- 每行按 Unicode 字符数不超过 120，编写时主动换行。
- 一个课程文件围绕一个连贯主题；数百行本身不是拆分理由。
- 不足 100 行的相邻同类课程文件是复查合并信号；合并保留覆盖 ID 和教学案例。
- “覆盖全面”指正常语义、协议入口、关键 fallback、常用工作流和真实陷阱，不制造
  穷举式输入或类型组合矩阵。
- 不依赖公网、sleep、真实用户目录或持久机器状态；临时资源写入 `/tmp/polyglot-*`
  或测试框架临时目录并可靠清理。

## 运行与门禁

宿主机不运行目标语言工具。所有解释器、编译器和测试框架位于 `ohdev`，统一入口为
`./tools/run.sh`。

纵向课程：

```bash
./tools/run.sh python -q --timeout=30 -W error
./tools/run.sh cpp
./tools/run.sh nodejs
```

横向概念：

```bash
./tools/run.sh concept 01_values_and_comparison/01_truthiness
./tools/run.sh family 01_values_and_comparison
./tools/run.sh concepts
```

结构门禁：

```bash
./tools/run.sh check
```

门禁分别验证语言路径、课程连续编号和覆盖标记、章节与主题连续编号、唯一测试入口、
至少两门语言、`polyglot-family`、`polyglot-concept`、`polyglot-related` 目标和
Unicode 120 字符行宽。它不能替代人工语义审阅；提交主题时还要确认各语言确实回答
同一问题。

修改测试时先跑受影响课程或单个概念，再跑对应全量。只有两者都通过才能称为 verified。

## 当前基线

- Python 3.10：课程 `001`–`178`；Python 3.10.12；`5025 passed, 39 skipped`。
- C++20：课程 `001`–`160`；GCC/libstdc++ 11.4.0、CMake 3.22.1、
  GoogleTest 1.16.0；`1409 passed, 15 skipped`。
- Node.js：课程 `001`–`107`；Node.js 24.18.0、ECMAScript 2025、
  ECMA-402 12th edition、npm 11.16.0；`935 passed`。
- 横向层有三个章节、四个主题：Python `16 passed`、C++ `15 passed`、Node.js `16 passed`。

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

## 单任务接续与 Git

`NEXT.md` 始终只包含一个任务：`ready` 表示可开始，`in_progress` 必须写清剩余步骤，
`blocked` 必须写证据和解除条件。只有准备暂停、blocked、用户要求交接或 goal 完成时
更新它；Git 历史保存已经发生的过程。

默认完成一个连贯改动后做一个本地提交。大规模移动、概念内容、运行器和文档尽量分开。
默认不得 push、创建远程分支或 PR；只有用户明确授权当前任务时才执行。禁止 force push
和整体 squash，保留工作树中的用户改动。

旧 checklist-first 实现截止于 commit `662e0d1`。查证历史时使用 `git show`，不要恢复
旧生成数据。
