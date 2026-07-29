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
  等完成声明；审计前测试数字改为执行快照。
- 正在重构项目规则和结构门禁：允许稳定编号空缺、不同语言使用不同横向组织方式，
  删除固定文件数、固定问题域和 stem 镜像约束，并明确 `polyglot-related` 只提供路径完整性。
- 当前审计语言为 Ruby，尚未开始课程文件修改。规则与门禁提交后，唯一下一步是从 block、
  Proc、lambda、开放类、mixin 和 refinement 开始逐文件审计 Ruby。
