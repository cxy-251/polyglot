# polyglot-covers: r.language.altrep-stable-interface-boundary

sequence <- 1:1000000
copy <- as.integer(sequence)

stopifnot(
    identical(typeof(sequence), "integer"),
    length(sequence) == 1000000L,
    identical(sequence[c(1L, 1000000L)], c(1L, 1000000L)),
    identical(sum(sequence), 500000500000),
    identical(sequence, copy)
)

# ALTREP 是否采用、何时 materialize 和对象布局没有稳定的 R 层 predicate，测试只断言公开向量接口。
