"""138｜cmd 与 shlex：从命令文本到解释器分派的完整工作流。

``shlex`` 负责把类 Unix shell 的文本切成 token，``cmd.Cmd`` 负责循环、
命令查找、帮助和补全。二者经常一起用于管理脚本和小型 REPL，因此放在
同一套案例中比按小模块拆开更便于查阅。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.cmd python.cmd.Cmd-subclass
# polyglot-covers: python.cmd.cmdloop python.cmd.stdin-and-cmdqueue
# polyglot-covers: python.cmd.preloop-precmd-postcmd-postloop
# polyglot-covers: python.cmd.parseline python.cmd.question-and-bang-shortcuts
# polyglot-covers: python.cmd.onecmd-do-dispatch python.cmd.default
# polyglot-covers: python.cmd.emptyline-repeats-lastcmd python.cmd.EOF-clears-lastcmd
# polyglot-covers: python.cmd.help-method-docstring-and-topics
# polyglot-covers: python.cmd.completenames python.cmd.complete-help
# polyglot-covers: python.cmd.complete-command-and-arguments
# polyglot-covers: python.cmd.columnize python.cmd.public-configuration
# polyglot-covers: python.stdlib.shlex python.shlex.split-comments-and-posix
# polyglot-covers: python.shlex.quote python.shlex.join-roundtrip
# polyglot-covers: python.shlex.posix-versus-compatibility-mode
# polyglot-covers: python.shlex.get-token-push-token-read-token
# polyglot-covers: python.shlex.eof-and-iterator-protocol
# polyglot-covers: python.shlex.punctuation-chars python.shlex.whitespace-split
# polyglot-covers: python.shlex.custom-character-classes
# polyglot-covers: python.shlex.sourcehook python.shlex.source-stack
# polyglot-covers: python.shlex.error-leader-and-lineno
# polyglot-covers: python.shlex.unclosed-quote-and-escape-errors
# polyglot-covers: python.shlex.split-none-deprecation
# polyglot-covers: python.cmd-shlex.safe-mini-command-workflow

import cmd
from io import StringIO
import shlex
import sys
from types import SimpleNamespace

import pytest


class TeachingShell(cmd.Cmd):
    """只实现案例需要的命令；事件列表让隐式分派顺序变得可观察。"""

    prompt = "teach> "
    intro = "教学控制台"

    def __init__(self, *, stdin=None, stdout=None):
        super().__init__(stdin=stdin, stdout=stdout)
        # 传入 stdin 还不够：默认 raw input 会绕过 self.stdin。
        self.use_rawinput = False
        self.events = []

    def preloop(self):
        self.events.append(("preloop",))

    def precmd(self, line):
        self.events.append(("precmd", line))
        if line.startswith("say "):
            return "echo " + line.removeprefix("say ")
        return line

    def postcmd(self, stop, line):
        self.events.append(("postcmd", stop, line))
        return stop

    def postloop(self):
        self.events.append(("postloop",))

    def do_echo(self, arg):
        """echo TEXT：记录并输出原样参数。"""

        self.events.append(("echo", arg))
        self.stdout.write(f"ECHO:{arg}\n")

    def complete_echo(self, text, line, begidx, endidx):
        choices = ["alpha", "alpine", "beta"]
        return [choice for choice in choices if choice.startswith(text)]

    def do_sum(self, arg):
        """sum N...：用 shlex 解析参数后求和。"""

        values = [int(token) for token in shlex.split(arg)]
        result = sum(values)
        self.events.append(("sum", values, result))
        self.stdout.write(f"SUM:{result}\n")

    def help_sum(self):
        self.stdout.write("sum 接受一个或多个整数\n")

    def help_concepts(self):
        self.stdout.write("concepts 是没有同名 do_* 的帮助主题\n")

    def do_hidden(self, arg):
        self.events.append(("hidden", arg))

    def do_shell(self, arg):
        # 这里只记录 ``!`` 快捷语法，绝不执行真实 shell。
        self.events.append(("shell", arg))

    def do_stop(self, arg):
        self.events.append(("stop", arg))
        return True

    def do_EOF(self, arg):
        self.events.append(("EOF", arg))
        return True

    def default(self, line):
        self.events.append(("default", line))
        return "unknown-result"


def make_shell(input_text=""):
    output = StringIO()
    shell = TeachingShell(stdin=StringIO(input_text), stdout=output)
    return shell, output


def test_cmd_public_configuration_and_constructor_streams():
    stdin = StringIO("stop\n")
    stdout = StringIO()
    shell = TeachingShell(stdin=stdin, stdout=stdout)

    assert shell.stdin is stdin
    assert shell.stdout is stdout
    assert shell.prompt == "teach> "
    assert shell.intro == "教学控制台"
    assert shell.completekey == "tab"
    assert shell.cmdqueue == []
    assert shell.use_rawinput is False
    assert "_" in shell.identchars


def test_parseline_strips_input_and_recognizes_shortcuts():
    shell, _ = make_shell()

    assert shell.parseline("  echo hello world  ") == (
        "echo",
        "hello world",
        "echo hello world",
    )
    assert shell.parseline("?sum") == ("help", "sum", "help sum")
    assert shell.parseline("!echo safe") == (
        "shell",
        "echo safe",
        "shell echo safe",
    )
    assert shell.parseline("   ") == (None, None, "")

    # 命令名只吸收 identchars；标点和后面的内容都属于 arg。
    assert shell.parseline("echo-value") == (
        "echo",
        "-value",
        "echo-value",
    )


def test_bang_without_do_shell_is_sent_to_default_as_an_unparsed_line():
    bare = cmd.Cmd(stdout=StringIO())

    assert bare.parseline("!echo hello") == (None, None, "!echo hello")


def test_onecmd_dispatches_do_method_and_returns_its_result():
    shell, output = make_shell()

    assert shell.onecmd("echo hello world") is None
    assert shell.onecmd("stop now") is True

    assert shell.events == [
        ("echo", "hello world"),
        ("stop", "now"),
    ]
    assert output.getvalue() == "ECHO:hello world\n"

    # onecmd 只是分派器，不会自动调用 precmd/postcmd；这些钩子属于 cmdloop。
    assert not any(event[0] == "precmd" for event in shell.events)


def test_unknown_command_uses_default_and_base_default_prints_diagnostic():
    shell, _ = make_shell()
    assert shell.onecmd("missing argument") == "unknown-result"
    assert shell.events == [("default", "missing argument")]

    output = StringIO()
    bare = cmd.Cmd(stdout=output)
    assert bare.onecmd("missing argument") is None
    assert output.getvalue() == "*** Unknown syntax: missing argument\n"


def test_emptyline_repeats_last_nonempty_command_by_default():
    shell, output = make_shell()

    shell.onecmd("echo repeat me")
    shell.onecmd("")

    assert shell.events == [
        ("echo", "repeat me"),
        ("echo", "repeat me"),
    ]
    assert output.getvalue() == "ECHO:repeat me\nECHO:repeat me\n"


def test_eof_command_clears_lastcmd_so_emptyline_does_not_repeat_eof():
    shell, _ = make_shell()
    shell.onecmd("echo before eof")

    assert shell.onecmd("EOF") is True
    assert shell.lastcmd == ""
    assert shell.onecmd("") is None
    assert shell.events[-1] == ("EOF", "")


def test_cmdloop_prefers_queued_commands_and_wraps_them_with_hooks():
    shell, output = make_shell("echo stdin should not be read\n")
    shell.cmdqueue.extend(["echo queued", "stop done"])

    shell.cmdloop(intro="队列演示")

    assert shell.events == [
        ("preloop",),
        ("precmd", "echo queued"),
        ("echo", "queued"),
        ("postcmd", None, "echo queued"),
        ("precmd", "stop done"),
        ("stop", "done"),
        ("postcmd", True, "stop done"),
        ("postloop",),
    ]
    assert output.getvalue() == "队列演示\nECHO:queued\n"


def test_cmdloop_reads_configured_stream_only_when_rawinput_is_disabled():
    shell, output = make_shell("say from stream\n")

    shell.cmdloop(intro="")

    assert ("precmd", "say from stream") in shell.events
    assert ("echo", "from stream") in shell.events
    # readline 返回空串时，cmdloop 合成特殊命令 EOF，再由 do_EOF 停止循环。
    assert ("EOF", "") in shell.events
    assert output.getvalue() == (
        "teach> ECHO:from stream\n"
        "teach> "
    )


def test_precmd_can_rewrite_and_postcmd_can_observe_effective_line():
    shell, output = make_shell()
    shell.cmdqueue.extend(["say rewritten", "stop"])

    shell.cmdloop(intro="")

    assert ("echo", "rewritten") in shell.events
    # postcmd 收到 precmd 改写后的命令，而不是用户最初输入。
    assert ("postcmd", None, "echo rewritten") in shell.events
    assert output.getvalue() == "ECHO:rewritten\n"


def test_shlex_and_cmd_form_a_safe_mini_command_pipeline():
    shell, output = make_shell()

    shell.onecmd('sum 10 "20" -5')

    assert shell.events == [("sum", [10, 20, -5], 25)]
    assert output.getvalue() == "SUM:25\n"


def test_help_prefers_help_method_then_command_docstring_then_nohelp():
    shell, output = make_shell()

    shell.do_help("sum")
    shell.do_help("echo")
    shell.do_help("missing")

    text = output.getvalue()
    assert "sum 接受一个或多个整数" in text
    assert "echo TEXT：记录并输出原样参数。" in text
    assert "*** No help on missing" in text


def test_help_without_topic_groups_documented_misc_and_undocumented_names():
    shell, output = make_shell()

    shell.do_help("")

    text = output.getvalue()
    assert shell.doc_header in text
    assert shell.misc_header in text
    assert shell.undoc_header in text
    assert "echo" in text
    assert "sum" in text
    assert "concepts" in text
    assert "hidden" in text


def test_command_and_help_name_completion_discovers_methods():
    shell, _ = make_shell()

    assert shell.completenames("ec") == ["echo"]
    assert "sum" in shell.complete_help("s", "help s", 5, 6)
    assert "concepts" in shell.complete_help("c", "help c", 5, 6)
    assert shell.completedefault("x", "missing x", 8, 9) == []


def test_complete_uses_command_names_first_then_command_specific_arguments(
    monkeypatch,
):
    shell, _ = make_shell()
    fake_readline = SimpleNamespace(
        get_line_buffer=lambda: "ec",
        get_begidx=lambda: 0,
        get_endidx=lambda: 2,
    )
    monkeypatch.setitem(sys.modules, "readline", fake_readline)

    assert shell.complete("ec", 0) == "echo"
    assert shell.complete("ec", 1) is None

    fake_readline.get_line_buffer = lambda: "echo al"
    fake_readline.get_begidx = lambda: 5
    fake_readline.get_endidx = lambda: 7
    assert shell.complete("al", 0) == "alpha"
    assert shell.complete("al", 1) == "alpine"
    assert shell.complete("al", 2) is None


def test_columnize_handles_empty_single_and_multi_column_output():
    output = StringIO()
    shell = cmd.Cmd(stdout=output)

    shell.columnize([])
    shell.columnize(["only"])
    shell.columnize(["alpha", "beta", "gamma", "delta"], displaywidth=18)

    lines = output.getvalue().splitlines()
    assert lines[:2] == ["<empty>", "only"]
    assert set(" ".join(lines[2:]).split()) == {
        "alpha",
        "beta",
        "gamma",
        "delta",
    }


def test_columnize_rejects_non_string_cells_with_indices():
    shell = cmd.Cmd(stdout=StringIO())

    with pytest.raises(TypeError, match=r"i in 1, 3"):
        shell.columnize(["ok", 2, "still ok", None])


def test_shlex_split_handles_quotes_escapes_and_optional_comments():
    command = r'''deploy "two words" 'literal $HOME' plain\ value'''

    assert shlex.split(command) == [
        "deploy",
        "two words",
        "literal $HOME",
        "plain value",
    ]
    assert shlex.split("value # kept", comments=False) == [
        "value",
        "#",
        "kept",
    ]
    assert shlex.split("value # ignored", comments=True) == ["value"]


def test_posix_and_compatibility_modes_differ_on_quotes_and_empty_tokens():
    text = "'two words' ''"

    assert shlex.split(text, posix=True) == ["two words", ""]
    assert shlex.split(text, posix=False) == ["'two words'", "''"]

    posix = shlex.shlex("", posix=True)
    compatibility = shlex.shlex("", posix=False)
    assert posix.eof is None
    assert compatibility.eof == ""


@pytest.mark.parametrize(
    ("value", "quoted"),
    [
        ("", "''"),
        ("plain-name.txt", "plain-name.txt"),
        ("two words", "'two words'"),
        ("a'b", "'a'\"'\"'b'"),
        ("$(do-not-run)", "'$(do-not-run)'"),
    ],
)
def test_quote_produces_one_unix_shell_token(value, quoted):
    assert shlex.quote(value) == quoted
    assert shlex.split(quoted) == [value]


def test_join_round_trips_tokens_including_injection_shaped_text():
    arguments = [
        "deploy",
        "two words",
        "file; rm -rf ignored",
        "a'b",
    ]

    command_text = shlex.join(arguments)

    assert shlex.split(command_text) == arguments
    assert "'file; rm -rf ignored'" in command_text
    # quote/join 只保证 Unix shell 的一个 token；更稳妥的执行方式仍是
    # 传参数列表并使用 shell=False。本案例只检查字符串，从不执行它。


def test_get_token_pushback_and_raw_read_have_different_layers():
    lexer = shlex.shlex("stream next", posix=True)
    lexer.whitespace_split = True
    lexer.push_token("manual")

    # read_token 直接读字符流，故意绕过 pushback；get_token 才先弹回 token。
    assert lexer.read_token() == "stream"
    assert lexer.get_token() == "manual"
    assert lexer.get_token() == "next"
    assert lexer.get_token() is None


def test_lexer_iterator_stops_at_mode_specific_eof_marker():
    lexer = shlex.shlex("one two", posix=True)
    lexer.whitespace_split = True
    iterator = iter(lexer)

    assert iterator is lexer
    assert next(iterator) == "one"
    assert next(iterator) == "two"
    with pytest.raises(StopIteration):
        next(iterator)
    with pytest.raises(StopIteration):
        next(iterator)


def test_punctuation_chars_groups_runs_but_does_not_validate_shell_grammar():
    lexer = shlex.shlex(
        "a && b; c >>> d",
        posix=True,
        punctuation_chars=True,
    )
    lexer.whitespace_split = True

    assert list(lexer) == [
        "a",
        "&&",
        "b",
        ";",
        "c",
        ">>>",
        "d",
    ]
    assert lexer.punctuation_chars == "();<>|&"
    # >>> 作为连续标点被原样返回；shlex 不判断它是不是有效 shell 运算符。
    with pytest.raises(AttributeError):
        lexer.punctuation_chars = "|"


def test_custom_punctuation_changes_wordchars_only_during_construction():
    lexer = shlex.shlex(
        "left|right --color=auto",
        posix=True,
        punctuation_chars="|",
    )

    assert "|" not in lexer.wordchars
    assert "-" in lexer.wordchars
    assert list(lexer) == ["left", "|", "right", "--color=auto"]


def test_character_class_attributes_define_a_small_custom_language():
    lexer = shlex.shlex(
        "high-value;next # comment\nlast",
        posix=True,
    )
    lexer.wordchars += "-"
    lexer.whitespace += ";"

    assert list(lexer) == ["high-value", "next", "last"]
    assert lexer.lineno == 2


def test_whitespace_split_keeps_non_whitespace_text_together():
    ordinary = shlex.shlex("path/to:file", posix=True)
    whitespace_only = shlex.shlex("path/to:file", posix=True)
    whitespace_only.whitespace_split = True

    assert list(ordinary) == ["path", "/", "to", ":", "file"]
    assert list(whitespace_only) == ["path/to:file"]


def test_source_directive_resolves_relative_to_current_infile(tmp_path):
    main_file = tmp_path / "configs" / "main.rc"
    child_file = main_file.with_name("child.rc")
    main_file.parent.mkdir()
    child_file.write_text("child 'two words'\n", encoding="utf-8")

    lexer = shlex.shlex(
        "source child.rc tail",
        infile=str(main_file),
        posix=True,
    )
    lexer.whitespace_split = True
    lexer.source = "source"

    # get_token 识别 source 后压入子文件，子文件 EOF 后再回到原字符流。
    assert list(lexer) == ["child", "two words", "tail"]
    assert lexer.infile == str(main_file)


def test_push_source_restores_parent_state_and_closes_child_stream():
    parent = StringIO("outer")
    child = StringIO("inner")
    lexer = shlex.shlex(parent, infile="parent.rc", posix=True)
    lexer.whitespace_split = True

    lexer.push_source(child, "child.rc")
    assert lexer.infile == "child.rc"
    assert lexer.lineno == 1
    assert list(lexer) == ["inner", "outer"]

    assert child.closed is True
    assert parent.closed is False
    assert lexer.infile == "parent.rc"


def test_sourcehook_strips_double_quotes_and_reports_opened_name(tmp_path):
    main_file = tmp_path / "main.rc"
    child_file = tmp_path / "child.rc"
    child_file.write_text("content", encoding="utf-8")
    lexer = shlex.shlex("", infile=str(main_file), posix=True)

    opened_name, stream = lexer.sourcehook('"child.rc"')
    try:
        assert opened_name == str(child_file)
        assert stream.read() == "content"
    finally:
        stream.close()


def test_error_leader_uses_current_or_explicit_file_and_line():
    lexer = shlex.shlex("one\ntwo", infile="config.rc", posix=True)
    lexer.whitespace_split = True

    assert lexer.get_token() == "one"
    assert lexer.lineno == 2
    assert lexer.error_leader() == '"config.rc", line 2: '
    assert lexer.error_leader("other.rc", 9) == '"other.rc", line 9: '


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("'never closed", "No closing quotation"),
        ("trailing\\", "No escaped character"),
    ],
)
def test_posix_lexer_reports_unfinished_quote_or_escape(text, message):
    lexer = shlex.shlex(text, infile="broken.rc", posix=True)
    lexer.whitespace_split = True

    with pytest.raises(ValueError, match=message):
        list(lexer)

    # 异常本身不附文件名；调用者可用 error_leader 拼出
    # 供编辑器识别的位置。
    assert lexer.error_leader().startswith('"broken.rc", line ')


def test_split_none_reads_stdin_but_is_deprecated_in_python_310(monkeypatch):
    monkeypatch.setattr(shlex.sys, "stdin", StringIO("one 'two words'"))

    with pytest.warns(DeprecationWarning, match="Passing None"):
        tokens = shlex.split(None)

    assert tokens == ["one", "two words"]


def test_read_token_does_not_expand_source_requests(tmp_path):
    child_file = tmp_path / "child.rc"
    child_file.write_text("inside", encoding="utf-8")
    lexer = shlex.shlex(
        "source child.rc",
        infile=str(tmp_path / "main.rc"),
        posix=True,
    )
    lexer.whitespace_split = True
    lexer.source = "source"

    assert lexer.read_token() == "source"
    # source 的特殊含义只在 get_token 层处理；直接 read_token 后已错过触发点。
    assert lexer.get_token() == "child.rc"
    assert lexer.get_token() is None
