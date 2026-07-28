# polyglot-covers: r.standard-library.text-binary-and-memory-connections

local({
    text_connection <- textConnection("captured", open = "w", local = TRUE)
    on.exit(close(text_connection), add = TRUE)
    writeLines(c("alpha", "beta"), text_connection)

    raw_connection <- rawConnection(raw(), open = "w+b")
    on.exit(close(raw_connection), add = TRUE)
    writeBin(c(1L, 256L), raw_connection, size = 4L, endian = "little")
    seek(raw_connection, where = 0L)
    decoded <- readBin(raw_connection, integer(), n = 2L, size = 4L, endian = "little")

    stopifnot(
        identical(captured, c("alpha", "beta")),
        identical(decoded, c(1L, 256L)),
        isOpen(text_connection),
        isOpen(raw_connection)
    )
})
