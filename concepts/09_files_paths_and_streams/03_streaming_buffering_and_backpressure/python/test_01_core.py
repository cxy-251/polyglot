"""流、缓冲与背压。

共同问题：文本与字节流如何区分；游标和刷新何时生效；生产者如何知道消费者暂时跟不上；
同步流与事件驱动流是否采用同一种背压协议。
"""

# polyglot-family: files_paths_and_streams
# polyglot-concept: streaming_buffering_and_backpressure
# polyglot-related: languages/python/stdlib/077-087_generic_operating_system_services/
# polyglot-related+: test_080_io_complete_base_raw_buffered_text_and_memory_streams.py

import io


def test_text_and_binary_streams_keep_distinct_value_types():
    text = io.StringIO()
    binary = io.BytesIO()

    assert text.write("你好") == 2
    assert binary.write("你好".encode()) == 6
    assert text.getvalue() == "你好"
    assert binary.getvalue() == "你好".encode()


def test_seek_changes_the_next_read_position():
    stream = io.BytesIO(b"abcdef")

    stream.seek(2)

    assert stream.read(2) == b"cd"
    assert stream.tell() == 4


def test_buffered_writer_requires_flush_to_reach_raw_stream():
    raw = io.BytesIO()
    buffered = io.BufferedWriter(raw)
    buffered.write(b"value")

    assert raw.getvalue() == b""
    buffered.flush()
    assert raw.getvalue() == b"value"


def test_synchronous_write_returns_progress_instead_of_a_drain_event():
    stream = io.BytesIO()

    assert stream.write(b"abc") == 3

    # Python 同步 io 通过阻塞、短写或异常表达进度；它没有 Node.js Writable 的 drain 协议。
