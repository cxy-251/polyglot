# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_097_text_binary_and_memory_connections.R
#
# 共同问题：二进制缓冲区怎样读写整数，字节序如何指定。
# 对照观察：R 以 raw vector/connection 表达缓冲区；`readBin`/`writeBin` 显式指定 size 与 endian。

local({
    connection <- rawConnection(raw(), open = "w+b")
    on.exit(close(connection), add = TRUE)
    writeBin(c(1L, 256L), connection, size = 4L, endian = "little")
    bytes <- rawConnectionValue(connection)
    seek(connection, 0L)
    values <- readBin(connection, integer(), n = 2L, size = 4L, endian = "little")

    stopifnot(length(bytes) == 8L, identical(values, c(1L, 256L)))
})
