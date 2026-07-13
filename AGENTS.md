# Agent Contract

这个仓库必须让一场全新的对话只依靠工作树就能继续，不依赖之前的聊天记录。

## 开始工作

每场对话按顺序执行：

1. 查看 `git status --short` 和最近的 Git commit。
2. 阅读 `README.md`、`sources.lock` 和 `NEXT.md`。
3. `NEXT.md` 是唯一的当前任务入口；不要寻找或创建完整任务清单。
4. 先阅读任务列出的官方资料、目标文件、覆盖点和案例，再开始写代码。
5. 如果工作中断，把准确的剩余步骤写进 `NEXT.md` 的 `Handoff`。

## 项目目标

Polyglot 是一个通过测试代码学习编程语言的案例仓库，固定覆盖 Python、C++、Node.js、Julia、R、Go 和 Rust。

案例应当同时展示：

- 基础语法和正常用法；
- 容易忽略的高级语义；
- 表层操作对应的数据模型、协议或语言机制；
- 标准库中可复用的实际工作流；
- 真实、常见且有教学价值的陷阱。

测试代码是项目的主要产品。不要重新建立庞大的 Markdown/JSON checklist、Dash 对象快照、数据库快照或 `chatgpt-sources/`。

## 当前阶段

- 当前只编写 Python 3.10 测试套。
- 用户明确要求先完成 Python 编写阶段，再统一运行测试。
- 在用户改变要求或进入统一验证阶段前，不运行 pytest，也不把任何 Python 文件称为“已验证”或“完成”。
- `NEXT.md` 可以推进到下一个编写任务，但必须持续注明整个 Python 测试集尚未运行。
- 允许按连贯主题做本地阶段性 commit；提交前做文本和 diff 静态审阅，commit message 必须表明这是尚未统一验证的 authoring checkpoint。

## Python 内容来源

`sources.lock` 锁定当前解释器和官方资料系列。来源优先级为：

1. Python Language Reference：语法和核心语义主目录；
2. Python Data Model：特殊方法、协议和隐式分派；
3. Built-in Functions / Built-in Types：内置函数和核心类型行为；
4. Python Standard Library Reference：标准库模块工作流；
5. PEP：仅补充版本演进或参考手册没有充分解释的设计背景。

Dash 和对象索引以后只用于发现遗漏，不决定测试结构和学习优先级。

## Python 测试规范

- 使用 pytest；被演示的 API 必须来自 Python 语言本身或标准库。
- 一个测试文件围绕一个连贯主题，文件名和测试名必须便于以后搜索。
- 中文注释要详细但必要：解释协议分派、求值顺序、返回值语义、版本差异和陷阱，不逐行复述代码。
- “覆盖全面”指覆盖官方正常语义、协议入口、关键 fallback、常用工作流和真实陷阱；不要制造穷举式边界矩阵。
- 有常见坑时必须用案例和注释讲清楚；没有值得讲的坑时不要硬加“注意事项”。
- 自定义协议类型保持最小，只实现当前主题需要的方法。
- 每个文件顶部使用 `polyglot-covers` 注释声明稳定的覆盖 ID；完成状态以后由工具扫描测试代码得出。
- 不使用网络、sleep、真实用户目录或持久机器状态；文件案例使用 pytest 临时目录。

## 单任务接续

`NEXT.md` 始终只包含一个当前任务：

- `ready`：下一场对话可以直接开始；
- `in_progress`：已有代码或分析，`Handoff` 必须写清剩余步骤；
- `blocked`：必须写出证据和解除条件。

编写完一个测试套后，静态审阅文件，然后把 `NEXT.md` 覆盖为下一个测试套。Git 历史保存已经发生的过程，`NEXT.md` 不累积历史任务。

阶段性 commit 只表示测试代码已经完成首轮编写，不表示 pytest 通过。只有最终 Docker 统一验证和修复结束后，才能把相应范围称为 verified。

## 执行边界

- 宿主机不安装或直接调用各语言运行时。
- 所有运行时、编译器和测试框架都位于 `ohdev` Docker 容器。
- 宿主机统一入口是 `./tools/run.sh`；它在容器外使用 `docker exec`。
- 容器内入口是 `./tools/run-in-container.sh`。
- 构建缓存和临时状态写入 `/tmp/polyglot-*` 或测试框架的临时目录。

旧 checklist-first 实现截止于 commit `662e0d1`。需要查证历史判断时使用 `git show`，不要把旧生成数据恢复到当前工作树。
