"""202｜临时 PTY 中的真实 curses window 与 panel stack 工作流。

window/panel C API 必须在已初始化终端中运行。本文件为每个案例创建 24×80 临时 PTY，
让隔离子进程通过 ``curses.wrapper`` 使用真实 ncurses，并从独立 pipe 返回 JSON。
它不接管用户终端、不读取输入、不 sleep；缺少 curses/terminfo 的平台会明确 skip。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import fcntl
import json
import os
import pty
import struct
import subprocess
import sys
import termios
import textwrap

import pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="PTY workflow requires POSIX")


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
