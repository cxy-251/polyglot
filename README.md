# Polyglot Stdlib By Example

这是一个用“可运行示例测试”学习主流编程语言标准库的项目。

当前阶段先暂停写测试，重点构建各语言 checklist 的数据模型、来源基线、轻量审计脚本和任务渲染流程。Python、C++、Node.js、Julia、R、Go、Rust 都是 active checklist；其中 Python/C++ 的模型更细，其他语言先采用 Dash-backed 初版。

## 当前范围

项目语言范围固定为：

- Python: active checklist
- C++: active checklist
- Node.js: active checklist
- Julia: active checklist
- R: active checklist
- Go: active checklist
- Rust: active checklist

其他语言暂时不进入项目。根目录只保留这一个 `README.md`，不要在子目录散落 README。

## 项目结构

```text
catalog.json
checklists/
  python/
    schema.json
    language.checklist.json
    stdlib.baseline.json
    stdlib.objects.json
    stdlib.checklist.json
    stdlib.tasks.json
  cpp/
    schema.json
    language.checklist.json
    stdlib.baseline.json
    stdlib.objects.json
    stdlib.checklist.json
    stdlib.tasks.json
  nodejs/
    schema.json
    language.checklist.json
    stdlib.baseline.json
    stdlib.objects.json
    stdlib.checklist.json
    stdlib.tasks.json
  julia/   (same six JSON files)
  r/       (same six JSON files)
  go/      (same six JSON files)
  rust/    (same six JSON files)
chatgpt-sources/
  python/
  cpp/
  nodejs/
  julia/
  r/
  go/
  rust/
tools/
  run.sh
  run-in-container.sh
  cpp_checklist_status.py
  cpp_stdlib_audit.py
  cpp_render_task.py
  dash_language_configs.py
  dash_docset.py
  dash_stdlib_common.py
  go_checklist_status.py
  go_stdlib_audit.py
  go_render_task.py
  julia_checklist_status.py
  julia_stdlib_audit.py
  julia_render_task.py
  nodejs_checklist_status.py
  nodejs_stdlib_audit.py
  nodejs_render_task.py
  python_checklist_status.py
  python_stdlib_audit.py
  python_render_task.py
  python_api_inventory.py
  r_checklist_status.py
  r_stdlib_audit.py
  r_render_task.py
  rust_checklist_status.py
  rust_stdlib_audit.py
  rust_render_task.py
languages/
```

`languages/` 当前可以为空；未来恢复写测试时再按 `languages/<language-id>/` 建立测试文件。不要用子目录 README 填充结构说明。

## Python 数据源

`checklists/python/` 是当前核心工作区：

| 文件 | 职责 | 是否手改 |
| --- | --- | --- |
| `schema.json` | Python checklist/task 数据结构和状态枚举。 | 改数据模型时才改。 |
| `language.checklist.json` | Python 语言核心：builtins、常量、异常、内置类型、data model、magic methods、协议分派。 | 可以人工维护。 |
| `stdlib.baseline.json` | 官方标准库目录快照，来自 Python 文档 `library/index.html`。 | 不手改，用脚本刷新。 |
| `stdlib.objects.json` | 官方 Sphinx `objects.inv` 快照，过滤到 `py:*` 且 `library/...` 的 API 候选对象。 | 不手改，用脚本刷新。 |
| `stdlib.checklist.json` | 由 baseline + objects 派生的完整 stdlib 分类骨架。 | 不逐行人工精炼。 |
| `stdlib.tasks.json` | 唯一的 Python stdlib 人工任务文件；一个 task 用 `covers` 关联多个官方 API，用 `cases` 写测试场景。 | 可以人工维护，是 stdlib 长期重点。 |

来源关系：

```text
https://docs.python.org/3/library/index.html -> stdlib.baseline.json
https://docs.python.org/3/objects.inv         -> stdlib.objects.json

stdlib.baseline.json + stdlib.objects.json -> stdlib.checklist.json
stdlib.tasks.json                          -> curated runnable-example tasks
```

`stdlib.checklist.json` 是审计兜底，不应该变成长期人工维护的大清单。新的人工判断优先进入 `stdlib.tasks.json`。不要把 Python stdlib tasks 拆成多个文件；目标是让一个文件覆盖标准库里普遍需要掌握的 API。

## Task 模型

当前 `stdlib.tasks.json` 有 53 个 curated tasks，逐步覆盖普遍需要掌握的标准库 API。优先级是常用性和学习价值，不是机械覆盖 `objects.inv` 的每一个名字。

- `list`
- `dict`
- `str`
- `heapq`、`pathlib`、`json`
- `collections`、`itertools`、`functools`、`operator`
- `re`、`datetime`、`zoneinfo`
- `math`、`statistics`、`random`
- `decimal`、`fractions`

task 形状示例：

```json
{
  "id": "heapq.min_heap_workflow",
  "target": "heapq",
  "module": "heapq",
  "title": "Use a list as a min-heap",
  "covers": ["heapq.heapify", "heapq.heappush", "heapq.heappop"],
  "cases": [
    "heapify mutates a list in place",
    "successive heappop calls produce ascending values"
  ],
  "protocols": ["__lt__"],
  "status": "todo",
  "test_files": []
}
```

`covers` 必须能对应到 `stdlib.objects.json` 里的官方对象名。`cases` 写学习场景，不写边界题清单。

## C++ 数据源

`checklists/cpp/` 采用同样的 checklist-first 思路。C++ 没有 Python `objects.inv` 这种官方 Sphinx 对象索引，所以本项目使用 cppreference 的标准库 header 组织和本机 Dash C++.docset 作为离线可导航参考，生成 header/symbol baseline、objects 索引和派生 checklist 骨架：

| 文件 | 职责 | 是否手改 |
| --- | --- | --- |
| `schema.json` | C++ checklist/task 数据结构和状态枚举。 | 改数据模型时才改。 |
| `language.checklist.json` | C++ 语言核心：RAII、值/引用/move 语义、模板、迭代器、lambda、异常边界。 | 可以人工维护。 |
| `stdlib.baseline.json` | 标准库 header + symbol baseline，用来约束 task `covers`。包含 active、compatibility、deprecated、removed、gated 等可用性状态。 | 不逐行人工维护，用 `tools/cpp_stdlib_audit.py refresh-baseline` 重写。 |
| `stdlib.objects.json` | C++ API object 索引；优先从本机 Dash C++.docset 导入，可显式使用 cppreference Doxygen tag XML，缺失 symbol 由 baseline fallback 补洞。 | 不手改，用脚本刷新。 |
| `stdlib.checklist.json` | 由 baseline + objects 派生的完整 stdlib 分类骨架。 | 不逐行人工精炼。 |
| `stdlib.tasks.json` | 唯一的 C++ stdlib 人工任务文件；覆盖普遍需要掌握的标准库 API。 | 可以人工维护，是 C++ stdlib 长期重点。 |

C++ baseline、objects 和 checklist 都是“事实/审计层”，不是学习计划。baseline 按 cppreference 的标准库 header 页组织，当前覆盖 C++23 baseline，并把 C++26 library facilities 标成 `gated`。objects 默认读取 `~/Library/Application Support/Dash/DocSets/C++/C++.docset`；如果显式提供 cppreference HTML book archive 里的 `cppreference-doxygen-web.tag.xml` 或 `cppreference-doxygen-local.tag.xml`，则使用 tag XML。Dash/tag 都没有覆盖到的 baseline symbol 会标成 `baseline-fallback`，保证 task covers 仍然可审计。常用性筛选只发生在 `stdlib.tasks.json`。

来源关系：

```text
https://en.cppreference.com/w/cpp/header
https://en.cppreference.com/w/cpp/standard_library
https://en.cppreference.com/w/cpp/symbol_index
        -> tools/cpp_stdlib_audit.py refresh-baseline
        -> checklists/cpp/stdlib.baseline.json

local Dash C++.docset or cppreference HTML book archive / Doxygen tag XML
        -> tools/cpp_stdlib_audit.py refresh-objects
        -> checklists/cpp/stdlib.objects.json

stdlib.baseline.json + stdlib.objects.json
        -> tools/cpp_stdlib_audit.py refresh-checklist
        -> checklists/cpp/stdlib.checklist.json

checklists/cpp/stdlib.tasks.json -> curated runnable-example tasks
```

`stdlib.checklist.json` 和 Python 版本一样是审计兜底，不应该变成长期人工维护的大清单。不要把 C++ stdlib tasks 拆成多个文件。

C++ task 形状示例：

```json
{
  "id": "containers.vector_sequence",
  "title": "Use std::vector as the default sequence container",
  "headers": ["<vector>"],
  "covers": ["std::vector", "std::vector::push_back", "std::vector::at"],
  "cases": [
    "push_back and emplace_back grow a contiguous sequence",
    "at performs checked access while operator[] is unchecked"
  ],
  "status": "todo",
  "test_files": []
}
```

C++ `covers` 必须能对应到 `checklists/cpp/stdlib.objects.json` 的 object `name`；baseline fallback 会保证 baseline symbols 也进入 objects。和 Python 一样，不要把 C++ stdlib tasks 拆成多个文件。

## Dash-backed 语言

Node.js、Julia、R、Go、Rust 当前采用同一套 Dash-backed 初版模型。每个语言在 `checklists/<language-id>/` 下都有 6 个 JSON 文件：

- `schema.json`
- `language.checklist.json`
- `stdlib.baseline.json`
- `stdlib.objects.json`
- `stdlib.checklist.json`
- `stdlib.tasks.json`

`stdlib.baseline.json`、`stdlib.objects.json`、`stdlib.checklist.json` 由本机 Dash docset 生成，是机器事实层和审计层；`stdlib.tasks.json` 是唯一的人工 stdlib 学习任务文件。不要把这些语言的 tasks 拆成多个文件。

默认 Dash 来源：

| 语言 | Dash docset | 对象范围 |
| --- | --- | --- |
| Node.js | `NodeJS.docset` | Node API page 里的 module/class/function/property/event/error。 |
| Julia | `Julia.docset` | Base/Core 和 stdlib 文档对象。 |
| R | `R.docset` | R distribution/recommended packages 里的 package/function。 |
| Go | `Go.docset` | public Go standard packages，排除 internal/vendor。 |
| Rust | `Rust.docset` | `std::` / `/std/` API 对象。 |

刷新模式：

```bash
python3 tools/nodejs_stdlib_audit.py refresh-all
python3 tools/julia_stdlib_audit.py refresh-all
python3 tools/r_stdlib_audit.py refresh-all
python3 tools/go_stdlib_audit.py refresh-all
python3 tools/rust_stdlib_audit.py refresh-all
```

这些命令不访问网络；它们读取 `~/Library/Application Support/Dash/DocSets`。`refresh-all` 只重写机器层 baseline/objects/checklist，不重写人工维护的 `stdlib.tasks.json`。

## 工具

宿主机入口仍然是 `./tools/run.sh`，它会通过 Docker `exec` 进入 `ohdev`：

```bash
./tools/run.sh list
./tools/run.sh checklist python
./tools/run.sh checklist cpp
./tools/run.sh checklist nodejs
./tools/run.sh checklist julia
./tools/run.sh checklist r
./tools/run.sh checklist go
./tools/run.sh checklist rust
./tools/run.sh python
./tools/run.sh cpp
./tools/run.sh all-checklists
```

当前各语言入口等价于对应 checklist 状态检查，不跑 pytest、编译器或语言测试。

语言专用工具都以语言前缀开头：

```bash
python3 tools/cpp_checklist_status.py
python3 tools/cpp_stdlib_audit.py audit
python3 tools/cpp_stdlib_audit.py refresh-baseline
python3 tools/cpp_stdlib_audit.py refresh-objects
python3 tools/cpp_stdlib_audit.py refresh-objects --dash-docset "/path/to/C++.docset"
python3 tools/cpp_stdlib_audit.py refresh-objects --source-dir /path/to/cppreference-html-book
python3 tools/cpp_stdlib_audit.py refresh-objects --no-dash
python3 tools/cpp_stdlib_audit.py refresh-checklist
python3 tools/cpp_render_task.py vector
python3 tools/cpp_render_task.py std::vector::push_back
python3 tools/go_checklist_status.py
python3 tools/go_stdlib_audit.py audit
python3 tools/go_render_task.py strings
python3 tools/julia_checklist_status.py
python3 tools/julia_stdlib_audit.py audit
python3 tools/julia_render_task.py Base.Dict
python3 tools/nodejs_checklist_status.py
python3 tools/nodejs_stdlib_audit.py audit
python3 tools/nodejs_render_task.py path
python3 tools/python_checklist_status.py python
python3 tools/python_stdlib_audit.py audit
python3 tools/python_stdlib_audit.py audit --objects heapq pathlib json list dict str
python3 tools/python_render_task.py heapq
python3 tools/python_render_task.py list.sort
python3 tools/python_api_inventory.py list dict str
python3 tools/r_checklist_status.py
python3 tools/r_stdlib_audit.py audit
python3 tools/r_render_task.py base
python3 tools/rust_checklist_status.py
python3 tools/rust_stdlib_audit.py audit
python3 tools/rust_render_task.py std::vec
```

刷新官方快照会访问 `docs.python.org` 并重写机器生成文件：

```bash
python3 tools/python_stdlib_audit.py refresh-baseline
python3 tools/python_stdlib_audit.py refresh-objects
```

刷新 C++ baseline 不访问网络；它使用 `tools/cpp_stdlib_audit.py` 中固化的 cppreference-sourced header/symbol inventory 重写 JSON：

```bash
python3 tools/cpp_stdlib_audit.py refresh-baseline
```

刷新 C++ objects 默认读取本机 Dash 的 C++.docset；也可以显式读取 cppreference offline HTML book archive 中的 Doxygen tag XML。Dash/tag 缺失的 symbol 会生成 baseline fallback objects：

```bash
python3 tools/cpp_stdlib_audit.py refresh-objects
python3 tools/cpp_stdlib_audit.py refresh-objects --dash-docset "/path/to/C++.docset"
python3 tools/cpp_stdlib_audit.py refresh-objects --source-dir /path/to/cppreference-html-book
python3 tools/cpp_stdlib_audit.py refresh-checklist
```

正常维护 checklist/task 不需要网络。

`tools/dash_docset.py` 是内部读取库，不是语言入口工具。它支持 Dash 新版 CoreData 索引和旧版 `searchIndex` 表，后续 Node.js、Julia、R、Go、Rust 的 docset 导入会复用这条路径。

当前还没有写 runnable tests，所以不要把 checklist/task 数据变更当成代码测试来处理。默认验证保持轻量：

- 只改 `stdlib.tasks.json`：确认 JSON 能解析，且新增 `covers` 都存在于 `stdlib.objects.json`。
- C++ 只改 `stdlib.tasks.json`：确认 JSON 能解析，且新增 `covers` 都存在于 `stdlib.objects.json` 的 `objects[].name`，或运行 `python3 tools/cpp_stdlib_audit.py audit`。
- Dash-backed 语言只改 `stdlib.tasks.json`：确认 JSON 能解析，且运行对应 `python3 tools/<language>_stdlib_audit.py audit`。
- 改官方快照或 audit 分类：再跑对应的 audit。
- 改渲染或工具脚本：再跑脚本语法检查和一个代表性 render。
- 不默认跑 Docker 入口或 pytest；只有改 runner、容器入口、测试文件时才需要。

## ChatGPT Handoff

`chatgpt-sources/<language-id>/` 保留给“让 ChatGPT 应用生成单个测试文件”的未来流程：

- `project-contract.md`
- `task-template.md`
- 一个对应语言的 `example-test-file.*`

Codex 维护 checklist、task、审计脚本、渲染脚本和这些 handoff 源文件。ChatGPT 应用只在需要时生成一个完整测试文件。

未来测试约定：Python 使用 pytest；C++ 使用 GoogleTest；Node.js 使用 `node:test`；Julia 使用 `Test` stdlib；R 先使用 base `stopifnot()`；Go 使用 `testing`；Rust 使用 `#[test]` / `cargo test`。

## 编写原则

- checklist 服务于“学习一门语言”，不是只列 API 名字。
- 优先官方文档、标准条款结构和可审计的来源基线；有机器对象索引时才使用机器对象索引。
- Python builtins 要体现 data model / magic method / protocol dispatch，例如 `__abs__`、`__index__`、`__iter__`、`__format__`、descriptor、context manager、async protocol。
- C++ 标准库 task 要体现语言语义：RAII、值语义、move-only ownership、iterator/range 协议、templates、lambdas、异常边界和 const-correctness。
- Node.js task 要体现 callback/promise/event/stream/buffer/path/url 等运行时协议。
- Julia task 要体现 multiple dispatch、类型、集合、广播、stdlib module 的惯用法。
- R task 要体现 vectorization、data frame、formula/modeling、apply family 和 base/recommended packages。
- Go task 要体现 value/pointer、interface、slice/map、context、testing-friendly stdlib usage。
- Rust task 要体现 ownership/borrowing、Option/Result、traits、iterators、collections、path/fs/time。
- 标准库 task 要小而完整：一个 API、一个协议或一个惯用法一组示例。
- 被学习和演示的 API 只使用标准库；测试框架例外必须在 handoff contract 和 catalog 中明示。
- 生成文件、缓存和临时状态放在 `/tmp/polyglot-*` 或工具默认临时目录。

## Definition Of Done

当前阶段的完成标准：

- JSON 能被解析。
- task `covers` 没有未知对象名：所有语言都对 `stdlib.objects.json` 的 `objects[].name`。
- 如果改了脚本，对应脚本能做一次代表性运行。
- 如果只改 task 数据，不要求跑 Docker、pytest 或全量工具链验证。

恢复写测试后，task 或 item 只有在对应 runnable test 存在并通过 `./tools/run.sh <language>` 后，才可以标为 `done` 并写入 `test_files`。
