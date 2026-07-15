"""152｜ensurepip、venv 与 zipapp：隔离环境和可执行归档工作流。

三个模块共同回答“如何带着解释器能力交付程序”：``ensurepip`` 从捆绑
wheel 引导 pip，``venv`` 创建可重建的隔离前缀，``zipapp`` 把纯 Python
应用封装为单文件归档。所有环境和归档均位于 ``tmp_path``，
不联网、不升级 PyPI 依赖。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.ensurepip python.ensurepip.version
# polyglot-covers: python.ensurepip.cli-version python.ensurepip.offline-bundled-wheels
# polyglot-covers: python.ensurepip.bootstrap python.ensurepip.upgrade
# polyglot-covers: python.ensurepip.default-pip python.ensurepip.altinstall-conflict
# polyglot-covers: python.ensurepip.subprocess-side-effect-isolation
# polyglot-covers: python.stdlib.venv python.venv.env-builder
# polyglot-covers: python.venv.create-hooks python.venv.ensure-directories-context
# polyglot-covers: python.venv.create-configuration python.venv.setup-python
# polyglot-covers: python.venv.setup-scripts python.venv.post-setup
# polyglot-covers: python.venv.system-site-packages python.venv.prompt
# polyglot-covers: python.venv.pyvenv-cfg python.venv.prefix-base-prefix
# polyglot-covers: python.venv.activation-not-required
# polyglot-covers: python.venv.virtual-env-variable-not-authoritative
# polyglot-covers: python.venv.clear-existing-environment
# polyglot-covers: python.venv.install-scripts-placeholders
# polyglot-covers: python.venv.cli-multiple-environments
# polyglot-covers: python.venv.without-pip python.venv.non-portable-absolute-paths
# polyglot-covers: python.venv.upgrade-deps-network-boundary
# polyglot-covers: python.stdlib.zipapp python.zipapp.create-archive
# polyglot-covers: python.zipapp.directory-source python.zipapp.pathlike-target
# polyglot-covers: python.zipapp.main-existing python.zipapp.main-generated
# polyglot-covers: python.zipapp.interpreter python.zipapp.get-interpreter
# polyglot-covers: python.zipapp.executable-bit python.zipapp.compressed
# polyglot-covers: python.zipapp.filter-relative-path
# polyglot-covers: python.zipapp.file-object-source-target-ownership
# polyglot-covers: python.zipapp.copy-archive-replace-shebang
# polyglot-covers: python.zipapp.default-target python.zipapp.cli-info
# polyglot-covers: python.zipapp.entry-point-validation
# polyglot-covers: python.zipapp.runtime-dependency-boundary

from io import BytesIO
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import venv
import zipapp
import zipfile

import pytest

try:
    import ensurepip
except ModuleNotFoundError:
    # CPython 可以用 --without-ensurepip 构建；这不应阻止同文件的 venv/zipapp
    # 案例被收集和验证。
    ensurepip = None


requires_ensurepip = pytest.mark.skipif(
    ensurepip is None,
    reason="当前 CPython 构建未捆绑 ensurepip",
)


class RecordingEnvBuilder(venv.EnvBuilder):
    """调用真实 hooks，同时记录 EnvBuilder.create 的固定编排顺序。"""

    def __init__(self, **options):
        super().__init__(**options)
        self.events = []
        self.context = None

    def ensure_directories(self, env_dir):
        self.events.append("ensure_directories")
        return super().ensure_directories(env_dir)

    def create_configuration(self, context):
        self.events.append("create_configuration")
        return super().create_configuration(context)

    def setup_python(self, context):
        self.events.append("setup_python")
        return super().setup_python(context)

    def setup_scripts(self, context):
        self.events.append("setup_scripts")
        return super().setup_scripts(context)

    def post_setup(self, context):
        self.events.append("post_setup")
        self.context = context


def clean_child_environment(**updates):
    environment = os.environ.copy()
    for name in [
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "PIP_CONFIG_FILE",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
    ]:
        environment.pop(name, None)
    environment.update(updates)
    return environment


def run_command(arguments, **options):
    return subprocess.run(
        [str(argument) for argument in arguments],
        check=options.pop("check", True),
        capture_output=True,
        text=True,
        **options,
    )


def make_zipapp_source(root, *, with_main=True):
    source = root / "application"
    source.mkdir(parents=True)
    (source / "message.py").write_text(
        "def greeting(name):\n    return f'hello {name}'\n",
        encoding="utf-8",
    )
    if with_main:
        (source / "__main__.py").write_text(
            "import sys\nfrom message import greeting\nprint(greeting(sys.argv[1]))\n",
            encoding="utf-8",
        )
    return source


@requires_ensurepip
def test_ensurepip_reports_the_bundled_version_without_installing_anything():
    bundled = ensurepip.version()
    completed = run_command(
        [sys.executable, "-m", "ensurepip", "--version"],
        env=clean_child_environment(),
    )

    assert bundled
    assert all(part.isdigit() for part in bundled.split("."))
    assert completed.stdout.strip() == f"pip {bundled}"
    assert completed.stderr == ""


@requires_ensurepip
def test_ensurepip_rejects_conflicting_script_selection_before_bootstrap():
    with pytest.raises(ValueError, match="altinstall and default_pip"):
        ensurepip.bootstrap(altinstall=True, default_pip=True)


@requires_ensurepip
def test_ensurepip_bootstraps_pip_inside_a_temporary_venv_without_network(tmp_path):
    environment = tmp_path / "pip-environment"
    builder = RecordingEnvBuilder(with_pip=False)
    builder.create(str(environment))
    python = builder.context.env_exec_cmd

    missing = run_command(
        [python, "-m", "pip", "--version"],
        check=False,
        env=clean_child_environment(),
    )
    assert missing.returncode != 0
    assert "No module named pip" in missing.stderr

    bootstrapped = run_command(
        [python, "-m", "ensurepip", "--upgrade", "--default-pip"],
        env=clean_child_environment(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX="1"),
    )
    assert bootstrapped.returncode == 0

    installed = run_command(
        [python, "-m", "pip", "--version"],
        env=clean_child_environment(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX="1"),
    )
    assert "pip " in installed.stdout
    assert str(environment) in installed.stdout

    script_directory = Path(builder.context.bin_path)
    assert (script_directory / "pip").exists()
    assert (script_directory / f"pip{sys.version_info.major}").exists()
    assert (
        script_directory
        / f"pip{sys.version_info.major}.{sys.version_info.minor}"
    ).exists()

    # ensurepip 会临时改 sys.path/os.environ，故真实引导放在 venv 子进程中；
    # 它只读取随 CPython 捆绑的 wheel，不需要也不会访问 package index。


def test_envbuilder_create_runs_hooks_and_produces_an_isolated_prefix(tmp_path):
    environment = tmp_path / "teaching-env"
    builder = RecordingEnvBuilder(
        system_site_packages=True,
        with_pip=False,
        prompt="Teaching",
        symlinks=False,
    )
    builder.create(str(environment))
    context = builder.context

    assert builder.events == [
        "ensure_directories",
        "create_configuration",
        "setup_python",
        "setup_scripts",
        "post_setup",
    ]
    assert Path(context.env_dir) == environment
    assert context.env_name == "teaching-env"
    assert Path(context.bin_path).is_dir()
    assert Path(context.inc_path).is_dir()
    assert Path(context.env_exe).exists()
    assert Path(context.executable).resolve() == Path(sys._base_executable).resolve()

    configuration = (environment / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "include-system-site-packages = true" in configuration
    assert "prompt = 'Teaching'" in configuration

    program = (
        "import json, os, sys; "
        "print(json.dumps({"
        "'prefix': sys.prefix, 'base_prefix': sys.base_prefix, "
        "'exec_prefix': sys.exec_prefix, "
        "'base_exec_prefix': sys.base_exec_prefix, "
        "'virtual_env': os.environ.get('VIRTUAL_ENV')}))"
    )
    completed = run_command(
        [context.env_exec_cmd, "-c", program],
        env=clean_child_environment(),
    )
    state = json.loads(completed.stdout)
    assert Path(state["prefix"]) == environment
    assert Path(state["exec_prefix"]) == environment
    assert state["prefix"] != state["base_prefix"]
    assert state["exec_prefix"] != state["base_exec_prefix"]
    assert state["virtual_env"] is None

    # 激活只修改当前 shell 的 PATH/VIRTUAL_ENV；直接调用 env_exec_cmd 一样进入
    # venv，所以判断环境应比较 prefix/base_prefix，不能依赖 VIRTUAL_ENV。


def test_envbuilder_clear_removes_existing_contents_before_recreation(tmp_path):
    environment = tmp_path / "recreated-env"
    venv.create(str(environment), with_pip=False)
    marker = environment / "stale.txt"
    marker.write_text("old", encoding="utf-8")

    venv.EnvBuilder(clear=True, with_pip=False).create(str(environment))

    assert not marker.exists()
    assert (environment / "pyvenv.cfg").exists()
    binary_directory = "Scripts" if os.name == "nt" else "bin"
    assert (environment / binary_directory).is_dir()


def test_install_scripts_expands_context_placeholders(tmp_path):
    environment = tmp_path / "script-env"
    builder = RecordingEnvBuilder(with_pip=False, prompt="Custom")
    builder.create(str(environment))
    templates = tmp_path / "templates"
    common = templates / "common"
    common.mkdir(parents=True)
    template = common / "show-context"
    template.write_text(
        """#!__VENV_PYTHON__
ENV=__VENV_DIR__
NAME=__VENV_NAME__
BIN=__VENV_BIN_NAME__
PROMPT=__VENV_PROMPT__
""",
        encoding="utf-8",
    )
    template.chmod(0o755)

    builder.install_scripts(builder.context, str(templates))
    installed = Path(builder.context.bin_path) / "show-context"
    text = installed.read_text(encoding="utf-8")

    assert text.startswith(f"#!{builder.context.env_exe}\n")
    assert f"ENV={environment}" in text
    assert "NAME=script-env" in text
    assert f"BIN={builder.context.bin_name}" in text
    assert "Custom" in text
    assert "__VENV_" not in text

    # 生成脚本含 env_exe 的绝对路径，这使 venv 默认不可搬迁；
    # 移动目录后应重建。


def test_venv_cli_creates_multiple_without_pip_and_never_upgrades_online(tmp_path):
    first = tmp_path / "cli-one"
    second = tmp_path / "cli-two"
    completed = run_command(
        [
            sys.executable,
            "-m",
            "venv",
            "--without-pip",
            "--copies",
            "--prompt",
            "CLI",
            first,
            second,
        ],
        env=clean_child_environment(),
    )

    assert completed.returncode == 0
    for environment in [first, second]:
        configuration = (environment / "pyvenv.cfg").read_text(encoding="utf-8")
        assert "include-system-site-packages = false" in configuration
        executable = "python.exe" if os.name == "nt" else "python"
        binary = environment / ("Scripts" if os.name == "nt" else "bin") / executable
        assert binary.exists()
        pip_check = run_command(
            [binary, "-m", "pip", "--version"],
            check=False,
            env=clean_child_environment(),
        )
        assert pip_check.returncode != 0

    # --upgrade-deps 会调用 venv 内的 pip 访问 PyPI，本仓库永不在示例中启用它。


def test_zipapp_packages_existing_main_filters_files_and_runs(tmp_path):
    source = make_zipapp_source(tmp_path)
    (source / "private.secret").write_text("do not ship", encoding="utf-8")
    target = tmp_path / "application.pyz"
    visited = []

    def include(path):
        visited.append(path)
        return path.suffix != ".secret"

    zipapp.create_archive(
        source,
        target,
        interpreter="/usr/bin/env python3",
        filter=include,
        compressed=True,
    )

    assert all(isinstance(path, Path) and not path.is_absolute() for path in visited)
    assert zipapp.get_interpreter(target) == "/usr/bin/env python3"
    assert target.read_bytes().startswith(b"#!/usr/bin/env python3\n")
    if os.name == "posix":
        assert target.stat().st_mode & stat.S_IXUSR

    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) == {"__main__.py", "message.py"}
        assert all(
            item.compress_type == zipfile.ZIP_DEFLATED
            for item in archive.infolist()
        )

    completed = run_command(
        [sys.executable, target, "Ada"],
        env=clean_child_environment(),
    )
    assert completed.stdout == "hello Ada\n"


def test_zipapp_generates_main_that_imports_and_calls_an_entry_point(tmp_path):
    source = make_zipapp_source(tmp_path, with_main=False)
    package = source / "application"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text(
        "def main():\n    print('generated entry point')\n",
        encoding="utf-8",
    )
    target = tmp_path / "generated.pyz"

    zipapp.create_archive(source, target, main="application.cli:main")

    with zipfile.ZipFile(target) as archive:
        generated = archive.read("__main__.py").decode("utf-8")
    assert "import application.cli" in generated
    assert "application.cli.main()" in generated

    completed = run_command(
        [sys.executable, target],
        env=clean_child_environment(),
    )
    assert completed.stdout == "generated entry point\n"


def test_zipapp_file_objects_are_not_closed_by_create_or_inspect(tmp_path):
    source = make_zipapp_source(tmp_path)
    target = BytesIO()

    zipapp.create_archive(source, target)
    assert target.closed is False
    data = target.getvalue()
    assert data.startswith(b"PK")

    readable = BytesIO(data)
    assert zipapp.get_interpreter(readable) is None
    assert readable.closed is False

    copied = BytesIO()
    readable.seek(0)
    zipapp.create_archive(readable, copied, interpreter="python3")
    assert readable.closed is False
    assert copied.closed is False
    copied.seek(0)
    assert zipapp.get_interpreter(copied) == "python3"


def test_copying_an_archive_replaces_only_shebang_and_preserves_members(tmp_path):
    source = make_zipapp_source(tmp_path)
    original = tmp_path / "original.pyz"
    rewritten = tmp_path / "rewritten.pyz"
    zipapp.create_archive(source, original, interpreter="python3")

    zipapp.create_archive(
        original,
        rewritten,
        interpreter="/usr/bin/env python3",
        compressed=True,
    )

    assert zipapp.get_interpreter(original) == "python3"
    assert zipapp.get_interpreter(rewritten) == "/usr/bin/env python3"
    with zipfile.ZipFile(original) as first, zipfile.ZipFile(rewritten) as second:
        assert first.namelist() == second.namelist()
        assert {
            name: first.read(name) for name in first.namelist()
        } == {name: second.read(name) for name in second.namelist()}


def test_zipapp_default_target_and_cli_info_workflow(tmp_path):
    source = make_zipapp_source(tmp_path)
    zipapp.create_archive(source, interpreter="python3")
    default_target = source.with_suffix(".pyz")

    assert default_target.exists()
    completed = run_command(
        [sys.executable, "-m", "zipapp", "--info", default_target],
        env=clean_child_environment(),
    )
    assert completed.stdout.strip() == "Interpreter: python3"


def test_zipapp_rejects_missing_conflicting_and_malformed_entry_points(tmp_path):
    missing = make_zipapp_source(tmp_path / "missing", with_main=False)
    with pytest.raises(zipapp.ZipAppError, match="no entry point"):
        zipapp.create_archive(missing, tmp_path / "missing.pyz")

    malformed_root = tmp_path / "malformed"
    malformed = make_zipapp_source(malformed_root, with_main=False)
    with pytest.raises(zipapp.ZipAppError, match="Invalid entry point"):
        zipapp.create_archive(
            malformed,
            tmp_path / "malformed.pyz",
            main="not-a-module-callable",
        )

    existing_root = tmp_path / "existing"
    existing = make_zipapp_source(existing_root, with_main=True)
    with pytest.raises(zipapp.ZipAppError, match="Cannot specify entry point"):
        zipapp.create_archive(
            existing,
            tmp_path / "conflict.pyz",
            main="message:greeting",
        )

    # zipapp 只捆绑归档内文件，不捆绑解释器；native extensions 还必须匹配目标
    # 平台/ABI。需要真正独立可执行文件时应选择其他打包方案。
