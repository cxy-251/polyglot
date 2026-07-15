# NEXT

Status: `ready`

## 当前任务

在 `ohdev` Docker 容器中统一验证 Python 3.10 测试集 `001–178`，按失败类别修复
首轮编写中的语法、断言、平台差异和资源清理问题，直到整个 Python 测试集通过。

## 官方资料

- `sources.lock` 锁定的 Python 3.10 Language Reference、Data Model、Built-ins 和
  Standard Library Reference。
- 修复具体失败前，先阅读该测试文件顶部的 `polyglot-covers`，再核对对应官方章节；
  不建立新的完整 checklist。

## 目标文件

- `languages/python/language/`
- `languages/python/builtins/`
- `languages/python/stdlib/`
- 容器入口：`./tools/run.sh doctor`、`./tools/run.sh python`

## 覆盖点

- pytest 能收集全部 `test_001` 至 `test_178` 测试套。
- 正常平台上的断言与 Python 3.10 当前补丁版本语义一致。
- Windows、Unix、Tk、可选扩展和外部服务相关案例只在能力缺失时准确 skip。
- 临时文件、socket、模块全局状态、环境变量和导入缓存都在案例结束后恢复。
- 预期的弃用警告与真正的失败分开处理，不通过宽泛忽略掩盖问题。

## 案例

先运行全量测试并保存失败摘要；按共同根因批量修复，再重跑受影响文件，最后重跑
`./tools/run.sh python`。修复不得重排已经提交的文件编号，也不要把平台能力缺失
改写成虚假的通过断言。

## Handoff

- Python 3.10 首轮编写已覆盖 178 个全局连续编号测试套。
- `stdlib/` 文件夹已按内部文件范围编号，最后一个类别是
  `173-178_superseded_modules/`。
- 整个 Python 测试集从未运行；所有当前内容都只是未统一验证的 authoring
  checkpoint，不能称为 verified。
- 下一场对话从 `./tools/run.sh doctor` 和第一次 `./tools/run.sh python` 开始。
