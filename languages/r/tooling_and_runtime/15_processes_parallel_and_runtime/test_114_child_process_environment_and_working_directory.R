# polyglot-covers: r.tooling.child-process-environment-and-working-directory

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
