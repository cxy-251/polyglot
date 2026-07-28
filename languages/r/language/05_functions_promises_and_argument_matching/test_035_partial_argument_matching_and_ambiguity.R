# polyglot-covers: r.language.partial-argument-matching-and-ambiguity

local({
    old_option <- getOption("warnPartialMatchArgs")
    on.exit(options(warnPartialMatchArgs = old_option), add = TRUE)
    options(warnPartialMatchArgs = TRUE)

    target <- function(alpha, beta) alpha + beta
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
        identical(result, 3L),
        inherits(warning_condition, "warning"),
        grepl("partial argument match", conditionMessage(warning_condition)),
        inherits(tryCatch(ambiguous(al = 1L), error = identity), "error")
    )
})
