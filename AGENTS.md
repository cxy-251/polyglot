# Agent Contract

这个仓库必须让一场全新的对话只依靠工作树继续，不依赖以前的聊天记录。

## 开始工作

每场对话只执行一次以下启动流程：

1. 查看 `git status --short` 和最近的 Git commit。
2. 阅读 `README.md`、`sources.lock` 和 `NEXT.md`。
3. 只把 `NEXT.md` 作为当前任务入口，不寻找或创建完整任务清单。
4. 先阅读任务列出的官方资料、目标文件、覆盖点和已有案例，再修改代码。
5. 工作中断时，把准确剩余步骤写入 `NEXT.md` 的 `Handoff`。

上下文压缩、自动续写和同一 goal 内的阶段提交不算新对话；文件未被外部修改时，不要
反复读取启动文件。

## 项目目标

> Polyglot 通过可执行测试，对照学习不同语言如何解决相同问题，理解它们的共同概念、
> 语义差异、底层机制和迁移陷阱。

当前用 Python、C++ 和 Node.js 建立稳定框架；Julia、R、Go 和 Rust 保留在规划范围，
但暂停新增语言，直到 `NEXT.md` 明确改变阶段。

测试代码是主要产品。案例应展示基础语法、正常用法、高阶语义、隐式机制、实际工作流
和真实陷阱。不要重新建立大型 Markdown/JSON checklist、Dash 对象快照、数据库快照、
完整覆盖清单或 `chatgpt-sources/`。

## 混合目录结构

`concepts/NN_name/<language>/` 围绕共同问题并排保存各语言测试；
`languages/<language>/` 保留无法合理对照的语言特有机制及完整标准库路径。

内容进入 `concepts/` 必须同时满足：

1. 回答语言无关的共同问题；
2. 至少两门语言存在真实对照价值；
3. 并排阅读有助于理解语义差异或迁移陷阱。

不要求每个概念拥有三门语言，不把相似但不等价的机制强行对齐，不机械迁移全部核心
语义文件。先逐文件审计再建立目录，不预建空分类。模板、值类别等语言特有机制留在
`language_specific/`；Python 标准库、C++ 标准库、Node 核心模块及 npm 工作流仍留在
各自 `languages/` 路径。

能够执行的差异使用测试和断言表达；编译期错误、未定义行为、规范差异和平台差异使用
必要注释、特性检测或有理由的 skip。跨语言提示解释机制差异，不重复逐行代码。

移动现有内容优先使用 `git mv`，保留原编号、`polyglot-covers` ID、断言、注释和历史。
大规模移动与内容修改分开提交。

## 通用测试规范

- 文件名使用 `test_NNN_topic.<ext>`；`NNN` 在同一语言跨 `concepts/` 和 `languages/`
  全局唯一、连续且稳定，与其他语言编号无关。
- 新文件使用该语言当前最大编号的下一个值；不为插入主题批量重排已提交编号。
- 一个文件围绕一个连贯学习主题；相关小模块可以合并，数百行本身不是拆分理由。
- 不足 100 行的相邻同类文件是复查合并的强信号；合并必须保留覆盖 ID 和教学案例。
- 中文注释详细但必要，解释分派、求值顺序、生命周期、返回语义、版本差异和陷阱，
  不逐行复述代码。
- 每行按 Unicode 字符数不超过 120；编写时主动换行，不留到多轮审查后机械整改。
- “覆盖全面”指正常语义、协议入口、关键 fallback、常用工作流和真实陷阱，不制造
  穷举式输入或类型组合矩阵。
- 每个测试文件声明稳定的 `polyglot-covers` ID；状态由工具扫描代码得出。
- 不依赖公网、sleep、真实用户目录或持久机器状态；临时资源写入 `/tmp/polyglot-*`
  或测试框架临时目录，并可靠清理。

提交前在 `ohdev` 中运行 `./tools/run.sh check`。该门禁验证合法路径、覆盖标记、连续
编号、共同概念至少含两门语言，以及仓库内未忽略文本的 Unicode 120 字符行宽。

## 当前已验证基线

- Python 3.10：`001`–`178`；Python 3.10.12；严格命令
  `./tools/run.sh python -q --timeout=30 -W error`；结果 `5012 passed, 52 skipped`。
- C++20：`001`–`160`；GCC/libstdc++ 11.4.0、CMake 3.22.1、GoogleTest 1.16.0；
  `./tools/run.sh cpp` 结果 `1409 passed, 15 skipped`。
- Node.js：`001`–`107`；Node.js 24.18.0、ECMAScript 2025、ECMA-402 12th edition、
  npm 11.16.0；`./tools/run.sh nodejs` 结果 `935 passed`。

所有 skip 都有明确的实现能力、平台行为或可选依赖原因。修改测试时先跑受影响范围，
再跑对应语言全量；两者通过后才能继续称为 verified。准确工具链与官方资料见
`sources.lock`。

## Python 内容来源与规范

来源优先级：

1. Python Language Reference；
2. Python Data Model；
3. Built-in Functions / Built-in Types；
4. Python Standard Library Reference；
5. 仅用于补充版本演进或设计背景的 PEP。

使用 pytest。共同语义可位于 `concepts/*/python/`；特有机制位于
`languages/python/language_specific/`；标准库按官方服务类别留在
`languages/python/stdlib/`，不为每个模块单独建目录。

协议示例与触发它的语法或 API 放在一起。自定义协议类型保持最小；文件案例使用 pytest
临时目录。Dash 和对象索引只用于发现遗漏，不决定测试结构或学习优先级。

## C++ 内容来源与规范

来源优先级：

1. ISO/IEC 14882:2020 与对应 WG21 工作草案；
2. WG21 提案、缺陷报告和编辑报告；
3. GCC 11.4 与 libstdc++ 11.4 手册；
4. C++ Core Guidelines；
5. 只决定构建行为的 CMake 与 GoogleTest 官方文档。

cppreference 只帮助定位术语和标准章节，不作为语义争议的最终依据。Boost、POSIX 和
第三方 API 不属于当前标准库覆盖范围。

使用 C++20、GoogleTest 和 CTest。共同语义可位于 `concepts/*/cpp/`；特有机制位于
`languages/cpp/language_specific/`；标准库留在 `languages/cpp/standard_library/`。
CMake 使用 `ohdev` 已有 GoogleTest 源码，不复制依赖、不使用 FetchContent。

不执行未定义行为来“证明”未定义行为；优先使用 `requires`、type traits、
`static_assert`、受控编译检查和注释。GCC 11.4 缺失能力必须通过特性检测与说明保留。
测试目标使用 `-Wall -Wextra -Wpedantic -Werror`。

## Node.js 内容来源与规范

来源优先级：

1. ECMA-262 16th edition；
2. ECMA-402 12th edition；
3. Node.js 24.18.0 API 文档与对应源码；
4. Node.js 官方指南；
5. 仅补充演进和实现差异的 TC39 提案、Node.js issue 与变更记录。

MDN 只帮助定位概念，Test262 只用于发现遗漏，不作为争议的最终依据或复制来源。

使用内置 `node:test` 和 `node:assert/strict`，以 ESM `.mjs` 为主。共同语义可位于
`concepts/*/nodejs/`；特有机制、Node 核心和 npm 工作流分别位于
`languages/nodejs/language_specific/`、`node_core/` 和 `npm_and_package_workflows/`。
普通测试不安装 npm 依赖、不提交 `node_modules/`。

修改进程级监听器、环境变量或全局对象时用 `t.after()` 或 `try/finally` 恢复。网络案例
只监听回环地址和动态端口；异步测试等待明确事件、Promise 或资源关闭，不用时间延迟猜测。

## 单任务接续

`NEXT.md` 始终只包含一个任务：

- `ready`：下一场对话可直接开始；
- `in_progress`：已有代码或分析，`Handoff` 必须写清剩余步骤；
- `blocked`：写出证据和解除条件。

只有准备暂停、任务 blocked、用户要求交接或整个 goal 完成时才更新 `NEXT.md`。Git 历史
保存已经发生的过程，`NEXT.md` 不累积历史任务。阶段提交只表示一个连贯改动完成，不等于
测试已通过。

## 执行与 Git 边界

- 宿主机不安装或直接调用目标语言运行时；所有解释器、编译器和测试框架位于 `ohdev`。
- 宿主机入口是 `./tools/run.sh`，容器入口是 `./tools/run-in-container.sh`。
- 默认完成一个连贯概念或语言服务类别后做一个本地提交，不为单文件频繁提交。
- 默认不得 push、创建远程分支或 PR；只有用户明确授权当前任务时才可执行相应远程操作。
- 不 force push，不整体 squash；工作树中已有的用户改动必须保留。

旧 checklist-first 实现截止于 commit `662e0d1`。查证历史时使用 `git show`，不要恢复
旧生成数据。
