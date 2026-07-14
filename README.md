# Polyglot：通过测试学习编程语言

Polyglot 用可阅读、可执行的测试案例学习 Python、C++、Node.js、Julia、R、Go 和 Rust。

项目不仅展示“一个 API 怎么调用”，还要讲清楚：

- 基础语法和常见工作流；
- 高阶语言机制；
- 表层语法、内置函数与底层协议之间的关系；
- 官方语义中容易误解的行为和真实常见坑；
- 示例逻辑是否能通过对应测试框架验证。

例如 Python 中不仅要展示 `bool(value)`，还要展示真假值判断如何依次使用 `__bool__()` 和 `__len__()`；不仅展示 `for`，还要展示迭代协议和历史序列 fallback。

## 当前阶段

当前进入 Python 3.10 测试套编写阶段。`ohdev` 容器中的解释器是 Python 3.10.12，官方内容来源锁定到 Python 3.10 文档系列。

按照当前约定：

- 先连续编写 Python 测试套；
- 测试文件使用三位数编号表达推荐阅读顺序，例如 `test_001_...py`；
- 暂不运行 pytest；
- Python 编写阶段结束后统一在 `ohdev` 中执行；
- 当前所有 Python 文件都应视为 draft / unverified；
- 可以按连贯主题创建本地 authoring checkpoint commit，但这些 commit 不代表测试通过。

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
tools/run.sh                宿主机 Docker 入口
tools/run-in-container.sh   容器内测试入口
```

Python 测试按学习主题组织，而不是按官方文档的每个对象机械生成：

```text
languages/python/
  language/      语言语义、表达式、语句和数据模型
  builtins/      内置类型与内置函数
  stdlib/        标准库模块与跨 API 工作流
    file_and_directory_access/  文件与目录访问
    text_processing/            文本处理服务
```

主题允许跨层。例如真假值测试同时包含布尔表达式、`bool()`、`__bool__()` 和 `__len__()`，因为把它们放在一个测试套中更容易理解真实分派关系。

`stdlib/` 会继续按 Python 3.10 官方标准库目录的服务类别扩展，例如
`binary_data/`、`data_types/`、`concurrency/` 和 `networking/`。分类目录在写入
第一个测试套时才创建；目录用于控制标准库规模，不改变文件编号规则，也不会细分成
“每个模块一个文件夹”。跨模块工作流归入其主要学习目标所在的类别。

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

Python 编写阶段结束后，统一执行：

```bash
./tools/run.sh doctor
./tools/run.sh python
```

目前不要因为单个文件写完就运行测试；这一约定会在进入验证阶段时更新。

## 历史

重置前的 checklist、Dash 快照、审计脚本和 handoff source 保留在 commit `662e0d1`：

```bash
git show 662e0d1:checklists/python/language.checklist.json
git show 662e0d1:checklists/python/stdlib.tasks.json
```

这些资料可以用于查证，但不是当前仓库结构。
