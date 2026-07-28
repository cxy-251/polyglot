# polyglot-family: files_paths_and_streams
# polyglot-concept: streaming_buffering_and_backpressure
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_097_text_binary_and_memory_connections.R
#
# 共同问题：流怎样分块读取、缓冲和表达 backpressure。
# 对照观察：R connection 提供同步阻塞 I/O 和显式 chunk size；base API 没有异步 backpressure signal。

local({
    connection <- textConnection(c("alpha", "beta", "gamma"), open = "r")
    on.exit(close(connection), add = TRUE)
    first <- readLines(connection, n = 2L)
    second <- readLines(connection, n = 2L)
    exhausted <- readLines(connection, n = 1L)

    stopifnot(
        identical(first, c("alpha", "beta")),
        identical(second, "gamma"),
        identical(exhausted, character(0))
    )
})
