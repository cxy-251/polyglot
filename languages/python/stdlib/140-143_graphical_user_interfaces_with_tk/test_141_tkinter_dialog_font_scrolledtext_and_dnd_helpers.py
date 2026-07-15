"""141｜tkinter 小模块：对话框、字体、滚动文本与进程内拖放。

这些模块都建立在 tkinter 上，但各自代码量较小，因此合并成一个可检索的
辅助工作流文件。对话框案例替换最终的 Tk 命令，验证选项和返回值，
但不弹出窗口；
字体与 ScrolledText 只有在真实 Tk 根窗口可用时运行；dnd 使用最小控件
替身验证协议。

案例面向 Python 3.10；整个 Python 测试集尚未经过 pytest 统一验证。
"""

# polyglot-covers: python.stdlib.tkinter.commondialog python.tkinter.Dialog-show-hooks
# polyglot-covers: python.stdlib.tkinter.colorchooser python.tkinter.askcolor
# polyglot-covers: python.stdlib.tkinter.messagebox python.tkinter.messagebox-wrappers
# polyglot-covers: python.stdlib.tkinter.filedialog python.tkinter.native-file-wrappers
# polyglot-covers: python.tkinter.filedialog-result-normalization
# polyglot-covers: python.stdlib.tkinter.simpledialog python.tkinter.query-wrappers
# polyglot-covers: python.stdlib.tkinter.font python.tkinter.Font-create-query-config-copy
# polyglot-covers: python.tkinter.font-families-names-metrics-measure
# polyglot-covers: python.stdlib.tkinter.scrolledtext python.tkinter.ScrolledText-frame-delegation
# polyglot-covers: python.stdlib.tkinter.dnd python.tkinter.dnd-start-guard
# polyglot-covers: python.tkinter.dnd-enter-motion-leave-commit-cancel

from types import SimpleNamespace

import pytest


tkinter = pytest.importorskip("tkinter")
colorchooser = pytest.importorskip("tkinter.colorchooser")
commondialog = pytest.importorskip("tkinter.commondialog")
dnd = pytest.importorskip("tkinter.dnd")
filedialog = pytest.importorskip("tkinter.filedialog")
tkfont = pytest.importorskip("tkinter.font")
messagebox = pytest.importorskip("tkinter.messagebox")
scrolledtext = pytest.importorskip("tkinter.scrolledtext")
simpledialog = pytest.importorskip("tkinter.simpledialog")


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


class FakeDialogTk:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def call(self, *args):
        self.calls.append(args)
        return self.result


class FakeDialogMaster:
    def __init__(self, result):
        self.tk = FakeDialogTk(result)
        self.fixed_results = []

    def _options(self, options):
        flattened = []
        for key, value in sorted(options.items()):
            flattened.extend((f"-{key.rstrip('_')}", value))
        return tuple(flattened)


class TeachingDialog(commondialog.Dialog):
    command = "teaching_dialog"

    def __init__(self, *args, **kwargs):
        self.events = []
        super().__init__(*args, **kwargs)

    def _fixoptions(self):
        self.events.append("fix-options")
        self.options["normalized"] = True

    def _test_callback(self, master):
        self.events.append(("callback", master))

    def _fixresult(self, master, result):
        self.events.append(("fix-result", result))
        return f"fixed:{result}"


class FakeQuery:
    instances = []
    result = None

    def __init__(self, title, prompt, **options):
        self.title = title
        self.prompt = prompt
        self.options = options
        type(self).instances.append(self)

    def result(self):
        return type(self).result


class FakeDndRoot:
    pass


class FakeDndWidget:
    def __init__(self, root, *, master=None):
        self.root = root
        self.master = master
        self.options = {"cursor": "arrow"}
        self.bindings = {}
        self.containing = None

    def _root(self):
        return self.root

    def __getitem__(self, key):
        return self.options[key]

    def __setitem__(self, key, value):
        self.options[key] = value

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def unbind(self, sequence):
        self.bindings.pop(sequence, None)

    def winfo_containing(self, x, y):
        return self.containing


class DndSource:
    def __init__(self):
        self.ended = []

    def dnd_end(self, target, event):
        self.ended.append((target, event))


class DndTarget:
    def __init__(self):
        self.events = []

    def dnd_enter(self, source, event):
        self.events.append(("enter", source, event))

    def dnd_motion(self, source, event):
        self.events.append(("motion", source, event))

    def dnd_leave(self, source, event):
        self.events.append(("leave", source, event))

    def dnd_commit(self, source, event):
        self.events.append(("commit", source, event))


def test_common_dialog_updates_options_runs_hooks_and_normalizes_result():
    master = FakeDialogMaster("raw")
    dialog = TeachingDialog(master=master, title="before")

    result = dialog.show(title="after")

    assert result == "fixed:raw"
    assert dialog.options == {
        "title": "after",
        "normalized": True,
    }
    assert dialog.events == [
        "fix-options",
        ("callback", master),
        ("fix-result", "raw"),
    ]
    assert master.tk.calls == [
        (
            "teaching_dialog",
            "-normalized",
            True,
            "-title",
            "after",
        )
    ]


def test_color_chooser_converts_rgb_option_and_result_without_opening_dialog():
    master = FakeDialogMaster("#102030")
    master.winfo_rgb = lambda value: (0x1000, 0x2000, 0x3000)
    chooser = colorchooser.Chooser(
        master=master,
        initialcolor=(1, 2, 3),
        title="Color",
    )

    assert chooser.show() == ((16, 32, 48), "#102030")
    assert chooser.options["initialcolor"] == "#010203"

    canceled = colorchooser.Chooser(master=FakeDialogMaster(""))
    assert canceled.show() == (None, None)


def test_askcolor_passes_positional_color_as_initialcolor(monkeypatch):
    captured = []

    class FakeChooser:
        def __init__(self, **options):
            captured.append(options)

        def show(self):
            return (1, 2, 3), "#010203"

    monkeypatch.setattr(colorchooser, "Chooser", FakeChooser)

    assert colorchooser.askcolor("red", title="Pick") == (
        (1, 2, 3),
        "#010203",
    )
    assert captured == [{"title": "Pick", "initialcolor": "red"}]


def install_fake_message(monkeypatch, response):
    captured = []

    class FakeMessage:
        def __init__(self, **options):
            captured.append(options)

        def show(self):
            return response

    monkeypatch.setattr(messagebox, "Message", FakeMessage)
    return captured


def test_messagebox_show_wrappers_choose_icon_type_title_and_message(monkeypatch):
    captured = install_fake_message(monkeypatch, messagebox.OK)

    assert messagebox.showinfo("Title", "Body", detail="More") == "ok"

    assert captured == [
        {
            "detail": "More",
            "icon": messagebox.INFO,
            "type": messagebox.OK,
            "title": "Title",
            "message": "Body",
        }
    ]


@pytest.mark.parametrize(
    ("function_name", "response", "expected"),
    [
        ("askyesno", messagebox.YES, True),
        ("askyesno", messagebox.NO, False),
        ("askokcancel", messagebox.OK, True),
        ("askretrycancel", messagebox.CANCEL, False),
        ("askyesnocancel", messagebox.CANCEL, None),
        ("askquestion", messagebox.NO, messagebox.NO),
    ],
)
def test_messagebox_question_wrappers_normalize_symbolic_answers(
    monkeypatch,
    function_name,
    response,
    expected,
):
    install_fake_message(monkeypatch, response)
    function = getattr(messagebox, function_name)

    assert function("Question", "Continue?") == expected


def test_messagebox_boolean_tcl_result_is_mapped_back_to_yes_or_no(monkeypatch):
    install_fake_message(monkeypatch, True)
    assert messagebox.askquestion("Q", "M") == messagebox.YES


def install_fake_native_dialog(monkeypatch, class_name, response):
    captured = []

    class FakeNativeDialog:
        def __init__(self, **options):
            captured.append(options)

        def show(self):
            return response

    monkeypatch.setattr(filedialog, class_name, FakeNativeDialog)
    return captured


def test_file_dialog_convenience_wrappers_forward_options(monkeypatch):
    captured = install_fake_native_dialog(
        monkeypatch,
        "Open",
        "/tmp/example.txt",
    )

    assert filedialog.askopenfilename(
        title="Open",
        filetypes=(("Text", "*.txt"),),
    ) == "/tmp/example.txt"
    assert captured == [
        {
            "title": "Open",
            "filetypes": (("Text", "*.txt"),),
        }
    ]


def test_askopenfile_opens_returned_path_with_requested_mode(tmp_path, monkeypatch):
    path = tmp_path / "data.txt"
    path.write_text("payload", encoding="utf-8")
    install_fake_native_dialog(monkeypatch, "Open", str(path))

    stream = filedialog.askopenfile(mode="r")
    try:
        assert stream.read() == "payload"
    finally:
        stream.close()


def test_asksaveasfile_returns_none_on_cancel_without_creating_file(monkeypatch):
    install_fake_native_dialog(monkeypatch, "SaveAs", "")

    assert filedialog.asksaveasfile(mode="w") is None


def test_directory_wrapper_uses_directory_dialog_class(monkeypatch):
    captured = install_fake_native_dialog(monkeypatch, "Directory", "/tmp")

    assert filedialog.askdirectory(mustexist=True) == "/tmp"
    assert captured == [{"mustexist": True}]


def test_open_fixoptions_converts_outer_filetypes_container_to_tuple():
    dialog = filedialog.Open(filetypes=[("Text", "*.txt")])

    dialog._fixoptions()

    assert dialog.options["filetypes"] == (("Text", "*.txt"),)


def test_open_fixresult_records_initial_directory_and_filename():
    dialog = filedialog.Open()
    widget = SimpleNamespace(
        tk=SimpleNamespace(wantobjects=lambda: True),
    )

    result = dialog._fixresult(widget, "/work/report.txt")

    assert result == "/work/report.txt"
    assert dialog.options["initialdir"] == "/work"
    assert dialog.options["initialfile"] == "report.txt"


def test_simpledialog_ask_wrappers_choose_query_class_and_forward_limits(
    monkeypatch,
):
    captured = []

    class IntegerQuery:
        def __init__(self, title, prompt, **options):
            captured.append((title, prompt, options))
            self.result = 7

    monkeypatch.setattr(simpledialog, "_QueryInteger", IntegerQuery)

    assert simpledialog.askinteger(
        "Count",
        "How many?",
        minvalue=1,
        maxvalue=10,
        initialvalue=3,
    ) == 7
    assert captured == [
        (
            "Count",
            "How many?",
            {"minvalue": 1, "maxvalue": 10, "initialvalue": 3},
        )
    ]


def test_simpledialog_float_and_string_wrappers_return_dialog_result(monkeypatch):
    class FloatQuery:
        def __init__(self, *args, **kwargs):
            self.result = 2.5

    class StringQuery:
        def __init__(self, *args, **kwargs):
            self.result = "answer"

    monkeypatch.setattr(simpledialog, "_QueryFloat", FloatQuery)
    monkeypatch.setattr(simpledialog, "_QueryString", StringQuery)

    assert simpledialog.askfloat("F", "Value") == pytest.approx(2.5)
    assert simpledialog.askstring("S", "Value", show="*") == "answer"


def test_font_create_actual_configure_copy_measure_and_metrics(tk_root):
    font = tkfont.Font(
        root=tk_root,
        family="TkDefaultFont",
        size=12,
        weight=tkfont.BOLD,
    )

    assert font.cget("size") == 12
    assert font["weight"] == tkfont.BOLD
    assert font.actual("size") == 12
    assert font.measure("abc") >= 0
    assert font.metrics("linespace") > 0

    font.configure(size=14, slant=tkfont.ITALIC)
    copied = font.copy()
    assert copied.actual("size") == 14
    assert copied.actual("slant") == tkfont.ITALIC


def test_named_font_exists_flag_shares_existing_tk_font(tk_root):
    created = tkfont.Font(root=tk_root, name="TeachingFont", size=10)
    shared = tkfont.Font(root=tk_root, name="TeachingFont", exists=True)

    assert str(created) == "TeachingFont"
    assert str(shared) == "TeachingFont"
    shared.configure(size=16)
    assert created.actual("size") == 16
    assert "TeachingFont" in tkfont.names(root=tk_root)
    assert tkfont.families(root=tk_root)


def test_scrolledtext_combines_text_api_with_outer_frame_geometry(tk_root):
    widget = scrolledtext.ScrolledText(tk_root, width=20, height=4)
    widget.insert("1.0", "line one\nline two")
    widget.pack(fill="both", expand=True)

    assert widget.get("1.0", "end-1c") == "line one\nline two"
    assert isinstance(widget.vbar, tkinter.Scrollbar)
    assert widget.vbar.cget("command")
    assert widget.pack_info()["fill"] == "both"
    assert widget.frame.pack_slaves()

    widget.destroy()
    # destroy 来自 Text，只销毁内部文本命令；几何方法却委派给外层 Frame。
    assert widget.frame.winfo_exists() == 1
    widget.frame.destroy()
    assert widget.frame.winfo_exists() == 0


def make_dnd_event(widget, *, number=1, x=10, y=20):
    return SimpleNamespace(
        widget=widget,
        num=number,
        x_root=x,
        y_root=y,
    )


def test_dnd_start_installs_bindings_cursor_and_rejects_high_button_number():
    root = FakeDndRoot()
    widget = FakeDndWidget(root)
    source = DndSource()

    handler = dnd.dnd_start(source, make_dnd_event(widget))

    assert isinstance(handler, dnd.DndHandler)
    assert widget.options["cursor"] == "hand2"
    assert handler.release_pattern in widget.bindings
    assert "<Motion>" in widget.bindings

    high_button_widget = FakeDndWidget(FakeDndRoot())
    assert dnd.dnd_start(
        source,
        make_dnd_event(high_button_widget, number=6),
    ) is None
    handler.cancel()


def test_dnd_motion_walks_parents_and_dispatches_enter_motion_leave():
    root = FakeDndRoot()
    source_widget = FakeDndWidget(root)
    parent = FakeDndWidget(root)
    child = FakeDndWidget(root, master=parent)
    source = DndSource()
    target = DndTarget()
    parent.dnd_accept = lambda offered, event: target
    source_widget.containing = child
    handler = dnd.dnd_start(source, make_dnd_event(source_widget))
    motion = make_dnd_event(source_widget, x=30, y=40)

    handler.on_motion(motion)
    handler.on_motion(motion)
    source_widget.containing = None
    handler.on_motion(motion)

    assert [event[0] for event in target.events] == [
        "enter",
        "motion",
        "leave",
    ]
    handler.cancel(motion)
    assert source.ended == [(None, motion)]


def test_dnd_release_commits_target_then_notifies_source_and_cleans_up():
    root = FakeDndRoot()
    widget = FakeDndWidget(root)
    source = DndSource()
    target = DndTarget()
    target_widget = FakeDndWidget(root)
    target_widget.dnd_accept = lambda offered, event: target
    widget.containing = target_widget
    handler = dnd.dnd_start(source, make_dnd_event(widget))
    event = make_dnd_event(widget)
    handler.on_motion(event)

    handler.on_release(event)

    assert [item[0] for item in target.events] == ["enter", "commit"]
    assert source.ended == [(target, event)]
    assert widget.options["cursor"] == "arrow"
    assert widget.bindings == {}
    assert handler.root is None
