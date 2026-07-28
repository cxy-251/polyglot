# polyglot-covers: r.standard-library.stats-compiler-tools-utils-and-graphics

local({
    root <- tempfile("polyglot-r-stdlib-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)

    model <- stats::lm(mpg ~ wt, data = datasets::mtcars)
    compiled <- compiler::cmpfun(function(x) x + 1L)
    path <- file.path(root, "plot.pdf")
    grDevices::pdf(path)
    on.exit(grDevices::dev.off(), add = TRUE)
    graphics::plot(1:3, 1:3)

    stopifnot(
        length(stats::coef(model)) == 2L,
        identical(compiled(1L), 2L),
        grepl("^[[:xdigit:]]{32}$", unname(tools::md5sum(path))),
        grepl("R version", utils::capture.output(sessionInfo())[1L], fixed = TRUE)
    )
})
