# polyglot-covers: r.language.merge-keys-order-and-unmatched-rows

left <- data.frame(id = c(2L, 1L), left = c("b", "a"))
right <- data.frame(id = c(1L, 3L), right = c("A", "C"))

inner <- merge(left, right, by = "id")
outer <- merge(left, right, by = "id", all = TRUE)

stopifnot(
    identical(inner, data.frame(id = 1L, left = "a", right = "A")),
    identical(outer$id, 1:3),
    identical(outer$left, c("a", "b", NA_character_)),
    identical(outer$right, c("A", NA_character_, "C"))
)
