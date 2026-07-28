# polyglot-covers: r.language.match-percent-in-and-nomatch

table <- c("red", "green", NA_character_)

stopifnot(
    identical(match(c("green", "blue"), table), c(2L, NA_integer_)),
    identical(match(c("green", "blue"), table, nomatch = 0L), c(2L, 0L)),
    identical(c("red", "blue") %in% table, c(TRUE, FALSE)),
    identical(match(NA_character_, table), 3L),
    identical(match(c(NA_real_, NaN), c(NaN, NA_real_)), c(2L, 1L))
)
