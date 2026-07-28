# polyglot-covers: r.language.stable-order-rank-and-custom-keys

rows <- data.frame(key = c(2L, 1L, 2L), name = c("a", "b", "c"))
indices <- order(rows$key, method = "radix")
descending <- order(rows$key, decreasing = TRUE, method = "radix")

stopifnot(
    identical(indices, c(2L, 1L, 3L)),
    identical(rows$name[indices], c("b", "a", "c")),
    identical(descending, c(1L, 3L, 2L)),
    isTRUE(all.equal(rank(rows$key, ties.method = "min"), c(2, 1, 2))),
    identical(sort(c("bbb", "a", "cc"), method = "radix"), c("a", "bbb", "cc"))
)
