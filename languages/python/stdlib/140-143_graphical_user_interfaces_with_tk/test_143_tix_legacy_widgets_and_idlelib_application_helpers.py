"""143｜Tk GUI 边界：已弃用的 Tix 扩展与 IDLE 应用辅助逻辑。

``tkinter.tix`` 依赖单独安装的 Tix 且自 3.6 起弃用，新代码应优先使用 ttk；
相关案例只在容器确实拥有 Tix 与显示服务器时运行。
IDLE 文档描述一个应用，
而非稳定库 API。本文件仅展示 ``idlelib`` 中可独立复用的配置和段落格式化
逻辑，不把私有编辑器内部穷举成公共接口。

案例面向 Python 3.10。
"""

# polyglot-covers: python.stdlib.tkinter.tix python.tix-deprecated-boundary
# polyglot-covers: python.tix-extra-package-and-display-requirement
# polyglot-covers: python.tix.ButtonBox python.tix.ComboBox
# polyglot-covers: python.tix.NoteBook python.tix.PanedWindow
# polyglot-covers: python.tix.HList python.tix.Select
# polyglot-covers: python.stdlib.IDLE python.idlelib-application-boundary
# polyglot-covers: python.idlelib.format-reformat-paragraph
# polyglot-covers: python.idlelib.format-comment-and-indent-helpers
# polyglot-covers: python.idlelib.config.IdleConfParser

import importlib
import warnings

import pytest


tkinter = pytest.importorskip("tkinter")
idle_config = pytest.importorskip("idlelib.config")
idle_format = pytest.importorskip("idlelib.format")


@pytest.fixture
def tix_module():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return pytest.importorskip("tkinter.tix")


@pytest.fixture
def tix_root(tix_module):
    try:
        root = tix_module.Tk()
        root.tk.call("package", "require", "Tix")
    except tkinter.TclError as error:
        pytest.skip(f"当前容器没有可用的 Tix/显示服务器: {error}")
    root.withdraw()
    try:
        yield root
    finally:
        if root.winfo_exists():
            root.destroy()


def test_tix_import_emits_real_deprecation_warning_for_new_code(tix_module):
    # fixture 已先导入模块；reload 让模块自己的弃用分支再次执行。
    with pytest.warns(DeprecationWarning, match="unmaintained"):
        reloaded = importlib.reload(tix_module)

    assert reloaded.__name__ == "tkinter.tix"


def test_tix_buttonbox_and_combobox_manage_named_subwidgets(
    tix_module,
    tix_root,
):
    calls = []
    buttons = tix_module.ButtonBox(tix_root, orientation="horizontal")
    ok = buttons.add("ok", text="OK", command=lambda: calls.append("ok"))
    buttons.add("cancel", text="Cancel")

    assert ok is buttons.subwidget("ok")
    assert set(buttons.subwidgets_all()) >= {
        buttons.subwidget("ok"),
        buttons.subwidget("cancel"),
    }
    buttons.invoke("ok")
    assert calls == ["ok"]

    combo = tix_module.ComboBox(tix_root, editable=True)
    combo.insert("end", "alpha")
    combo.insert("end", "beta")
    combo.pick(1)
    assert combo["value"] == "beta"


def test_tix_notebook_and_panedwindow_return_page_and_pane_widgets(
    tix_module,
    tix_root,
):
    notebook = tix_module.NoteBook(tix_root)
    first_page = notebook.add("first", label="First")
    second_page = notebook.add("second", label="Second")

    assert notebook.pages() == ("first", "second")
    assert str(notebook.page("first")) == str(first_page)
    assert str(notebook.page("second")) == str(second_page)
    notebook.raise_page("second")
    assert notebook.raised() == "second"

    panes = tix_module.PanedWindow(tix_root, orientation="horizontal")
    left = panes.add("left", size=100)
    right = panes.add("right", size=200)
    assert panes.panes() == ("left", "right")
    assert str(panes.subwidget("left")) == str(left)
    assert str(panes.subwidget("right")) == str(right)
    panes.delete("left")
    assert panes.panes() == ("right",)


def test_tix_hlist_and_select_cover_hierarchy_and_named_choice(
    tix_module,
    tix_root,
):
    hierarchy = tix_module.HList(tix_root, separator=".")
    hierarchy.add("language", text="Language")
    hierarchy.add("language.python", text="Python")
    assert hierarchy.info_children("language") == ("language.python",)
    assert hierarchy.info_parent("language.python") == "language"
    hierarchy.delete_entry("language.python")
    assert not hierarchy.info_exists("language.python")

    selected = []
    choices = tix_module.Select(
        tix_root,
        allowzero=False,
        radio=True,
        command=lambda value: selected.append(value),
    )
    choices.add("basic", text="Basic")
    choices.add("advanced", text="Advanced")
    choices.invoke("advanced")
    assert selected[-1] == "advanced"


def test_idle_reformat_paragraph_preserves_words_and_respects_limit():
    source = (
        "Python protocols make implicit operations explicit when examples "
        "show both syntax and the corresponding special methods."
    )

    formatted = idle_format.reformat_paragraph(source, limit=40)

    assert formatted.replace("\n", " ") == source
    assert all(len(line) <= 40 for line in formatted.splitlines())


def test_idle_reformat_comment_preserves_comment_header_on_every_line():
    source = (
        "    ## A long teaching comment explains protocol dispatch and "
        "fallback behavior without narrating every statement."
    )

    formatted = idle_format.reformat_comment(
        source,
        limit=50,
        comment_header="    ##",
    )

    lines = formatted.splitlines()
    assert lines
    assert all(line.startswith("    ##") for line in lines)
    assert all(len(line) <= 50 for line in lines)
    assert idle_format.get_comment_header(source) == "    ##"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("", True),
        (" \t  \n", True),
        ("  value", False),
    ],
)
def test_idle_whitespace_helper_distinguishes_content(line, expected):
    assert idle_format.is_all_white(line) is expected


def test_idle_indent_helpers_keep_raw_prefix_and_compute_tab_width():
    assert idle_format.get_indent(" \t  value") == " \t  "
    raw, effective = idle_format.get_line_indent("\t  value", tabwidth=8)
    assert raw == 3
    assert effective == 10


def test_idle_config_parser_typed_get_set_remove_and_save(tmp_path):
    path = tmp_path / "config-main.cfg"
    path.write_text(
        "[General]\neditor-on-startup = 1\nwidth = 80\n",
        encoding="utf-8",
    )
    parser = idle_config.IdleConfParser(str(path))
    parser.Load()

    assert parser.Get(
        "General",
        "editor-on-startup",
        type="bool",
    ) is True
    assert parser.Get("General", "width", type="int") == 80
    assert parser.Get("General", "missing", default="fallback") == "fallback"

    assert parser.SetOption("General", "width", "100") is True
    assert parser.SetOption("General", "width", "100") is False
    assert parser.RemoveOption("General", "editor-on-startup") is True
    parser.Save()

    reloaded = idle_config.IdleConfParser(str(path))
    reloaded.Load()
    assert reloaded.Get("General", "width", type="int") == 100
    assert reloaded.Get("General", "editor-on-startup", default=None) is None
