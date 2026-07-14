# Current Task

ID: `python.stdlib.readline-rlcompleter`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `readline` 与 `rlcompleter` 测试套，覆盖历史记录、补全器注册/分隔符、hook 生命周期和 Python 名称/属性补全，同时隔离进程全局状态并说明 GNU readline、libedit 与非 Unix 平台差异。

## Covers

- `readline` 在 Unix 构建中的可选可用性，以及 GNU readline/libedit 行为不可假定完全一致；
- `parse_and_bind()` 的配置入口，只使用两种后端都可接受的最小绑定；
- `clear_history()` / `add_history()` / `get_current_history_length()`；
- `get_history_item()` 的 1-based 读取索引；
- `remove_history_item()` / `replace_history_item()` 的 0-based 修改索引；
- `read_history_file()` / `write_history_file()` / `append_history_file()` 与固定临时文件；
- `set_history_length()` / `get_history_length()` 对写文件截断的影响；
- `set_auto_history()` 只控制交互输入自动入历史，不影响显式 `add_history()`；
- `set_completer()` / `get_completer()` 与 `complete(text, state)` 的逐项协议；
- `set_completer_delims()` / `get_completer_delims()`，以及 delimiter 如何决定补全文本边界；
- `get_completion_type()` / `get_begidx()` / `get_endidx()` 仅在真实补全回调期间有可靠上下文；
- `set_startup_hook()` / `set_pre_input_hook()` / `set_completion_display_matches_hook()` 的注册和显式清理；
- `rlcompleter.Completer(namespace)` 的显式 namespace，不污染/依赖测试模块 globals；
- `complete()` 以 state=0,1,... 拉取候选，耗尽时返回 `None`；
- keyword、builtin、namespace 名称和 callable 候选的补全形状；
- `global_matches()` 与 `attr_matches()` 的直接使用；
- 单下划线/双下划线属性只有在用户已输入下划线前缀时才应出现；
- attribute completion 可能触发 `getattr()`、property/descriptor 等用户代码的风险边界。

## Common Pitfalls To Explain

- 假设所有平台都有 `readline`，或把 GNU readline 特有配置写成跨后端断言；
- 测试后不恢复 history、completer、delimiter、hook 等进程全局状态；
- 混淆 history 查询的 1-based 索引与 remove/replace 的 0-based 索引；
- 认为 `set_history_length()` 会立即裁剪内存历史，而不是影响写文件；
- 把 `set_auto_history(False)` 当作禁止显式 `add_history()`；
- 直接调用 completer 时仍相信 `get_begidx()` / `get_endidx()` 有当前行上下文；
- 忘记补全协议要递增 state 直到 `None`；
- 使用默认 namespace 后意外暴露调用方 globals；
- 对不可信对象做 attribute completion，触发 descriptor/property 副作用；
- 写依赖候选完整顺序或后端显示格式的脆弱断言。

## Target File

`languages/python/stdlib/test_040_readline_rlcompleter.py`

## Official Sources

- https://docs.python.org/3.10/library/readline.html
- https://docs.python.org/3.10/library/rlcompleter.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 文件级导入要对 `readline` 不可用的平台给出清晰 skip，不伪造实现；
- 用 autouse fixture 快照并恢复可读取的全局状态；没有 getter 的 hook 必须在 `try/finally` 中清回 `None`；
- 历史文件只能使用 `tmp_path`，不得读取或改写用户真实 history/init 文件；
- 不启动 REPL、不读取 stdin、不调用会重绘真实终端的交互路径；
- 候选只断言关键集合/前缀，不依赖完整排序；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--039 已完成文件/目录访问、正则与除 readline/rlcompleter 外的文本处理服务。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 040 readline/rlcompleter；不要先运行 pytest。
