"""082｜``argparse`` 的声明式参数解析、类型转换与 ``Namespace``。

``ArgumentParser`` 把命令行 token 映射到由 ``add_argument`` 声明的目标属性；
``type`` 在 ``choices`` 校验前转换输入。option 名中的连字符默认会转成属性名中的
下划线。这里直接传入 token list，避免案例依赖 pytest 自身的 ``sys.argv``。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.argparse.ArgumentParser python.argparse.add_argument
# polyglot-covers: python.argparse.parse_args python.argparse.Namespace
# polyglot-covers: python.argparse.positional python.argparse.optional
# polyglot-covers: python.argparse.type python.argparse.choices
# polyglot-covers: python.argparse.dest python.argparse.required-option
# polyglot-covers: python.argparse.option-equals-syntax python.argparse.short-option-attached-value
# polyglot-covers: python.argparse.short-option-cluster python.argparse.end-of-options
# polyglot-covers: python.argparse.negative-number-positional
# polyglot-covers: python.argparse.negative-number-option-ambiguity
# polyglot-covers: python.argparse.existing-namespace python.argparse.namespace-vars



import argparse
import io
from contextlib import redirect_stderr
import pytest
import shlex
from contextlib import redirect_stderr, redirect_stdout
import getopt

def test_parser_builds_a_typed_namespace_from_positionals_and_options():
    """type 的结果参与 choices；命令行字符串不会原样留在 Namespace 中。"""

    parser = argparse.ArgumentParser(prog="copy")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--retry-count", type=int, choices=range(1, 4), default=2)

    args = parser.parse_args(
        ["first.txt", "second.txt", "--output", "archive.zip", "--retry-count", "3"]
    )

    assert args == argparse.Namespace(
        sources=["first.txt", "second.txt"],
        output="archive.zip",
        retry_count=3,
    )
    assert vars(args)["retry_count"] == 3


def test_common_token_spellings_and_double_dash_are_not_shell_features():
    """这些形式由 argparse 解析；传 list 时并没有 shell 帮忙拆分。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("-I", dest="include_paths", action="append", default=[])
    parser.add_argument("--format", choices=("json", "text"))
    parser.add_argument("items", nargs="*")

    args = parser.parse_args(
        ["-vv", "-I/usr/include", "--format=json", "--", "--literal", "-3"]
    )

    assert args.verbose == 2
    assert args.include_paths == ["/usr/include"]
    assert args.format == "json"
    # ``--`` 自身不会进入结果；其后的 ``-`` 前缀 token 一律作为位置参数。
    assert args.items == ["--literal", "-3"]


def test_existing_namespace_keeps_defaults_but_explicit_tokens_still_win():
    """默认值只填补缺失属性；显式提供的 option 仍会覆盖已有属性。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--color", default="auto")
    parser.add_argument("--jobs", type=int, default="4")

    target = argparse.Namespace(color="always", marker="preserved")
    result = parser.parse_args([], namespace=target)

    assert result is target
    assert result.color == "always"
    assert result.jobs == 4
    assert result.marker == "preserved"

    parser.parse_args(["--color", "never"], namespace=target)
    assert target.color == "never"


def test_negative_numbers_are_positionals_until_a_similar_option_is_declared():
    """存在 ``-1`` option 时，负数 token 会进入 option 识别；``--`` 可消除歧义。"""

    numeric = argparse.ArgumentParser()
    numeric.add_argument("offset", type=int)
    assert numeric.parse_args(["-3"]).offset == -3

    ambiguous = argparse.ArgumentParser()
    ambiguous.add_argument("-1", dest="use_one", action="store_true")
    ambiguous.add_argument("offset", type=int)

    option = ambiguous.parse_args(["-1", "5"])
    positional = ambiguous.parse_args(["--", "-1"])

    assert option == argparse.Namespace(use_one=True, offset=5)
    assert positional == argparse.Namespace(use_one=False, offset=-1)


# ``argparse`` 内建 action、``nargs`` 结果形状与默认值语义。
#
# action 决定重复 option 如何更新同一个目标；``nargs`` 不只控制消费多少 token，
# 也会改变结果是 scalar 还是 list。默认值的转换规则尤其容易忽略：只有字符串
# 默认值会经过 ``type``，已经是其他 Python 对象的默认值会原样保存。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.argparse.action-store python.argparse.action-store-const
# polyglot-covers: python.argparse.action-store-true python.argparse.action-store-false
# polyglot-covers: python.argparse.BooleanOptionalAction python.argparse.action-count
# polyglot-covers: python.argparse.action-append python.argparse.action-append-const
# polyglot-covers: python.argparse.action-extend python.argparse.append-default-prefix
# polyglot-covers: python.argparse.nargs-integer python.argparse.nargs-question
# polyglot-covers: python.argparse.nargs-star python.argparse.nargs-plus
# polyglot-covers: python.argparse.REMAINDER python.argparse.nargs-result-shape
# polyglot-covers: python.argparse.string-default-type-conversion
# polyglot-covers: python.argparse.non-string-default-not-converted python.argparse.SUPPRESS



def test_constant_boolean_and_count_actions_encode_flag_semantics():
    """无值 flag 应用 action 表意，避免手工把字符串 ``"false"`` 当布尔值。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="store", default="normal")
    parser.add_argument("--fast", dest="mode", action="store_const", const="fast")
    parser.add_argument("--verbose", action="count", default=0)
    parser.add_argument("--color", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--feature", action="store_true")
    parser.add_argument("--no-cache", dest="cache", action="store_false", default=True)

    args = parser.parse_args(
        ["--fast", "--verbose", "--verbose", "--no-color", "--feature", "--no-cache"]
    )

    assert args.mode == "fast"
    assert args.verbose == 2
    assert args.color is False
    assert args.feature is True
    assert args.cache is False


def test_repeating_actions_accumulate_with_distinct_flattening_rules():
    """append 追加一个值，extend 展开一组值，append_const 追加预设常量。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", action="append", default=["base"])
    parser.add_argument("--include", action="extend", nargs="+")
    parser.add_argument("--debug-kind", dest="kinds", action="append_const", const="debug")
    parser.add_argument("--trace-kind", dest="kinds", action="append_const", const="trace")

    args = parser.parse_args(
        [
            "--tag",
            "api",
            "--tag",
            "cli",
            "--include",
            "src",
            "tests",
            "--include",
            "docs",
            "--debug-kind",
            "--trace-kind",
        ]
    )

    # 非空 append 默认序列会保留为结果前缀；它并非只在 option 缺席时使用。
    assert args.tag == ["base", "api", "cli"]
    assert args.include == ["src", "tests", "docs"]
    assert args.kinds == ["debug", "trace"]


def test_question_nargs_distinguishes_absent_bare_and_explicit_option():
    """option 的 nargs='?' 用 default/const/显式值表达三个状态。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--color", nargs="?", default="auto", const="always")

    assert parser.parse_args([]).color == "auto"
    assert parser.parse_args(["--color"]).color == "always"
    assert parser.parse_args(["--color", "never"]).color == "never"


def test_fixed_nargs_always_returns_lists_when_tokens_are_present():
    """nargs=1 也返回 list；option 缺席时 scalar default 不会自动装箱。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--one", nargs=1, type=int, default=7)
    parser.add_argument("--point", nargs=2, type=float)

    absent = parser.parse_args([])
    present = parser.parse_args(["--one", "8", "--point", "1.5", "2.5"])

    assert absent.one == 7
    assert present.one == [8]
    assert present.point == [1.5, 2.5]


def test_star_plus_and_remainder_have_different_consumption_contracts():
    """REMAINDER 保留后续 option-like token，适合转交给另一个命令解析器。"""

    list_parser = argparse.ArgumentParser()
    list_parser.add_argument("--labels", nargs="*")
    list_parser.add_argument("files", nargs="+")
    listed = list_parser.parse_args(
        ["--labels", "red", "blue", "--", "a.txt", "b.txt"]
    )

    command_parser = argparse.ArgumentParser()
    command_parser.add_argument("command")
    command_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    delegated = command_parser.parse_args(["tool", "--unknown", "value", "tail"])

    # 可变长 option 是贪婪的；``--`` 明确结束 labels，否则裸 token 都会被它消费。
    assert listed.labels == ["red", "blue"]
    assert listed.files == ["a.txt", "b.txt"]
    assert delegated.command == "tool"
    assert delegated.arguments == ["--unknown", "value", "tail"]


def test_only_string_defaults_are_passed_through_type_and_suppress_omits_dest():
    """非字符串 default 不经 type；SUPPRESS 让属性彻底缺席而不是值为 None。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default="1.5")
    parser.add_argument("--workers", type=float, default=2)
    parser.add_argument("--secret", default=argparse.SUPPRESS)

    args = parser.parse_args([])

    assert args.timeout == 1.5
    assert type(args.timeout) is float
    assert args.workers == 2
    assert type(args.workers) is int
    assert not hasattr(args, "secret")


# ``argparse`` 的帮助文本、父解析器、前缀与冲突消解。
#
# 帮助输出来自同一份 argument 声明，可通过 formatter 调整而不必维护第二份说明。
# ``parents`` 复制父解析器已存在的 action；``conflict_handler='resolve'`` 只替换
# 真正冲突的 option string，旧 action 若仍有别名便继续可用。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.argparse.prog python.argparse.usage
# polyglot-covers: python.argparse.description python.argparse.epilog
# polyglot-covers: python.argparse.help python.argparse.metavar
# polyglot-covers: python.argparse.format_help python.argparse.format_usage
# polyglot-covers: python.argparse.print_help python.argparse.ArgumentDefaultsHelpFormatter
# polyglot-covers: python.argparse.parents python.argparse.add_help
# polyglot-covers: python.argparse.prefix_chars python.argparse.allow_abbrev
# polyglot-covers: python.argparse.conflict_handler-resolve
# polyglot-covers: python.argparse.partial-option-prefix



def test_help_and_usage_are_rendered_from_parser_metadata():
    """metavar 只改变展示名，结果仍写入由 dest 决定的 input_path 属性。"""

    parser = argparse.ArgumentParser(
        prog="archiver",
        usage="%(prog)s [options] SOURCE",
        description="Create a deterministic archive.",
        epilog="See the project guide for formats.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_path", metavar="SOURCE", help="input directory")
    parser.add_argument("--level", type=int, default=3, help="compression level")

    help_text = parser.format_help()
    usage_text = parser.format_usage()
    destination = io.StringIO()
    parser.print_help(file=destination)

    assert usage_text == "usage: archiver [options] SOURCE\n"
    assert "Create a deterministic archive." in help_text
    assert "SOURCE" in help_text
    assert "compression level (default: 3)" in help_text
    assert help_text.rstrip().endswith("See the project guide for formats.")
    assert destination.getvalue() == help_text
    assert parser.parse_args(["workspace"]).input_path == "workspace"


def test_parent_parser_reuses_a_fully_declared_common_option_set():
    """父解析器关闭自身 help，避免子解析器合并时重复注册 -h/--help。"""

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--verbose", action="count", default=0)
    common.add_argument("--config", default="project.ini")

    build = argparse.ArgumentParser(prog="tool build", parents=[common])
    build.add_argument("target")
    args = build.parse_args(["--verbose", "--config", "ci.ini", "wheel"])

    assert args.verbose == 1
    assert args.config == "ci.ini"
    assert args.target == "wheel"
    assert sum(action.dest == "config" for action in build._actions) == 1
    assert "--config CONFIG" in build.format_help()
    # help 中 usage 和 options 表各出现一次文本；应检查 action 没有重复注册，
    # 不能用整份帮助字符串的 substring 次数替代结构断言。


def test_prefix_chars_changes_both_user_options_and_automatic_help_flags():
    """不含 '-' 的 prefix_chars 会使自动 help 采用第一个可用前缀。"""

    parser = argparse.ArgumentParser(prog="plus", prefix_chars="+")
    parser.add_argument("+v", "++verbose", action="store_true")

    assert parser.parse_args(["++verbose"]).verbose is True
    help_text = parser.format_help()
    assert "+h" in help_text
    assert "++help" in help_text


def test_allow_abbrev_controls_long_option_prefix_consumption():
    """parse_known_args 也可能吞掉未知参数，因为默认允许唯一长 option 前缀。"""

    abbreviated = argparse.ArgumentParser(add_help=False)
    abbreviated.add_argument("--foobar")
    args, remainder = abbreviated.parse_known_args(["--foo", "value", "tail"])

    strict = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    strict.add_argument("--foobar")
    strict_args, strict_remainder = strict.parse_known_args(["--foo", "value", "tail"])

    assert args.foobar == "value"
    assert remainder == ["tail"]
    assert strict_args.foobar is None
    assert strict_remainder == ["--foo", "value", "tail"]


def test_resolve_removes_only_the_conflicting_option_string():
    """旧 action 的 -f 未冲突，所以在 --format 被新 action 接管后仍然存在。"""

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("-f", "--format", dest="legacy_format")
    parser = argparse.ArgumentParser(
        parents=[parent],
        conflict_handler="resolve",
    )
    parser.add_argument("--format", dest="output_format")

    legacy = parser.parse_args(["-f", "text"])
    modern = parser.parse_args(["--format", "json"])

    assert legacy.legacy_format == "text"
    assert legacy.output_format is None
    assert modern.legacy_format is None
    assert modern.output_format == "json"


# ``argparse`` 子命令、展示分组、互斥约束与 ``FileType``。
#
# subparser 让每个子命令拥有独立参数集合，``set_defaults`` 常用来附加分派函数。
# argument group 只重排帮助文本，互斥 group 才增加解析约束。``FileType`` 会在解析阶段
# 打开资源，调用方必须明确关闭；复杂 CLI 通常只解析路径，再在业务阶段打开文件。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.argparse.add_subparsers python.argparse.subparser-required
# polyglot-covers: python.argparse.subparser-dest python.argparse.subparser-aliases
# polyglot-covers: python.argparse.subparser-selected-attributes
# polyglot-covers: python.argparse.subcommand-dispatch
# polyglot-covers: python.argparse.add_argument_group
# polyglot-covers: python.argparse.add_mutually_exclusive_group
# polyglot-covers: python.argparse.mutually-exclusive-required
# polyglot-covers: python.argparse.FileType python.argparse.FileType-close-ownership
# polyglot-covers: python.argparse.set_defaults python.argparse.get_default




def _run_command(args):
    return f"run:{args.jobs}"


def _show_command(args):
    return f"show:{args.output_format}"


def test_subparsers_select_arguments_and_attach_a_dispatch_callable():
    """只有被选子解析器的 action 才向最终 Namespace 添加属性。"""

    parser = argparse.ArgumentParser(prog="project")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", aliases=["execute"])
    run.add_argument("--jobs", type=int, default=1)
    run.set_defaults(handler=_run_command)

    show = commands.add_parser("show")
    show.add_argument("--format", dest="output_format", default="text")
    show.set_defaults(handler=_show_command)

    run_args = parser.parse_args(["run", "--jobs", "3"])
    alias_args = parser.parse_args(["execute", "--jobs", "2"])
    show_args = parser.parse_args(["show", "--format", "json"])

    assert run_args.command == "run"
    assert run_args.handler(run_args) == "run:3"
    assert not hasattr(run_args, "output_format")
    assert alias_args.handler(alias_args) == "run:2"
    assert show_args.handler(show_args) == "show:json"
    assert not hasattr(show_args, "jobs")

    error_output = io.StringIO()
    with redirect_stderr(error_output):
        with pytest.raises(SystemExit) as raised:
            parser.parse_args([])
    assert raised.value.code == 2
    assert "the following arguments are required: command" in error_output.getvalue()


def test_argument_groups_shape_help_but_namespace_remains_flat():
    """展示 group 不创建嵌套对象；其 action 仍直接写到同一个 Namespace。"""

    parser = argparse.ArgumentParser(prog="client")
    authentication = parser.add_argument_group(
        "authentication",
        "credentials used by the remote service",
    )
    authentication.add_argument("--user", required=True)
    authentication.add_argument("--token")

    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--stdout", action="store_true")
    output.add_argument("--output")

    args = parser.parse_args(["--user", "ada", "--token", "secret", "--stdout"])

    assert args.user == "ada"
    assert args.token == "secret"
    assert args.stdout is True
    assert args.output is None
    help_text = parser.format_help()
    assert "authentication:" in help_text
    assert "credentials used by the remote service" in help_text

    error_output = io.StringIO()
    with redirect_stderr(error_output):
        with pytest.raises(SystemExit) as raised:
            parser.parse_args(["--user", "ada"])
    assert raised.value.code == 2
    assert "one of the arguments --stdout --output is required" in error_output.getvalue()


def test_mutually_exclusive_conflict_is_an_argument_error_when_exit_is_disabled():
    """exit_on_error=False 可把 action 间的冲突交给嵌入式调用方处理。"""

    parser = argparse.ArgumentParser(exit_on_error=False)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--quiet", action="store_true")
    output.add_argument("--verbose", action="store_true")

    with pytest.raises(argparse.ArgumentError, match="not allowed with argument"):
        parser.parse_args(["--quiet", "--verbose"])


def test_filetype_returns_an_open_stream_whose_lifetime_belongs_to_the_caller(tmp_path):
    """FileType 不是 pathlib.Path 转换器；成功解析后得到的是已打开 stream。"""

    source = tmp_path / "input.txt"
    source.write_text("alpha\nbeta\n", encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        type=argparse.FileType("r", encoding="utf-8"),
    )
    args = parser.parse_args([str(source)])

    stream = args.source
    try:
        assert stream.name == str(source)
        assert stream.read().splitlines() == ["alpha", "beta"]
        assert stream.closed is False
    finally:
        stream.close()

    assert stream.closed is True


def test_parser_defaults_can_supply_non_cli_dispatch_metadata():
    """set_defaults 可覆盖 action default；显式命令行值仍具有最高优先级。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="safe")
    parser.set_defaults(mode="fast", handler="build")

    assert parser.get_default("mode") == "fast"
    assert parser.get_default("handler") == "build"
    assert parser.parse_args([]) == argparse.Namespace(mode="fast", handler="build")
    assert parser.parse_args(["--mode", "safe"]).mode == "safe"


# ``argparse`` 的 partial parse、intermixed parse 与 ``@`` 参数文件。
#
# ``parse_known_args`` 适合把未知 token 转交给下一级，但仍受长 option 缩写规则影响。
# ``parse_intermixed_args`` 允许可选参数穿插在 ``nargs='*'`` 位置参数中。参数文件默认一行
# 对应一个 token；若需要 shell-like 引号或一行多参数，应覆盖转换 hook 并明确其语法。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.argparse.parse_known_args python.argparse.unknown-arguments
# polyglot-covers: python.argparse.parse_intermixed_args
# polyglot-covers: python.argparse.parse_known_intermixed_args
# polyglot-covers: python.argparse.intermixed-positional-options
# polyglot-covers: python.argparse.fromfile_prefix_chars
# polyglot-covers: python.argparse.argument-file-one-token-per-line
# polyglot-covers: python.argparse.convert_arg_line_to_args
# polyglot-covers: python.argparse.argument-file-custom-tokenization



class ShellLineArgumentParser(argparse.ArgumentParser):
    """把每行显式定义为 shlex 语法，并允许 ``#`` 注释。"""

    def convert_arg_line_to_args(self, arg_line):
        return shlex.split(arg_line, comments=True)


def test_parse_known_args_returns_unknown_tokens_without_rejecting_them():
    """已知参数照常类型转换，未知参数保持原顺序交给调用方。"""

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--jobs", type=int, default=1)

    args, unknown = parser.parse_known_args(
        ["--jobs", "4", "--plugin-color", "blue", "payload"]
    )

    assert args == argparse.Namespace(jobs=4)
    assert unknown == ["--plugin-color", "blue", "payload"]


def test_intermixed_parse_reopens_a_star_positional_after_an_option():
    """普通解析会把 option 后恢复的位置值留作 unknown；intermixed 会重新收集它们。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--format")
    parser.add_argument("command")
    parser.add_argument("values", nargs="*", type=int)
    tokens = ["sum", "1", "--format", "json", "2", "3"]

    regular, regular_unknown = parser.parse_known_args(tokens)
    intermixed = parser.parse_intermixed_args(tokens)

    assert regular.command == "sum"
    assert regular.values == [1]
    assert regular_unknown == ["2", "3"]
    assert intermixed == argparse.Namespace(format="json", command="sum", values=[1, 2, 3])


def test_known_intermixed_variant_preserves_unrecognized_options():
    """known 与 intermixed 可组合，用于既允许穿插又需要向下转交参数的场景。"""

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--format")
    parser.add_argument("values", nargs="*", type=int)

    args, unknown = parser.parse_known_intermixed_args(
        ["1", "--format", "json", "2", "--plugin-flag"]
    )

    assert args == argparse.Namespace(format="json", values=[1, 2])
    assert unknown == ["--plugin-flag"]


def test_default_argument_file_conversion_treats_each_line_as_one_token(tmp_path):
    """默认实现不按空白再次拆词，因此 option 及其值通常分别占一行。"""

    argument_file = tmp_path / "arguments.txt"
    argument_file.write_text("--mode\nfast\ninput file.txt\n", encoding="utf-8")

    parser = argparse.ArgumentParser(fromfile_prefix_chars="@")
    parser.add_argument("--mode")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args([f"@{argument_file}"])

    assert args.mode == "fast"
    assert args.files == ["input file.txt"]


def test_argument_file_hook_can_define_quoted_multi_token_lines(tmp_path):
    """自定义转换器的规则属于文件格式契约，不应暗中依赖平台 shell。"""

    argument_file = tmp_path / "shell-like.args"
    argument_file.write_text(
        '--name "Ada Lovelace"\n--tag alpha --tag beta # ignored\n',
        encoding="utf-8",
    )

    parser = ShellLineArgumentParser(fromfile_prefix_chars="@")
    parser.add_argument("--name")
    parser.add_argument("--tag", action="append")
    args = parser.parse_args([f"@{argument_file}"])

    assert args.name == "Ada Lovelace"
    assert args.tag == ["alpha", "beta"]


# ``argparse`` 自定义 registry/action、错误传播与非退出式嵌入。
#
# 解析器默认把命令行错误打印到 stderr 并以状态 2 退出，这对 CLI 合理、对库代码却未必。
# Python 3.10 的 ``exit_on_error=False`` 只把一部分 action 错误改为 ``ArgumentError``；
# 未知参数仍会触发 ``SystemExit``。需要完全控制时应覆写 ``error``/``exit``。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.argparse.Action python.argparse.custom-action
# polyglot-covers: python.argparse.Action.__call__ python.argparse.ArgumentError
# polyglot-covers: python.argparse.register python.argparse.named-custom-type
# polyglot-covers: python.argparse.exit_on_error python.argparse.error-status-2
# polyglot-covers: python.argparse.exit-on-error-incomplete-scope
# polyglot-covers: python.argparse.ArgumentParser.error python.argparse.ArgumentParser.exit
# polyglot-covers: python.argparse.help-action-exit-zero python.argparse.literal-percent-help




class KeyValueAction(argparse.Action):
    """把重复的 KEY=VALUE option 合并为字典。"""

    def __call__(self, parser, namespace, values, option_string=None):
        key, separator, value = values.partition("=")
        if not separator or not key:
            raise argparse.ArgumentError(self, "expected KEY=VALUE")

        # Namespace 的默认字典可能由调用方传入；复制后再更新可避免意外修改外部对象。
        result = dict(getattr(namespace, self.dest, None) or {})
        result[key] = value
        setattr(namespace, self.dest, result)


class ParseFailure(Exception):
    pass


class ParserExit(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class NonExitingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParseFailure(message)

    def exit(self, status=0, message=None):
        raise ParserExit(status, message)


def _hex_integer(value):
    return int(value, 16)


def test_custom_action_can_validate_and_accumulate_repeated_options():
    """Action 接收已匹配的值并负责写 Namespace；协议错误用 ArgumentError 表达。"""

    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.register("action", "key-value", KeyValueAction)
    parser.add_argument("--define", action="key-value", default={})

    args = parser.parse_args(["--define", "color=blue", "--define", "jobs=4"])
    assert args.define == {"color": "blue", "jobs": "4"}

    with pytest.raises(argparse.ArgumentError, match="expected KEY=VALUE"):
        parser.parse_args(["--define", "broken"])


def test_registry_allows_a_stable_symbolic_name_for_a_custom_type():
    """register 的名称只属于该 parser；它适合配置驱动的 parser 构造器。"""

    parser = argparse.ArgumentParser()
    parser.register("type", "hex-integer", _hex_integer)
    parser.add_argument("--mask", type="hex-integer")

    assert parser.parse_args(["--mask", "ff"]).mask == 255


def test_exit_on_error_false_does_not_cover_unrecognized_arguments():
    """类型失败成为 ArgumentError，但最终 leftover 检查在 3.10 仍调用 error/exit。"""

    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument("--count", type=int)

    with pytest.raises(argparse.ArgumentError, match="invalid int value"):
        parser.parse_args(["--count", "NaN"])

    error_output = io.StringIO()
    with redirect_stderr(error_output):
        with pytest.raises(SystemExit) as raised:
            parser.parse_args(["--unknown"])

    assert raised.value.code == 2
    assert "unrecognized arguments: --unknown" in error_output.getvalue()


def test_overriding_error_and_exit_gives_embedded_callers_full_control():
    """error 处理失败，exit 还处理 --help 等成功终止；两条路径不能合并。"""

    parser = NonExitingArgumentParser(prog="embedded")
    parser.add_argument("--required", required=True)

    with pytest.raises(ParseFailure, match="required"):
        parser.parse_args([])

    help_output = io.StringIO()
    with redirect_stdout(help_output):
        with pytest.raises(ParserExit) as raised:
            parser.parse_args(["--help"])

    assert raised.value.status == 0
    assert raised.value.message is None
    assert "usage: embedded" in help_output.getvalue()


def test_literal_percent_in_help_must_be_doubled_before_interpolation():
    """help 字符串会执行 %-formatting；``%%`` 才渲染为单个百分号。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--ratio", help="accept values up to 100%%")

    assert "accept values up to 100%" in parser.format_help()


# ``getopt.getopt`` 的 C/Unix 风格 option 扫描与返回协议。
#
# ``getopt`` 不生成 Namespace，也不负责帮助文本；它只返回有序的 ``(option, value)``
# pair 和剩余 operand。short option 后的冒号、long option 后的等号是在声明“必须有值”，
# 不是命令行拼写的一部分。遇到第一个非 option 后，传统扫描立即停止。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.getopt.getopt python.getopt.shortopts
# polyglot-covers: python.getopt.short-option-cluster
# polyglot-covers: python.getopt.short-option-required-argument
# polyglot-covers: python.getopt.short-option-attached-argument
# polyglot-covers: python.getopt.longopts python.getopt.long-option-required-argument
# polyglot-covers: python.getopt.long-option-equals-value
# polyglot-covers: python.getopt.option-value-pairs python.getopt.repeated-options
# polyglot-covers: python.getopt.stop-at-first-operand
# polyglot-covers: python.getopt.double-dash python.getopt.lone-dash



def test_short_options_preserve_order_and_support_attached_values():
    """cluster 逐字展开；需要值的 option 会消费 cluster 余串或下一个 token。"""

    options, operands = getopt.getopt(
        ["-av", "-bfast", "-c", "slow", "input.txt"],
        "avb:c:",
    )

    assert options == [
        ("-a", ""),
        ("-v", ""),
        ("-b", "fast"),
        ("-c", "slow"),
    ]
    assert operands == ["input.txt"]


def test_long_options_accept_separate_or_equals_values_and_can_repeat():
    """返回名称会规范为完整 ``--name``，但值始终是字符串。"""

    options, operands = getopt.getopt(
        [
            "--verbose",
            "--output=first.txt",
            "--output",
            "second.txt",
            "payload",
        ],
        "",
        ["verbose", "output="],
    )

    assert options == [
        ("--verbose", ""),
        ("--output", "first.txt"),
        ("--output", "second.txt"),
    ]
    assert operands == ["payload"]


def test_traditional_scanning_leaves_everything_after_the_first_operand():
    """后续 ``-v`` 不再解释为 option；返回 operands 是原参数的 trailing slice。"""

    options, operands = getopt.getopt(
        ["-a", "first", "-v", "second"],
        "av",
    )

    assert options == [("-a", "")]
    assert operands == ["first", "-v", "second"]


def test_double_dash_ends_scanning_while_lone_dash_is_an_operand():
    """``--`` 被丢弃；单独 ``-`` 本身保留，并像普通 operand 一样终止传统扫描。"""

    terminated = getopt.getopt(["-v", "--", "-x", "tail"], "vx")
    lone_dash = getopt.getopt(["-", "-v"], "v")

    assert terminated == ([("-v", "")], ["-x", "tail"])
    assert lone_dash == ([], ["-", "-v"])


# ``getopt.gnu_getopt`` 的 intermixed 扫描、长 option 前缀与错误对象。
#
# GNU 模式默认允许 option 与 operand 穿插，但 ``+`` shortopts 前缀或环境变量
# ``POSIXLY_CORRECT`` 会恢复遇到 operand 即停止的规则。long option 允许唯一前缀，
# 因此扩充 option 集可能让过去的缩写突然产生歧义；稳定接口应鼓励完整拼写。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.getopt.gnu_getopt python.getopt.gnu-intermixed-scanning
# polyglot-covers: python.getopt.gnu-leading-plus python.getopt.POSIXLY_CORRECT
# polyglot-covers: python.getopt.long-option-unique-prefix
# polyglot-covers: python.getopt.long-option-ambiguous-prefix
# polyglot-covers: python.getopt.GetoptError python.getopt.GetoptError.msg
# polyglot-covers: python.getopt.GetoptError.opt python.getopt.error-alias
# polyglot-covers: python.getopt.unknown-option-error
# polyglot-covers: python.getopt.missing-option-argument-error
# polyglot-covers: python.getopt.unexpected-long-option-argument-error




def test_gnu_scanning_collects_options_while_preserving_operand_order():
    """intermixed 只改变扫描顺序；options 与 operands 各自在结果中维持出现顺序。"""

    options, operands = getopt.gnu_getopt(
        ["first", "-v", "second", "--output", "result", "third"],
        "v",
        ["output="],
    )

    assert options == [("-v", ""), ("--output", "result")]
    assert operands == ["first", "second", "third"]


def test_leading_plus_and_posix_environment_restore_stop_at_operand(monkeypatch):
    """两种 POSIX 开关都使第一个 operand 后的 option 保持未解析。"""

    tokens = ["first", "-v", "second"]
    leading_plus = getopt.gnu_getopt(tokens, "+v")

    monkeypatch.setenv("POSIXLY_CORRECT", "1")
    environment = getopt.gnu_getopt(tokens, "v")

    assert leading_plus == ([], tokens)
    assert environment == ([], tokens)


def test_unique_long_prefix_expands_to_the_declared_full_name():
    """``--fo`` 只匹配 foo；``--f`` 同时匹配 foo/frob，因而不能猜测。"""

    options, operands = getopt.getopt(["--fo", "payload"], "", ["foo", "frob"])

    assert options == [("--foo", "")]
    assert operands == ["payload"]

    with pytest.raises(getopt.GetoptError) as raised:
        getopt.getopt(["--f"], "", ["foo", "frob"])

    assert raised.value.msg == "option --f not a unique prefix"
    assert raised.value.opt == "f"
    assert str(raised.value) == raised.value.msg


@pytest.mark.parametrize(
    ("tokens", "shortopts", "longopts", "expected_opt", "message_fragment"),
    [
        (["-x"], "v", [], "x", "not recognized"),
        (["-o"], "o:", [], "o", "requires argument"),
        (["--verbose=yes"], "", ["verbose"], "verbose", "must not have an argument"),
    ],
)
def test_malformed_options_expose_machine_readable_error_context(
    tokens,
    shortopts,
    longopts,
    expected_opt,
    message_fragment,
):
    """调用方可用 opt 定位问题；不要解析本地化后的 msg 文本来恢复 option。"""

    with pytest.raises(getopt.GetoptError) as raised:
        getopt.getopt(tokens, shortopts, longopts)

    assert raised.value.opt == expected_opt
    assert message_fragment in raised.value.msg
    assert getopt.error is getopt.GetoptError
