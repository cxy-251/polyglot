# polyglot-covers: r.language.named-positional-and-exact-argument-matching

target <- function(alpha, beta, gamma = 3L) c(alpha = alpha, beta = beta, gamma = gamma)

stopifnot(
    identical(target(1L, 2L), c(alpha = 1L, beta = 2L, gamma = 3L)),
    identical(target(beta = 2L, alpha = 1L), c(alpha = 1L, beta = 2L, gamma = 3L)),
    identical(
        do.call(target, list(alpha = 1L, beta = 2L, gamma = 4L)),
        c(alpha = 1L, beta = 2L, gamma = 4L)
    ),
    identical(names(match.call(target, quote(target(alpha = 1L, beta = 2L))))[2:3], c("alpha", "beta"))
)
