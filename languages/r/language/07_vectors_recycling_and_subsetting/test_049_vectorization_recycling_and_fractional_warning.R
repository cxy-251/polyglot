# polyglot-covers: r.language.vectorization-recycling-and-zero-length-boundaries

stopifnot(
    identical(1:4 + 10L, 11:14),
    identical(1:4 + c(10L, 20L), c(11L, 22L, 13L, 24L))
)

warning_condition <- NULL
result <- withCallingHandlers(
    1:5 + c(10L, 20L),
    warning = function(condition) {
        warning_condition <<- condition
        invokeRestart("muffleWarning")
    }
)
stopifnot(
    identical(result, c(11L, 22L, 13L, 24L, 15L)),
    inherits(warning_condition, "warning")
)

stopifnot(
    identical(integer(0) + 1L, integer(0)),
    identical(logical(0) & TRUE, logical(0)),
    identical(paste0(character(0), "suffix"), "suffix"),
    identical(paste0(character(0), "suffix", recycle0 = TRUE), character(0)),
    identical(ifelse(logical(0), 1L, 2L), logical(0)),
    identical(seq_along(NULL), integer(0))
)

# 长度整除时静默 recycling；非整倍数产生 warning；不同 API 对零长度传播有自己的合同。
