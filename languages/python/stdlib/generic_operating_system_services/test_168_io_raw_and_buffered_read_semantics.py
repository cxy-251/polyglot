"""168｜custom ``RawIOBase``、single-call raw read 与 buffered fill/peek/read1。

raw read 允许一次 syscall 的 short result；buffered read 可多次读取 raw 以满足
requested size。``peek`` 不推进 logical position，且返回量可能多于请求值；
``read1`` 限制最多触发一次 raw read，适合在 buffer 之上实现协议 framing。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.io.RawIOBase.read python.io.RawIOBase.readall
# polyglot-covers: python.io.RawIOBase.readinto python.io.raw-short-read
# polyglot-covers: python.io.BufferedReader python.io.buffered-multiple-raw-reads
# polyglot-covers: python.io.BufferedReader.peek python.io.peek-position
# polyglot-covers: python.io.BufferedReader.read1 python.io.single-raw-read
# polyglot-covers: python.io.DEFAULT_BUFFER_SIZE python.io.binary-type-discipline

import io

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
