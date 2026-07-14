"""279｜``StreamReader`` buffer、EOF、精确读取和 separator limit。

read(n>0) 有至少一个 byte 即可返回，并不保证填满；readexactly 才要求指定长度。
readuntil 成功时包含 separator，超过 limit 时数据仍留在 buffer；EOF 前数据不足则用
IncompleteReadError.partial 暴露残片。案例直接 feed protocol 数据以消除真实 I/O 时序。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.StreamReader
# polyglot-covers: python.asyncio.StreamReader.read
# polyglot-covers: python.asyncio.StreamReader.read-zero
# polyglot-covers: python.asyncio.StreamReader.read-until-eof
# polyglot-covers: python.asyncio.StreamReader.readline
# polyglot-covers: python.asyncio.StreamReader.readline-partial-eof
# polyglot-covers: python.asyncio.StreamReader.readexactly
# polyglot-covers: python.asyncio.StreamReader.readuntil
# polyglot-covers: python.asyncio.StreamReader.at_eof
# polyglot-covers: python.asyncio.StreamReader-async-iteration
# polyglot-covers: python.asyncio.StreamReader-limit
# polyglot-covers: python.asyncio.IncompleteReadError
# polyglot-covers: python.asyncio.IncompleteReadError.partial
# polyglot-covers: python.asyncio.IncompleteReadError.expected
# polyglot-covers: python.asyncio.LimitOverrunError
# polyglot-covers: python.asyncio.LimitOverrunError.consumed
# polyglot-covers: python.asyncio.readuntil-limit-data-retained
# polyglot-covers: python.asyncio.readuntil-eof-buffer-reset

import asyncio

import pytest


def test_read_readline_and_eof_consume_buffer_with_distinct_guarantees():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"abcdef\nlast")

        assert await reader.read(0) == b""
        assert await reader.read(3) == b"abc"
        assert await reader.readline() == b"def\n"
        assert reader.at_eof() is False

        reader.feed_eof()
        assert await reader.readline() == b"last"
        assert await reader.read() == b""
        assert reader.at_eof() is True

    asyncio.run(scenario())


def test_readexactly_reports_partial_bytes_and_expected_count_at_eof():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"abc")
        reader.feed_eof()

        with pytest.raises(asyncio.IncompleteReadError) as raised:
            await reader.readexactly(5)

        assert isinstance(raised.value, EOFError)
        assert raised.value.partial == b"abc"
        assert raised.value.expected == 5
        assert reader.at_eof() is True

    asyncio.run(scenario())


def test_readuntil_limit_error_retains_data_for_a_different_recovery_read():
    async def scenario():
        reader = asyncio.StreamReader(limit=4)
        reader.feed_data(b"abcdef\nrest")
        reader.feed_eof()

        with pytest.raises(asyncio.LimitOverrunError) as raised:
            await reader.readuntil(b"\n")
        assert raised.value.consumed == 6

        # LimitOverrunError 不消费 buffer；caller 可丢弃 consumed bytes 或改用 read。
        assert await reader.read(7) == b"abcdef\n"
        assert await reader.read() == b"rest"

    asyncio.run(scenario())


def test_readuntil_eof_reports_partial_separator_and_resets_buffer():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"header\r")
        reader.feed_eof()

        with pytest.raises(asyncio.IncompleteReadError) as raised:
            await reader.readuntil(b"\r\n")
        assert raised.value.partial == b"header\r"
        assert raised.value.expected is None
        assert await reader.read() == b""

    asyncio.run(scenario())


def test_stream_reader_async_iteration_yields_lines_until_eof():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"first\nsecond\npartial")
        reader.feed_eof()

        return [line async for line in reader]

    assert asyncio.run(scenario()) == [b"first\n", b"second\n", b"partial"]
