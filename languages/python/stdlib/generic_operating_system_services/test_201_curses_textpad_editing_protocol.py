"""201｜``curses.textpad`` rectangle、Textbox 编辑命令与 window protocol。

Textbox 只依赖 curses window 的光标、字符和行操作。本文件用确定性的内存 window
执行真实 Textbox 代码，覆盖 Emacs-like 控制键、insert mode、validator 和 gather，
同时避免初始化用户终端。fake 只模拟当前案例所需的 curses window 契约。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import curses
import curses.ascii
from curses.textpad import rectangle
from curses.textpad import Textbox


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
