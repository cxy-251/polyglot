"""086｜``curses.wrapper`` 的终端生命周期与 process-global settings。

wrapper 负责 initscr、noecho、cbreak、keypad 和最终恢复；即使 callback 抛异常也会执行
清理。测试用 fake 函数审计调用顺序，不改变真实终端。ESC delay 与 tab size 是 curses
进程级状态，案例在 finally 中恢复，避免影响同一 pytest process 的其他测试。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.curses.wrapper python.curses.initscr
# polyglot-covers: python.curses.noecho python.curses.echo
# polyglot-covers: python.curses.cbreak python.curses.nocbreak
# polyglot-covers: python.curses.window.keypad python.curses.start_color
# polyglot-covers: python.curses.endwin python.curses.wrapper-exception-cleanup
# polyglot-covers: python.curses.wrapper-ignores-start-color-error
# polyglot-covers: python.curses.get_escdelay python.curses.set_escdelay
# polyglot-covers: python.curses.get_tabsize python.curses.set_tabsize
# polyglot-covers: python.curses.version python.curses.ncurses_version
# polyglot-covers: python.curses.error




import curses
import pytest
import curses.ascii as ascii_tools
import curses.ascii
from curses.textpad import rectangle
from curses.textpad import Textbox
import fcntl
import json
import os
import pty
import struct
import subprocess
import sys
import termios
import textwrap

class FakeWindow:
    def __init__(self, events):
        self.events = events

    def keypad(self, enabled):
        self.events.append(("keypad", enabled))


def _patch_lifecycle(monkeypatch, events, *, color_error=False):
    window = FakeWindow(events)

    def initscr():
        events.append("initscr")
        return window

    def record(name):
        return lambda: events.append(name)

    def start_color():
        events.append("start_color")
        if color_error:
            raise curses.error("terminal has no color")

    monkeypatch.setattr(curses, "initscr", initscr)
    monkeypatch.setattr(curses, "noecho", record("noecho"))
    monkeypatch.setattr(curses, "cbreak", record("cbreak"))
    monkeypatch.setattr(curses, "start_color", start_color)
    monkeypatch.setattr(curses, "echo", record("echo"))
    monkeypatch.setattr(curses, "nocbreak", record("nocbreak"))
    monkeypatch.setattr(curses, "endwin", record("endwin"))
    return window


def test_wrapper_initializes_calls_application_and_restores_in_reverse_mode_order(
    monkeypatch,
):
    """callback 收到 stdscr 及附加参数，其返回值原样成为 wrapper 返回值。"""

    events = []
    window = _patch_lifecycle(monkeypatch, events)

    def application(stdscr, name, *, count):
        events.append(("application", stdscr is window, name, count))
        return "result"

    result = curses.wrapper(application, "demo", count=2)

    assert result == "result"
    assert events == [
        "initscr",
        "noecho",
        "cbreak",
        ("keypad", 1),
        "start_color",
        ("application", True, "demo", 2),
        ("keypad", 0),
        "echo",
        "nocbreak",
        "endwin",
    ]


def test_wrapper_ignores_color_setup_failure_but_restores_after_callback_failure(
    monkeypatch,
):
    """start_color 的 curses.error 被忽略；应用异常则在清理后原样传播。"""

    events = []
    _patch_lifecycle(monkeypatch, events, color_error=True)

    def application(stdscr):
        events.append("application")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        curses.wrapper(application)

    assert events[-5:] == [
        "application",
        ("keypad", 0),
        "echo",
        "nocbreak",
        "endwin",
    ]


def test_escape_delay_and_tab_size_are_mutable_global_settings():
    """数值由整个 curses screen 共享，不是单个 window 属性。"""

    original_escape_delay = curses.get_escdelay()
    original_tab_size = curses.get_tabsize()
    try:
        curses.set_escdelay(25)
        curses.set_tabsize(4)
        assert curses.get_escdelay() == 25
        assert curses.get_tabsize() == 4
    finally:
        curses.set_escdelay(original_escape_delay)
        curses.set_tabsize(original_tab_size)


def test_version_and_error_objects_expose_linked_curses_capability():
    """version 是 extension build 标识；ncurses_version 在 ncurses build 上结构化提供。"""

    assert isinstance(curses.version, bytes)
    assert issubclass(curses.error, Exception)
    if hasattr(curses, "ncurses_version"):
        version = curses.ncurses_version
        assert type(version.major) is int
        assert type(version.minor) is int
        assert type(version.patch) is int


# ``curses.ascii`` 的 locale-independent ASCII 分类与位变换。
#
# 这些函数只解释 7-bit ASCII 数值，接受整数或单字符字符串；它们不等同于 Unicode
# ``str.is*``。``ctrl`` 清除高三位，``alt`` 设置 meta bit，``ascii`` 清除 meta bit，
# 而 ``unctrl`` 把控制字符转为适合终端展示的 caret notation。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.curses.ascii-control-constants
# polyglot-covers: python.curses.ascii.isascii python.curses.ascii.isalnum
# polyglot-covers: python.curses.ascii.isalpha python.curses.ascii.isblank
# polyglot-covers: python.curses.ascii.iscntrl python.curses.ascii.isctrl
# polyglot-covers: python.curses.ascii.isdigit python.curses.ascii.isgraph
# polyglot-covers: python.curses.ascii.islower python.curses.ascii.ismeta
# polyglot-covers: python.curses.ascii.isprint python.curses.ascii.ispunct
# polyglot-covers: python.curses.ascii.isspace python.curses.ascii.isupper
# polyglot-covers: python.curses.ascii.isxdigit
# polyglot-covers: python.curses.ascii.ascii python.curses.ascii.ctrl
# polyglot-covers: python.curses.ascii.alt python.curses.ascii.unctrl




@pytest.mark.parametrize(
    ("function", "accepted", "rejected"),
    [
        (ascii_tools.isalnum, "A", "!"),
        (ascii_tools.isalpha, "z", "7"),
        (ascii_tools.isblank, "\t", "\n"),
        (ascii_tools.iscntrl, ascii_tools.DEL, " "),
        (ascii_tools.isctrl, ascii_tools.NUL, ascii_tools.DEL),
        (ascii_tools.isdigit, "9", "a"),
        (ascii_tools.isgraph, "!", " "),
        (ascii_tools.islower, "a", "A"),
        (ascii_tools.isprint, " ", "\n"),
        (ascii_tools.ispunct, "?", "Q"),
        (ascii_tools.isspace, "\r", "x"),
        (ascii_tools.isupper, "Z", "z"),
        (ascii_tools.isxdigit, "f", "g"),
    ],
)
def test_ascii_character_classes_have_explicit_7_bit_boundaries(
    function,
    accepted,
    rejected,
):
    assert function(accepted) is True
    assert function(rejected) is False


def test_ascii_and_meta_membership_do_not_follow_unicode_categories():
    """0x80 以上是 meta；非 ASCII Unicode 字母不会因 isalpha 而被接受。"""

    assert ascii_tools.isascii(0) is True
    assert ascii_tools.isascii(127) is True
    assert ascii_tools.isascii(128) is False
    assert ascii_tools.ismeta(128) is True
    assert ascii_tools.ismeta("é") is True
    assert ascii_tools.isalpha("é") is False


def test_bit_transformations_preserve_string_or_integer_result_kind():
    """输入 str 返回 str，输入 int 返回 int；这些操作本质都是 bit mask。"""

    assert ascii_tools.ctrl("C") == "\x03"
    assert ascii_tools.ctrl(ord("C")) == 3
    assert ascii_tools.alt("A") == chr(0xC1)
    assert ascii_tools.alt(ord("A")) == 0xC1
    assert ascii_tools.ascii(chr(0xC1)) == "A"
    assert ascii_tools.ascii(0xC1) == ord("A")


def test_unctrl_uses_caret_and_meta_notation():
    """DEL 特判为 ^?；高位字符先加 !，再展示其低 7 位形式。"""

    assert ascii_tools.unctrl(ascii_tools.NUL) == "^@"
    assert ascii_tools.unctrl("\x01") == "^A"
    assert ascii_tools.unctrl(ascii_tools.DEL) == "^?"
    assert ascii_tools.unctrl("A") == "A"
    assert ascii_tools.unctrl(ascii_tools.alt("A")) == "!A"


def test_control_constant_aliases_match_terminal_conventions():
    """HT/TAB 与 LF/NL 是历史命名别名；SP 是唯一命名的普通空格。"""

    assert ascii_tools.HT == ascii_tools.TAB == 9
    assert ascii_tools.LF == ascii_tools.NL == 10
    assert ascii_tools.ESC == 27
    assert ascii_tools.SP == 32
    assert ascii_tools.controlnames[ascii_tools.ESC] == "ESC"


def test_string_inputs_must_contain_exactly_one_character():
    """内部使用 ord；多字符字符串是调用错误，不会逐字符分类。"""

    with pytest.raises(TypeError):
        ascii_tools.isdigit("12")


# ``curses.textpad`` rectangle、Textbox 编辑命令与 window protocol。
#
# Textbox 只依赖 curses window 的光标、字符和行操作。本文件用确定性的内存 window
# 执行真实 Textbox 代码，覆盖 Emacs-like 控制键、insert mode、validator 和 gather，
# 同时避免初始化用户终端。fake 只模拟当前案例所需的 curses window 契约。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.curses.textpad.rectangle
# polyglot-covers: python.curses.textpad.Textbox
# polyglot-covers: python.curses.textpad.Textbox.insert_mode
# polyglot-covers: python.curses.textpad.Textbox.stripspaces
# polyglot-covers: python.curses.textpad.Textbox.do_command
# polyglot-covers: python.curses.textpad.Textbox.edit
# polyglot-covers: python.curses.textpad.Textbox.edit-validator
# polyglot-covers: python.curses.textpad.Textbox.gather
# polyglot-covers: python.curses.textpad.emacs-navigation
# polyglot-covers: python.curses.textpad.backspace-delete
# polyglot-covers: python.curses.textpad.insert-character-shift



class RecordingWindow:
    def __init__(self):
        self.calls = []

    def vline(self, *args):
        self.calls.append(("vline",) + args)

    def hline(self, *args):
        self.calls.append(("hline",) + args)

    def addch(self, *args):
        self.calls.append(("addch",) + args)


class GridWindow:
    def __init__(self, height, width, lines=(), keys=()):
        self.height = height
        self.width = width
        self.grid = []
        for y in range(height):
            source = lines[y] if y < len(lines) else ""
            self.grid.append(list(source[:width].ljust(width)))
        self.y = 0
        self.x = 0
        self.keys = list(keys)
        self.keypad_calls = []
        self.refresh_count = 0

    def getmaxyx(self):
        return self.height, self.width

    def getyx(self):
        return self.y, self.x

    def keypad(self, enabled):
        self.keypad_calls.append(enabled)

    def move(self, y, x):
        if not (0 <= y < self.height and 0 <= x < self.width):
            raise curses.error("cursor outside window")
        self.y, self.x = y, x

    def inch(self, *coordinates):
        if coordinates:
            y, x = coordinates
        else:
            y, x = self.y, self.x
        return ord(self.grid[y][x])

    def addch(self, ch):
        character = chr(ch) if isinstance(ch, int) else ch
        self.grid[self.y][self.x] = character
        if self.x < self.width - 1:
            self.x += 1
        elif self.y < self.height - 1:
            self.y += 1
            self.x = 0
        else:
            raise curses.error("bottom-right cell written")

    def delch(self):
        row = self.grid[self.y]
        del row[self.x]
        row.append(" ")

    def clrtoeol(self):
        self.grid[self.y][self.x :] = [" "] * (self.width - self.x)

    def deleteln(self):
        del self.grid[self.y]
        self.grid.append([" "] * self.width)

    def insertln(self):
        self.grid.insert(self.y, [" "] * self.width)
        self.grid.pop()

    def refresh(self):
        self.refresh_count += 1

    def getch(self):
        return self.keys.pop(0)

    def contents(self):
        return ["".join(row) for row in self.grid]


def test_rectangle_draws_edges_then_four_corners(monkeypatch):
    """坐标包含 corners；水平/垂直 line 长度只覆盖两角之间的内部边。"""

    symbols = {
        "ACS_VLINE": ord("|"),
        "ACS_HLINE": ord("-"),
        "ACS_ULCORNER": ord("1"),
        "ACS_URCORNER": ord("2"),
        "ACS_LRCORNER": ord("3"),
        "ACS_LLCORNER": ord("4"),
    }
    for name, value in symbols.items():
        monkeypatch.setattr(curses, name, value, raising=False)
    window = RecordingWindow()

    rectangle(window, 1, 2, 5, 7)

    assert window.calls == [
        ("vline", 2, 2, ord("|"), 3),
        ("hline", 1, 3, ord("-"), 4),
        ("hline", 5, 3, ord("-"), 4),
        ("vline", 2, 7, ord("|"), 3),
        ("addch", 1, 2, ord("1")),
        ("addch", 1, 7, ord("2")),
        ("addch", 5, 7, ord("3")),
        ("addch", 5, 2, ord("4")),
    ]


def test_edit_processes_printable_backspace_validator_and_ctrl_g():
    """validator 在命令分派前变换 key；Ctrl-G 终止后 edit 调 gather。"""

    window = GridWindow(
        1,
        6,
        keys=[ord("a"), ord("b"), curses.ascii.BS, ord("c"), curses.ascii.BEL],
    )
    textbox = Textbox(window)
    textbox.stripspaces = False
    seen = []

    def validate(ch):
        seen.append(ch)
        return ch

    result = textbox.edit(validate=validate)

    assert result == "ac    "
    assert seen[-1] == curses.ascii.BEL
    assert textbox.lastcmd == curses.ascii.BEL
    assert window.keypad_calls == [1]
    assert window.refresh_count == 4


def test_insert_mode_shifts_existing_printable_characters_right():
    """遇到第一个 blank 时停止搬移，并把 cursor 放回新插入字符之后。"""

    window = GridWindow(1, 5, lines=["ac"])
    window.move(0, 1)
    textbox = Textbox(window, insert_mode=True)

    assert textbox.do_command(ord("b")) == 1
    assert window.contents() == ["abc  "]
    assert window.getyx() == (0, 2)


def test_navigation_line_editing_and_refresh_commands_update_window_state():
    """Ctrl-E 定位到 first blank；上下移动会把 x clamp 到较短行的末尾。"""

    window = GridWindow(3, 5, lines=["abc", "xy", ""])
    textbox = Textbox(window)

    window.move(0, 2)
    textbox.do_command(curses.ascii.SOH)
    assert window.getyx() == (0, 0)
    textbox.do_command(curses.ascii.ENQ)
    assert window.getyx() == (0, 3)
    textbox.do_command(curses.ascii.SO)
    assert window.getyx() == (1, 2)
    textbox.do_command(curses.ascii.DLE)
    assert window.getyx() == (0, 2)

    textbox.do_command(curses.ascii.EOT)
    assert window.contents()[0] == "ab   "
    textbox.do_command(curses.ascii.FF)
    assert window.refresh_count == 1

    window.move(1, 0)
    textbox.do_command(curses.ascii.SI)
    assert window.contents() == ["ab   ", "     ", "xy   "]
    assert textbox.do_command(curses.ascii.BEL) == 0


# 临时 PTY 中的真实 curses window 与 panel stack 工作流。
#
# window/panel C API 必须在已初始化终端中运行。本文件为每个案例创建 24×80 临时 PTY，
# 让隔离子进程通过 ``curses.wrapper`` 使用真实 ncurses，并从独立 pipe 返回 JSON。
# 它不接管用户终端、不读取输入、不 sleep；缺少 curses/terminfo 的平台会明确 skip。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.curses.newwin python.curses.window.getmaxyx
# polyglot-covers: python.curses.window.box python.curses.window.addstr
# polyglot-covers: python.curses.window.addnstr python.curses.window.inch
# polyglot-covers: python.curses.window.move python.curses.window.delch
# polyglot-covers: python.curses.window.insstr python.curses.window.derwin
# polyglot-covers: python.curses.window.nodelay python.curses.window.timeout
# polyglot-covers: python.curses.window.getch python.curses.window.noutrefresh
# polyglot-covers: python.curses.doupdate python.curses.has_colors
# polyglot-covers: python.curses.init_pair python.curses.color_pair
# polyglot-covers: python.curses.pair_number python.curses.A_CHARTEXT
# polyglot-covers: python.curses.panel.new_panel python.curses.panel.top_panel
# polyglot-covers: python.curses.panel.bottom_panel python.curses.panel.update_panels
# polyglot-covers: python.curses.panel.Panel.above python.curses.panel.Panel.below
# polyglot-covers: python.curses.panel.Panel.top python.curses.panel.Panel.bottom
# polyglot-covers: python.curses.panel.Panel.hide python.curses.panel.Panel.show
# polyglot-covers: python.curses.panel.Panel.hidden python.curses.panel.Panel.move
# polyglot-covers: python.curses.panel.Panel.replace python.curses.panel.Panel.window
# polyglot-covers: python.curses.panel.Panel.set_userptr python.curses.panel.Panel.userptr




_section_202_pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="PTY workflow requires POSIX",
)


def _run_in_temporary_pty(script):
    """运行 child，终端控制序列走 PTY，结构化结果走单独 pipe。"""

    master_fd, slave_fd = pty.openpty()
    result_read, result_write = os.pipe()
    fcntl.ioctl(
        slave_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", 24, 80, 0, 0),
    )
    environment = os.environ.copy()
    environment["TERM"] = "xterm"
    environment.pop("LINES", None)
    environment.pop("COLUMNS", None)
    process = subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(script), str(result_write)],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        pass_fds=(result_write,),
        close_fds=True,
        env=environment,
    )
    os.close(slave_fd)
    os.close(result_write)
    try:
        return_code = process.wait()
        chunks = []
        while True:
            chunk = os.read(result_read, 4096)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(result_read)
        os.close(master_fd)

    assert return_code == 0
    assert chunks, "child did not return a structured curses result"
    result = json.loads(b"".join(chunks).decode("utf-8"))
    if "unsupported" in result:
        pytest.skip(result["unsupported"])
    assert "error" not in result, result.get("error")
    return result["ok"]


@_section_202_pytestmark
def test_real_window_drawing_cursor_nonblocking_input_and_batched_refresh():
    """noutrefresh 只更新 virtual screen；一次 doupdate 合并实际终端刷新。"""

    result = _run_in_temporary_pty(
        """
        import curses
        import json
        import os
        import sys

        output_fd = int(sys.argv[1])

        def application(stdscr):
            screen_size = stdscr.getmaxyx()
            window = curses.newwin(4, 12, 0, 0)
            window.box()
            window.addstr(1, 1, "abc", curses.A_BOLD)
            window.move(1, 2)
            character = window.inch() & curses.A_CHARTEXT
            window.delch()
            window.insstr(1, 2, "B")

            window.nodelay(True)
            no_input = window.getch()
            window.timeout(0)
            child = window.derwin(1, 5, 2, 1)
            child.addnstr("hello", 4)
            window.noutrefresh()
            child.noutrefresh()
            curses.doupdate()

            color_pair = None
            if curses.has_colors():
                curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
                color_pair = curses.pair_number(curses.color_pair(1))
            return {
                "screen_size": screen_size,
                "window_size": window.getmaxyx(),
                "character": character,
                "no_input": no_input,
                "color_pair": color_pair,
            }

        try:
            payload = {"ok": curses.wrapper(application)}
        except (ImportError, curses.error) as exc:
            payload = {"unsupported": f"{type(exc).__name__}: {exc}"}
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
        os.write(output_fd, json.dumps(payload).encode("utf-8"))
        """
    )

    assert result["screen_size"] == [24, 80]
    assert result["window_size"] == [4, 12]
    assert result["character"] == ord("b")
    assert result["no_input"] == -1
    assert result["color_pair"] in (None, 1)


@_section_202_pytestmark
def test_real_panel_stack_reorders_hides_moves_replaces_and_keeps_user_data():
    """必须持有 Panel 引用；丢失最后引用会 GC 并把它从全局 panel stack 移除。"""

    result = _run_in_temporary_pty(
        """
        import curses
        import curses.panel
        import json
        import os
        import sys

        output_fd = int(sys.argv[1])

        def application(stdscr):
            first_window = curses.newwin(2, 6, 0, 0)
            second_window = curses.newwin(2, 6, 2, 2)
            first = curses.panel.new_panel(first_window)
            second = curses.panel.new_panel(second_window)
            initial = {
                "top_is_second": curses.panel.top_panel() is second,
                "bottom_is_first": curses.panel.bottom_panel() is first,
                "first_above_is_second": first.above() is second,
                "second_below_is_first": second.below() is first,
            }

            first.top()
            moved_to_top = curses.panel.top_panel() is first
            first.bottom()
            moved_to_bottom = curses.panel.bottom_panel() is first
            second.hide()
            hidden = second.hidden()
            second.show()
            shown = not second.hidden()
            second.move(4, 4)

            replacement = curses.newwin(2, 6, 4, 4)
            second.replace(replacement)
            marker = {"kind": "overlay"}
            second.set_userptr(marker)
            curses.panel.update_panels()
            curses.doupdate()
            return {
                **initial,
                "moved_to_top": moved_to_top,
                "moved_to_bottom": moved_to_bottom,
                "hidden": hidden,
                "shown": shown,
                "window_replaced": second.window() is replacement,
                "userptr_preserved": second.userptr() is marker,
            }

        try:
            payload = {"ok": curses.wrapper(application)}
        except (ImportError, curses.error) as exc:
            payload = {"unsupported": f"{type(exc).__name__}: {exc}"}
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
        os.write(output_fd, json.dumps(payload).encode("utf-8"))
        """
    )

    assert result == {
        "top_is_second": True,
        "bottom_is_first": True,
        "first_above_is_second": True,
        "second_below_is_first": True,
        "moved_to_top": True,
        "moved_to_bottom": True,
        "hidden": True,
        "shown": True,
        "window_replaced": True,
        "userptr_preserved": True,
    }
