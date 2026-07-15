"""040｜``readline`` 全局状态与 ``rlcompleter`` Python 名称补全示例。

``readline`` 是 Unix 构建中的可选模块，背后可能是 GNU readline 或 libedit；历史、
completer、delimiter 与 hooks 都是进程全局状态。``rlcompleter`` 则把 keyword、
builtins、显式 namespace 和对象属性适配成 ``complete(text, state)`` 协议。

本文件不启动 REPL、不读取 stdin，也不调用 ``redisplay()``。历史文件只写入 pytest
临时目录；可读取的全局状态由 autouse fixture 恢复，没有 getter 的 hooks 在测试内
用 finally 清除。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.readline python.readline.backend
# polyglot-covers: python.readline.parse_and_bind python.readline.line-buffer-context
# polyglot-covers: python.readline.history-list python.readline.history-indexing
# polyglot-covers: python.readline.history-file python.readline.history-length
# polyglot-covers: python.readline.append_history_file python.readline.auto-history
# polyglot-covers: python.readline.completer python.readline.completer-delims
# polyglot-covers: python.readline.completion-context python.readline.hooks
# polyglot-covers: python.stdlib.rlcompleter python.rlcompleter.Completer
# polyglot-covers: python.rlcompleter.global_matches python.rlcompleter.attr_matches
# polyglot-covers: python.rlcompleter.state-protocol python.rlcompleter.underscore-filter
# polyglot-covers: python.rlcompleter.attribute-side-effects

import subprocess
import sys

import pytest


try:
    import readline
except ImportError:
    pytest.skip(
        "readline 是 Unix 构建中的可选标准库模块；当前解释器未提供",
        allow_module_level=True,
    )


if not hasattr(readline, "clear_history"):
    pytest.skip(
        "底层 readline 库未提供 clear_history，无法安全隔离全局 history",
        allow_module_level=True,
    )


# rlcompleter 在 Unix 上导入时会自动安装默认 completer；collection 不应永久改变
# 测试进程原状态，所以导入完成后立即恢复。
_COMPLETER_BEFORE_RLCOMPLETER_IMPORT = readline.get_completer()
try:
    import rlcompleter
finally:
    readline.set_completer(_COMPLETER_BEFORE_RLCOMPLETER_IMPORT)


def _history_items():
    """按文档规定的 1-based 查询索引复制当前全局 history。"""

    return [
        readline.get_history_item(index)
        for index in range(1, readline.get_current_history_length() + 1)
    ]


def _collect_completions(completer, text, limit=256):
    """模拟 readline 递增 state，直到 completer 返回 None。"""

    matches = []
    for state in range(limit):
        match = completer.complete(text, state)
        if match is None:
            return matches
        assert isinstance(match, str)
        assert match.startswith(text)
        matches.append(match)
    raise AssertionError("completer 在安全上限内没有返回 None")


@pytest.fixture(autouse=True)
def restore_readline_global_state():
    """隔离可读取状态；readline 没有为 startup/display hooks 提供 getter。"""

    original_history = _history_items()
    original_history_length = readline.get_history_length()
    original_completer = readline.get_completer()
    original_delimiters = readline.get_completer_delims()

    readline.clear_history()
    readline.set_history_length(-1)
    try:
        yield
    finally:
        readline.clear_history()
        for line in original_history:
            readline.add_history(line)
        readline.set_history_length(original_history_length)
        readline.set_completer(original_completer)
        readline.set_completer_delims(original_delimiters)


def test_backend_specific_binding_uses_documented_gnu_or_libedit_syntax():
    """libedit 的配置语法与 GNU readline 不同，不能盲目共享 inputrc 行。"""

    # parse_and_bind 没有读取/恢复已有绑定的 API，因此放进子进程隔离配置变更。
    program = """
import readline

is_libedit = "libedit" in (readline.__doc__ or "")
binding = "bind ^I rl_complete" if is_libedit else "tab: complete"
assert readline.parse_and_bind(binding) is None
print("libedit" if is_libedit else "gnu-readline")
"""
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() in {"gnu-readline", "libedit"}

    # 这里只验证对应后端的最小绑定，不断言后端显示、按键或 inputrc 内部状态。


def test_line_buffer_and_completion_indexes_are_contextual_interactive_state():
    """查询函数可调用，但没有真实 readline callback 时，其内容/坐标没有输入行语义。"""

    assert isinstance(readline.get_line_buffer(), str)
    assert isinstance(readline.get_completion_type(), int)
    assert isinstance(readline.get_begidx(), int)
    assert isinstance(readline.get_endidx(), int)

    # insert_text 会改变当前全局编辑缓冲，redisplay 会触碰真实终端；单元测试不调用它们。
    assert callable(readline.insert_text)
    assert callable(readline.redisplay)


def test_history_queries_are_one_based_but_replace_and_remove_are_zero_based():
    """这是 readline 最容易混淆的索引差异：读取从 1 开始，修改位置从 0 开始。"""

    readline.add_history("first")
    readline.add_history("second")
    readline.add_history("third")

    assert readline.get_current_history_length() == 3
    assert readline.get_history_item(0) is None
    assert readline.get_history_item(1) == "first"
    assert readline.get_history_item(3) == "third"
    assert readline.get_history_item(4) is None

    readline.replace_history_item(1, "SECOND")
    assert _history_items() == ["first", "SECOND", "third"]

    readline.remove_history_item(0)
    assert _history_items() == ["SECOND", "third"]


def test_clear_history_removes_memory_items_without_touching_any_file():
    """clear_history 只清当前进程列表；未显式 write 时不存在持久化副作用。"""

    readline.add_history("temporary")
    assert readline.get_current_history_length() == 1

    assert readline.clear_history() is None
    assert readline.get_current_history_length() == 0
    assert readline.get_history_item(1) is None


def test_history_length_limits_file_output_not_the_in_memory_list(tmp_path):
    """set_history_length 在 write_history_file 时截断文件，不会立即裁剪内存。"""

    history_file = tmp_path / "limited.history"
    for line in ("alpha", "beta", "gamma"):
        readline.add_history(line)

    assert readline.set_history_length(2) is None
    assert readline.get_history_length() == 2
    assert readline.write_history_file(str(history_file)) is None
    assert _history_items() == ["alpha", "beta", "gamma"]

    readline.clear_history()
    readline.read_history_file(str(history_file))
    assert _history_items() == ["beta", "gamma"]


def test_read_history_file_appends_to_existing_memory_history(tmp_path):
    """read_history_file 的语义是 load-and-append；需要替换时应先 clear_history。"""

    history_file = tmp_path / "append-on-read.history"
    readline.add_history("from-file")
    readline.write_history_file(str(history_file))

    readline.clear_history()
    readline.add_history("already-in-memory")
    readline.read_history_file(str(history_file))

    assert _history_items() == ["already-in-memory", "from-file"]


def test_read_history_file_reports_a_missing_explicit_path(tmp_path):
    """显式路径不存在时抛 FileNotFoundError；不要退回用户 ~/.history。"""

    missing = tmp_path / "does-not-exist.history"

    with pytest.raises(FileNotFoundError):
        readline.read_history_file(str(missing))


def test_append_history_file_writes_only_the_requested_recent_items(tmp_path):
    """并发会话常记录启动时长度，退出时只 append 本会话新增的尾部项目。"""

    if not hasattr(readline, "append_history_file"):
        pytest.skip("底层 readline 版本不支持 append_history_file")

    history_file = tmp_path / "concurrent.history"
    readline.add_history("existing")
    readline.write_history_file(str(history_file))
    previous_length = readline.get_current_history_length()

    readline.add_history("new-one")
    readline.add_history("new-two")
    new_count = readline.get_current_history_length() - previous_length
    assert new_count == 2
    assert readline.append_history_file(new_count, str(history_file)) is None

    readline.clear_history()
    readline.read_history_file(str(history_file))
    assert _history_items() == ["existing", "new-one", "new-two"]


def test_disabling_auto_history_does_not_disable_explicit_add_history():
    """set_auto_history 只控制 input/readline 的隐式调用；显式 API 始终由调用方决定。"""

    assert readline.set_auto_history(False) is None
    try:
        readline.add_history("explicit-even-when-auto-is-off")
        assert _history_items() == ["explicit-even-when-auto-is-off"]
    finally:
        # API 没有 getter；恢复 CPython 文档声明的默认值，避免影响其他测试。
        readline.set_auto_history(True)


def test_custom_completer_registration_delimiters_and_state_protocol():
    """readline 保存 function(text, state)；delimiter 决定真实回调收到的 text 范围。"""

    def custom_completer(text, state):
        matches = [
            word
            for word in ("alpha", "alpine", "beta")
            if word.startswith(text)
        ]
        return matches[state] if state < len(matches) else None

    assert readline.set_completer(custom_completer) is None
    assert readline.get_completer() is custom_completer

    readline.set_completer_delims(" \t,;")
    assert readline.get_completer_delims() == " \t,;"

    assert [custom_completer("al", state) for state in range(3)] == [
        "alpha",
        "alpine",
        None,
    ]

    # 直接调用 function 不会应用 delimiter；切词发生在底层真实 completion callback。


def test_startup_pre_input_and_display_hooks_are_registered_then_cleared():
    """三个 hook 没有 getter；只验证注册接口，不启动 prompt，并始终在 finally 清理。"""

    calls = []

    def startup_hook():
        calls.append(("startup",))

    def pre_input_hook():
        calls.append(("pre-input",))

    def display_hook(substitution, matches, longest_match_length):
        calls.append(("display", substitution, matches, longest_match_length))

    try:
        assert readline.set_startup_hook(startup_hook) is None
        if hasattr(readline, "set_pre_input_hook"):
            assert readline.set_pre_input_hook(pre_input_hook) is None
        assert readline.set_completion_display_matches_hook(display_hook) is None

        # 注册本身不会调用 hook；只有真实交互式 readline 生命周期才会触发。
        assert calls == []
    finally:
        readline.set_startup_hook(None)
        if hasattr(readline, "set_pre_input_hook"):
            readline.set_pre_input_hook(None)
        readline.set_completion_display_matches_hook(None)


def test_completer_requires_a_dictionary_for_an_explicit_nonempty_namespace():
    """显式 namespace 应是 dict；这也避免补全器隐式依赖测试模块的 globals。"""

    namespace = {"project_value": 42}
    completer = rlcompleter.Completer(namespace)

    assert completer.namespace is namespace
    assert completer.use_main_ns == 0

    with pytest.raises(TypeError, match="namespace must be a dictionary"):
        rlcompleter.Completer(["not", "a", "dict"])


def test_global_matches_combines_namespace_keywords_and_builtins_with_postfixes():
    """有参数 callable 追加 ``(``，无参数 callable 追加 ``()``，普通值不追加。"""

    def project_function(value):
        return value

    def project_ready():
        return True

    namespace = {
        "project_value": 42,
        "project_function": project_function,
        "project_ready": project_ready,
        "len": 7,
    }
    completer = rlcompleter.Completer(namespace)

    project_matches = set(completer.global_matches("project_"))
    assert project_matches == {
        "project_value",
        "project_function(",
        "project_ready()",
    }

    assert "return " in completer.global_matches("ret")
    assert "try:" in completer.global_matches("try")
    assert "False" in completer.global_matches("False")

    # 显式 namespace 先于 builtins；同名普通值会遮住 builtin len 的 callable 后缀。
    assert completer.global_matches("len") == ["len"]


def test_complete_returns_successive_matches_and_none_when_state_is_exhausted():
    """state 不是页码或偏移文本；调用方从 0 连续递增，直到第一次 None。"""

    namespace = {
        "atlas_alpha": 1,
        "atlas_beta": 2,
        "atlas_gamma": 3,
    }
    completer = rlcompleter.Completer(namespace)
    matches = _collect_completions(completer, "atlas_")

    assert set(matches) == {"atlas_alpha", "atlas_beta", "atlas_gamma"}
    assert completer.complete("atlas_", len(matches)) is None


def test_attr_matches_exposes_public_members_and_avoids_evaluating_properties():
    """Python 3.10 会识别 property 并省略 getattr，因此补全不会执行该 getter。"""

    class Sample:
        visible = 1
        _private = 2
        __special__ = 3

        def method(self, value):
            return value

        def ready(self):
            return True

        @property
        def dangerous_property(self):
            raise AssertionError("补全不应求值 property")

    completer = rlcompleter.Completer({"obj": Sample()})
    public = set(completer.attr_matches("obj."))

    assert "obj.visible" in public
    assert "obj.method(" in public
    assert "obj.ready()" in public
    assert "obj.dangerous_property" in public
    assert all(not match.startswith("obj._") for match in public)


def test_attr_matches_reveals_private_names_only_after_user_types_underscore():
    """空属性前缀隐藏所有下划线名；单下划线前缀仍隐藏双下划线名。"""

    class Sample:
        visible = 1
        _private = 2
        __special__ = 3

    completer = rlcompleter.Completer({"obj": Sample()})

    public = completer.attr_matches("obj.")
    private = completer.attr_matches("obj._")
    dunder = completer.attr_matches("obj.__")

    assert "obj._private" not in public
    assert "obj.__special__" not in public
    assert "obj._private" in private
    assert all(not match.startswith("obj.__") for match in private)
    assert "obj.__special__" in dunder
    assert "obj.__class__()" in dunder
    # rlcompleter 会给可无参调用的对象加 ()，给其他 callable 加左括号。


def test_attribute_completion_can_execute_dir_and_getattr_user_code():
    """property 有专项保护不等于无副作用；自定义 __dir__/__getattr__ 仍会执行。"""

    accesses = []

    class DynamicObject:
        def __dir__(self):
            return ["dynamic_value"]

        def __getattr__(self, name):
            accesses.append(name)
            if name == "dynamic_value":
                return 42
            raise AttributeError(name)

    completer = rlcompleter.Completer({"dynamic": DynamicObject()})

    assert completer.attr_matches("dynamic.dynamic") == [
        "dynamic.dynamic_value"
    ]
    assert accesses == ["dynamic_value"]

    # 因而 attribute completion 只适合用户已授权检查的可信对象图。


def test_dotted_expression_errors_are_silenced_but_getattr_was_still_invoked():
    """求值最后一个点之前的表达式会捕获异常并返回空候选，但副作用已经发生。"""

    accesses = []

    class ExplosiveObject:
        def __getattr__(self, name):
            accesses.append(name)
            raise RuntimeError("boom")

    completer = rlcompleter.Completer({"root": ExplosiveObject()})

    assert completer.attr_matches("root.child.value") == []
    assert accesses == ["child"]


def test_attr_matches_rejects_calls_and_indexing_instead_of_evaluating_them():
    """支持的是 NAME.NAME 形状，不是任意 Python 表达式求值器。"""

    calls = []

    def factory():
        calls.append("called")
        return object()

    completer = rlcompleter.Completer({"factory": factory, "items": [object()]})

    assert completer.attr_matches("factory().value") == []
    assert completer.attr_matches("items[0].value") == []
    assert calls == []
