# polyglot-covers: r.tooling.test-installed-package-offline

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-tests-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root, install_tests = TRUE)
    old_library <- Sys.getenv("R_LIBS_USER", unset = NA_character_)
    on.exit({
        if (is.na(old_library)) {
            Sys.unsetenv("R_LIBS_USER")
        } else {
            Sys.setenv(R_LIBS_USER = old_library)
        }
    }, add = TRUE)
    Sys.setenv(R_LIBS_USER = installed$library)

    result <- suppressMessages(
        tools::testInstalledPackage(
            "polyglotrfixture",
            lib.loc = installed$library,
            outDir = root,
            types = "tests"
        )
    )

    stopifnot(
        identical(result, 0L),
        file.exists(file.path(root, "polyglotrfixture-tests", "basic.Rout"))
    )
})
