"""140｜tkinter：Tcl 解释器、变量回调与经典控件工作流。

tkinter 是 Python 对 Tcl/Tk 的薄封装。``Tcl()`` 不创建窗口，适合验证
字符串边界、变量和事件队列；经典 Widget 需要可用的 Tk 与显示服务器。
本文件将二者放在一起，但用 ``tk_root`` 夹具只跳过确实需要窗口的案例。

这些案例不会进入 ``mainloop``，不会等待真实时间，也不会留下窗口。
它们面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.tkinter python.tkinter.Tcl-headless-interpreter
# polyglot-covers: python.tkinter.Tcl-eval-call-list-and-conversions
# polyglot-covers: python.tkinter.Variable-name-value-equality
# polyglot-covers: python.tkinter.StringVar-IntVar-DoubleVar-BooleanVar
# polyglot-covers: python.tkinter.Variable-trace-add-remove-info
# polyglot-covers: python.tkinter.Variable-read-write-unset-traces
# polyglot-covers: python.tkinter.Misc-register-deletecommand
# polyglot-covers: python.tkinter.Misc-after-after-idle-after-cancel
# polyglot-covers: python.tkinter.Widget-option-mapping-and-configure
# polyglot-covers: python.tkinter.Widget-bind-unbind-bindtags
# polyglot-covers: python.tkinter.Button-command-invoke-state
# polyglot-covers: python.tkinter.Checkbutton-Radiobutton-variable-coupling
# polyglot-covers: python.tkinter.Entry-edit-selection-validation
# polyglot-covers: python.tkinter.Text-content-index-mark-tag-search
# polyglot-covers: python.tkinter.Listbox-items-selection-activation
# polyglot-covers: python.tkinter.Canvas-items-coordinates-tags-overlap
# polyglot-covers: python.tkinter.Menu-command-checkbutton-cascade
# polyglot-covers: python.tkinter.Scale-Spinbox-Scrollbar
# polyglot-covers: python.tkinter.Pack-Grid-Place-geometry-managers
# polyglot-covers: python.tkinter.PanedWindow-pane-management
# polyglot-covers: python.tkinter.PhotoImage-pixel-zoom-subsample
# polyglot-covers: python.tkinter.Toplevel-window-manager-state
# polyglot-covers: python.tkinter.widget-lifecycle-and-winfo
# polyglot-covers: python.tkinter.TclError-display-unavailable-skip

import pytest


tkinter = pytest.importorskip(
    "tkinter",
    reason="此标准库构建没有可导入的 tkinter",
)


@pytest.fixture
def tcl():
    """Tcl(useTk=False) 不连接显示服务器，也不加载 Tk 控件命令。"""

    return tkinter.Tcl()


@pytest.fixture
def tk_root():
    """只有能真实创建 Tk 根窗口时才运行控件案例。"""

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


def test_tcl_eval_call_and_expression_results_are_tcl_boundaries(tcl):
    assert tcl.eval("expr {6 * 7}") == "42"
    assert tcl.call("string", "toupper", "Hello") == "HELLO"
    assert tcl.call("expr", "{10 / 4}") == 2
    assert tcl.call("expr", "{10.0 / 4}") == pytest.approx(2.5)

    # eval 总是返回 Tcl 字符串；wantobjects 模式下 call 会尽量还原数字对象。
    assert isinstance(tcl.eval("expr {10 / 4}"), str)
    assert isinstance(tcl.call("expr", "{10 / 4}"), int)


def test_tcl_list_roundtrip_preserves_spaces_empty_values_and_braces(tcl):
    value = tcl.call(
        "list",
        "plain",
        "two words",
        "",
        "{already braced}",
    )

    assert tcl.splitlist(value) == (
        "plain",
        "two words",
        "",
        "{already braced}",
    )
    with pytest.raises(tkinter.TclError):
        tcl.splitlist("{unclosed")


def test_tcl_boolean_integer_and_float_converters_accept_tcl_spellings(tcl):
    assert tcl.getboolean("yes") is True
    assert tcl.getboolean("off") is False
    assert tcl.getint("0x10") == 16
    assert tcl.getdouble("1.25e2") == pytest.approx(125)

    with pytest.raises(ValueError, match="boolean"):
        tcl.getboolean("perhaps")
    with pytest.raises(tkinter.TclError):
        tcl.getint("3.5")


def test_tcl_global_variable_set_get_and_unset(tcl):
    tcl.globalsetvar("course_topic", "protocols")

    assert tcl.globalgetvar("course_topic") == "protocols"
    tcl.globalunsetvar("course_topic")
    with pytest.raises(tkinter.TclError, match="no such variable"):
        tcl.globalgetvar("course_topic")


def test_string_variable_named_storage_and_python_representation(tcl):
    variable = tkinter.StringVar(
        master=tcl,
        value="初始值",
        name="course_name",
    )

    assert str(variable) == "course_name"
    assert variable.get() == "初始值"
    assert tcl.globalgetvar("course_name") == "初始值"
    variable.set("new value")
    assert variable.get() == "new value"


def test_typed_variables_convert_on_get_and_boolean_set(tcl):
    integer = tkinter.IntVar(master=tcl, value=3)
    floating = tkinter.DoubleVar(master=tcl, value="2.5")
    boolean = tkinter.BooleanVar(master=tcl, value="yes")

    assert integer.get() == 3
    assert isinstance(integer.get(), int)
    assert floating.get() == pytest.approx(2.5)
    assert isinstance(floating.get(), float)
    assert boolean.get() is True

    integer.set(4.0)
    boolean.set("off")
    assert integer.get() == 4
    assert boolean.get() is False


def test_boolean_variable_rejects_value_tcl_cannot_interpret(tcl):
    variable = tkinter.BooleanVar(master=tcl)

    with pytest.raises(ValueError, match="boolean"):
        variable.set("not-a-bool")


def test_variable_equality_requires_name_class_and_interpreter_in_python_310(tcl):
    first = tkinter.StringVar(master=tcl, name="shared")
    same_storage = tkinter.StringVar(master=tcl, name="shared")
    different_class = tkinter.IntVar(master=tcl, name="shared")
    other_interpreter = tkinter.Tcl()
    same_name_elsewhere = tkinter.StringVar(
        master=other_interpreter,
        name="shared",
    )

    assert first == same_storage
    assert first != different_class
    assert first != same_name_elsewhere
    assert first != "shared"


def test_write_trace_receives_name_index_mode_and_can_be_removed(tcl):
    variable = tkinter.StringVar(master=tcl, name="traced", value="before")
    calls = []

    callback_name = variable.trace_add(
        "write",
        lambda name, index, mode: calls.append((name, index, mode)),
    )
    assert callback_name
    assert variable.trace_info()

    variable.set("after")
    assert calls == [("traced", "", "write")]

    variable.trace_remove("write", callback_name)
    assert variable.trace_info() == []
    variable.set("silent")
    assert len(calls) == 1


def test_read_and_unset_traces_fire_at_different_operations(tcl):
    variable = tkinter.StringVar(master=tcl, name="lifecycle", value="ready")
    calls = []
    variable.trace_add(
        ("read", "unset"),
        lambda name, index, mode: calls.append((name, mode)),
    )

    assert variable.get() == "ready"
    tcl.globalunsetvar("lifecycle")

    assert calls == [
        ("lifecycle", "read"),
        ("lifecycle", "unset"),
    ]
    with pytest.raises(tkinter.TclError):
        variable.get()


def test_register_exposes_python_callable_as_tcl_command_then_deletes_it(tcl):
    calls = []

    command_name = tcl.register(
        lambda left, right: calls.append((left, right)) or int(left) + int(right)
    )

    assert tcl.call(command_name, "20", "22") == 42
    assert calls == [("20", "22")]
    tcl.deletecommand(command_name)
    with pytest.raises(tkinter.TclError, match="invalid command name"):
        tcl.call(command_name, "1", "2")


def test_after_zero_and_after_idle_run_via_event_queue_without_sleep(tcl):
    events = []
    tcl.after(0, events.append, "timer")
    tcl.after_idle(events.append, "idle")

    assert events == []
    tcl.eval("update")
    assert set(events) == {"timer", "idle"}


def test_after_cancel_prevents_scheduled_callback_without_waiting(tcl):
    events = []
    identifier = tcl.after(60_000, events.append, "too late")

    tcl.after_cancel(identifier)
    tcl.eval("update")

    assert events == []
    # 取消一个已经不存在的 Tcl after id 在 3.10 中不会抛错。
    assert tcl.after_cancel(identifier) is None


def test_widget_options_support_mapping_query_and_incremental_configure(tk_root):
    label = tkinter.Label(
        tk_root,
        text="before",
        padx=5,
        anchor="w",
    )

    assert label["text"] == "before"
    assert label.cget("padx") == 5
    all_options = label.configure()
    assert "text" in all_options
    assert len(all_options["text"]) == 5

    result = label.configure(text="after", pady=3)
    assert result is None
    assert label["text"] == "after"
    assert label["pady"] == 3


def test_button_invoke_runs_command_unless_disabled(tk_root):
    calls = []
    button = tkinter.Button(
        tk_root,
        text="Save",
        command=lambda: calls.append("saved") or "result",
    )

    assert button.invoke() == "result"
    assert calls == ["saved"]

    button.configure(state=tkinter.DISABLED)
    assert button.invoke() == ""
    assert calls == ["saved"]


def test_checkbutton_and_radiobutton_share_tcl_variables(tk_root):
    enabled = tkinter.StringVar(master=tk_root, value="no")
    choice = tkinter.IntVar(master=tk_root, value=0)
    check = tkinter.Checkbutton(
        tk_root,
        variable=enabled,
        onvalue="yes",
        offvalue="no",
    )
    first = tkinter.Radiobutton(tk_root, variable=choice, value=1)
    second = tkinter.Radiobutton(tk_root, variable=choice, value=2)

    assert check.invoke() == ""
    assert enabled.get() == "yes"
    check.deselect()
    assert enabled.get() == "no"
    first.invoke()
    assert choice.get() == 1
    second.select()
    assert choice.get() == 2


def test_entry_editing_indices_selection_and_validation_callback(tk_root):
    validated = []
    validator = tk_root.register(
        lambda proposed: validated.append(proposed) or proposed.isdigit()
    )
    entry = tkinter.Entry(
        tk_root,
        validate="key",
        validatecommand=(validator, "%P"),
    )

    entry.insert(0, "123")
    assert entry.get() == "123"
    assert entry.index(tkinter.END) == 3
    assert entry.insert(tkinter.END, "x") is None
    assert entry.get() == "123"
    assert validated[-1] == "123x"

    entry.selection_range(0, 2)
    assert entry.selection_present() is True
    entry.icursor(1)
    assert entry.index(tkinter.INSERT) == 1
    entry.delete(1, tkinter.END)
    assert entry.get() == "1"


def test_text_uses_line_column_indices_and_implicit_final_newline(tk_root):
    text = tkinter.Text(tk_root, width=20, height=4)
    text.insert("1.0", "alpha\nbeta")

    assert text.get("1.0", "end-1c") == "alpha\nbeta"
    assert text.index(tkinter.END) == "3.0"
    assert text.get("1.0", tkinter.END).endswith("\n")

    text.mark_set("bookmark", "2.2")
    assert text.index("bookmark") == "2.2"
    text.insert("bookmark", "X")
    assert text.get("2.0", "2.end") == "beXta"


def test_text_tags_ranges_configuration_and_search(tk_root):
    text = tkinter.Text(tk_root)
    text.insert("1.0", "red blue red")
    text.tag_add("highlight", "1.0", "1.3")
    text.tag_configure("highlight", foreground="red", underline=True)

    assert tuple(map(str, text.tag_ranges("highlight"))) == ("1.0", "1.3")
    assert text.tag_cget("highlight", "foreground") == "red"

    count = tkinter.IntVar(master=tk_root)
    found = text.search("red", "1.1", stopindex=tkinter.END, count=count)
    assert found == "1.9"
    assert count.get() == 3


def test_listbox_items_selection_and_activation(tk_root):
    listbox = tkinter.Listbox(tk_root, height=4)
    listbox.insert(tkinter.END, "alpha", "beta", "gamma")

    assert listbox.size() == 3
    assert listbox.get(0, tkinter.END) == ("alpha", "beta", "gamma")
    listbox.selection_set(1, 2)
    assert listbox.curselection() == (1, 2)
    listbox.activate(2)
    assert listbox.index(tkinter.ACTIVE) == 2

    listbox.delete(0)
    assert listbox.get(0, tkinter.END) == ("beta", "gamma")


def test_canvas_item_ids_coordinates_options_tags_and_overlap(tk_root):
    canvas = tkinter.Canvas(tk_root, width=100, height=100)
    rectangle = canvas.create_rectangle(
        10,
        10,
        40,
        40,
        fill="red",
        tags=("shape", "hot"),
    )
    line = canvas.create_line(0, 0, 50, 50, tags="shape")

    assert rectangle != line
    assert canvas.type(rectangle) == "rectangle"
    assert canvas.coords(rectangle) == [10.0, 10.0, 40.0, 40.0]
    assert canvas.itemcget(rectangle, "fill") == "red"
    assert set(canvas.gettags(rectangle)) == {"shape", "hot"}
    assert set(canvas.find_withtag("shape")) == {rectangle, line}
    assert rectangle in canvas.find_overlapping(20, 20, 21, 21)

    canvas.move(rectangle, 5, -5)
    assert canvas.coords(rectangle) == [15.0, 5.0, 45.0, 35.0]
    canvas.delete("hot")
    assert canvas.type(rectangle) is None


def test_menu_invocation_command_checkbutton_and_cascade(tk_root):
    calls = []
    flag = tkinter.BooleanVar(master=tk_root, value=False)
    menu = tkinter.Menu(tk_root, tearoff=False)
    submenu = tkinter.Menu(menu, tearoff=False)
    menu.add_command(label="Run", command=lambda: calls.append("run"))
    menu.add_checkbutton(label="Flag", variable=flag)
    menu.add_cascade(label="More", menu=submenu)

    assert menu.index(tkinter.END) == 2
    assert menu.type(0) == "command"
    assert menu.type(1) == "checkbutton"
    assert menu.type(2) == "cascade"
    menu.invoke(0)
    menu.invoke(1)
    assert calls == ["run"]
    assert flag.get() is True


def test_scale_spinbox_and_scrollbar_value_protocols(tk_root):
    scale = tkinter.Scale(tk_root, from_=0, to=10, resolution=0.5)
    spinbox = tkinter.Spinbox(tk_root, from_=1, to=5)
    scrollbar_calls = []
    scrollbar = tkinter.Scrollbar(
        tk_root,
        command=lambda *args: scrollbar_calls.append(args),
    )

    scale.set(3.5)
    assert scale.get() == pytest.approx(3.5)
    spinbox.delete(0, tkinter.END)
    spinbox.insert(0, "4")
    assert spinbox.get() == "4"

    scrollbar.set(0.25, 0.75)
    assert scrollbar.get() == pytest.approx((0.25, 0.75))
    scrollbar.activate("slider")
    assert scrollbar.activate() == "slider"


def test_pack_grid_and_place_report_managed_children_and_forget(tk_root):
    pack_parent = tkinter.Frame(tk_root)
    packed = tkinter.Label(pack_parent, text="packed")
    packed.pack(side="left", padx=2)
    assert pack_parent.pack_slaves() == [packed]
    assert packed.pack_info()["side"] == "left"
    packed.pack_forget()
    assert pack_parent.pack_slaves() == []

    grid_parent = tkinter.Frame(tk_root)
    gridded = tkinter.Label(grid_parent, text="gridded")
    gridded.grid(row=1, column=2, sticky="nsew")
    grid_parent.grid_rowconfigure(1, weight=1)
    grid_parent.grid_columnconfigure(2, weight=2)
    assert grid_parent.grid_slaves(row=1, column=2) == [gridded]
    assert gridded.grid_info()["sticky"] == "nesw"
    assert grid_parent.grid_rowconfigure(1)["weight"] == 1
    gridded.grid_remove()
    assert gridded.winfo_manager() == ""
    gridded.grid()
    assert gridded.winfo_manager() == "grid"

    place_parent = tkinter.Frame(tk_root, width=100, height=100)
    placed = tkinter.Label(place_parent, text="placed")
    placed.place(relx=0.5, rely=0.5, anchor="center")
    assert place_parent.place_slaves() == [placed]
    assert placed.place_info()["anchor"] == "center"
    placed.place_forget()
    assert place_parent.place_slaves() == []


def test_panedwindow_add_configure_forget_and_restore_panes(tk_root):
    panes = tkinter.PanedWindow(tk_root, orient=tkinter.HORIZONTAL)
    left = tkinter.Frame(panes, width=20)
    right = tkinter.Frame(panes, width=30)
    panes.add(left, minsize=10)
    panes.add(right)

    assert panes.panes() == (str(left), str(right))
    assert int(panes.panecget(left, "minsize")) == 10
    panes.paneconfigure(right, stretch="always")
    assert panes.panecget(right, "stretch") == "always"
    panes.forget(left)
    assert panes.panes() == (str(right),)


def test_bind_returns_command_identifier_and_unbind_removes_it(tk_root):
    label = tkinter.Label(tk_root, text="events")
    calls = []

    callback_id = label.bind(
        "<Button-1>",
        lambda event: calls.append((event.x, event.y)),
    )
    assert callback_id
    assert callback_id in label.bind("<Button-1>")
    assert str(label) in label.bindtags()

    label.unbind("<Button-1>", callback_id)
    assert label.bind("<Button-1>") == ""
    assert calls == []


def test_photoimage_pixel_data_copy_zoom_and_subsample(tk_root):
    image = tkinter.PhotoImage(master=tk_root, width=2, height=2)
    image.put("#ff0000", to=(0, 0))
    image.put("#00ff00", to=(1, 0))

    assert image.width() == 2
    assert image.height() == 2
    assert image.get(0, 0) in {(255, 0, 0), "255 0 0"}

    copied = image.copy()
    zoomed = image.zoom(2, 3)
    sampled = zoomed.subsample(2, 3)
    assert (copied.width(), copied.height()) == (2, 2)
    assert (zoomed.width(), zoomed.height()) == (4, 6)
    assert (sampled.width(), sampled.height()) == (2, 2)


def test_toplevel_window_manager_title_geometry_and_withdraw_state(tk_root):
    window = tkinter.Toplevel(tk_root)
    try:
        window.title("Teaching Window")
        window.geometry("240x120+10+20")
        window.update_idletasks()
        window.withdraw()

        assert window.title() == "Teaching Window"
        assert window.geometry().startswith("240x120")
        assert window.state() == "withdrawn"
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        assert window.protocol("WM_DELETE_WINDOW")
    finally:
        window.destroy()


def test_widget_names_relationships_winfo_and_destroy_lifecycle(tk_root):
    frame = tkinter.Frame(tk_root, name="panel")
    label = tkinter.Label(frame, name="status", text="ready")

    assert str(frame).endswith(".panel")
    assert str(label).endswith(".panel.status")
    assert label.master is frame
    assert frame.winfo_children() == [label]
    assert label.winfo_parent() == str(frame)
    assert label.winfo_toplevel() is tk_root
    assert label.winfo_exists() == 1

    label.destroy()
    assert label.winfo_exists() == 0
    assert frame.winfo_children() == []
