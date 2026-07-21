# Polyglot：通过测试学习编程语言

Polyglot 用可阅读、可执行的测试案例学习 Python、C++、Node.js、Julia、R、Go 和 Rust。

项目不仅展示“一个 API 怎么调用”，还要讲清楚：

- 基础语法和常见工作流；
- 高阶语言机制；
- 表层语法、内置函数与底层协议之间的关系；
- 官方语义中容易误解的行为和真实常见坑；
- 示例逻辑是否能通过对应测试框架验证。

例如 Python 中不仅要展示 `bool(value)`，还要展示真假值判断如何依次使用
`__bool__()` 和 `__len__()`；不仅展示 `for`，还要展示迭代协议和历史序列
fallback。

## 当前阶段

Python 3.10 基线已经完成统一验证。`ohdev` 容器中的解释器是 Python 3.10.12，
官方内容来源锁定到 Python 3.10 文档系列。

C++20 基线也已完成统一验证。当前工具链是 GCC/libstdc++ 11.4.0、CMake 3.22.1，
以及 `ohdev` 中 OpenHarmony 工作区自带的 GoogleTest 1.16.0。构建输出位于
`/tmp/polyglot-cpp-build`，普通测试运行不下载依赖。

Node.js 基线已完成统一验证。运行时锁定为 Node.js 24.18.0 LTS，语言规范锁定到
ECMAScript 2025 与 ECMA-402 12th edition，包管理器为随运行时提供的 npm 11.16.0。
测试使用内置 `node:test`，普通执行不安装依赖、不访问公网。

当前验证证据：

- `languages/python/` 有 178 个测试文件，编号从 `001` 连续到 `178`；
- 每个文件都有 `polyglot-covers` 覆盖标记，`stdlib/` 分类目录与编号范围一致；
- 所有测试代码按 Unicode 字符计数均不超过 100 列；
- 严格全量命令 `./tools/run.sh python -q --timeout=30 -W error` 的结果为
  `5012 passed, 52 skipped`；
- 52 个 skip 都来自明确的平台或可选能力差异，例如 Windows API、Tk、
  IANA zone data、特定 dbm backend 和 ensurepip，不是失败用例。
- `languages/cpp/` 有 160 个测试文件，编号从 `001` 连续到 `160`；语言语义
  独立成区，C++20 标准库按 17 个连续服务分区组织，每个文件都有唯一覆盖标记；
- 全部 C++ 源码通过仓库 `.clangd` 的主机静态诊断，测试代码按 Unicode 字符计数
  均不超过 100 列；
- 全量命令 `./tools/run.sh cpp` 的结果为 `1409 passed, 15 skipped`；15 个 skip
  都明确记录了 GCC/libstdc++ 11、标准模块、平台行为或已知实现缺陷的能力边界。
- `languages/nodejs/` 有 107 个测试文件，编号从 `001` 连续到 `107`；内容分为
  ECMAScript 语言、Node 核心与 Web API、npm 和包工作流三个学习分区；
- Node.js 每个文件都有唯一 `polyglot-covers` 标记，全部测试代码按 Unicode 字符
  计数均不超过 100 列；
- 全量命令 `./tools/run.sh nodejs` 的结果为 `935 passed`，没有失败或跳过案例。

下一阶段的唯一入口仍是 `NEXT.md`；不要从 README 推测并行任务。

## 新对话从哪里开始

只需要读取：

```text
AGENTS.md
sources.lock
NEXT.md
```

`NEXT.md` 永远只保存一个下一步任务。完整标准库对象清单、临时数据库和覆盖报告以后按需生成到 `/tmp`，不进入 Git。

## 仓库结构

```text
AGENTS.md                   跨对话执行契约
README.md                   项目目标和当前阶段
NEXT.md                     唯一的当前任务
sources.lock                语言版本和权威资料入口
project.json                稳定语言范围与测试框架
languages/python/           Python 教学测试
languages/cpp/              C++20 教学测试与 CMake 入口
languages/nodejs/           ECMAScript、Node.js 与 npm 教学测试
tools/run.sh                宿主机 Docker 入口
tools/run-in-container.sh   容器内测试入口
```

Python 测试按学习主题组织，而不是按官方文档的每个对象机械生成：

```text
languages/python/
  language/      语言语义、表达式、语句和数据模型
  builtins/      内置类型与内置函数
  stdlib/        标准库模块与跨 API 工作流
    030-035_file_and_directory_access/  文件与目录访问
    036-040_text_processing/            文本处理服务
```

主题允许跨层。例如真假值测试同时包含布尔表达式、`bool()`、`__bool__()` 和 `__len__()`，因为把它们放在一个测试套中更容易理解真实分派关系。

`stdlib/` 已按 Python 3.10 官方标准库目录的服务类别组织。目录名前缀同时标明
其中的测试编号范围；目录用于控制标准库规模，不改变全局文件编号规则，也不会
细分成“每个模块一个文件夹”。跨模块工作流归入其主要学习目标所在的类别。

同一学习阶段的文件按三位数连续编号，编号是稳定的推荐阅读顺序，主题后缀用于
搜索。例如：

```text
test_001_truth_value_testing.py
test_002_comparison_semantics.py
test_003_binary_operator_dispatch.py
```

编号在整个 `languages/python/` 中全局连续，不会在子目录中重新从 001 开始。
新增文件必须先查看所有 Python 子目录已有的最大编号，再使用下一个编号；不要
为了插入新主题批量重排已提交编号。若后来发现遗漏，优先补充到原主题文件，
确实需要独立文件时追加新编号，并在注释中说明它依赖的前置主题。

## 执行模型

宿主机不直接运行 Python 或其他语言工具：

```text
./tools/run.sh
    ↓ docker exec ohdev
./tools/run-in-container.sh
    ↓ pytest / 编译器 / 对应测试框架
```

Python 严格全量验证执行：

```bash
./tools/run.sh doctor
./tools/run.sh python -q --timeout=30 -W error
```

以后修改 Python 文件时，先复跑受影响类别，再运行上述完整命令；只有两者都通过，
才能继续称当前 Python 基线为 verified。

C++ 阶段验证执行：

```bash
./tools/run.sh cpp
./tools/run.sh cpp -R '^test_001_'
```

第一个命令配置、增量编译并运行全部 CTest；第二个命令用于按文件编号筛选已发现的
GoogleTest 案例。C++ 测试在小批次和类别边界提前验证，不等全部测试套写完后首次编译。

Node.js 全量与单文件验证执行：

```bash
./tools/run.sh nodejs
./tools/run.sh nodejs \
  languages/nodejs/01_language/test_001_primitive_values_numeric_models_and_equality.mjs
```

Node.js 测试固定使用容器内的 Node.js 24.18.0 和内置 `node:test`。单文件路径必须作为
第一个附加参数传入；测试仍由宿主机入口转交给 `ohdev`，不直接调用宿主机 Node.js。

主机阅读 C++ 代码使用仓库根目录的 `.clangd`。它让主机已有的 clangd 读取 macOS SDK，
并把 Docker 挂载对应的 GoogleTest 头文件加入索引；这只提供跳转、补全和静态诊断，
不改变所有编译与测试仍在 `ohdev` 中执行的边界。

## 历史

重置前的 checklist、Dash 快照、审计脚本和 handoff source 保留在 commit `662e0d1`：

```bash
git show 662e0d1:checklists/python/language.checklist.json
git show 662e0d1:checklists/python/stdlib.tasks.json
```

这些资料可以用于查证，但不是当前仓库结构。
