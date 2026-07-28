polyglot_package_source <- function() {
    normalizePath(
        file.path("languages", "r", "package_fixture", "polyglotrfixture"),
        mustWork = TRUE
    )
}

copy_polyglot_package <- function(root) {
    copied <- file.copy(polyglot_package_source(), root, recursive = TRUE)
    stopifnot(copied)
    file.path(root, "polyglotrfixture")
}

run_r_command <- function(arguments, working_directory, environment = character()) {
    old_directory <- setwd(working_directory)
    on.exit(setwd(old_directory), add = TRUE)
    output <- system2(
        file.path(R.home("bin"), "R"),
        arguments,
        stdout = TRUE,
        stderr = TRUE,
        env = environment
    )
    list(status = attr(output, "status", exact = TRUE) %||% 0L, output = output)
}

`%||%` <- function(value, fallback) {
    if (is.null(value)) fallback else value
}

build_polyglot_package <- function(root) {
    source <- copy_polyglot_package(root)
    result <- run_r_command(
        c("CMD", "build", "--no-manual", shQuote(source)),
        root
    )
    if (!identical(result$status, 0L)) {
        stop(paste(result$output, collapse = "\n"))
    }
    tarballs <- list.files(root, "^polyglotrfixture_.*[.]tar[.]gz$", full.names = TRUE)
    stopifnot(length(tarballs) == 1L)
    tarballs[[1L]]
}

install_polyglot_package <- function(root, install_tests = FALSE) {
    tarball <- build_polyglot_package(root)
    library <- file.path(root, "library")
    dir.create(library)
    arguments <- c(
        "CMD", "INSTALL", "--no-multiarch",
        if (install_tests) "--install-tests" else character(),
        "-l", shQuote(library), shQuote(tarball)
    )
    result <- run_r_command(arguments, root)
    if (!identical(result$status, 0L)) {
        stop(paste(result$output, collapse = "\n"))
    }
    list(library = library, tarball = tarball, output = result$output)
}
