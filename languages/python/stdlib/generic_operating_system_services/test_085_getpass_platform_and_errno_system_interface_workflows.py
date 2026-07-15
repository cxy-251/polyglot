"""085｜``getpass`` 无回显输入的 fallback 与登录名查找顺序。

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
import platform
import errno
import os

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


# ``platform`` 的 portable uname、展示字符串与 Python build 信息。
#
# platform 返回的是“尽力识别”结果，无法确定的字段可能为空；测试只校验结构和同一进程
# 内部一致性，不硬编码容器 kernel、hostname 或 CPU。``platform()`` 明确面向人类展示，
# 不能作为稳定机器协议；自动判断应选择 system/machine 或 os-release 的结构化字段。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.platform.uname python.platform.uname-namedtuple
# polyglot-covers: python.platform.system python.platform.node
# polyglot-covers: python.platform.release python.platform.version
# polyglot-covers: python.platform.machine python.platform.processor
# polyglot-covers: python.platform.platform python.platform.platform-aliased
# polyglot-covers: python.platform.platform-terse python.platform.human-readable-warning
# polyglot-covers: python.platform.python_version python.platform.python_version_tuple
# polyglot-covers: python.platform.python_implementation
# polyglot-covers: python.platform.python_build python.platform.python_compiler
# polyglot-covers: python.platform.python_branch python.platform.python_revision



def test_uname_is_a_six_field_named_tuple_consistent_with_accessors():
    """platform.uname 比 os.uname 多 processor，且前两字段命名为 system/node。"""

    info = platform.uname()

    assert info._fields == (
        "system",
        "node",
        "release",
        "version",
        "machine",
        "processor",
    )
    assert tuple(info) == (
        platform.system(),
        platform.node(),
        platform.release(),
        platform.version(),
        platform.machine(),
        platform.processor(),
    )
    assert all(isinstance(value, str) for value in info)


def test_platform_string_options_remain_human_readable_not_machine_schema():
    """aliased/terse 改变信息选择；只可依赖返回 str，不应按连字符位置反解析。"""

    verbose = platform.platform(aliased=False, terse=False)
    aliased = platform.platform(aliased=True, terse=False)
    terse = platform.platform(aliased=False, terse=True)

    assert isinstance(verbose, str)
    assert isinstance(aliased, str)
    assert isinstance(terse, str)
    assert verbose
    assert terse


def test_python_version_helpers_match_structured_interpreter_version():
    """version tuple 元素是字符串；patchlevel 即使为零也不会省略。"""

    version_tuple = platform.python_version_tuple()

    assert len(version_tuple) == 3
    assert all(isinstance(part, str) for part in version_tuple)
    assert platform.python_version() == ".".join(version_tuple)
    assert tuple(map(int, version_tuple)) == tuple(sys.version_info[:3])
    assert platform.python_implementation().lower() == sys.implementation.name.lower()


def test_python_build_metadata_has_stable_shapes_but_platform_defined_values():
    """branch/revision 在 release build 中可能为空，不能据此判断解释器是否合法。"""

    build_number, build_date = platform.python_build()

    assert isinstance(build_number, str)
    assert isinstance(build_date, str)
    assert isinstance(platform.python_compiler(), str)
    assert isinstance(platform.python_branch(), str)
    assert isinstance(platform.python_revision(), str)


# ``platform`` architecture、system alias 与 OS-specific probe fallback。
#
# ``architecture`` 可能调用系统 ``file`` 命令，只是 executable 格式的启发式结果；判断
# 当前解释器位数时 ``sys.maxsize`` 更可靠。OS-specific 函数在其他系统通常返回调用方
# 提供的 fallback 或空字段，适合展示信息而非能力检测。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.platform.architecture python.platform.architecture-fallback
# polyglot-covers: python.platform.architecture-file-command-caveat
# polyglot-covers: python.platform.system_alias python.platform.SunOS-Solaris-alias
# polyglot-covers: python.platform.libc_ver
# polyglot-covers: python.platform.java_ver python.platform.win32_ver
# polyglot-covers: python.platform.win32_edition python.platform.win32_is_iot
# polyglot-covers: python.platform.mac_ver
# polyglot-covers: python.platform.platform-specific-empty-fields



def test_architecture_returns_strings_and_agrees_with_pointer_size_indicator():
    """linkage 可为空；bits 对当前解释器通常来自 executable probe 或 pointer size。"""

    bits, linkage = platform.architecture()
    pointer_bits = "64bit" if sys.maxsize > 2**32 else "32bit"

    assert bits in ("32bit", "64bit")
    assert bits == pointer_bits
    assert isinstance(linkage, str)


def test_system_alias_maps_sunos_release_to_common_solaris_numbering():
    """SunOS 5.x 的 marketing alias 是 Solaris 2.x；未知 system 保持不变。"""

    assert platform.system_alias("SunOS", "5.11", "Generic") == (
        "Solaris",
        "2.11",
        "Generic",
    )
    assert platform.system_alias("ExampleOS", "1.2", "build") == (
        "ExampleOS",
        "1.2",
        "build",
    )


def test_libc_probe_returns_caller_fallback_when_file_cannot_be_scanned(tmp_path):
    """不存在的 executable 不抛错，而是返回给定 lib/version fallback。"""

    missing = tmp_path / "missing-executable"

    assert platform.libc_ver(
        executable=str(missing),
        lib="unknown-libc",
        version="unknown-version",
    ) == ("unknown-libc", "unknown-version")


def test_platform_specific_probes_keep_documented_tuple_shapes():
    """不要把空字段当作否定能力；它只表示当前实现无法取得识别信息。"""

    java = platform.java_ver()
    windows = platform.win32_ver()
    mac = platform.mac_ver()

    assert len(java) == 4
    assert len(java[2]) == 3
    assert len(java[3]) == 3
    assert len(windows) == 4
    assert len(mac) == 3
    assert len(mac[1]) == 3


def test_windows_edition_helpers_have_explicit_non_windows_fallback():
    """edition 返回 None 表示无法取得；IoT predicate 相应为 False。"""

    if platform.system() != "Windows":
        assert platform.win32_edition() is None
        assert platform.win32_is_iot() is False


# ``platform.freedesktop_os_release`` parsing、candidate fallback 与 cache。
#
# Python 3.10 新增的 os-release reader 会解引号/反斜杠，保证 NAME、ID、PRETTY_NAME
# 三个基础字段，并返回 dict copy。它缓存首次成功解析；测试替换内部 candidate path 指向
# ``tmp_path``，既执行真实 public parser，又不读取或修改宿主机 ``/etc/os-release``。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.platform.freedesktop_os_release
# polyglot-covers: python.platform.os-release-candidate-order
# polyglot-covers: python.platform.os-release-shell-unquoting
# polyglot-covers: python.platform.os-release-required-defaults
# polyglot-covers: python.platform.os-release-vendor-fields
# polyglot-covers: python.platform.os-release-ID_LIKE-workflow
# polyglot-covers: python.platform.os-release-cache
# polyglot-covers: python.platform.os-release-copy-on-return
# polyglot-covers: python.platform.os-release-missing-error




def _redirect_candidates(monkeypatch, *paths):
    monkeypatch.setattr(platform, "_os_release_candidates", tuple(map(str, paths)))
    monkeypatch.setattr(platform, "_os_release_cache", None)


def test_os_release_uses_first_readable_candidate_and_unquotes_values(
    tmp_path,
    monkeypatch,
):
    """ID/ID_LIKE 用于程序判断；PRETTY_NAME 等展示字段不适合稳定比较。"""

    missing = tmp_path / "missing-os-release"
    release_file = tmp_path / "os-release"
    release_file.write_text(
        """\
# ignored comment
NAME="Example Linux"
ID=example
PRETTY_NAME="Example Linux \\"Stable\\""
VERSION_ID="1.0"
ID_LIKE="debian rhel"
VENDOR_FIELD="cost=\\$0"
""",
        encoding="utf-8",
    )
    _redirect_candidates(monkeypatch, missing, release_file)

    info = platform.freedesktop_os_release()

    assert info["NAME"] == "Example Linux"
    assert info["ID"] == "example"
    assert info["PRETTY_NAME"] == 'Example Linux "Stable"'
    assert info["VERSION_ID"] == "1.0"
    assert [info["ID"], *info["ID_LIKE"].split()] == [
        "example",
        "debian",
        "rhel",
    ]
    assert info["VENDOR_FIELD"] == "cost=$0"


def test_os_release_returns_copies_and_caches_first_success(tmp_path, monkeypatch):
    """修改返回 dict 不污染 cache；磁盘变化也需新进程或显式失效内部 cache 才可见。"""

    release_file = tmp_path / "os-release"
    release_file.write_text("ID=first\n", encoding="utf-8")
    _redirect_candidates(monkeypatch, release_file)

    first = platform.freedesktop_os_release()
    first["ID"] = "mutated-by-caller"
    release_file.write_text("ID=second\n", encoding="utf-8")
    cached = platform.freedesktop_os_release()

    assert cached["ID"] == "first"
    assert cached["NAME"] == "Linux"
    assert cached["PRETTY_NAME"] == "Linux"
    assert first is not cached

    platform._os_release_cache = None
    assert platform.freedesktop_os_release()["ID"] == "second"


def test_os_release_raises_when_no_candidate_is_readable(tmp_path, monkeypatch):
    """缺少 os-release 是可预期平台差异，调用方可捕获 OSError 再选择其他识别方法。"""

    first = tmp_path / "absent-one"
    second = tmp_path / "absent-two"
    _redirect_candidates(monkeypatch, first, second)

    with pytest.raises(OSError):
        platform.freedesktop_os_release()


# ``errno`` 平台符号、``errorcode`` 反向映射与 ``OSError`` 分类。
#
# errno 名称是 C 系统错误码的可读常量，具体可用集合由平台决定；业务分支应比较
# ``exc.errno`` 与符号常量，不解析可能本地化的错误文本。构造 OSError 时，CPython 会按
# 常见 errno 自动选择 FileNotFoundError、PermissionError 等更具体的内建异常子类。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.errno.integer-symbols python.errno.platform-dependent-symbols
# polyglot-covers: python.errno.errorcode python.errno.numeric-to-symbol-name
# polyglot-covers: python.errno.ENOENT python.errno.EACCES
# polyglot-covers: python.errno.EEXIST python.errno.EAGAIN
# polyglot-covers: python.errno.OSError.errno python.errno.OSError.filename
# polyglot-covers: python.errno.OSError-subclass-dispatch
# polyglot-covers: python.errno.os.strerror python.errno.localized-message-caveat




def test_errorcode_entries_point_back_to_available_integer_constants():
    """同值 alias 可能只保留一个规范名称，因此不要反向假设每个 alias 都出现。"""

    assert errno.errorcode[errno.ENOENT] == "ENOENT"
    assert errno.errorcode[errno.EACCES] in {"EACCES", "EPERM"}

    for number, name in errno.errorcode.items():
        assert isinstance(number, int)
        assert name.startswith("E")
        assert getattr(errno, name) == number


def test_real_missing_path_exposes_symbolic_errno_and_filename(tmp_path):
    """高级异常类型便于捕获，errno 仍保留底层可移植错误原因。"""

    missing = tmp_path / "does-not-exist"

    with pytest.raises(FileNotFoundError) as raised:
        os.open(missing, os.O_RDONLY)

    assert raised.value.errno == errno.ENOENT
    assert raised.value.filename == str(missing)
    assert errno.errorcode[raised.value.errno] == "ENOENT"


@pytest.mark.parametrize(
    ("number", "expected_type"),
    [
        (errno.ENOENT, FileNotFoundError),
        (errno.EACCES, PermissionError),
        (errno.EEXIST, FileExistsError),
        (errno.EAGAIN, BlockingIOError),
    ],
)
def test_oserror_constructor_dispatches_common_errno_to_specific_subclass(
    number,
    expected_type,
):
    """该自动分派发生在直接构造 OSError；构造任意自定义子类时不会再次改类。"""

    error = OSError(number, os.strerror(number), "resource")

    assert type(error) is expected_type
    assert error.errno == number
    assert error.filename == "resource"


def test_strerror_is_for_people_and_may_be_localized():
    """只依赖它返回非空文本；机器逻辑继续使用 errno 整数。"""

    message = os.strerror(errno.ENOENT)

    assert isinstance(message, str)
    assert message
