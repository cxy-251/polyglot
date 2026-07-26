# Next task

Status: `ready`

## Current task

评审三个双轴试点，并从“迭代协议”与“资源清理”中只选择一个建立 `004_*` 横向概念。
不要迁移任何语言课程文件，不继续文件系统概念，也不启动 Julia。

## Official references

- Python 3.10 Data Model、Expressions 与相关标准库文档；
- ISO C++20 / WG21 工作草案及 libstdc++ 11.4 手册；
- ECMAScript 2025、Node.js 24.18.0 API 文档与对应源码；
- 版本与固定入口继续使用 `sources.lock`。

先阅读相关完整课程，只有存在清晰共同问题矩阵时才实施一个新概念。

## Candidate course files

迭代协议：

- `languages/python/language/test_008_iteration_and_generator_protocols.py`
- C++：
  `languages/cpp/standard_library/08_iterators/`
  `test_071_iterator_traits_concepts_indirect_access_and_customization_points.cpp`
- `languages/nodejs/language/test_016_iterables_iterators_generators_and_iterator_closing.mjs`

资源清理：

- `languages/python/language/test_010_context_manager_protocols.py`
- `languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp`
- `languages/nodejs/language/test_027_explicit_resource_management_and_disposable_stacks.mjs`

## Acceptance

- 先比较两个候选的共同问题是否足够具体，再选择对照价值更高的一项。
- 只新增 `concepts/004_name/{language}/test_name.<ext>`，不移动、裁剪课程文件。
- 各语言使用相同问题矩阵；缺失机制使用注释，不编造等价能力。
- 每个概念文件保持精简，并用 `polyglot-related` 指回对应课程。
- 运行单概念、概念全量、三门语言受影响课程及统一结构门禁。

## Handoff

1. Python `001`–`178`、C++ `001`–`160`、Node.js `001`–`107` 已全部恢复到各自
   `languages/` 主线；语言课程不再分散到 `concepts/`。
2. 横向层只包含 `001_truthiness`、`002_equality`、`003_argument_passing` 三个试点，
   每个概念为三门语言各一个局部命名测试。
3. `./tools/run.sh concept NNN_name` 运行单个概念；`./tools/run.sh concepts` 运行全部。
4. `./tools/run.sh check` 分别检查纵向课程和横向概念，并验证 `polyglot-related`。
5. 不要批量恢复原先十个宽泛概念，也不要把标准库课程迁入横向层。
