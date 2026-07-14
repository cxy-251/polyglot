"""198｜``getpass`` 无回显输入的 fallback 与登录名查找顺序。

getpass 优先使用 controlling terminal；无法控制 echo 时才警告并从 stdin 普通读取。
测试故意拒绝 ``/dev/tty`` 并使用内存流，不触碰真实终端设置，也不保存真实密码。
``getuser`` 首先按固定环境变量顺序找非空值，最后才查询 Unix password database。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.getpass.getpass python.getpass.prompt
# polyglot-covers: python.getpass.stream python.getpass.controlling-terminal
# polyglot-covers: python.getpass.echo-free-fallback
# polyglot-covers: python.getpass.GetPassWarning python.getpass.stdin-fallback
# polyglot-covers: python.getpass.prompt-encoding-replace
# polyglot-covers: python.getpass.getuser python.getpass.getuser-environment-order
# polyglot-covers: python.getpass.getuser-empty-environment-ignored
# polyglot-covers: python.getpass.getuser-password-database-fallback

import getpass
import io
import sys
import types

import pytest


def _deny_controlling_terminal(*args, **kwargs):
    raise OSError("no controlling terminal")


@pytest.mark.skipif(
    getpass.getpass is not getpass.unix_getpass,
    reason="该 fallback 路径针对 Unix getpass 实现",
)
def test_public_getpass_warns_and_reads_stdin_when_echo_cannot_be_disabled(
    monkeypatch,
):
    """fallback 会显式告知可能回显；返回值去掉一个末尾换行。"""

    input_stream = io.StringIO("secret value\n")
    prompt_stream = io.StringIO()
    monkeypatch.setattr(getpass.os, "open", _deny_controlling_terminal)
    monkeypatch.setattr(sys, "stdin", input_stream)

    with pytest.warns(getpass.GetPassWarning, match="Can not control echo"):
        password = getpass.getpass("Secret: ", stream=prompt_stream)

    assert password == "secret value"
    assert prompt_stream.getvalue() == (
        "Warning: Password input may be echoed.\nSecret: \n"
    )
    assert issubclass(getpass.GetPassWarning, UserWarning)


@pytest.mark.skipif(
    getpass.getpass is not getpass.unix_getpass,
    reason="该 prompt encoding 路径针对 Unix getpass 实现",
)
def test_unencodable_prompt_uses_stream_encoding_with_replace(monkeypatch):
    """prompt 无法编码时尽量输出替代字符，而不是因提示文字阻止密码读取。"""

    raw_output = io.BytesIO()
    prompt_stream = io.TextIOWrapper(
        raw_output,
        encoding="ascii",
        errors="strict",
    )
    monkeypatch.setattr(getpass.os, "open", _deny_controlling_terminal)
    monkeypatch.setattr(sys, "stdin", io.StringIO("answer\n"))
    try:
        with pytest.warns(getpass.GetPassWarning):
            password = getpass.getpass("密码: ", stream=prompt_stream)
        prompt_stream.flush()

        assert password == "answer"
        assert raw_output.getvalue() == (
            b"Warning: Password input may be echoed.\n??: \n"
        )
    finally:
        prompt_stream.detach()


def test_getuser_uses_first_nonempty_environment_variable(monkeypatch):
    """优先级是 LOGNAME、USER、LNAME、USERNAME；空字符串视为未设置。"""

    for name in ("LOGNAME", "USER", "LNAME", "USERNAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LOGNAME", "")
    monkeypatch.setenv("USER", "second")
    monkeypatch.setenv("LNAME", "third")
    monkeypatch.setenv("USERNAME", "fourth")

    assert getpass.getuser() == "second"

    monkeypatch.setenv("LOGNAME", "first")
    assert getpass.getuser() == "first"


@pytest.mark.skipif(not hasattr(getpass.os, "getuid"), reason="平台没有 Unix uid/pwd fallback")
def test_getuser_falls_back_to_password_database_when_environment_is_absent(
    monkeypatch,
):
    """pwd lookup 的异常不会吞掉；调用方能看到平台数据库失败原因。"""

    for name in ("LOGNAME", "USER", "LNAME", "USERNAME"):
        monkeypatch.delenv(name, raising=False)

    looked_up = []

    def getpwuid(uid):
        looked_up.append(uid)
        return ("database-user",)

    fake_pwd = types.SimpleNamespace(getpwuid=getpwuid)
    monkeypatch.setitem(sys.modules, "pwd", fake_pwd)
    monkeypatch.setattr(getpass.os, "getuid", lambda: 42)

    assert getpass.getuser() == "database-user"
    assert looked_up == [42]
