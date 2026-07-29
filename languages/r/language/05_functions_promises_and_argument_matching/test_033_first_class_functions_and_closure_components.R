# polyglot-covers: r.language.function-objects-and-argument-matching

offset <- 3L
add_offset <- function(value = 1L) value + offset
functions <- list(add_offset, identity)
target <- function(alpha, beta, gamma = 3L) c(alpha = alpha, beta = beta, gamma = gamma)

stopifnot(
    identical(typeof(add_offset), "closure"),
    identical(formals(add_offset), pairlist(value = 1L)),
    identical(body(add_offset), quote(value + offset)),
    identical(environment(add_offset), environment()),
    identical(functions[[1L]](4L), 7L),
    identical(functions[[2L]]("value"), "value"),
    identical(target(1L, 2L), c(alpha = 1L, beta = 2L, gamma = 3L)),
    identical(target(beta = 2L, alpha = 1L), c(alpha = 1L, beta = 2L, gamma = 3L)),
    identical(
        do.call(target, list(alpha = 1L, beta = 2L, gamma = 4L)),
        c(alpha = 1L, beta = 2L, gamma = 4L)
    )
)

local({
    old_option <- getOption("warnPartialMatchArgs")
    on.exit(options(warnPartialMatchArgs = old_option), add = TRUE)
    options(warnPartialMatchArgs = TRUE)

    warning_condition <- NULL
    result <- withCallingHandlers(
        target(al = 1L, beta = 2L),
        warning = function(condition) {
            warning_condition <<- condition
            invokeRestart("muffleWarning")
        }
    )
    ambiguous <- function(alpha, alphabet) alpha + alphabet
    stopifnot(
        identical(result, c(alpha = 1L, beta = 2L, gamma = 3L)),
        inherits(warning_condition, "warning"),
        inherits(tryCatch(ambiguous(al = 1L), error = identity), "error")
    )
})

# R 依次采用 exact name、唯一 partial name、position 匹配；`...` 取得其余参数。
