"""141｜``netrc`` credential lookup、default fallback、macdef 与权限保护。

``netrc`` 把 machine/default 条目映射为三元组，并保留 ``macdef`` 的原始命令行。
无参数读取 POSIX ``~/.netrc`` 时会检查 owner/mode，防止其他用户读取
password；显式路径主要用于调用方指定的文件，并不会触发这项 home-file
安全策略。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.netrc.netrc python.netrc.machine
# polyglot-covers: python.netrc.login python.netrc.account
# polyglot-covers: python.netrc.password python.netrc.default
# polyglot-covers: python.netrc.authenticators python.netrc.default-fallback
# polyglot-covers: python.netrc.missing-host python.netrc.hosts
# polyglot-covers: python.netrc.macdef python.netrc.macros
# polyglot-covers: python.netrc.repr python.netrc.comments-discarded
# polyglot-covers: python.netrc.NetrcParseError python.netrc.error-filename-line
# polyglot-covers: python.netrc.utf8-first python.netrc.ascii-password-limit
# polyglot-covers: python.netrc.default-home-file python.netrc.posix-permission-check
# polyglot-covers: python.netrc.explicit-file-no-permission-check

import os
from netrc import NetrcParseError, netrc

import pytest


def test_machine_entries_and_default_follow_documented_lookup_order(tmp_path):
    """exact machine 优先；未知 host 回退到 default；两者都没有时返回 None。"""

    path = tmp_path / "credentials.netrc"
    path.write_text(
        """
        machine api.example
          login alice
          account operations
          password p@ss-word!
        machine mirror.example login bob password token-2
        default login guest password anonymous@example.invalid
        """,
        encoding="utf-8",
    )

    credentials = netrc(path)

    assert credentials.authenticators("api.example") == (
        "alice",
        "operations",
        "p@ss-word!",
    )
    assert credentials.authenticators("mirror.example") == ("bob", None, "token-2")
    assert credentials.authenticators("unknown.example") == (
        "guest",
        None,
        "anonymous@example.invalid",
    )
    assert credentials.hosts["default"][0] == "guest"

    without_default = tmp_path / "without-default.netrc"
    without_default.write_text(
        "machine only.example login one password secret\n",
        encoding="utf-8",
    )
    assert netrc(without_default).authenticators("unknown.example") is None


def test_macdef_preserves_command_lines_until_a_blank_line(tmp_path):
    """macro 由空行终止；macros value 是含原 newline 的命令行 list。"""

    path = tmp_path / "macros.netrc"
    path.write_text(
        """machine ftp.example login alice password secret
macdef deploy
cd releases
put app.tar.gz

macdef cleanup
delete app.old

""",
        encoding="utf-8",
    )

    parsed = netrc(path)

    assert parsed.macros == {
        "deploy": ["cd releases\n", "put app.tar.gz\n"],
        "cleanup": ["delete app.old\n"],
    }


def test_password_punctuation_is_allowed_but_whitespace_terminates_token(tmp_path):
    """password 可含 ASCII punctuation；空白会开始下一个 token 并导致错误。"""

    valid = tmp_path / "punctuation.netrc"
    valid.write_text(
        "machine api.example login alice password !#$%&()*+,-./:;=?@[]^_{}~\n",
        encoding="utf-8",
    )
    assert netrc(valid).authenticators("api.example")[2] == "!#$%&()*+,-./:;=?@[]^_{}~"

    invalid = tmp_path / "whitespace.netrc"
    invalid.write_text(
        "machine api.example login alice password two words\n",
        encoding="utf-8",
    )
    with pytest.raises(NetrcParseError, match="bad follower token"):
        netrc(invalid)


def test_repr_serializes_data_but_discards_comments_and_can_be_parsed_again(tmp_path):
    """repr 是 netrc-format dump，不是 source-preserving editor；comment 不会保留。"""

    original = tmp_path / "original.netrc"
    original.write_text(
        "# deployment account\n"
        "machine api.example login alice account ops password secret\n",
        encoding="utf-8",
    )
    parsed = netrc(original)

    dumped = repr(parsed)
    assert "deployment account" not in dumped
    assert "machine api.example" in dumped

    round_trip = tmp_path / "round-trip.netrc"
    round_trip.write_text(dumped, encoding="utf-8")
    assert netrc(round_trip).hosts == parsed.hosts


def test_parse_error_exposes_filename_and_line_for_diagnostics(tmp_path):
    """不完整 machine entry 抛专用异常，并提供 filename/lineno。"""

    path = tmp_path / "broken.netrc"
    path.write_text("machine api.example login\n", encoding="utf-8")

    with pytest.raises(NetrcParseError) as caught:
        netrc(path)

    assert caught.value.filename == path
    # 具体计数由 shlex 的 newline consumption 决定，异常始终携带可展示的行号。
    assert isinstance(caught.value.lineno, int)
    assert caught.value.lineno >= 1
    assert caught.value.msg


def test_explicit_file_uses_utf8_first_and_does_not_enforce_home_mode(tmp_path):
    """3.10 先以 UTF-8 解码；显式 file 即使 mode 0644 也不走 ~/.netrc 检查。"""

    path = tmp_path / "explicit.netrc"
    path.write_text(
        "# UTF-8 注释：部署凭据\n"
        "machine api.example login alice account operations password ascii-secret\n",
        encoding="utf-8",
    )
    path.chmod(0o644)

    assert netrc(path).authenticators("api.example") == (
        "alice",
        "operations",
        "ascii-secret",
    )


@pytest.mark.skipif(os.name != "posix", reason="owner/mode 检查只属于 POSIX")
def test_default_home_file_rejects_group_or_other_access(tmp_path, monkeypatch):
    """无参数才把文件当作用户 secret；0600 通过，0644 因 password 被拒绝。"""

    home_file = tmp_path / ".netrc"
    home_file.write_text(
        "machine api.example login alice password secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))

    home_file.chmod(0o644)
    with pytest.raises(NetrcParseError, match="access too permissive"):
        netrc()

    home_file.chmod(0o600)
    assert netrc().authenticators("api.example") == ("alice", None, "secret")
