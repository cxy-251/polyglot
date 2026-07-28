# polyglot-covers: r.tooling.options-environment-and-working-directory-cleanup

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
