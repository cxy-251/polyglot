# polyglot-covers: r.tooling.noninteractive-graphics-and-runtime-capabilities

local({
    root <- tempfile("polyglot-r-graphics-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    path <- file.path(root, "plot.pdf")
    grDevices::pdf(path, width = 4, height = 3)
    on.exit(grDevices::dev.off(), add = TRUE)
    graphics::plot(1:3, type = "l")

    stopifnot(
        !interactive(),
        identical(names(dev.cur()), "pdf"),
        is.logical(capabilities("cairo")),
        file.exists(path)
    )
})
