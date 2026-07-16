"""176｜optparse 与 pipes：遗留命令行解析和 shell 转换管道。

optparse 仍常见于尚未迁移到 argparse 的命令行程序；pipes 则把
外部命令描述为需要文件或标准流的转换步骤。案例覆盖读懂和维护旧代码
所需的动作、类型、回调、冲突处理与管道拓扑。pipes 案例只在 Unix 运行，
实际命令只调用当前 Python 解释器。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.optparse python.optparse.option-parser
# polyglot-covers: python.optparse.store python.optparse.boolean-actions
# polyglot-covers: python.optparse.append python.optparse.count python.optparse.store-const
# polyglot-covers: python.optparse.types python.optparse.choice python.optparse.complex
# polyglot-covers: python.optparse.short-cluster python.optparse.long-abbreviation
# polyglot-covers: python.optparse.defaults python.optparse.positional-arguments
# polyglot-covers: python.optparse.interspersed-arguments python.optparse.option-group
# polyglot-covers: python.optparse.help python.optparse.version python.optparse.parse-error
# polyglot-covers: python.optparse.conflict-handler python.optparse.callback
# polyglot-covers: python.optparse.option-value-error python.optparse.custom-type
# polyglot-covers: python.stdlib.pipes python.pipes.template python.pipes.step-kinds
# polyglot-covers: python.pipes.append python.pipes.prepend python.pipes.clone
# polyglot-covers: python.pipes.reset python.pipes.debug python.pipes.makepipeline
# polyglot-covers: python.pipes.copy python.pipes.open-read python.pipes.open-write
# polyglot-covers: python.pipes.shell-command-risk python.pipes.temporary-files

import os
import pipes
import shlex
import sys
from optparse import Option
from optparse import OptionConflictError
from optparse import OptionGroup
from optparse import OptionParser
from optparse import OptionValueError

import pytest


def python_filter(source):
    """构造只调用当前解释器的 shell 步骤，两个层次都显式引用。"""
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}"


def uppercase_filter():
    return python_filter(
        "import sys; sys.stdout.write(sys.stdin.read().upper())"
    )


def test_option_parser_store_boolean_append_count_and_const_actions():
    parser = OptionParser(add_help_option=False)
    parser.add_option("-o", "--output", dest="output")
    parser.add_option("--color", action="store_true", default=False)
    parser.add_option("--no-color", action="store_false", dest="color")
    parser.add_option("-I", action="append", dest="include")
    parser.add_option("-v", action="count", dest="verbosity")
    parser.add_option(
        "--mode-fast",
        action="store_const",
        const="fast",
        dest="mode",
    )

    options, arguments = parser.parse_args(
        [
            "-o",
            "result.txt",
            "--color",
            "-Ione",
            "-I",
            "two",
            "-vv",
            "--mode-fast",
            "input.txt",
        ]
    )

    assert options.output == "result.txt"
    assert options.color is True
    assert options.include == ["one", "two"]
    assert options.verbosity == 2
    assert options.mode == "fast"
    assert arguments == ["input.txt"]
    # Values 不是 dict；字段名来自 dest，
    # 未出现且无 default 的动作通常得到 None。


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["--jobs", "4"], 4),
        (["--ratio", "0.25"], 0.25),
        (["--offset", "1+2j"], 1 + 2j),
        (["--format", "json"], "json"),
    ],
)
def test_builtin_option_types_convert_before_values_are_returned(arguments, expected):
    parser = OptionParser()
    parser.add_option("--jobs", type="int")
    parser.add_option("--ratio", type="float")
    parser.add_option("--offset", type="complex")
    parser.add_option("--format", type="choice", choices=("json", "text"))

    options, _ = parser.parse_args(arguments)
    destination = arguments[0].removeprefix("--").replace("-", "_")

    assert getattr(options, destination) == expected


def test_short_options_can_cluster_and_unambiguous_long_options_can_abbreviate():
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="count", default=0)
    parser.add_option("--output-directory")

    options, arguments = parser.parse_args(["-vv", "--output-d", "build"])

    assert options.verbose == 2
    assert options.output_directory == "build"
    assert arguments == []
    # 长选项缩写方便交互，却可能在以后新增相同前缀选项时变成歧义。


def test_ambiguous_long_option_reports_a_parse_error(capsys):
    parser = OptionParser(prog="legacy-tool")
    parser.add_option("--verbose", action="store_true")
    parser.add_option("--verify", action="store_true")

    with pytest.raises(SystemExit) as raised:
        parser.parse_args(["--ver"])

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert "Usage: legacy-tool" in error
    assert "ambiguous option" in error


def test_parser_defaults_are_overridden_by_the_command_line():
    parser = OptionParser()
    parser.add_option("--color", default="red")
    parser.set_defaults(color="blue", jobs=1)

    default_options, _ = parser.parse_args([])
    explicit_options, _ = parser.parse_args(["--color", "green"])

    assert vars(default_options) == {"color": "blue", "jobs": 1}
    assert vars(explicit_options) == {"color": "green", "jobs": 1}


def test_interspersed_options_are_enabled_by_default_but_can_be_disabled():
    interspersed = OptionParser()
    interspersed.add_option("-v", action="store_true", default=False)
    options, arguments = interspersed.parse_args(["input.txt", "-v", "tail"])

    strict = OptionParser()
    strict.add_option("-v", action="store_true", default=False)
    strict.disable_interspersed_args()
    strict_options, strict_arguments = strict.parse_args(
        ["input.txt", "-v", "tail"]
    )

    assert options.v is True
    assert arguments == ["input.txt", "tail"]
    assert strict_options.v is False
    assert strict_arguments == ["input.txt", "-v", "tail"]
    # 子命令风格解析器常需在首个位置参数处停止，
    # 避免吞掉子命令自己的选项。


def test_option_group_changes_help_layout_without_changing_values():
    parser = OptionParser(usage="%prog [options] INPUT")
    network = OptionGroup(parser, "Network", "Connection controls")
    network.add_option("--timeout", type="float", metavar="SECONDS")
    parser.add_option_group(network)

    help_text = parser.format_help()
    options, arguments = parser.parse_args(["--timeout", "1.5", "data.bin"])

    assert "Network:" in help_text
    assert "Connection controls" in help_text
    assert "--timeout=SECONDS" in help_text
    assert options.timeout == 1.5
    assert arguments == ["data.bin"]


def test_standard_help_and_version_actions_exit_successfully(capsys):
    parser = OptionParser(prog="legacy-tool", version="%prog 2.4")

    with pytest.raises(SystemExit) as help_exit:
        parser.parse_args(["--help"])
    help_output = capsys.readouterr().out

    with pytest.raises(SystemExit) as version_exit:
        parser.parse_args(["--version"])
    version_output = capsys.readouterr().out

    assert help_exit.value.code == 0
    assert "Usage: legacy-tool" in help_output
    assert version_exit.value.code == 0
    assert version_output.strip() == "legacy-tool 2.4"


def test_invalid_typed_value_exits_with_usage_on_stderr(capsys):
    parser = OptionParser(prog="legacy-tool")
    parser.add_option("--jobs", type="int")

    with pytest.raises(SystemExit) as raised:
        parser.parse_args(["--jobs", "many"])

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert "Usage: legacy-tool" in error
    assert "invalid integer value" in error


def test_conflicting_option_strings_raise_by_default_or_resolve_explicitly():
    strict = OptionParser()
    strict.add_option("-v", "--verbose", action="store_true")
    with pytest.raises(OptionConflictError):
        strict.add_option("-v", "--version-info", action="store_true")

    resolving = OptionParser(conflict_handler="resolve")
    resolving.add_option("-v", "--verbose", action="store_true")
    resolving.add_option("-v", "--version-info", action="store_true")

    short, _ = resolving.parse_args(["-v"])
    long, _ = resolving.parse_args(["--verbose"])
    assert short.version_info is True
    assert long.verbose is True
    # resolve 只把冲突的 option string 交给新选项；
    # 旧选项若仍有别名就继续存在。


def test_callback_can_build_structured_values_and_raise_option_value_error():
    def parse_assignment(option, option_string, value, parser):
        if "=" not in value:
            raise OptionValueError(f"{option_string} requires KEY=VALUE")
        key, item = value.split("=", 1)
        parser.values.metadata[key] = item

    parser = OptionParser()
    parser.set_defaults(metadata={})
    parser.add_option(
        "--set",
        action="callback",
        callback=parse_assignment,
        type="string",
    )

    options, _ = parser.parse_args(["--set", "color=blue", "--set", "jobs=4"])
    assert options.metadata == {"color": "blue", "jobs": "4"}

    with pytest.raises(SystemExit) as raised:
        parser.parse_args(["--set", "broken"])
    assert raised.value.code == 2


def test_custom_option_subclass_adds_a_hexadecimal_type():
    def check_hex(option, option_string, value):
        try:
            return int(value, 16)
        except ValueError as error:
            raise OptionValueError(
                f"option {option_string}: invalid hexadecimal value: {value}"
            ) from error

    class HexOption(Option):
        TYPES = Option.TYPES + ("hexadecimal",)
        TYPE_CHECKER = Option.TYPE_CHECKER.copy()
        TYPE_CHECKER["hexadecimal"] = check_hex

    parser = OptionParser(option_class=HexOption)
    parser.add_option("--mask", type="hexadecimal")

    options, _ = parser.parse_args(["--mask", "ff"])
    assert options.mask == 255


def test_pipes_template_validates_topology_and_file_placeholders():
    template = pipes.Template()

    with pytest.raises(ValueError, match="SOURCE can only be prepended"):
        template.append("producer", pipes.SOURCE)
    with pytest.raises(ValueError, match="SINK can only be appended"):
        template.prepend("consumer", pipes.SINK)
    with pytest.raises(ValueError, match=r"missing \$IN"):
        template.append("converter $OUT", pipes.FILEIN_FILEOUT)
    with pytest.raises(ValueError, match=r"missing \$OUT"):
        template.append("converter $IN", pipes.FILEIN_FILEOUT)

    template.prepend("producer", pipes.SOURCE)
    template.append("consumer", pipes.SINK)
    assert template.steps == [
        ("producer", ".-"),
        ("consumer", "-."),
    ]
    with pytest.raises(ValueError, match="already ends with SINK"):
        template.append("another", pipes.STDIN_STDOUT)


def test_pipes_clone_is_independent_and_reset_only_clears_steps():
    original = pipes.Template()
    original.debug(True)
    original.append(uppercase_filter(), pipes.STDIN_STDOUT)
    clone = original.clone()

    clone.append(uppercase_filter(), pipes.STDIN_STDOUT)
    original.reset()

    assert original.steps == []
    assert original.debugging is True
    assert len(clone.steps) == 2
    assert clone.debugging is True


def test_makepipeline_quotes_paths_and_debug_prints_the_generated_shell(tmp_path, capsys):
    template = pipes.Template()
    template.append(uppercase_filter(), pipes.STDIN_STDOUT)
    template.debug(True)
    source = tmp_path / "input with spaces.txt"
    target = tmp_path / "output with spaces.txt"

    command = template.makepipeline(str(source), str(target))

    assert command.startswith("set -x; ")
    assert shlex.quote(str(source)) in command
    assert shlex.quote(str(target)) in command
    assert capsys.readouterr().out.strip() in command
    # 模板命令本身仍是 /bin/sh 文本；路径会引用，
    # 不代表任意 cmd 参数自动安全。


@pytest.mark.skipif(os.name != "posix", reason="pipes 使用 Unix /bin/sh 管道")
def test_pipes_copy_runs_a_standard_stream_filter_between_files(tmp_path):
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("Python\nstdlib\n", encoding="utf-8")
    template = pipes.Template()
    template.append(uppercase_filter(), pipes.STDIN_STDOUT)

    status = template.copy(str(source), str(target))

    assert os.waitstatus_to_exitcode(status) == 0
    assert target.read_text(encoding="utf-8") == "PYTHON\nSTDLIB\n"


@pytest.mark.skipif(os.name != "posix", reason="pipes 使用 Unix /bin/sh 管道")
def test_pipes_open_read_and_write_expose_the_outer_end_of_a_pipeline(tmp_path):
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("read side", encoding="utf-8")
    template = pipes.Template()
    template.append(uppercase_filter(), pipes.STDIN_STDOUT)

    with template.open(str(source), "r") as reader:
        assert reader.read() == "READ SIDE"
    with template.open(str(target), "w") as writer:
        writer.write("write side")

    assert target.read_text(encoding="utf-8") == "WRITE SIDE"


def test_file_steps_name_real_inputs_and_outputs_with_shell_variables(tmp_path):
    template = pipes.Template()
    copy_program = python_filter(
        "import pathlib, sys; "
        "pathlib.Path(sys.argv[2]).write_bytes(pathlib.Path(sys.argv[1]).read_bytes())"
    )
    template.append(
        f'{copy_program} "$IN" "$OUT"',
        pipes.FILEIN_FILEOUT,
    )

    command = template.makepipeline(
        str(tmp_path / "source.bin"),
        str(tmp_path / "target.bin"),
    )

    assert "IN=" in command
    assert "OUT=" in command
    assert '"$IN" "$OUT"' in command
    # 相邻步骤一旦需要真实文件，pipes 会创建中间临时文件，
    # 并在管道结束后删除。
