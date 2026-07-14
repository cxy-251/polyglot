"""179｜``argparse`` 的帮助文本、父解析器、前缀与冲突消解。

帮助输出来自同一份 argument 声明，可通过 formatter 调整而不必维护第二份说明。
``parents`` 复制父解析器已存在的 action；``conflict_handler='resolve'`` 只替换
真正冲突的 option string，旧 action 若仍有别名便继续可用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.argparse.prog python.argparse.usage
# polyglot-covers: python.argparse.description python.argparse.epilog
# polyglot-covers: python.argparse.help python.argparse.metavar
# polyglot-covers: python.argparse.format_help python.argparse.format_usage
# polyglot-covers: python.argparse.print_help python.argparse.ArgumentDefaultsHelpFormatter
# polyglot-covers: python.argparse.parents python.argparse.add_help
# polyglot-covers: python.argparse.prefix_chars python.argparse.allow_abbrev
# polyglot-covers: python.argparse.conflict_handler-resolve
# polyglot-covers: python.argparse.partial-option-prefix

import argparse
import io


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
    assert build.format_help().count("--config") == 1


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
