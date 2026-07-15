# NEXT

Status: `in_progress`

## Current task

继续 Python 3.10 全量 Docker 验证。先复跑并修正 internet data 与 structured markup
这一批，然后依据全量 pytest 的剩余失败继续按标准库服务类别修复。

整个 `languages/python/` 测试集尚未统一验证通过，不能称为 verified 或完成。

## Official references

- Python 3.10 Standard Library：`base64`、`binascii`、`mimetypes`、`email`、`mailbox`
- Python 3.10 Standard Library：`html.parser`、`xml.dom`、`xml.dom.minidom`、
  `xml.dom.pulldom`、`xml.sax`、`xml.parsers.expat`
- 解释器和资料系列以 `sources.lock` 为准

## Target files

- `104-110_internet_data_handling/`：`test_105_*`、`test_106_*`、`test_107_*`
- `104-110_internet_data_handling/`：`test_108_*`、`test_109_*`、`test_110_*`
- `111-115_structured_markup_tools/`：`test_111_*`、`test_113_*`、`test_114_*`、
  `test_115_*`

## Coverage and cases

- 保留每个案例原来的教学覆盖，不用放宽断言来掩盖真实语义。
- 精确区分 Python 3.10 的返回类型、异常类型、全局状态前置条件和补丁版本差异。
- 对 SAX/DOM 的分块文本、属性对象生命周期、locator 可用时机和 Expat 回调分流给出中文说明。
- 修复后先做本类别复跑，再回到完整测试集，不把局部通过外推成全量通过。

## Handoff

1. 全量初始基线：`5059` 个 pytest item，`175 failed, 4838 passed, 51 skipped`。
2. 前两批共 `59` 个失败已在 ohdev 的 Python 3.10.12 中复跑清零，并提交为
   `9abb5b5 Fix initial Python 3.10 validation batches`。
3. 当前第三批已准确复现 `27 failed, 289 passed`；对应修复已写入上列 10 个文件，
   `git diff --check` 与改动行 100 字符检查均通过，但尚未再次运行 pytest。
4. 复跑命令：

   ```bash
   ./tools/run.sh python -q --tb=short --timeout=30 \
     languages/python/stdlib/104-110_internet_data_handling \
     languages/python/stdlib/111-115_structured_markup_tools
   ```
5. 当前 Codex 外部执行额度已用尽，Docker 命令被系统拒绝，并提示到
   `2026-07-22 16:06 Asia/Shanghai` 后再试；不要改用宿主机 Python 绕过容器边界。
6. 本类别清零后重新运行全量 pytest，继续处理其余约 89 个基线失败；最终必须以完整
   `languages/python/` 一次通过、静态覆盖审计通过为完成证据。
