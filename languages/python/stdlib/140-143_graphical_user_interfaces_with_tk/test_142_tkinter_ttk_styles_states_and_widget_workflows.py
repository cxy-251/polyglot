"""142｜tkinter.ttk：主题样式、控件状态与结构化数据工作流。

ttk 把行为与外观分离。本文件用一个真实但隐藏的 Tk 根窗口，集中展示
样式数据库、状态规格和 ttk 独有控件；若容器没有显示服务器，
仅跳过本文件而不伪造控件命令。

案例面向 Python 3.10。
"""

# polyglot-covers: python.stdlib.tkinter.ttk python.ttk.Widget-state-instate
# polyglot-covers: python.ttk.Style-configure-map-lookup
# polyglot-covers: python.ttk.Style-layout-elements-themes
# polyglot-covers: python.ttk.Button-Checkbutton-Radiobutton
# polyglot-covers: python.ttk.Entry-Combobox-Spinbox
# polyglot-covers: python.ttk.Notebook-tab-lifecycle
# polyglot-covers: python.ttk.Progressbar-determinate-step
# polyglot-covers: python.ttk.Panedwindow-pane-lifecycle
# polyglot-covers: python.ttk.Scale-Scrollbar
# polyglot-covers: python.ttk.Treeview-hierarchy-items-values
# polyglot-covers: python.ttk.Treeview-columns-displaycolumns
# polyglot-covers: python.ttk.Treeview-selection-focus-move-detach-delete
# polyglot-covers: python.ttk.Treeview-tags-bindings
# polyglot-covers: python.ttk.LabeledScale-OptionMenu
# polyglot-covers: python.ttk-classic-option-incompatibility

import pytest


tkinter = pytest.importorskip("tkinter")
ttk = pytest.importorskip("tkinter.ttk")


@pytest.fixture
def tk_root():
    try:
        root = tkinter.Tk()
    except tkinter.TclError as error:
        pytest.skip(f"当前容器不能创建 Tk 根窗口: {error}")
    root.withdraw()
    try:
        yield root
    finally:
        if root.winfo_exists():
            root.destroy()


def test_widget_state_returns_changes_and_instate_can_run_callback(tk_root):
    button = ttk.Button(tk_root, text="Run")

    changed = button.state(["disabled", "focus"])
    assert set(changed) == {"!disabled", "!focus"}
    assert button.instate(["disabled", "focus"]) is True
    assert button.instate(["!disabled"]) is False

    calls = []
    result = button.instate(
        ["disabled"],
        lambda value: calls.append(value) or "matched",
        "payload",
    )
    assert result == "matched"
    assert calls == ["payload"]
    assert set(button.state(["!disabled", "!focus"])) == {
        "disabled",
        "focus",
    }


def test_ttk_rejects_classic_fg_bg_options_in_favor_of_styles(tk_root):
    with pytest.raises(tkinter.TclError, match="unknown option"):
        ttk.Label(tk_root, text="bad", fg="red")


def test_style_configure_query_and_lookup_share_named_style(tk_root):
    style = ttk.Style(tk_root)
    style.configure(
        "Teaching.TLabel",
        foreground="navy",
        padding=4,
    )

    label = ttk.Label(tk_root, text="Styled", style="Teaching.TLabel")
    assert label.cget("style") == "Teaching.TLabel"
    assert style.configure("Teaching.TLabel", "foreground") == "navy"
    assert style.configure("Teaching.TLabel")["padding"] == 4
    assert style.lookup("Teaching.TLabel", "foreground") == "navy"
    assert style.lookup("Missing.TLabel", "not-an-option", default="fallback") == (
        "fallback"
    )


def test_style_map_preserves_first_matching_state_order(tk_root):
    style = ttk.Style(tk_root)
    style.map(
        "Teaching.TButton",
        foreground=[
            ("pressed", "red"),
            ("active", "blue"),
            ("disabled", "gray"),
        ],
    )

    mapping = style.map("Teaching.TButton", "foreground")
    assert mapping == [
        ("pressed", "red"),
        ("active", "blue"),
        ("disabled", "gray"),
    ]
    assert style.lookup(
        "Teaching.TButton",
        "foreground",
        ("pressed", "active"),
    ) == "red"


def test_style_layout_roundtrip_and_element_introspection(tk_root):
    style = ttk.Style(tk_root)
    layout = [
        (
            "Teaching.background",
            {
                "sticky": "nswe",
                "children": [
                    ("Teaching.padding", {"sticky": "nswe"}),
                ],
            },
        )
    ]

    style.layout("Teaching.TFrame", layout)

    returned = style.layout("Teaching.TFrame")
    assert returned[0][0] == "Teaching.background"
    assert returned[0][1]["sticky"] == "nswe"
    assert returned[0][1]["children"][0][0] == "Teaching.padding"
    assert style.element_names()
    assert isinstance(style.element_options("Button.label"), tuple)


def test_style_can_create_use_and_restore_child_theme(tk_root):
    style = ttk.Style(tk_root)
    original = style.theme_use()
    theme_name = "polyglot_teaching_theme"
    if theme_name not in style.theme_names():
        style.theme_create(
            theme_name,
            parent=original,
            settings={
                "Teaching.TLabel": {
                    "configure": {"foreground": "purple"},
                }
            },
        )

    try:
        style.theme_use(theme_name)
        assert style.theme_use() == theme_name
        assert style.lookup("Teaching.TLabel", "foreground") == "purple"
    finally:
        style.theme_use(original)


def test_button_and_selection_widgets_use_command_and_shared_variables(tk_root):
    calls = []
    button = ttk.Button(
        tk_root,
        text="Run",
        command=lambda: calls.append("run") or "done",
    )
    flag = tkinter.BooleanVar(master=tk_root, value=False)
    choice = tkinter.StringVar(master=tk_root, value="none")
    check = ttk.Checkbutton(tk_root, variable=flag)
    first = ttk.Radiobutton(tk_root, variable=choice, value="first")

    assert button.invoke() == "done"
    check.invoke()
    first.invoke()
    assert calls == ["run"]
    assert flag.get() is True
    assert choice.get() == "first"

    button.state(["disabled"])
    assert button.invoke() == ""
    assert calls == ["run"]


def test_entry_combobox_and_spinbox_value_and_selection_protocols(tk_root):
    entry = ttk.Entry(tk_root)
    entry.insert(0, "hello")
    entry.selection_range(1, 4)
    assert entry.get() == "hello"
    assert entry.selection_present() is True

    combo = ttk.Combobox(
        tk_root,
        values=("alpha", "beta", "gamma"),
        state="readonly",
    )
    assert combo.current() == -1
    combo.current(1)
    assert combo.current() == 1
    assert combo.get() == "beta"
    combo.set("gamma")
    assert combo.get() == "gamma"

    spinbox = ttk.Spinbox(tk_root, from_=1, to=5, increment=0.5)
    spinbox.set("2.5")
    assert spinbox.get() == "2.5"


def test_notebook_add_insert_select_hide_forget_and_tab_options(tk_root):
    notebook = ttk.Notebook(tk_root)
    first = ttk.Frame(notebook)
    second = ttk.Frame(notebook)
    third = ttk.Frame(notebook)
    notebook.add(first, text="First")
    notebook.add(third, text="Third")
    notebook.insert(1, second, text="Second")

    assert notebook.tabs() == (str(first), str(second), str(third))
    assert notebook.index(second) == 1
    assert notebook.tab(second, "text") == "Second"
    notebook.select(second)
    assert notebook.select() == str(second)

    notebook.hide(second)
    assert notebook.tab(second, "state") == "hidden"
    notebook.add(second)
    assert notebook.tab(second, "state") == "normal"
    notebook.forget(third)
    assert notebook.tabs() == (str(first), str(second))


def test_progressbar_step_updates_determinate_variable_and_wraps(tk_root):
    value = tkinter.DoubleVar(master=tk_root, value=95)
    progress = ttk.Progressbar(
        tk_root,
        mode="determinate",
        maximum=100,
        variable=value,
    )

    progress.step(3)
    assert value.get() == pytest.approx(98)
    progress.step(5)
    assert value.get() == pytest.approx(3)


def test_ttk_panedwindow_add_insert_query_and_forget(tk_root):
    panes = ttk.Panedwindow(tk_root, orient="horizontal")
    first = ttk.Frame(panes)
    second = ttk.Frame(panes)
    third = ttk.Frame(panes)
    panes.add(first, weight=1)
    panes.add(third, weight=3)
    panes.insert(1, second, weight=2)

    assert panes.panes() == (str(first), str(second), str(third))
    assert panes.pane(second, "weight") == 2
    panes.pane(second, weight=4)
    assert panes.pane(second)["weight"] == 4
    panes.forget(first)
    assert panes.panes() == (str(second), str(third))


def test_ttk_scale_and_scrollbar_query_values_and_commands(tk_root):
    values = []
    scale = ttk.Scale(
        tk_root,
        from_=0,
        to=10,
        command=lambda value: values.append(float(value)),
    )
    scrollbar = ttk.Scrollbar(tk_root)

    scale.set(4.5)
    assert scale.get() == pytest.approx(4.5)
    assert values[-1] == pytest.approx(4.5)
    scrollbar.set(0.2, 0.8)
    assert scrollbar.get() == pytest.approx((0.2, 0.8))


def make_tree(tk_root):
    tree = ttk.Treeview(
        tk_root,
        columns=("language", "level"),
        displaycolumns=("level", "language"),
        show=("tree", "headings"),
    )
    tree.heading("#0", text="Topic")
    tree.heading("language", text="Language")
    tree.heading("level", text="Level")
    tree.column("language", width=90, anchor="w")
    tree.column("level", width=60, anchor="center")
    return tree


def test_treeview_hierarchy_items_values_columns_and_display_order(tk_root):
    tree = make_tree(tk_root)
    python = tree.insert(
        "",
        "end",
        iid="python",
        text="Python",
        values=("py", "advanced"),
        tags=("language",),
    )
    child = tree.insert(python, "end", iid="protocols", text="Protocols")

    assert python == "python"
    assert child == "protocols"
    assert tree.parent(child) == python
    assert tree.get_children("") == (python,)
    assert tree.get_children(python) == (child,)
    assert tree.item(python, "text") == "Python"
    assert tree.item(python, "values") == ("py", "advanced")
    assert tree.set(python, "level") == "advanced"
    assert tree["displaycolumns"] == ("level", "language")
    assert tree.column("language", "width") == 90

    tree.set(python, "level", "expert")
    assert tree.set(python) == {"language": "py", "level": "expert"}


def test_treeview_selection_focus_move_detach_reattach_and_delete(tk_root):
    tree = make_tree(tk_root)
    first = tree.insert("", "end", iid="first", text="First")
    second = tree.insert("", "end", iid="second", text="Second")
    child = tree.insert(first, "end", iid="child", text="Child")

    tree.selection_set(first, second)
    tree.focus(second)
    assert tree.selection() == (first, second)
    assert tree.focus() == second

    tree.move(child, "", 0)
    assert tree.parent(child) == ""
    assert tree.index(child) == 0
    tree.detach(second)
    assert tree.exists(second) is True
    assert second not in tree.get_children("")
    tree.reattach(second, "", "end")
    assert second in tree.get_children("")

    tree.delete(first)
    assert tree.exists(first) is False


def test_treeview_tags_configuration_membership_and_bind_script(tk_root):
    tree = make_tree(tk_root)
    item = tree.insert("", "end", iid="tagged", tags=("important",))
    tree.tag_configure("important", foreground="red", background="white")

    assert tree.tag_has("important", item) is True
    assert tree.tag_has("important") == (item,)
    assert tree.tag_configure("important", "foreground") == "red"

    callback_id = tree.tag_bind(
        "important",
        "<Button-1>",
        lambda event: None,
    )
    assert callback_id
    assert callback_id in tree.tag_bind("important", "<Button-1>")


def test_labeledscale_and_optionmenu_compose_smaller_ttk_widgets(tk_root):
    variable = tkinter.DoubleVar(master=tk_root, value=4)
    labeled = ttk.LabeledScale(tk_root, variable=variable, from_=0, to=10)
    choice = tkinter.StringVar(master=tk_root)
    menu = ttk.OptionMenu(tk_root, choice, "alpha", "alpha", "beta")

    assert labeled.scale.get() == pytest.approx(4)
    variable.set(7)
    labeled.update_idletasks()
    assert labeled.label.cget("text") in {7, "7", "7.0"}
    assert choice.get() == "alpha"
    menu.set_menu("beta", "beta", "gamma")
    assert choice.get() == "beta"
