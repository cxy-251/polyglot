# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/r/tooling_and_runtime/16_native_interface_and_unsafe_boundaries/
# polyglot-related+: test_123_dot_call_sexp_types_and_allocations.R
#
# 共同问题：typed view 的对齐和底层缓冲区生命周期如何约束。
# 对照观察：base R raw vector 没有可写 typed view/alignment API；`readBin` 从任意字节偏移解码副本。

local({
    bytes <- as.raw(c(0xff, 0x01, 0x00, 0x00, 0x00))
    connection <- rawConnection(bytes, open = "rb")
    on.exit(close(connection), add = TRUE)
    seek(connection, 1L)
    value <- readBin(connection, integer(), n = 1L, size = 4L, endian = "little")

    stopifnot(
        identical(value, 1L),
        identical(typeof(bytes), "raw"),
        identical(length(bytes), 5L)
    )
})
