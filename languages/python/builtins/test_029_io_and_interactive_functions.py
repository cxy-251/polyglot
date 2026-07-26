"""029｜``open`` / ``print`` / ``input`` / ``breakpoint`` / ``help`` 示例。

open 连接路径与 text/binary stream；print/input 使用标准流；breakpoint/help 委托
可替换的运行时钩子。本文件只操作 pytest 临时目录和内存流，调试/帮助入口也会
替换为记录器，不进入真实交互环境。

内容基于 Python 3.10 Built-in Functions 和 io 文档。更完整的 pathlib、io、
文件格式工作流留给标准库主题。
"""

# polyglot-covers: python.builtin.open python.open.mode python.open.encoding
# polyglot-covers: python.open.errors python.open.newline python.open.context-manager
# polyglot-covers: python.file.read python.file.write python.file.iteration
# polyglot-covers: python.file.seek python.file.tell python.file.truncate
# polyglot-covers: python.builtin.print python.builtin.input
# polyglot-covers: python.builtin.breakpoint python.builtin.help
# polyglot-covers: python.runtime.standard-streams python.runtime.interactive-hooks

import io
import pydoc
import sys

import pytest


def test_open_text_file_with_explicit_encoding_and_context_manager(tmp_path):
    """text mode 读写 str；with 离开时即使以后不用句柄也会可靠关闭。"""

    path = tmp_path / "notes.txt"

    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        assert handle.writable()
        assert not handle.readable()
        assert handle.closed is False
        written = handle.write("café\n")
        assert written == 5

    assert handle.closed is True

    with open(path, encoding="utf-8") as handle:
        # 未写 mode 时默认是 "r" 文本读取模式。
        assert handle.readable()
        assert not handle.writable()
        assert handle.read() == "café\n"

    # 外部文本协议应显式写 encoding；依赖平台 locale 会让同一仓库在不同机器表现不同。


def test_closed_file_rejects_later_io_operations(tmp_path):
    """context manager 关闭的是资源，不只是把 Python 变量移出作用域。"""

    path = tmp_path / "closed.txt"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("done")

    assert handle.closed

    with pytest.raises(ValueError, match="closed file"):
        handle.write("too late")

    # 若函数返回 file object，调用方必须知道谁负责 close；更简单的 API 常返回已读数据。


def test_read_readline_and_iteration_advance_the_same_stream_position(tmp_path):
    """所有读取接口共享当前位置；seek(0) 才会回到开头。"""

    path = tmp_path / "lines.txt"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("first\nsecond\nthird\n")

    with open(path, "r", encoding="utf-8", newline="") as handle:
        assert handle.read(5) == "first"
        assert handle.readline() == "\n"
        assert next(handle) == "second\n"
        assert list(handle) == ["third\n"]

        handle.seek(0)
        assert handle.readlines() == ["first\n", "second\n", "third\n"]

    # file iterator 是句柄本身当前位置上的一次性遍历，不是每次 for 都自动从头开始。


def test_binary_mode_uses_bytes_and_deterministic_seek_offsets(tmp_path):
    """binary stream 不做编码/换行转换，seek/tell 以字节位置工作。"""

    path = tmp_path / "packet.bin"

    with open(path, "wb") as handle:
        assert handle.write(b"abcdef") == 6
        assert handle.tell() == 6

    with open(path, "r+b") as handle:
        assert handle.seek(2) == 2
        assert handle.write(b"XY") == 2
        assert handle.tell() == 4
        assert handle.truncate() == 4

    with open(path, "rb") as handle:
        assert handle.read() == b"abXY"


def test_text_and_binary_streams_reject_crossed_value_types(tmp_path):
    """text stream 只写 str，binary stream 只写 bytes-like，不做隐式 encode/decode。"""

    text_path = tmp_path / "text.txt"
    with open(text_path, "w", encoding="utf-8") as text_file:
        with pytest.raises(TypeError):
            text_file.write(b"bytes")

    binary_path = tmp_path / "binary.bin"
    with open(binary_path, "wb") as binary_file:
        with pytest.raises(TypeError):
            binary_file.write("text")

        assert binary_file.write(bytearray(b"ok")) == 2


def test_write_mode_truncates_existing_file_immediately(tmp_path):
    """``w`` 在成功打开时就截断已有文件，不必等第一次 write。"""

    path = tmp_path / "truncate.txt"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("valuable data")

    with open(path, "w", encoding="utf-8"):
        pass

    with open(path, "r", encoding="utf-8") as handle:
        assert handle.read() == ""

    # 需要原子替换时通常先写同目录临时文件并 os.replace，而不是直接 w 覆盖目标。


def test_read_write_mode_updates_without_initial_truncation(tmp_path):
    """``r+`` 要求文件存在，并允许从当前位置读写而不在打开时清空。"""

    path = tmp_path / "update.txt"
    with open(path, "w", encoding="ascii") as handle:
        handle.write("abc")

    with open(path, "r+", encoding="ascii") as handle:
        assert handle.read(1) == "a"
        # text stream 可能预读缓冲；切换读写方向前显式 seek 同步逻辑位置。
        assert handle.seek(1) == 1
        assert handle.write("X") == 1
        handle.seek(0)
        assert handle.read() == "aXc"

    with pytest.raises(FileNotFoundError):
        open(tmp_path / "missing.txt", "r+", encoding="utf-8")


def test_append_mode_writes_at_end_even_after_seek(tmp_path):
    """``a``/``a+`` 的写入定位到文件末尾；seek 主要影响读取位置。"""

    path = tmp_path / "append.txt"
    with open(path, "w", encoding="ascii") as handle:
        handle.write("first")

    with open(path, "a+", encoding="ascii") as handle:
        handle.seek(0)
        assert handle.read() == "first"
        handle.seek(0)
        handle.write("-second")
        handle.seek(0)
        assert handle.read() == "first-second"

    # append 适合日志式追加；需要原位覆盖字段时使用 r+ 并精确管理偏移。


def test_exclusive_create_mode_refuses_to_overwrite_existing_path(tmp_path):
    """``x`` 只创建新文件，路径已存在就抛 FileExistsError。"""

    path = tmp_path / "exclusive.txt"

    with open(path, "x", encoding="utf-8") as handle:
        handle.write("created once")

    with pytest.raises(FileExistsError):
        open(path, "x", encoding="utf-8")

    with open(path, "r", encoding="utf-8") as handle:
        assert handle.read() == "created once"


def test_text_newline_reading_can_translate_or_preserve_line_endings(tmp_path):
    """newline=None 启用通用换行转换；newline='' 识别但保留原终止符。"""

    path = tmp_path / "mixed-newlines.txt"
    with open(path, "wb") as handle:
        handle.write(b"first\r\nsecond\rthird\n")

    with open(path, "r", encoding="ascii", newline=None) as handle:
        assert handle.read() == "first\nsecond\nthird\n"

    with open(path, "r", encoding="ascii", newline="") as handle:
        assert handle.read() == "first\r\nsecond\rthird\n"


def test_explicit_output_newline_controls_text_translation(tmp_path):
    """写入时可把每个 ``\n`` 明确转换为协议规定的终止符。"""

    path = tmp_path / "crlf.txt"
    with open(path, "w", encoding="ascii", newline="\r\n") as handle:
        handle.write("first\nsecond\n")

    with open(path, "rb") as handle:
        assert handle.read() == b"first\r\nsecond\r\n"

    # 对 CSV 等自带换行管理的库，应按该库约定选择 newline，避免重复转换。


def test_text_encoding_error_policy_is_explicit_at_open_boundary(tmp_path):
    """严格模式暴露不可编码文本；replace 会有意丢失原字符。"""

    strict_path = tmp_path / "strict-ascii.txt"
    with open(strict_path, "w", encoding="ascii") as handle:
        with pytest.raises(UnicodeEncodeError):
            handle.write("café")

    replacement_path = tmp_path / "replace-ascii.txt"
    with open(replacement_path, "w", encoding="ascii", errors="replace") as handle:
        assert handle.write("café") == 4

    with open(replacement_path, "rb") as handle:
        assert handle.read() == b"caf?"

    # errors="ignore"/"replace" 是数据损失决策，不应作为未知乱码的默认修复方式。


def test_print_converts_objects_and_controls_separator_end_and_destination():
    """print 对每个对象调用 str，并把格式化结果写入给定 text stream。"""

    output = io.StringIO()

    returned = print("items", 3, None, sep=" | ", end="!", file=output)

    assert returned is None
    assert output.getvalue() == "items | 3 | None!"

    # print 输出供人阅读，不是稳定序列化协议；机器数据应使用 json/csv 等明确格式。


def test_print_flush_true_delegates_to_stream_flush():
    """flush=True 在完成 write 后调用目标流的 flush。"""

    class RecordingStream(io.StringIO):
        def __init__(self):
            super().__init__()
            self.flush_count = 0

        def flush(self):
            self.flush_count += 1
            super().flush()

    output = RecordingStream()

    print("ready", file=output, flush=True)

    assert output.getvalue() == "ready\n"
    assert output.flush_count == 1


def test_input_writes_prompt_reads_one_line_and_only_removes_line_ending(monkeypatch):
    """input 不做 strip：前后普通空格仍属于返回文本。"""

    fake_input = io.StringIO("  Alice  \n42\n")
    fake_output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", fake_input)
    monkeypatch.setattr(sys, "stdout", fake_output)

    name = input("Name: ")
    number_text = input()

    assert name == "  Alice  "
    assert number_text == "42"
    assert type(number_text) is str
    assert int(number_text) == 42
    assert fake_output.getvalue() == "Name: "

    # 是否 strip、是否允许空值、如何解析数字都应由输入校验层显式决定。


def test_input_raises_eoferror_when_no_line_is_available(monkeypatch):
    """EOF 与用户输入空行不同：前者抛异常，后者返回空字符串。"""

    monkeypatch.setattr(sys, "stdin", io.StringIO("\n"))
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    assert input() == ""

    with pytest.raises(EOFError):
        input()


def test_breakpoint_delegates_arguments_and_return_to_sys_breakpointhook(monkeypatch):
    """替换 breakpointhook 可让库/测试控制调试行为而不进入默认 pdb。"""

    calls = []

    def fake_hook(*args, **kwargs):
        calls.append((args, kwargs))
        return "continued"

    monkeypatch.setattr(sys, "breakpointhook", fake_hook)

    returned = breakpoint("reason", step=True)

    assert returned == "continued"
    assert calls == [(('reason',), {"step": True})]

    # 默认 hook 通常进入 pdb；自动化路径必须替换 hook 或按部署策略禁用 breakpoint。


def test_help_delegates_to_pydoc_and_can_be_replaced_for_automation(monkeypatch):
    """help 是 site 提供的交互入口，调用时把主题交给 pydoc.help。"""

    calls = []

    def fake_help(topic=None):
        calls.append(topic)
        return "documented"

    monkeypatch.setattr(pydoc, "help", fake_help)

    returned = help(str.upper)

    assert returned == "documented"
    assert calls == [str.upper]

    # 无参数 help 会进入交互帮助；自动化文档提取应直接使用 pydoc/inspect 的明确 API。
