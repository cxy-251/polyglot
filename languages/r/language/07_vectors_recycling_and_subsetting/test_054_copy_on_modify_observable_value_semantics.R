# polyglot-covers: r.language.copy-on-modify-observable-value-semantics

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

# NAMED/refcount 和实际复制时机属于实现观察；这里只锁定可见的值语义。
