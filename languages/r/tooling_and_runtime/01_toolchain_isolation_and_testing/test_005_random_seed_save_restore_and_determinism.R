# polyglot-covers: r.tooling.random-seed-save-restore-and-determinism

local({
    had_seed <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    old_seed <- if (had_seed) get(".Random.seed", envir = .GlobalEnv) else NULL
    on.exit({
        if (had_seed) {
            assign(".Random.seed", old_seed, envir = .GlobalEnv)
        } else if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
            rm(".Random.seed", envir = .GlobalEnv)
        }
    }, add = TRUE)

    set.seed(20260728)
    first <- runif(4)
    set.seed(20260728)
    second <- runif(4)
    stopifnot(identical(first, second), length(first) == 4L, all(first >= 0 & first < 1))
})
