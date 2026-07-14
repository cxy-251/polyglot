"""199｜``curses.wrapper`` 的终端生命周期与 process-global settings。

wrapper 负责 initscr、noecho、cbreak、keypad 和最终恢复；即使 callback 抛异常也会执行
清理。测试用 fake 函数审计调用顺序，不改变真实终端。ESC delay 与 tab size 是 curses
进程级状态，案例在 finally 中恢复，避免影响同一 pytest process 的其他测试。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
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
