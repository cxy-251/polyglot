# polyglot-covers: r.language.match-call-and-argument-normalization

normalize <- function(alpha, beta = 2L, ..., expand = TRUE) {
    match.call(expand.dots = expand)
}

expanded <- normalize(be = 4L, alpha = 1L, extra = 9L)
packed <- normalize(be = 4L, alpha = 1L, extra = 9L, expand = FALSE)

stopifnot(
    identical(expanded$alpha, 1L),
    identical(expanded$beta, 4L),
    identical(expanded$extra, 9L),
    is.pairlist(packed$...),
    identical(packed$...$extra, 9L)
)
