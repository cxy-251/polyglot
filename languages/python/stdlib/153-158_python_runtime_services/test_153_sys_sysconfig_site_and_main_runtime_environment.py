"""153｜sys、sysconfig、site 与 __main__：解释器环境和启动边界。

这组模块回答“当前 Python 是怎样启动和安装的”。案例区分只读的解释器
事实、
必须恢复的进程级开关，以及只有在新解释器启动时才能可靠观察的行为。
涉及 ``.pth``、审计钩子和 ``__main__`` 的案例都放进子进程，避免污染 pytest
进程；子进程仍使用运行测试的同一个 Python 3.10 容器解释器。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.sys python.sys.version-info
# polyglot-covers: python.sys.implementation python.sys.hexversion
# polyglot-covers: python.sys.platform-byteorder-maxsize-maxunicode
# polyglot-covers: python.sys.executable-prefix-base-prefix
# polyglot-covers: python.sys.argv-orig-argv python.sys.path
# polyglot-covers: python.sys.modules python.sys.builtin-module-names
# polyglot-covers: python.sys.stdlib-module-names
# polyglot-covers: python.sys.default-encoding python.sys.filesystem-encoding-errors
# polyglot-covers: python.sys.getsizeof-dunder-sizeof python.sys.intern
# polyglot-covers: python.sys.getrefcount-cpython-detail
# polyglot-covers: python.sys.displayhook python.sys.builtins-underscore
# polyglot-covers: python.sys.excepthook python.sys.original-hooks
# polyglot-covers: python.sys.exit-system-exit python.sys.finally-on-exit
# polyglot-covers: python.sys.recursion-limit python.sys.thread-switch-interval
# polyglot-covers: python.sys.int-max-str-digits
# polyglot-covers: python.sys.current-frames python.sys.current-exceptions
# polyglot-covers: python.sys.audit python.sys.add-audit-hook
# polyglot-covers: python.sys.audit-hook-not-sandbox
# polyglot-covers: python.stdlib.sysconfig python.sysconfig.config-vars
# polyglot-covers: python.sysconfig.paths python.sysconfig.schemes
# polyglot-covers: python.sysconfig.custom-expansion-vars
# polyglot-covers: python.sysconfig.platform python.sysconfig.python-version
# polyglot-covers: python.sysconfig.is-python-build python.sysconfig-cli
# polyglot-covers: python.stdlib.site python.site.site-packages
# polyglot-covers: python.site.user-base-user-site-enable-state
# polyglot-covers: python.site.addsitedir python.site.pth-files
# polyglot-covers: python.site.pth-import-lines python.sitecustomize
# polyglot-covers: python.site-cli
# polyglot-covers: python.stdlib.__main__ python.main.top-level-environment
# polyglot-covers: python.main.command-string-script-module
# polyglot-covers: python.main.name-spec-package-argv0
# polyglot-covers: python.main.import-main-namespace python.main.name-guard

import builtins
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import threading

import pytest


def run_python(*arguments, cwd=None, env=None, check=True):
    """用当前测试解释器启动隔离案例，并保留文本形式的标准流。"""

    completed = subprocess.run(
        [sys.executable, *map(str, arguments)],
        cwd=cwd,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )
    return completed


def child_environment(extra_path=None):
    environment = os.environ.copy()
    if extra_path is not None:
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(extra_path), existing) if part
        )
    return environment


def test_version_implementation_and_machine_facts_describe_this_interpreter():
    assert sys.version_info[:2] == (
        sys.version_info.major,
        sys.version_info.minor,
    )
    assert sys.hexversion >> 24 == sys.version_info.major
    assert sys.implementation.name
    assert sys.implementation.version[:2] == sys.version_info[:2]
    assert isinstance(sys.implementation.cache_tag, (str, type(None)))

    assert sys.platform
    assert sys.byteorder in {"little", "big"}
    assert sys.maxsize > 0
    assert (sys.maxsize + 1) & sys.maxsize == 0
    assert sys.maxunicode == 0x10FFFF


def test_executable_and_prefixes_distinguish_runtime_from_virtual_environment():
    assert Path(sys.executable).name
    assert all(
        isinstance(value, str)
        for value in (sys.prefix, sys.exec_prefix, sys.base_prefix, sys.base_exec_prefix)
    )

    in_virtual_environment = (
        sys.prefix != sys.base_prefix or sys.exec_prefix != sys.base_exec_prefix
    )
    # ``prefix`` 可以被 venv 改写；定位解释器原始安装时应查看 ``base_prefix``。
    if not in_virtual_environment:
        assert sys.prefix == sys.base_prefix
        assert sys.exec_prefix == sys.base_exec_prefix


def test_argument_path_and_module_registries_are_live_process_state():
    assert isinstance(sys.argv, list)
    assert isinstance(sys.path, list)
    assert sys.modules["sys"] is sys
    assert "sys" in sys.builtin_module_names
    assert "pathlib" in sys.stdlib_module_names

    # ``orig_argv`` 保留解释器选项，``argv`` 只保留交给程序的参数；pytest
    # 的具体启动参数不稳定，因此这里只验证接口形状。
    assert isinstance(sys.orig_argv, list)
    assert all(isinstance(argument, str) for argument in sys.orig_argv)


def test_text_encodings_separate_default_and_filesystem_boundaries():
    assert sys.getdefaultencoding() == "utf-8"
    assert isinstance(sys.getfilesystemencoding(), str)
    assert sys.getfilesystemencoding()
    assert isinstance(sys.getfilesystemencodeerrors(), str)
    assert sys.getfilesystemencodeerrors()


def test_getsizeof_uses_sizeof_protocol_but_not_recursive_referents():
    class Sized:
        def __sizeof__(self):
            return 123

    instance = Sized()
    assert sys.getsizeof(instance) >= 123
    assert sys.getsizeof([instance]) < sys.getsizeof([instance] * 1_000)
    # 容器的浅大小不包含它所引用对象的全部大小；统计对象图需另写
    # 遍历策略。
    assert sys.getsizeof(["x"]) == sys.getsizeof(["x" * 10_000])


def test_intern_reuses_equal_strings_and_getrefcount_has_a_temporary_reference():
    first = sys.intern("polyglot-runtime-key")
    second = sys.intern("".join(["polyglot-", "runtime-key"]))
    assert first is second

    marker = object()
    # CPython 调用 ``getrefcount(marker)`` 本身会临时再传入一次引用；
    # 精确数字还会受局部变量和实现细节影响，所以教学代码不应把它当
    # 业务断言。
    assert sys.getrefcount(marker) >= 2


def test_displayhook_prints_repr_and_updates_builtins_underscore(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.delattr(builtins, "_", raising=False)

    sys.displayhook({"answer": 42})
    assert output.getvalue() == "{'answer': 42}\n"
    assert builtins._ == {"answer": 42}

    output.seek(0)
    output.truncate()
    sys.displayhook(None)
    assert output.getvalue() == ""


def test_excepthook_formats_an_uncaught_exception_and_original_hooks_remain_available(
    monkeypatch,
):
    output = StringIO()
    monkeypatch.setattr(sys, "stderr", output)
    try:
        raise LookupError("missing item")
    except LookupError as error:
        sys.excepthook(type(error), error, error.__traceback__)

    rendered = output.getvalue()
    assert "Traceback (most recent call last)" in rendered
    assert "LookupError: missing item" in rendered
    assert callable(sys.__displayhook__)
    assert callable(sys.__excepthook__)
    assert callable(sys.__unraisablehook__)
    assert callable(sys.__breakpointhook__)


def test_sys_exit_raises_system_exit_and_normal_finally_cleanup_still_runs():
    events = []
    with pytest.raises(SystemExit) as captured:
        try:
            sys.exit(7)
        finally:
            events.append("cleanup")

    assert captured.value.code == 7
    assert events == ["cleanup"]
    # ``sys.exit`` 只在主线程未被捕获时退出进程，因为它本质是抛出
    # SystemExit。
    assert issubclass(SystemExit, BaseException)
    assert not issubclass(SystemExit, Exception)


def test_recursion_and_thread_switch_settings_are_restored_after_the_example():
    original_recursion = sys.getrecursionlimit()
    original_interval = sys.getswitchinterval()
    try:
        sys.setrecursionlimit(max(original_recursion, 1_500))
        sys.setswitchinterval(0.01)
        assert sys.getrecursionlimit() >= 1_500
        assert sys.getswitchinterval() == pytest.approx(0.01)
        with pytest.raises(ValueError):
            sys.setswitchinterval(0)
    finally:
        sys.setrecursionlimit(original_recursion)
        sys.setswitchinterval(original_interval)


def test_integer_string_digit_limit_is_a_process_setting_added_to_3_10_patches():
    original = sys.get_int_max_str_digits()
    try:
        minimum = sys.int_info.str_digits_check_threshold
        sys.set_int_max_str_digits(minimum)
        assert sys.get_int_max_str_digits() == minimum
        with pytest.raises(ValueError):
            sys.set_int_max_str_digits(minimum - 1)
        sys.set_int_max_str_digits(0)
        assert sys.get_int_max_str_digits() == 0
    finally:
        sys.set_int_max_str_digits(original)


def test_current_frames_exposes_each_thread_without_waiting_or_polling():
    ready = threading.Event()
    release = threading.Event()
    observed = {}

    def worker():
        local_marker = "worker-is-paused"
        ready.set()
        release.wait()
        observed["marker"] = local_marker

    thread = threading.Thread(target=worker, name="polyglot-current-frame")
    thread.start()
    assert ready.wait(timeout=5)
    try:
        frames = sys._current_frames()
        assert threading.get_ident() in frames
        assert thread.ident in frames
        assert frames[thread.ident].f_code.co_name in {"wait", "worker"}
    finally:
        release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert observed == {"marker": "worker-is-paused"}


def test_current_exceptions_reports_the_active_exception_per_thread():
    try:
        raise RuntimeError("currently handled")
    except RuntimeError as error:
        active = sys._current_exceptions()[threading.get_ident()]
        assert active[0] is RuntimeError
        assert active[1] is error
        assert active[2] is error.__traceback__


def test_audit_hooks_are_demonstrated_in_a_child_because_they_cannot_be_removed():
    program = """
import json
import sys

events = []
def hook(name, arguments):
    if name.startswith("polyglot."):
        events.append([name, list(arguments)])
    if name == "polyglot.denied":
        raise PermissionError("rejected by teaching hook")

sys.addaudithook(hook)
sys.audit("polyglot.message", 7, "hello")
try:
    sys.audit("polyglot.denied", "payload")
except PermissionError as error:
    events.append(["caught", str(error)])
print(json.dumps(events))
"""
    events = json.loads(run_python("-c", program).stdout)
    assert events == [
        ["polyglot.message", [7, "hello"]],
        ["polyglot.denied", ["payload"]],
        ["caught", "rejected by teaching hook"],
    ]
    # 审计钩子适合可观测性和受控环境加固，但 Python 级钩子能被恶意代码
    # 绕过。官方明确不把它定义成沙箱；安全边界仍需由进程/容器权限
    # 建立。


def test_sysconfig_exposes_build_variables_without_assuming_platform_values():
    variables = sysconfig.get_config_vars()
    short_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert isinstance(variables, dict)
    assert sysconfig.get_config_var("py_version_short") == short_version
    assert variables["prefix"] == sys.prefix
    assert isinstance(sysconfig.get_platform(), str)
    assert sysconfig.get_python_version() == short_version
    assert isinstance(sysconfig.is_python_build(), bool)
    assert sysconfig.get_config_var("a-key-that-does-not-exist") is None


def test_sysconfig_schemes_expand_named_installation_paths():
    scheme_names = sysconfig.get_scheme_names()
    path_names = sysconfig.get_path_names()
    default_scheme = sysconfig.get_default_scheme()
    paths = sysconfig.get_paths(default_scheme)

    assert default_scheme in scheme_names
    assert {"stdlib", "platstdlib", "purelib", "platlib", "include", "scripts", "data"} <= set(
        path_names
    )
    # get_path_names 是公共核心集合；具体 scheme 可额外暴露平台相关路径。
    assert set(path_names) <= set(paths)
    assert sysconfig.get_path("stdlib", default_scheme) == paths["stdlib"]
    assert all(Path(path).is_absolute() for path in paths.values())


def test_sysconfig_custom_vars_preview_an_install_layout_without_writing_it(tmp_path):
    preview = sysconfig.get_paths(
        "posix_prefix",
        vars={
            "base": str(tmp_path / "base"),
            "platbase": str(tmp_path / "platform"),
            "installed_base": str(tmp_path / "installed"),
            "installed_platbase": str(tmp_path / "installed-platform"),
        },
    )

    assert preview["purelib"].startswith(str(tmp_path / "base"))
    assert preview["platlib"].startswith(str(tmp_path / "platform"))
    assert not (tmp_path / "base").exists()
    assert sysconfig.get_preferred_scheme("prefix") in sysconfig.get_scheme_names()
    assert sysconfig.get_preferred_scheme("user") in sysconfig.get_scheme_names()


def test_sysconfig_module_cli_prints_a_diagnostic_report():
    completed = run_python("-m", "sysconfig")
    assert "Platform:" in completed.stdout
    assert "Python version:" in completed.stdout
    assert "Paths:" in completed.stdout
    assert "Variables:" in completed.stdout


def test_site_reports_global_and_user_installation_locations():
    import site

    assert isinstance(site.getsitepackages(), list)
    assert all(isinstance(path, str) for path in site.getsitepackages())
    assert isinstance(site.getuserbase(), str)
    assert isinstance(site.getusersitepackages(), str)
    assert site.ENABLE_USER_SITE in {True, False, None}


def test_addsitedir_processes_paths_and_executable_pth_lines_in_a_child(tmp_path):
    site_directory = tmp_path / "teaching-site"
    extra_directory = site_directory / "extra-packages"
    extra_directory.mkdir(parents=True)
    (site_directory / "marker.py").write_text("events = []\n", encoding="utf-8")
    (site_directory / "polyglot.pth").write_text(
        "# comments and blank lines are ignored\n"
        "extra-packages\n"
        "missing-directory\n"
        "import marker; marker.events.append('pth code ran')\n",
        encoding="utf-8",
    )
    program = """
import json
import site
import sys

site.addsitedir(sys.argv[1])
import marker
print(json.dumps({"events": marker.events, "paths": sys.path}))
"""
    result = json.loads(run_python("-S", "-c", program, site_directory).stdout)

    assert result["events"] == ["pth code ran"]
    assert str(site_directory) in result["paths"]
    assert str(extra_directory) in result["paths"]
    assert str(site_directory / "missing-directory") not in result["paths"]
    # ``.pth`` 中以 import 开头的单行会在每次解释器启动时执行；它不是
    # 普通配置数据，因此不应放入不受信任的代码，也不应写成长程序。


def test_sitecustomize_is_imported_during_normal_startup_but_not_with_no_site(tmp_path):
    (tmp_path / "sitecustomize.py").write_text(
        "import builtins\nbuiltins.POLYGLOT_SITE_CUSTOMIZED = 'loaded'\n",
        encoding="utf-8",
    )
    environment = child_environment(tmp_path)
    expression = "import builtins; print(getattr(builtins, 'POLYGLOT_SITE_CUSTOMIZED', 'missing'))"

    assert run_python("-c", expression, env=environment).stdout.strip() == "loaded"
    assert run_python("-S", "-c", expression, env=environment).stdout.strip() == "missing"


def test_site_cli_reports_paths_and_uses_status_for_user_site_state():
    import site

    completed = run_python("-m", "site")
    assert "USER_BASE:" in completed.stdout
    assert "USER_SITE:" in completed.stdout
    assert completed.returncode == 0

    expected_status = {True: 0, False: 1, None: 2}[site.ENABLE_USER_SITE]
    user_base = run_python("-m", "site", "--user-base", check=False)
    user_site = run_python("-m", "site", "--user-site", check=False)
    assert user_base.returncode == expected_status
    assert user_site.returncode == expected_status
    assert user_base.stdout.strip() == site.getuserbase()
    assert user_site.stdout.strip() == site.getusersitepackages()


def test_main_metadata_differs_for_command_script_and_dash_m_module(tmp_path):
    probe = (
        "import json, sys; "
        "print(json.dumps({'name': __name__, 'spec': None if __spec__ is None else __spec__.name, "
        "'package': __package__, 'argv0': sys.argv[0]}))"
    )
    command = json.loads(run_python("-c", probe).stdout)
    assert command == {"name": "__main__", "spec": None, "package": None, "argv0": "-c"}

    script_path = tmp_path / "program.py"
    script_path.write_text(probe, encoding="utf-8")
    script = json.loads(run_python(script_path).stdout)
    assert script["name"] == "__main__"
    assert script["spec"] is None
    assert script["package"] is None
    assert Path(script["argv0"]) == script_path

    (tmp_path / "demo_module.py").write_text(probe, encoding="utf-8")
    module = json.loads(
        run_python("-m", "demo_module", cwd=tmp_path, env=child_environment(tmp_path)).stdout
    )
    assert module["name"] == "__main__"
    assert module["spec"] == "demo_module"
    assert module["package"] == ""
    assert Path(module["argv0"]).name == "demo_module.py"


def test_importing_main_reads_the_current_top_level_namespace():
    program = """
import __main__
import json

answer = 42
print(json.dumps({
    "same_globals": __main__.__dict__ is globals(),
    "answer": __main__.answer,
    "name": __main__.__name__,
}))
"""
    result = json.loads(run_python("-c", program).stdout)
    assert result == {"same_globals": True, "answer": 42, "name": "__main__"}


def test_name_guard_keeps_cli_side_effects_out_of_normal_import(tmp_path):
    module_path = tmp_path / "guarded.py"
    module_path.write_text(
        "events = ['module body']\n"
        "def main():\n"
        "    events.append('main called')\n"
        "    print('|'.join(events))\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )
    environment = child_environment(tmp_path)

    imported = run_python(
        "-c",
        "import guarded; print('|'.join(guarded.events))",
        env=environment,
    )
    executed = run_python("-m", "guarded", cwd=tmp_path, env=environment)
    assert imported.stdout.strip() == "module body"
    assert executed.stdout.strip() == "module body|main called"
