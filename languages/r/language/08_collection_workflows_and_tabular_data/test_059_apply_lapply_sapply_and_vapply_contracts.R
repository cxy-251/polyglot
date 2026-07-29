# polyglot-covers: r.language.apply-split-map-filter-and-reduce-contracts

values <- list(first = 1:2, second = 3:5)

stopifnot(
    identical(lapply(values, sum), list(first = 3L, second = 12L)),
    identical(sapply(values, length), c(first = 2L, second = 3L)),
    identical(vapply(values, length, integer(1)), c(first = 2L, second = 3L)),
    inherits(tryCatch(vapply(values, identity, integer(1)), error = identity), "error"),
    identical(apply(matrix(1:4, nrow = 2L), 2L, sum), c(3L, 7L))
)

groups <- factor(c("a", "b", "a"), levels = c("a", "b", "c"))
parts <- split(c(10L, 20L, 30L), groups, drop = FALSE)
stopifnot(
    identical(parts$a, c(10L, 30L)),
    identical(parts$c, integer(0)),
    identical(unname(unsplit(parts, groups)), c(10L, 20L, 30L))
)

sequence <- c(2L, 4L, 6L)
stopifnot(
    identical(Map(`+`, sequence, 1:3), list(3L, 6L, 9L)),
    identical(Filter(function(value) value > 2L, sequence), c(4L, 6L)),
    identical(Reduce(`+`, sequence), 12L),
    identical(Reduce(`+`, sequence, accumulate = TRUE), c(2L, 6L, 12L))
)

# base R 没有统一外部 iterator 协议；向量化、apply/Map、split 与 Reduce 是不同形状的入口。
