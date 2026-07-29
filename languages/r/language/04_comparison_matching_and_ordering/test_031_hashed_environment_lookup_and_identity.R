# polyglot-covers: r.language.environment-identity-sets-and-ordering-protocol

table <- new.env(hash = TRUE, parent = emptyenv())
assign("answer", 42L, envir = table)
alias <- table
alias$extra <- "shared"
left <- c(1L, 2L, 2L)
right <- c(2L, 3L)
factor_value <- factor(c("b", "a"), levels = c("a", "b"))

stopifnot(
    identical(get("answer", envir = table, inherits = FALSE), 42L),
    exists("answer", envir = table, inherits = FALSE),
    !exists("missing", envir = table, inherits = FALSE),
    identical(table, alias),
    identical(table$extra, "shared"),
    environmentName(table) == "",
    identical(union(left, right), 1:3),
    identical(intersect(left, right), 2L),
    identical(setdiff(left, right), 1L),
    setequal(c(1L, 1L, 2L), c(2L, 1L)),
    identical(xtfrm(factor_value), c(2L, 1L)),
    identical(order(factor_value), c(2L, 1L))
)

# environment 是引用对象；集合函数先按值去重；类可通过 xtfrm 提供排序代理。
