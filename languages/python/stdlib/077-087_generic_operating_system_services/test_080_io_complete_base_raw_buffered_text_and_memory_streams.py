"""080｜``io`` hierarchy、stream capability、context manager 与 line iteration。

I/O category 由 text、buffered binary、raw binary 三层组成；具体 stream 可只实现其中
一部分操作。caller 应先理解 readable/writable/seekable 契约，并处理
``UnsupportedOperation``，而不是假设所有 file-like objects 都像磁盘文件。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.io.IOBase python.io.RawIOBase
# polyglot-covers: python.io.BufferedIOBase python.io.TextIOBase
# polyglot-covers: python.io.stream-hierarchy python.io.stream-capabilities
# polyglot-covers: python.io.UnsupportedOperation python.io.unsupported-operation-inheritance
# polyglot-covers: python.io.readable python.io.writable python.io.seekable
# polyglot-covers: python.io.stream-context-manager python.io.closed-stream-error
# polyglot-covers: python.io.stream-iteration python.io.readlines
# polyglot-covers: python.io.writelines python.io.writelines-no-separator




import io
import pytest
import os
import builtins

def test_unsupported_operation_is_both_oserror_and_valueerror():
    """双重继承兼容旧捕获方式；精确处理时仍应捕获 io.UnsupportedOperation。"""

    error = io.UnsupportedOperation("seek")

    assert isinstance(error, OSError)
    assert isinstance(error, ValueError)


def test_iobase_defaults_describe_a_stream_with_no_optional_capabilities():
    """IOBase 只给 protocol skeleton；subclass 按需实现 seek/read/write。"""

    stream = io.IOBase()

    assert stream.readable() is False
    assert stream.writable() is False
    assert stream.seekable() is False
    assert stream.isatty() is False
    with pytest.raises(io.UnsupportedOperation):
        stream.seek(0)
    with pytest.raises(io.UnsupportedOperation):
        stream.fileno()


def test_context_manager_closes_stream_even_when_suite_raises():
    """close 可重复调用；关闭后的 I/O 一般以 ValueError 表示 lifecycle error。"""

    stream = io.BytesIO(b"payload")
    with pytest.raises(RuntimeError, match="body failed"):
        with stream as entered:
            assert entered is stream
            raise RuntimeError("body failed")

    assert stream.closed is True
    stream.close()
    with pytest.raises(ValueError):
        stream.read()


def test_stream_iteration_and_readlines_preserve_line_terminators():
    """iteration 逐行产出，不自动 strip；EOF 后再次迭代不重新 rewind。"""

    stream = io.StringIO("first\nsecond\nlast")

    assert list(stream) == ["first\n", "second\n", "last"]
    assert list(stream) == []

    stream.seek(0)
    assert stream.readlines() == ["first\n", "second\n", "last"]


def test_writelines_does_not_insert_any_line_separator():
    """参数名是 lines，但元素可以没有 newline；separator 完全由 caller 提供。"""

    stream = io.StringIO()
    assert stream.writelines(["a", "b\n", "c"]) is None

    assert stream.getvalue() == "ab\nc"


# custom ``RawIOBase``、single-call raw read 与 buffered fill/peek/read1。
#
# raw read 允许一次 syscall 的 short result；buffered read 可多次读取 raw 以满足
# requested size。``peek`` 不推进 logical position，且返回量可能多于请求值；
# ``read1`` 限制最多触发一次 raw read，适合在 buffer 之上实现协议 framing。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.io.RawIOBase.read python.io.RawIOBase.readall
# polyglot-covers: python.io.RawIOBase.readinto python.io.raw-short-read
# polyglot-covers: python.io.BufferedReader python.io.buffered-multiple-raw-reads
# polyglot-covers: python.io.BufferedReader.peek python.io.peek-position
# polyglot-covers: python.io.BufferedReader.read1 python.io.single-raw-read
# polyglot-covers: python.io.DEFAULT_BUFFER_SIZE python.io.binary-type-discipline


class ChunkedRaw(io.RawIOBase):
    """每次最多给两个 bytes，用于把 raw 与 buffered 调用次数显式化。"""

    def __init__(self, payload):
        self._payload = payload
        self._position = 0
        self.readinto_calls = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        self.readinto_calls += 1
        if self._position >= len(self._payload):
            return 0
        count = min(2, len(buffer), len(self._payload) - self._position)
        buffer[:count] = self._payload[self._position : self._position + count]
        self._position += count
        return count


def test_raw_positive_read_uses_one_readinto_but_readall_loops_to_eof():
    """short raw result 不是 EOF；只有 b''/readinto=0 表示 EOF。"""

    raw = ChunkedRaw(b"abcdef")

    assert raw.read(5) == b"ab"
    assert raw.readinto_calls == 1
    assert raw.readall() == b"cdef"
    assert raw.readinto_calls >= 4


def test_buffered_reader_combines_multiple_short_raw_reads():
    """非 interactive raw 上，read(size) 会尝试填满 size 或直到 EOF。"""

    raw = ChunkedRaw(b"abcdefgh")
    buffered = io.BufferedReader(raw, buffer_size=4)

    assert buffered.read(5) == b"abcde"
    assert raw.readinto_calls >= 3
    assert buffered.read() == b"fgh"


def test_peek_does_not_advance_and_may_return_more_than_requested():
    """只能依赖 prefix/非推进语义，不能断言 peek(1) 恰好返回一个 byte。"""

    buffered = io.BufferedReader(ChunkedRaw(b"abcdef"), buffer_size=4)
    preview = buffered.peek(1)

    assert preview.startswith(b"a")
    assert buffered.read(1) == b"a"


def test_read1_performs_at_most_one_raw_read_when_buffer_is_empty():
    """custom raw 每次最多给两个 bytes，所以 read1(10) 也只得到两个。"""

    raw = ChunkedRaw(b"abcdef")
    buffered = io.BufferedReader(raw, buffer_size=4)

    assert buffered.read1(10) == b"ab"
    assert raw.readinto_calls == 1

    assert io.DEFAULT_BUFFER_SIZE > 0


# ``BytesIO`` random access、readinto 与 zero-copy ``getbuffer`` view。
#
# ``getvalue`` 复制并忽略 cursor；``getbuffer`` 返回共享 writable view。共享 view
# 存活期间 buffer 不能 resize 或 close，这是常见 ``BufferError`` 来源。
# 预分配目标时，
# ``readinto`` 可避免为结果再创建 bytes object。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.io.BytesIO python.io.BytesIO.getvalue
# polyglot-covers: python.io.BytesIO.seek python.io.BytesIO.truncate
# polyglot-covers: python.io.BytesIO.readinto python.io.BytesIO.readinto1
# polyglot-covers: python.io.BytesIO.getbuffer python.io.zero-copy-buffer-view
# polyglot-covers: python.io.bytesio-view-mutation python.io.bytesio-view-resize-lock
# polyglot-covers: python.io.BufferError python.io.memoryview-release




def test_bytesio_cursor_overwrite_append_and_truncate_are_independent_of_getvalue():
    """构造后 cursor 在开头；write 默认 overwrite，seek(end) 后才 append。"""

    stream = io.BytesIO(b"abcdef")
    assert stream.tell() == 0
    assert stream.write(b"XY") == 2
    assert stream.getvalue() == b"XYcdef"

    stream.seek(0, io.SEEK_END)
    stream.write(b"!")
    assert stream.getvalue() == b"XYcdef!"

    stream.seek(3)
    assert stream.truncate() == 3
    assert stream.tell() == 3
    assert stream.getvalue() == b"XYc"


def test_readinto_and_readinto1_fill_existing_mutable_buffers():
    """返回 count 决定有效 prefix；目标 buffer 多余部分保持原值。"""

    stream = io.BytesIO(b"abcdef")
    first = bytearray(b"xxxx")
    second = bytearray(b"yyy")

    assert stream.readinto(first) == 4
    assert first == b"abcd"
    assert stream.readinto1(second) == 2
    assert second == b"efy"


def test_getbuffer_view_mutates_owner_and_temporarily_prevents_resize_or_close():
    """release view 后 owner 才能 resize/close；del view 也可释放 export。"""

    stream = io.BytesIO(b"abcdef")
    view = stream.getbuffer()
    view[2:4] = b"XY"

    assert stream.getvalue() == b"abXYef"
    stream.seek(0, io.SEEK_END)
    with pytest.raises(BufferError):
        stream.write(b"more")
    with pytest.raises(BufferError):
        stream.close()

    view.release()
    stream.seek(0, io.SEEK_END)
    assert stream.write(b"!") == 1
    stream.close()
    assert stream.closed is True


# ``FileIO`` raw ownership、BufferedWriter flush/detach 与 BufferedRandom。
#
# ``FileIO`` 每个 positive read/write 最多一次 syscall；``BufferedWriter`` 接受
# 全部 input 后可暂存在 userspace，直到 flush/close。``detach`` 转移底层 raw stream
# 所有权，原 buffer 随即不可用，caller 必须负责关闭返回对象。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.io.FileIO python.io.raw-file-io
# polyglot-covers: python.io.FileIO.mode python.io.FileIO.name
# polyglot-covers: python.io.FileIO.readinto python.io.fileio-fd-ownership
# polyglot-covers: python.io.BufferedWriter python.io.buffered-writer-flush
# polyglot-covers: python.io.BufferedIOBase.detach python.io.detached-buffer-unusable
# polyglot-covers: python.io.BufferedRandom python.io.buffered-random-read-write-seek
# polyglot-covers: python.io.BufferedRWPair python.io.buffered-rw-pair-separate-streams




def test_fileio_wraps_path_or_existing_fd_and_closefd_controls_ownership(tmp_path):
    """path mode 会拥有新 fd；整数 fd 可用 closefd=False 保留给 caller。"""

    path = tmp_path / "raw.bin"
    with io.FileIO(path, "w+") as raw:
        assert raw.mode == "rb+"
        assert raw.name == path
        assert os.get_inheritable(raw.fileno()) is False
        assert raw.write(b"abcdef") == 6
        raw.seek(0)
        target = bytearray(4)
        assert raw.readinto(target) == 4
        assert target == b"abcd"

    fd = os.open(path, os.O_RDONLY)
    try:
        with io.FileIO(fd, "r", closefd=False) as borrowed:
            assert borrowed.name == fd
            assert borrowed.read(2) == b"ab"
        assert os.fstat(fd).st_size == 6
    finally:
        os.close(fd)


def test_buffered_writer_holds_small_write_until_flush(tmp_path):
    """返回 input length 只表示 buffer 接受，不表示 kernel 已观察 bytes。"""

    path = tmp_path / "buffered.bin"
    raw = io.FileIO(path, "w")
    writer = io.BufferedWriter(raw, buffer_size=16)
    try:
        assert writer.write(b"small") == 5
        assert os.fstat(raw.fileno()).st_size == 0
        assert writer.flush() is None
        assert os.fstat(raw.fileno()).st_size == 5
    finally:
        writer.close()

    assert raw.closed is True
    assert path.read_bytes() == b"small"


def test_detach_returns_raw_and_leaves_buffer_permanently_unusable(tmp_path):
    """detach 前先 flush；返回的 raw 不会随旧 wrapper 自动 close。"""

    path = tmp_path / "detached.bin"
    writer = io.BufferedWriter(io.FileIO(path, "w"), buffer_size=8)
    writer.write(b"data")
    writer.flush()
    raw = writer.detach()
    try:
        assert raw.closed is False
        with pytest.raises(ValueError):
            writer.write(b"unusable")
        raw.write(b"-raw")
    finally:
        raw.close()

    assert path.read_bytes() == b"data-raw"


def test_buffered_random_synchronizes_reads_writes_and_seek(tmp_path):
    """同一 seekable raw 既读又写时用 BufferedRandom，不用同对象构造 RWPair。"""

    path = tmp_path / "random.bin"
    with io.BufferedRandom(io.FileIO(path, "w+"), buffer_size=4) as stream:
        stream.write(b"abcdef")
        stream.seek(2)
        assert stream.read(2) == b"cd"
        stream.seek(2)
        stream.write(b"XY")
        stream.seek(0)
        assert stream.read() == b"abXYef"


def test_buffered_rw_pair_uses_distinct_reader_and_writer(tmp_path):
    """RWPair 不同步同一个 raw；这里明确提供 input/output 两个 stream。"""

    source = tmp_path / "source.bin"
    target = tmp_path / "target.bin"
    source.write_bytes(b"input")
    reader = io.FileIO(source, "r")
    writer = io.FileIO(target, "w")
    pair = io.BufferedRWPair(reader, writer, 4)
    try:
        assert pair.read(3) == b"inp"
        assert pair.write(b"out") == 3
        pair.flush()
    finally:
        pair.close()

    assert target.read_bytes() == b"out"


# ``TextIOWrapper`` encoding/errors/newlines、opaque tell cookie 与 detach。
#
# text stream 的 position 是 decoder state cookie，不应当成 byte offset 运算。newline
# 参数同时控制 read recognition/translation 与 write translation；encoding 应显式给出，
# 避免 locale-dependent defaults。detach 后 wrapper 不可用，binary buffer 归 caller。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.io.TextIOWrapper python.io.text-binary-layering
# polyglot-covers: python.io.text-encoding python.io.text-errors
# polyglot-covers: python.io.universal-newlines python.io.TextIOBase.newlines
# polyglot-covers: python.io.text-write-newline-translation
# polyglot-covers: python.io.text-tell-cookie python.io.text-seek-cookie
# polyglot-covers: python.io.TextIOWrapper.detach python.io.text-detach-ownership
# polyglot-covers: python.io.TextIOWrapper.reconfigure python.io.reconfigure-read-limit
# polyglot-covers: python.io.line-buffering python.io.write-through




def test_universal_newline_read_normalizes_three_terminators_and_records_them():
    """newline=None 把 CR/LF/CRLF 都返回为 LF；newlines 记录已观察类型。"""

    binary = io.BytesIO(b"a\r\nb\rc\n")
    text = io.TextIOWrapper(binary, encoding="ascii", newline=None)

    assert text.read() == "a\nb\nc\n"
    assert set(text.newlines) == {"\r", "\n", "\r\n"}


def test_empty_newline_recognizes_all_terminators_but_returns_them_untranslated():
    """newline='' 常用于 parser 必须保留原始行尾的场景。"""

    text = io.TextIOWrapper(
        io.BytesIO(b"a\r\nb\rc\n"),
        encoding="ascii",
        newline="",
    )

    assert text.readlines() == ["a\r\n", "b\r", "c\n"]


def test_write_newline_translation_and_explicit_error_policy():
    """newline='\r\n' 转换输入 LF；errors='backslashreplace' 避免静默丢字符。"""

    binary = io.BytesIO()
    text = io.TextIOWrapper(
        binary,
        encoding="ascii",
        errors="backslashreplace",
        newline="\r\n",
    )
    text.write("café\n")
    text.flush()

    assert binary.getvalue() == b"caf\\xe9\r\n"
    assert text.encoding == "ascii"
    assert text.errors == "backslashreplace"


def test_text_tell_value_is_only_reused_as_an_opaque_seek_cookie():
    """multibyte decoder 可预读 binary data；只保存并传回 cookie，不自行加减。"""

    text = io.TextIOWrapper(io.BytesIO("甲乙丙".encode("utf-8")), encoding="utf-8")
    assert text.read(1) == "甲"
    cookie = text.tell()
    assert text.read(1) == "乙"

    assert text.seek(cookie) == cookie
    assert text.read(1) == "乙"
    with pytest.raises(io.UnsupportedOperation):
        text.seek(1, io.SEEK_CUR)


def test_detach_transfers_binary_buffer_and_invalidates_text_wrapper():
    """flush 后 detach，避免 bytes 留在 wrapper；返回 buffer 由 caller close。"""

    binary = io.BytesIO()
    text = io.TextIOWrapper(binary, encoding="utf-8")
    text.write("中文")
    text.flush()
    detached = text.detach()
    try:
        assert detached.getvalue() == "中文".encode("utf-8")
        with pytest.raises(ValueError):
            text.write("unusable")
    finally:
        detached.close()


def test_reconfigure_after_write_flushes_but_after_read_cannot_change_encoding():
    """write 后允许换 encoding；首次 read 后 decoder state 阻止变更。"""

    binary = io.BytesIO()
    writer = io.TextIOWrapper(binary, encoding="utf-8")
    writer.write("é")
    writer.reconfigure(encoding="utf-16-le", write_through=True)
    writer.write("甲")
    writer.flush()
    assert binary.getvalue() == "é".encode("utf-8") + "甲".encode("utf-16-le")
    assert writer.write_through is True

    reader = io.TextIOWrapper(io.BytesIO(b"abc"), encoding="ascii")
    assert reader.read(1) == "a"
    with pytest.raises(io.UnsupportedOperation):
        reader.reconfigure(encoding="utf-8")


def test_line_buffering_flushes_when_write_contains_newline():
    """line_buffering 检测 newline/CR；没有换行的 write 不保证立即下沉。"""

    binary = io.BytesIO()
    text = io.TextIOWrapper(binary, encoding="ascii", line_buffering=True)
    text.write("line\n")

    assert text.line_buffering is True
    assert binary.getvalue() == b"line\n"


# ``StringIO``、high-level aliases、``open_code`` 与 Python 3.10 encoding helper。
#
# StringIO 是 character stream，不执行 codec；构造后的 cursor 位于开头，首次 write
# 会 overwrite 而非 append。``open_code`` 用 binary mode 表达“把文件当可执行代码”
# 的意图；公开 API 接受 optional encoding 时可用 ``text_encoding`` 标出 locale choice。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.io.StringIO python.io.StringIO.getvalue
# polyglot-covers: python.io.stringio-initial-position python.io.stringio-overwrite
# polyglot-covers: python.io.stringio-newline-translation
# polyglot-covers: python.io.open python.io.open-alias
# polyglot-covers: python.io.open-code python.io.executable-code-binary-open
# polyglot-covers: python.io.text-encoding-helper python.io.EncodingWarning
# polyglot-covers: python.io.BlockingIOError python.io.text-binary-type-error




def test_stringio_initial_cursor_overwrites_and_getvalue_ignores_position():
    """若要 append，应显式 seek(SEEK_END)；getvalue 不移动当前 cursor。"""

    stream = io.StringIO("abcdef")
    assert stream.tell() == 0
    assert stream.write("XY") == 2
    before = stream.tell()

    assert stream.getvalue() == "XYcdef"
    assert stream.tell() == before

    stream.seek(0, io.SEEK_END)
    stream.write("!")
    assert stream.getvalue() == "XYcdef!"


def test_stringio_can_translate_written_newlines_without_using_an_encoding():
    """newline 处理属于 text layer；StringIO 始终存 str，不生成 bytes。"""

    stream = io.StringIO(newline="\r\n")
    stream.write("a\nb")

    assert stream.getvalue() == "a\r\nb"


def test_io_open_alias_and_open_code_binary_contract(tmp_path):
    """open_code 需要 absolute str path，并返回可 seek 的 binary stream。"""

    path = tmp_path / "module.py"
    path.write_text("answer = 42\n", encoding="utf-8")

    assert io.open is builtins.open
    with io.open_code(str(path.resolve())) as stream:
        assert stream.read() == b"answer = 42\n"
        assert stream.mode == "rb"


def test_text_encoding_marks_explicit_or_locale_choice_for_api_authors():
    """warn_default_encoding flag 开启时，None 路径还会在 caller 位置发 warning。"""

    assert io.text_encoding("utf-8") == "utf-8"
    assert io.text_encoding(None) == "locale"
    assert issubclass(EncodingWarning, Warning)


def test_text_and_binary_streams_reject_cross_category_values():
    """codec boundary 不能靠隐式转换；caller 必须明确 encode/decode。"""

    with pytest.raises(TypeError):
        io.BytesIO().write("text")
    with pytest.raises(TypeError):
        io.StringIO().write(b"bytes")

    assert io.BlockingIOError is BlockingIOError
