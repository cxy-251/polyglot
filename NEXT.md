# Next task

Status: `ready`

## Current task

只在现有章节体系中建立一个新的同步迭代主题：

```text
concepts/04_collections_and_iteration/01_iteration_protocol/
```

不要把它建立为顶层 `005`。保持 `languages/` 课程不动，不启动 Julia、R、Go 或 Rust，
也不同时开始其他主题。

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
concepts/04_collections_and_iteration/01_iteration_protocol/python/test_iteration_protocol.py
concepts/04_collections_and_iteration/01_iteration_protocol/cpp/test_iteration_protocol.cpp
concepts/04_collections_and_iteration/01_iteration_protocol/nodejs/test_iteration_protocol.mjs
```

每个文件使用 `polyglot-family: collections_and_iteration`、
`polyglot-concept: iteration_protocol`，并通过 `polyglot-related` 指向同语言最直接的
完整课程。概念只处理同步迭代，不扩展到异步迭代器。

## Acceptance

- 三门语言围绕同一组已核实的问题组织精简断言。
- 明确表达取得迭代器、逐步推进、完成信号以及提前退出时是否存在关闭协议。
- 语言不存在对应机制时用准确注释说明，不编造等价能力。
- 不移动、拆分或改写语言课程，不复制完整课程的大量案例。
- 运行单主题、`family 04_collections_and_iteration`、概念全量、三门语言全量和结构门禁。

## Handoff

1. 横向层已改为连续的 `NN_family/NN_topic/<language>/test_<topic>` 三级结构。
2. 当前三个章节包含四个主题；12 个测试案例语义未改，只迁移路径并增加章节标记。
3. `concept` 运行一个主题，`family` 运行一个章节，`concepts` 运行整个横向层。
4. 四个主题全量结果：Python `16 passed`、C++ `15 passed`、Node.js `16 passed`。
5. 纵向课程基线：Python `5025 passed, 39 skipped`；C++ `1409 passed, 15 skipped`；
   Node.js `935 passed`。
