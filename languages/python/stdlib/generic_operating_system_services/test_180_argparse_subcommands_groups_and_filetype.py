"""180｜``argparse`` 子命令、展示分组、互斥约束与 ``FileType``。

subparser 让每个子命令拥有独立参数集合，``set_defaults`` 常用来附加分派函数。
argument group 只重排帮助文本，互斥 group 才增加解析约束。``FileType`` 会在解析阶段
打开资源，调用方必须明确关闭；复杂 CLI 通常只解析路径，再在业务阶段打开文件。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.argparse.add_subparsers python.argparse.subparser-required
# polyglot-covers: python.argparse.subparser-dest python.argparse.subparser-aliases
# polyglot-covers: python.argparse.subparser-selected-attributes
# polyglot-covers: python.argparse.subcommand-dispatch
# polyglot-covers: python.argparse.add_argument_group
# polyglot-covers: python.argparse.add_mutually_exclusive_group
# polyglot-covers: python.argparse.mutually-exclusive-required
# polyglot-covers: python.argparse.FileType python.argparse.FileType-close-ownership
# polyglot-covers: python.argparse.set_defaults python.argparse.get_default

import argparse
from contextlib import redirect_stderr
import io

import pytest


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
