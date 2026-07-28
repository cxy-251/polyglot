# polyglot-covers: r.tooling.connections-sinks-and-graphics-device-cleanup

local({
    output_file <- tempfile("polyglot-r-output-", fileext = ".txt")
    plot_file <- tempfile("polyglot-r-plot-", fileext = ".pdf")
    connection <- file(output_file, open = "wt")
    on.exit({
        try(close(connection), silent = TRUE)
        while (sink.number(type = "output") > 0L) sink(type = "output")
        while (!is.null(grDevices::dev.list())) grDevices::dev.off()
        unlink(c(output_file, plot_file))
    }, add = TRUE)

    sink(connection)
    cat("captured")
    sink(type = "output")
    close(connection)

    grDevices::pdf(plot_file)
    graphics::plot.new()
    grDevices::dev.off()

    stopifnot(
        identical(readLines(output_file, warn = FALSE), "captured"),
        file.exists(plot_file),
        is.null(grDevices::dev.list())
    )
})
