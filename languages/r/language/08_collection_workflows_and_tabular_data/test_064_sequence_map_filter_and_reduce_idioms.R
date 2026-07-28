# polyglot-covers: r.language.sequence-map-filter-and-reduce-idioms

values <- c(2L, 4L, 6L)

stopifnot(
    identical(seq_along(values), 1:3),
    identical(Map(`+`, values, 1:3), list(3L, 6L, 9L)),
    identical(Filter(function(value) value > 2L, values), c(4L, 6L)),
    identical(Reduce(`+`, values), 12L),
    identical(Reduce(`+`, values, accumulate = TRUE), c(2L, 6L, 12L))
)

# base R 没有统一的外部 iterator 协议；向量化、apply/Map、seq_along 和 Reduce 是惯用入口。
