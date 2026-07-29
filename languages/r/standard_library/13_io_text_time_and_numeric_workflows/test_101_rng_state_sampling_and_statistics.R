# polyglot-covers: r.standard-library.rng-state-stream-selection-and-sampling

local({
    had_seed <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    old_seed <- if (had_seed) get(".Random.seed", envir = .GlobalEnv) else NULL
    old_kind <- RNGkind()
    on.exit({
        do.call(RNGkind, as.list(old_kind))
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
        length(first) == 5L,
        all(first >= 1L & first <= 100L),
        identical(RNGkind(), c("Mersenne-Twister", "Inversion", "Rejection"))
    )
})

# RNGkind 和 .Random.seed 共同决定流；测试必须恢复两者，不能污染随后运行的统计代码。
