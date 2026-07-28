# polyglot-covers: r.standard-library.rng-state-sampling-and-statistics

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

    RNGkind("Mersenne-Twister", "Inversion", "Rejection")
    set.seed(2026)
    first <- sample.int(100L, 5L)
    set.seed(2026)
    second <- sample.int(100L, 5L)

    stopifnot(
        identical(first, second),
        identical(mean(c(1, 2, 3)), 2),
        isTRUE(all.equal(stats::var(c(1, 2, 3)), 1))
    )
})
