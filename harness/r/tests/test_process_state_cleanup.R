# Harness 验证课程示例采用结构化 cleanup 恢复进程级状态。
local({
    original_option <- getOption("polyglot.option")
    original_environment <- Sys.getenv("POLYGLOT_R_STATE", unset = NA_character_)
    original_directory <- getwd()

    on.exit({
        options(polyglot.option = original_option)
        if (is.na(original_environment)) {
            Sys.unsetenv("POLYGLOT_R_STATE")
        } else {
            Sys.setenv(POLYGLOT_R_STATE = original_environment)
        }
        setwd(original_directory)
    }, add = TRUE)

    temporary_directory <- tempfile("polyglot-r-state-")
    stopifnot(dir.create(temporary_directory))
    on.exit(unlink(temporary_directory, recursive = TRUE), add = TRUE)

    options(polyglot.option = "temporary")
    Sys.setenv(POLYGLOT_R_STATE = "temporary")
    setwd(temporary_directory)
    stopifnot(
        identical(getOption("polyglot.option"), "temporary"),
        identical(Sys.getenv("POLYGLOT_R_STATE"), "temporary"),
        identical(getwd(), normalizePath(temporary_directory))
    )
})

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
