# polyglot-covers: r.tooling.library-trees-lazy-loading-and-package-cache

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root)
    package_path <- file.path(installed$library, "polyglotrfixture")

    stopifnot(
        dir.exists(package_path),
        file.exists(file.path(package_path, "R", "polyglotrfixture.rdb")),
        file.exists(file.path(package_path, "R", "polyglotrfixture.rdx")),
        "polyglotrfixture" %in% rownames(installed.packages(lib.loc = installed$library)),
        identical(find.package("polyglotrfixture", lib.loc = installed$library), package_path)
    )
})
