# polyglot-covers: r.standard-library.noninteractive-graphics-device-lifecycle

local({
    root <- tempfile("polyglot-r-stdlib-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    path <- file.path(root, "plot.pdf")
    grDevices::pdf(path)
    device <- grDevices::dev.cur()
    closed <- FALSE
    on.exit(if (!closed) grDevices::dev.off(device), add = TRUE)
    graphics::plot(1:3, 1:3, type = "b")
    grDevices::dev.off(device)
    closed <- TRUE
    header <- readBin(path, raw(), n = 4L)

    stopifnot(
        identical(names(device), "pdf"),
        identical(rawToChar(header), "%PDF"),
        file.info(path)$size > 4,
        is.logical(capabilities("cairo"))
    )
})

# 非交互图形写入显式 device；关闭 device 才完成文件，cairo 等后端只做能力检测。
