# polyglot-covers: r.language.split-unsplit-and-empty-factor-groups

groups <- factor(c("a", "b", "a"), levels = c("a", "b", "c"))
values <- c(10L, 20L, 30L)
parts <- split(values, groups, drop = FALSE)

stopifnot(
    identical(parts$a, c(10L, 30L)),
    identical(parts$b, 20L),
    identical(parts$c, integer(0)),
    identical(unname(unsplit(parts, groups)), values),
    identical(names(parts), c("a", "b", "c"))
)
