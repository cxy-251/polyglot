# polyglot-covers: r.tooling.system2-status-environment-and-working-directory

success <- system2(
    file.path(R.home("bin"), "Rscript"),
    c("--vanilla", "-e", shQuote("cat('ok')")),
    stdout = TRUE,
    stderr = TRUE
)
failure <- suppressWarnings(system2(
    file.path(R.home("bin"), "Rscript"),
    c("--vanilla", "-e", shQuote("quit(status = 7L)")),
    stdout = TRUE,
    stderr = TRUE
))

stopifnot(
    identical(success, "ok"),
    is.null(attr(success, "status", exact = TRUE)),
    identical(attr(failure, "status", exact = TRUE), 7L)
)

local({
    root <- tempfile("polyglot-r-child-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    expression <- "cat(Sys.getenv('POLYGLOT_VALUE'), normalizePath(getwd()), sep='|')"
    old_directory <- setwd(root)
    on.exit(setwd(old_directory), add = TRUE)
    output <- system2(
        file.path(R.home("bin"), "Rscript"),
        c("--vanilla", "-e", shQuote(expression)),
        stdout = TRUE,
        env = "POLYGLOT_VALUE=child"
    )
    stopifnot(
        identical(output, paste("child", normalizePath(root), sep = "|")),
        identical(Sys.getenv("POLYGLOT_VALUE", unset = ""), "")
    )
})

# system2 的零退出码不附 status；非零码作为属性返回。cwd 继承，env 可按 child 显式覆盖。
