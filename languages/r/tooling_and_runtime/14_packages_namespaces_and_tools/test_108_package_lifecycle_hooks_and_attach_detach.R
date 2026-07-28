# polyglot-covers: r.tooling.package-lifecycle-hooks-and-attach-detach

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root)
    old_paths <- .libPaths()
    on.exit(.libPaths(old_paths), add = TRUE)
    .libPaths(c(installed$library, old_paths))

    startup <- capture.output(
        suppressPackageStartupMessages(library("polyglotrfixture", character.only = TRUE)),
        type = "message"
    )
    on.exit(detach("package:polyglotrfixture", unload = TRUE, character.only = TRUE), add = TRUE)

    stopifnot(
        "package:polyglotrfixture" %in% search(),
        identical(double_value(4), 8),
        identical(startup, character(0))
    )
})
