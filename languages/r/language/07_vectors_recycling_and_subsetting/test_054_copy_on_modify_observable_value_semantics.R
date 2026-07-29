# polyglot-covers: r.language.value-semantics-reference-objects-and-altrep-boundary

original <- c(1L, 2L, 3L)
alias <- original
alias[1L] <- 9L

list_original <- list(values = original)
list_alias <- list_original
list_alias$values[2L] <- 8L

stopifnot(
    identical(original, c(1L, 2L, 3L)),
    identical(alias, c(9L, 2L, 3L)),
    identical(list_original$values, c(1L, 2L, 3L)),
    identical(list_alias$values, c(1L, 8L, 3L))
)

environment_value <- new.env(parent = emptyenv())
environment_value$count <- 1L
environment_alias <- environment_value
environment_alias$count <- 2L
sequence <- 1:1000000
copy <- as.integer(sequence)

stopifnot(
    identical(environment_value$count, 2L),
    identical(environment_value, environment_alias),
    identical(typeof(sequence), "integer"),
    identical(sequence[c(1L, 1000000L)], c(1L, 1000000L)),
    identical(sum(sequence), 500000500000),
    identical(sequence, copy)
)

# 普通向量保证可见的值语义，environment 明确是引用对象。NAMED/refcount、实际复制与 ALTREP
# materialization 都是实现观察，R 层课程不把它们锁定为接口保证。
