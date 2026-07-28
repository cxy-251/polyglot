# polyglot-covers: r.tooling.r-cmd-build-install-and-check

local({
    source("languages/r/support/package_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-package-check-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    installed <- install_polyglot_package(root, install_tests = TRUE)

    check <- run_r_command(
        c(
            "CMD", "check", "--no-manual", "--no-vignettes",
            "--no-build-vignettes", "--no-examples", shQuote(installed$tarball)
        ),
        root,
        environment = c("_R_CHECK_CRAN_INCOMING_=false", "_R_CHECK_FORCE_SUGGESTS_=false")
    )
    log_path <- file.path(root, "polyglotrfixture.Rcheck", "00check.log")
    check_log <- readLines(log_path, warn = FALSE)
    if (!any(grepl("Status: OK", check_log, fixed = TRUE))) {
        note_lines <- grep("NOTE|WARNING|ERROR|Good practice|Last[.]lib", check_log)
        context <- unique(unlist(lapply(note_lines, function(index) {
            seq.int(max(1L, index - 3L), min(length(check_log), index + 3L))
        })))
        stop(paste(check_log[context], collapse = "\n"))
    }

    stopifnot(
        identical(check$status, 0L),
        file.exists(log_path)
    )
})
