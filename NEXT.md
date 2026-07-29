# Next task

Status: `in_progress`

## Goal

停止扩充语言，对 Python、C++、Node.js、Go、Rust、Julia、R、Lua、Ruby 九门 active
language 进行完整文件级语义审计和课程重构。审计后的课程以教学问题、官方语义和真实
迁移价值为中心，不维持审计前固定 `128` 个纵向文件、`73` 个横向文件或机械同构目录。

## Audit contract

- `languages/<language>/` 只承载语言语义、标准库和真实开发工作流；工具链版本、runner、
  bootstrap、仓库配置、环境隔离和构建工程验证移入 `harness/<language>/`。
- 课程与概念编号保持稳定且唯一；合并或删除后允许空缺，不批量重排。
- `concepts/` 只保留共同问题的最小代表案例；不同语言可以使用不同文件数量和 stem。
- 每个文件直接落实 `保留、扩充、合并、移动、删除、纠错` 之一，不建立大型 checklist
  或生成式 inventory；测试通过不等于内容审查完成。
- 审计顺序固定为 `Ruby → Lua → R → Julia → Rust → Go → Node.js → C++ → Python`，
  每次只处理一门语言。完成一门后运行该语言纵向、相关横向、10 个 family、完整 concepts
  和结构门禁，再进入下一门。

## Current stage

- 已撤销 `content_review_complete`、`curriculum-reviewed` 和 reviewed implementation
  等完成声明；规则与结构门禁已经允许稳定编号空缺和不同语言采用不同横向组织方式，
  并明确 `polyglot-related` 的路径检查不能替代语义审查。
- Ruby 已完成文件级审计：纵向课程由审计前 128 个文件重构为 74 个，编号范围
  `002`–`120` 且保留稳定空缺；49 个横向 topic 使用 72 个 Ruby 文件；runner、隔离环境、
  本地 gem/C extension fixture 和 5 个工程验证移入 `harness/ruby/`。
- Ruby 验证通过：74 个纵向文件、72 个横向文件、10 个 family、完整 concepts、
  `ruby-harness`、`list-concepts`、`doctor`、结构门禁和 `git diff --check`。
- Lua 已完成文件级审计：纵向课程由审计前 128 个文件重构为 61 个，编号范围
  `002`–`122` 且保留稳定空缺；49 个横向 topic 使用 66 个 Lua 文件；runner、环境隔离、
  C host/module fixture 和 3 个工程验证移入 `harness/lua/`。
- Lua 验证通过：61 个纵向文件、66 个横向文件、10 个 family、完整 concepts、
  `lua-harness`、`list-concepts`、`doctor`、结构门禁和 `git diff --check`。
- R 已完成文件级审计：纵向课程由审计前 128 个文件重构为 56 个，编号范围
  `009`–`126` 且保留稳定空缺；49 个横向 topic 使用 67 个 R 文件；runner、状态隔离、
  本地 package/native fixture 和 4 个工程验证移入 `harness/r/`。
- R 验证通过：56 个纵向文件、67 个横向文件、10 个 family、完整 concepts、
  `r-harness`、`list-concepts`、`doctor`、结构门禁和 `git diff --check`。
- Julia 已完成文件级审计：纵向课程由审计前 128 个文件重构为 71 个，编号范围
  `002`–`127` 且保留稳定空缺；49 个横向 topic 使用 65 个 Julia 文件；锁定版本、
  depot/project/runner 隔离、本地工程 fixture 和 2 个验证移入 `harness/julia/`。
- Julia 验证通过：71 个纵向文件、65 个横向文件、10 个 family、完整 concepts、
  `julia-harness`、`list-concepts`、`doctor`、结构门禁和 `git diff --check`。
- Rust 已完成文件级审计：纵向课程由审计前 128 个文件重构为 60 个，编号范围
  `009`–`124` 且保留稳定空缺；49 个横向 topic 使用 67 个 Rust 文件；Cargo runner、
  toolchain/工程配置、编译失败 fixture 和 7 个工程验证移入 `harness/rust/`。
- Rust 验证通过：97 个纵向测试、67 个横向测试、49 个精确 topic、10 个 family、
  完整 concepts、7 个 harness 测试与 1 个 doc test、`list-concepts`、`doctor`、
  结构门禁和 `git diff --check`。
- Go 已完成文件级审计：纵向课程由审计前 128 个文件重构为 65 个，编号范围
  `009`–`127` 且保留稳定空缺；49 个横向 topic 使用 64 个 Go 文件；module/workspace、
  testing/toolchain、构建选择、锁定运行时观察和 12 个工程测试移入 `harness/go/`。
- Go 验证通过：115 个纵向测试、71 个横向测试、49 个精确 topic、10 个 family、
  完整 concepts、15 个 harness 测试、`go vet`、`list-concepts`、`doctor`、
  结构门禁和 `git diff --check`。
- Node.js 已完成文件级审计：纵向课程由审计前 107 个文件重构为 103 个，编号范围
  `001`–`107` 且保留稳定空缺；49 个横向 topic 使用 70 个 Node.js 文件；`node:test`
  context/mock/snapshot/CLI runner、package 配置和 4 个工程验证移入 `harness/nodejs/`。
- Node.js 验证通过：900 个纵向测试、248 个横向测试、49 个精确 topic、10 个 family、
  完整 concepts、35 个 harness 测试、`list-concepts`、`doctor`、结构门禁和
  `git diff --check`。
- C++ 已完成文件级审计：160 个纵向课程文件均为独立的语言或标准库教学单元，编号
  `001`–`160`；49 个横向 topic 使用 70 个 C++ 文件；CMake/GoogleTest 工程、锁定
  C++20/GCC 构建契约和 1 个工程验证移入 `harness/cpp/`。审计删除空 `SUCCEED()`
  包装，补成真实 endian、execution-policy 终止和 C++20 numeric workflow 断言。
- C++ 验证通过：`1409 passed, 15 skipped` 的 1424 个纵向测试、240 个横向测试、
  49 个精确 topic、10 个 family、完整 concepts、1 个 harness 测试、`list-concepts`、
  `doctor`、结构门禁和 `git diff --check`。
- Python 已完成文件级审计：178 个纵向课程文件均为独立的 language、builtins 或 stdlib
  教学单元，编号 `001`–`178`；49 个横向 topic 使用 72 个 Python 文件；pytest 版本、
  runner、用户目录/bytecode/cache 隔离和 2 个工程验证移入 `harness/python/`。审计消除了
  跨测试模块依赖、默认 bytecode 目录假设、固定安装布局和精确工具链版本课程断言，并将
  重复的运行时能力横向文件合并。
- Python 验证通过：`5025 passed, 39 skipped` 的纵向课程、249 个横向测试、49 个精确
  topic、10 个 family、完整 concepts、2 个 harness 测试、`list-concepts`、`doctor`、
  结构门禁和 `git diff --check`。
- 九门语言文件级审计均已完成。唯一下一步是汇总真实审计决策数量、恢复完成声明，执行
  九门纵向课程、全部 harness、完整 concepts、`doctor planned`、结构门禁与工作树最终验证。
