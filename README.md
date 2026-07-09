# Polyglot Stdlib By Example

这是一个用“可运行示例测试”学习主流编程语言标准库的项目。

当前阶段先暂停写测试，重点构建各语言 checklist 的数据模型、官方来源快照、审计脚本和任务渲染流程。Python 是当前唯一 active checklist；其他语言先保留空 checklist 目录作为规划占位。

## 当前范围

项目语言范围固定为：

- Python: active checklist
- C++: placeholder checklist
- Node.js: placeholder checklist
- Julia: placeholder checklist
- R: placeholder checklist
- Go: placeholder checklist
- Rust: placeholder checklist

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
  nodejs/
  julia/
  r/
  go/
  rust/
chatgpt-sources/
  python/
tools/
  run.sh
  run-in-container.sh
  python_checklist_status.py
  python_stdlib_audit.py
  python_render_task.py
  python_api_inventory.py
languages/
```

`languages/` 当前可以为空；未来恢复写测试时再按 `languages/<language-id>/` 建立测试文件。`checklists/` 下的空语言目录先保留，不用 README 填充。

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

## 工具

宿主机入口仍然是 `./tools/run.sh`，它会通过 Docker `exec` 进入 `ohdev`：

```bash
./tools/run.sh list
./tools/run.sh checklist python
./tools/run.sh python
./tools/run.sh all-checklists
```

当前 `python` 入口等价于 Python checklist 状态检查，不跑 pytest。

Python 专用工具都以 `python_` 开头：

```bash
python3 tools/python_checklist_status.py python
python3 tools/python_stdlib_audit.py audit
python3 tools/python_stdlib_audit.py audit --objects heapq pathlib json list dict str
python3 tools/python_render_task.py heapq
python3 tools/python_render_task.py list.sort
python3 tools/python_api_inventory.py list dict str
```

刷新官方快照会访问 `docs.python.org` 并重写机器生成文件：

```bash
python3 tools/python_stdlib_audit.py refresh-baseline
python3 tools/python_stdlib_audit.py refresh-objects
```

正常维护 checklist/task 不需要网络。

## ChatGPT Handoff

`chatgpt-sources/python/` 保留给“让 ChatGPT 应用生成单个测试文件”的未来流程：

- `project-contract.md`
- `task-template.md`
- `example-test-file.py`

Codex 维护 checklist、task、审计脚本、渲染脚本和这些 handoff 源文件。ChatGPT 应用只在需要时生成一个完整 `_test.py` 文件。

## 编写原则

- checklist 服务于“学习一门语言”，不是只列 API 名字。
- 优先官方文档和官方对象索引，脚本产物要可审计。
- Python builtins 要体现 data model / magic method / protocol dispatch，例如 `__abs__`、`__index__`、`__iter__`、`__format__`、descriptor、context manager、async protocol。
- 标准库 task 要小而完整：一个 API、一个协议或一个惯用法一组示例。
- 只使用标准库和 runtime-bundled tools。
- 生成文件、缓存和临时状态放在 `/tmp/polyglot-*` 或工具默认临时目录。

## Definition Of Done

当前阶段的完成标准：

- JSON 能被解析。
- Python checklist 状态脚本能运行。
- baseline audit missing 为 0。
- objects audit missing 为 0，且 task `covers` 没有未知官方对象名。
- `python_render_task.py` 对 task 和旧 checklist item 都能渲染。

恢复写测试后，task 或 item 只有在对应 runnable test 存在并通过 `./tools/run.sh <language>` 后，才可以标为 `done` 并写入 `test_files`。
