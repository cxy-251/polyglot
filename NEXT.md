# Next task

Status: `ready`

## Current task

只建立一个新的横向概念：

```text
concepts/005_iteration_protocol/
```

保持 `languages/` 课程不动，不启动 Julia、R、Go 或 Rust，也不同时开始其他概念。

## Research first

先使用 `sources.lock` 锁定的 Python 3.10、C++20 和 ECMAScript 2025 官方资料，逐门核对
迭代器取得、推进、结束信号、单次消费与提前退出语义。只有确认共同问题矩阵后才写测试，
不要把名称相似但语义不同的机制强行等同。

优先阅读：

- `languages/python/language/test_008_iteration_and_generator_protocols.py`
- `languages/cpp/language/test_005_statements_control_flow_and_range_for.cpp`
- `languages/cpp/standard_library/08_iterators/`
  `test_071_iterator_traits_concepts_indirect_access_and_customization_points.cpp`
- `languages/nodejs/language/test_016_iterables_iterators_generators_and_iterator_closing.mjs`

## Target files

```text
concepts/005_iteration_protocol/python/test_iteration_protocol.py
concepts/005_iteration_protocol/cpp/test_iteration_protocol.cpp
concepts/005_iteration_protocol/nodejs/test_iteration_protocol.mjs
```

每个文件使用 `polyglot-concept: iteration_protocol`，并通过 `polyglot-related` 指向同语言
最直接的完整课程。概念只处理同步迭代，不扩展到异步迭代器。

## Acceptance

- 三门语言围绕同一组已核实的问题组织精简断言。
- 明确表达取得迭代器、逐步推进、完成信号以及提前退出时是否存在关闭协议。
- 语言不存在对应机制时用准确注释说明，不编造等价能力。
- 不移动、拆分或改写语言课程，不复制完整课程的大量案例。
- 运行单概念、概念全量、三门语言全量和统一结构门禁。

## Handoff

1. `004_resource_cleanup` 已完成，覆盖正常退出、异常退出、LIFO、触发机制和异常冲突。
2. 单概念结果：Python `5 passed`、C++ `4 passed`、Node.js `5 passed`。
3. 全部四个概念：Python `16 passed`、C++ `15 passed`、Node.js `16 passed`。
4. 纵向课程：Python `5025 passed, 39 skipped`；C++ `1409 passed, 15 skipped`；
   Node.js `935 passed`。
5. Python 运行器已修正：带 pytest 选项的课程命令仍限定在 `languages/python`；
   显式课程文件路径仍可单独运行。
