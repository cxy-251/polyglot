"""182｜``argparse`` 自定义 registry/action、错误传播与非退出式嵌入。

解析器默认把命令行错误打印到 stderr 并以状态 2 退出，这对 CLI 合理、对库代码却未必。
Python 3.10 的 ``exit_on_error=False`` 只把一部分 action 错误改为 ``ArgumentError``；
未知参数仍会触发 ``SystemExit``。需要完全控制时应覆写 ``error``/``exit``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.argparse.Action python.argparse.custom-action
# polyglot-covers: python.argparse.Action.__call__ python.argparse.ArgumentError
# polyglot-covers: python.argparse.register python.argparse.named-custom-type
# polyglot-covers: python.argparse.exit_on_error python.argparse.error-status-2
# polyglot-covers: python.argparse.exit-on-error-incomplete-scope
# polyglot-covers: python.argparse.ArgumentParser.error python.argparse.ArgumentParser.exit
# polyglot-covers: python.argparse.help-action-exit-zero python.argparse.literal-percent-help

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io

import pytest


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
