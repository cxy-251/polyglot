"""147｜pydoc、Development Mode、lib2to3 与 CPython 测试辅助工作流。

本套合并 Development Tools 类别中规模较小的工具：从对象生成文档、用
开发模式启动诊断更严格的子解释器、把 Python 2 语法迁移为 Python 3，
以及理解 CPython 自身测试辅助包的适用边界。案例不启动 pydoc HTTP 服务，
也不扫描全机模块。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.pydoc python.pydoc.describe
# polyglot-covers: python.pydoc.locate python.pydoc.resolve
# polyglot-covers: python.pydoc.getdoc python.pydoc.classify-class-attrs
# polyglot-covers: python.pydoc.safeimport python.pydoc.error-during-import
# polyglot-covers: python.pydoc.render-doc python.pydoc.plaintext-renderer
# polyglot-covers: python.pydoc.helper python.pydoc.html-document
# polyglot-covers: python.pydoc.writedoc python.pydoc.module-documentation-workflow
# polyglot-covers: python.pydoc.cli-text-output python.pydoc.no-web-server-in-tests
# polyglot-covers: python.stdlib.development-mode python.devmode.x-dev
# polyglot-covers: python.devmode.python-dev-mode-environment
# polyglot-covers: python.devmode.sys-flags python.devmode.sys-xoptions
# polyglot-covers: python.devmode.faulthandler python.devmode.asyncio-debug
# polyglot-covers: python.devmode.warning-defaults python.devmode.explicit-overrides
# polyglot-covers: python.stdlib.2to3 python.stdlib.lib2to3
# polyglot-covers: python.lib2to3.get-fixers python.lib2to3.refactoring-tool
# polyglot-covers: python.lib2to3.refactor-string python.lib2to3.refactor-docstring
# polyglot-covers: python.lib2to3.parse-error python.lib2to3.trailing-newline
# polyglot-covers: python.lib2to3.pytree-node-leaf-clone
# polyglot-covers: python.lib2to3.cli-diff-and-write
# polyglot-covers: python.lib2to3.mechanical-migration-review-boundary
# polyglot-covers: python.stdlib.test python.test-support.cpython-internal-boundary
# polyglot-covers: python.test-support.captured-streams
# polyglot-covers: python.test-support.swap-attr-and-item
# polyglot-covers: python.test-support.environment-var-guard
# polyglot-covers: python.test-support.os-helper-temp-dir
# polyglot-covers: python.test-support.resource-gating
# polyglot-covers: python.test-support.script-helper-child-interpreter

import json
import os
from pathlib import Path
import pydoc
import subprocess
import sys
import types

import pytest


class DocumentedWidget:
    """A small documented widget.

    Args:
        name: Human-readable widget name.
    """

    category = "demo"

    def __init__(self, name):
        self.name = name

    @property
    def label(self):
        """Return the display label."""

        return f"widget:{self.name}"

    def render(self, prefix=""):
        """Render this widget with an optional prefix."""

        return prefix + self.label


def child_environment(**updates):
    """清除会污染启动选项的环境变量，再按案例显式补入。"""

    environment = os.environ.copy()
    for name in [
        "PYTHONDEVMODE",
        "PYTHONWARNINGS",
        "PYTHONASYNCIODEBUG",
        "PYTHONMALLOC",
        "PYTHONFAULTHANDLER",
    ]:
        environment.pop(name, None)
    environment.update(updates)
    return environment


def run_python(*arguments, environment=None, check=True):
    return subprocess.run(
        [sys.executable, *arguments],
        check=check,
        capture_output=True,
        text=True,
        env=environment or child_environment(),
    )


def test_pydoc_describe_locate_resolve_and_getdoc():
    assert pydoc.describe(DocumentedWidget) == "class DocumentedWidget"
    assert pydoc.locate("collections.Counter").__name__ == "Counter"
    assert pydoc.locate("str.removeprefix") is str.removeprefix
    assert pydoc.locate("polyglot.name.that.does.not.exist") is None

    resolved, name = pydoc.resolve(DocumentedWidget)
    assert resolved is DocumentedWidget
    assert name == "DocumentedWidget"

    doc = pydoc.getdoc(DocumentedWidget.render)
    assert doc == "Render this widget with an optional prefix."
    assert pydoc.describe(DocumentedWidget("alpha")) == "DocumentedWidget"


def test_classify_class_attrs_reports_where_and_how_attributes_are_defined():
    attributes = {item[0]: item for item in pydoc.classify_class_attrs(DocumentedWidget)}

    assert attributes["category"][1] == "data"
    assert attributes["category"][2] is DocumentedWidget
    assert attributes["label"][1] == "readonly property"
    assert attributes["label"][3] is DocumentedWidget.__dict__["label"]
    assert attributes["render"][1] == "method"

    # classify_class_attrs 也包含继承属性；defining_class 可用来区分本类 API 和
    # object 提供的基础协议。
    assert attributes["__repr__"][2] is object


def test_safeimport_distinguishes_missing_modules_from_import_time_failures(
    tmp_path,
    monkeypatch,
):
    monkeypatch.syspath_prepend(str(tmp_path))
    good_name = "polyglot_pydoc_good_module"
    bad_name = "polyglot_pydoc_bad_module"
    (tmp_path / f"{good_name}.py").write_text("VALUE = 7\n", encoding="utf-8")
    (tmp_path / f"{bad_name}.py").write_text(
        "raise RuntimeError('broken at import time')\n",
        encoding="utf-8",
    )

    assert pydoc.safeimport(good_name).VALUE == 7
    assert pydoc.safeimport("polyglot_pydoc_missing_module") is None

    with pytest.raises(pydoc.ErrorDuringImport) as captured:
        pydoc.safeimport(bad_name)
    assert captured.value.exc is RuntimeError
    assert isinstance(captured.value.value, RuntimeError)
    assert captured.value.tb is not None
    assert "broken at import time" in str(captured.value)

    # safeimport 会实际执行模块顶层代码，
    # 绝不是读取不可信模块文档的 sandbox。
    sys.modules.pop(good_name, None)
    sys.modules.pop(bad_name, None)


def test_render_doc_and_helper_produce_searchable_plain_text():
    rendered = pydoc.render_doc(DocumentedWidget, renderer=pydoc.plaintext)

    assert rendered.startswith("Python Library Documentation: class DocumentedWidget")
    assert "A small documented widget." in rendered
    assert "render(self, prefix='')" in rendered
    assert "label" in rendered

    # Helper 默认写 stdout；这里直接验证其可替换输出流，
    # 避免调用交互 pager。
    from io import StringIO

    stream = StringIO()
    output = pydoc.Helper(output=stream)
    output(DocumentedWidget.render)
    assert "Help on function render" in stream.getvalue()
    assert "Render this widget" in stream.getvalue()


def test_html_document_and_writedoc_create_local_static_documentation(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = types.ModuleType("polyglot_documented_module")
    module.__doc__ = "A generated module for pydoc."
    module.__file__ = str(tmp_path / "polyglot_documented_module.py")
    module.__all__ = ["greet"]
    exec(
        '''
def greet(name):
    """Return a greeting."""
    return f"hello {name}"
''',
        module.__dict__,
    )

    html = pydoc.HTMLDoc().document(module, module.__name__)
    # HTMLDoc 会把文档字符串中的普通空格转成不换行实体，不能用纯文本子串比较 HTML。
    assert "A&nbsp;generated&nbsp;module&nbsp;for&nbsp;pydoc." in html
    assert "greet" in html

    monkeypatch.chdir(tmp_path)
    pydoc.writedoc(module)
    generated = tmp_path / "polyglot_documented_module.html"
    assert generated.exists()
    generated_html = generated.read_text(encoding="utf-8")
    assert "Return&nbsp;a&nbsp;greeting." in generated_html
    assert "wrote polyglot_documented_module.html" in capsys.readouterr().out


def test_pydoc_command_line_renders_text_without_starting_a_server():
    completed = run_python("-m", "pydoc", "collections.Counter")

    assert completed.returncode == 0
    assert "class Counter" in completed.stdout
    assert "Dict subclass for counting hashable items" in completed.stdout
    assert completed.stderr == ""

    # ``pydoc -b`` 会绑定本地端口并打开浏览器，``-k`` 会导入/扫描大量模块；
    # 它们不适合作为确定性测试案例，因此这里只覆盖一次性文本输出
    # 工作流。


def test_x_dev_exposes_flags_faulthandler_and_asyncio_debug_state():
    program = (
        "import asyncio, faulthandler, json, sys; "
        "loop = asyncio.new_event_loop(); "
        "print(json.dumps({"
        "'flag': sys.flags.dev_mode, "
        "'xoption': sys._xoptions.get('dev'), "
        "'faulthandler': faulthandler.is_enabled(), "
        "'asyncio_debug': loop.get_debug()})); "
        "loop.close()"
    )
    completed = run_python("-X", "dev", "-c", program)
    state = json.loads(completed.stdout)

    assert state == {
        "flag": True,
        "xoption": True,
        "faulthandler": True,
        "asyncio_debug": True,
    }


def test_python_dev_mode_environment_variable_enables_the_same_startup_bundle():
    completed = run_python(
        "-c",
        "import json, sys; print(json.dumps([sys.flags.dev_mode, sys._xoptions]))",
        environment=child_environment(PYTHONDEVMODE="1"),
    )
    flag, options = json.loads(completed.stdout)

    assert flag is True
    # 环境变量启用同一启动 bundle，但 sys._xoptions 只记录真正的 -X 命令行选项。
    assert "dev" not in options


def test_development_mode_changes_warning_defaults_but_explicit_flags_can_override():
    program = "import warnings; warnings.warn('resource leaked', ResourceWarning)"

    normal = run_python("-c", program)
    development = run_python("-X", "dev", "-c", program)
    suppressed = run_python(
        "-X",
        "dev",
        "-W",
        "ignore::ResourceWarning",
        "-c",
        program,
    )

    assert normal.stderr == ""
    assert "ResourceWarning: resource leaked" in development.stderr
    assert suppressed.stderr == ""

    # Development Mode 是一组便于开发的启动默认值，
    # 不是“更严格语言模式”。
    # 显式 -W、PYTHONMALLOC 等选项仍可覆盖相关设置，具体 bundle
    # 也可能随版本演进。


def test_lib2to3_fixer_catalog_and_refactor_string_workflow():
    pytest.importorskip("lib2to3")
    from lib2to3.refactor import RefactoringTool
    from lib2to3.refactor import get_fixers_from_package

    fixers = get_fixers_from_package("lib2to3.fixes")
    assert "lib2to3.fixes.fix_print" in fixers
    assert "lib2to3.fixes.fix_xrange" in fixers
    assert "lib2to3.fixes.fix_except" in fixers

    tool = RefactoringTool(fixers)
    source = (
        "print 'hello'\n"
        "for index in xrange(3):\n"
        "    print index\n"
        "try:\n"
        "    raise ValueError('bad')\n"
        "except ValueError, error:\n"
        "    print error\n"
    )
    migrated = str(tool.refactor_string(source, "legacy.py"))

    assert "print('hello')" in migrated
    assert "for index in range(3):" in migrated
    assert "except ValueError as error:" in migrated
    assert "print(error)" in migrated


def test_lib2to3_refactors_prompts_inside_docstrings():
    from lib2to3.refactor import RefactoringTool
    from lib2to3.refactor import get_fixers_from_package

    tool = RefactoringTool(get_fixers_from_package("lib2to3.fixes"))
    lesson = (
        "Example::\n\n"
        "    >>> print 'hello'\n"
        "    hello\n"
        "    >>> list(xrange(2))\n"
        "    [0, 1]\n"
    )
    migrated = tool.refactor_docstring(lesson, "guide.rst")

    assert ">>> print('hello')" in migrated
    assert ">>> list(range(2))" in migrated
    assert "    hello" in migrated


def test_lib2to3_parser_requires_complete_input_and_exposes_a_pytree():
    from lib2to3 import pygram
    from lib2to3 import pytree
    from lib2to3.pgen2 import driver
    from lib2to3.pgen2.parse import ParseError
    from lib2to3.refactor import RefactoringTool

    tool = RefactoringTool([])
    with pytest.raises(ParseError):
        tool.refactor_string("value = 1", "missing-newline.py")

    grammar_driver = driver.Driver(pygram.python_grammar, convert=pytree.convert)
    tree = grammar_driver.parse_string("value = 1\n")
    assert isinstance(tree, pytree.Node)
    assert [leaf.value for leaf in tree.leaves()] == ["value", "=", "1", "\n", ""]

    cloned = tree.clone()
    assert cloned is not tree
    assert str(cloned) == str(tree)
    assert all(left is not right for left, right in zip(tree.leaves(), cloned.leaves()))


def test_2to3_cli_shows_diff_by_default_and_only_writes_with_w_flag(tmp_path):
    source = tmp_path / "legacy.py"
    source.write_text("print 'hello'\n", encoding="utf-8")

    preview = run_python("-m", "lib2to3", "-f", "print", str(source))
    assert preview.returncode == 0
    assert "-print 'hello'" in preview.stdout
    assert "+print('hello')" in preview.stdout
    assert source.read_text(encoding="utf-8") == "print 'hello'\n"

    written = run_python(
        "-m",
        "lib2to3",
        "-w",
        "-n",
        "-f",
        "print",
        str(source),
    )
    assert written.returncode == 0
    assert source.read_text(encoding="utf-8") == "print('hello')\n"
    assert not Path(f"{source}.bak").exists()

    # 2to3 是语法树驱动的机械迁移器，不理解业务语义，
    # 也不把代码升级成所有现代最佳实践。真实迁移仍要审阅 diff，
    # 并运行目标项目自己的测试。


def test_cpython_test_support_stream_swap_environment_and_temp_helpers(
    tmp_path,
    monkeypatch,
):
    support = pytest.importorskip("test.support")
    os_helper = pytest.importorskip("test.support.os_helper")

    with support.captured_stdout() as stdout:
        print("captured output")
    with support.captured_stderr() as stderr:
        print("captured error", file=sys.stderr)
    assert stdout.getvalue() == "captured output\n"
    assert stderr.getvalue() == "captured error\n"

    target = types.SimpleNamespace(state="old")
    mapping = {"mode": "prod"}
    with support.swap_attr(target, "state", "new"):
        assert target.state == "new"
    with support.swap_item(mapping, "mode", "test"):
        assert mapping["mode"] == "test"
    assert target.state == "old"
    assert mapping == {"mode": "prod"}

    variable = "POLYGLOT_SUPPORT_ENV"
    monkeypatch.setenv(variable, "outside")
    with os_helper.EnvironmentVarGuard() as environment:
        environment.set(variable, "inside")
        environment.set("POLYGLOT_SUPPORT_TEMP", "temporary")
        assert os.environ[variable] == "inside"
    assert os.environ[variable] == "outside"
    assert "POLYGLOT_SUPPORT_TEMP" not in os.environ

    directory = tmp_path / "support-temp-dir"
    with os_helper.temp_dir(path=str(directory)) as created:
        assert Path(created) == directory
        (directory / "record.txt").write_text("data", encoding="utf-8")
    assert not directory.exists()


def test_cpython_test_support_resource_gate_and_script_helper(monkeypatch):
    support = pytest.importorskip("test.support")
    script_helper = pytest.importorskip("test.support.script_helper")

    monkeypatch.setattr(support, "use_resources", [])
    assert support.is_resource_enabled("network") is False
    with pytest.raises(support.ResourceDenied):
        support.requires("network", "network intentionally disabled")

    return_code, stdout, stderr = script_helper.assert_python_ok(
        "-c",
        "print('child-ok')",
        __isolated=False,
    )
    assert return_code == 0
    assert stdout == b"child-ok\n"
    assert stderr == b""

    # test.support 是 CPython 回归测试的内部工具箱，
    # 不承诺像普通标准库 API 那样稳定，
    # 某些精简发行版还会完全不安装 test 包。
    # 应用测试应首选 pytest/unittest；这里只用 importorskip
    # 明确记录实现和安装边界。
