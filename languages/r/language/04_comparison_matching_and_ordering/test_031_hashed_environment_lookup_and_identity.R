# polyglot-covers: r.language.hashed-environment-lookup-and-identity

table <- new.env(hash = TRUE, parent = emptyenv())
assign("answer", 42L, envir = table)
alias <- table
alias$extra <- "shared"

stopifnot(
    identical(get("answer", envir = table, inherits = FALSE), 42L),
    exists("answer", envir = table, inherits = FALSE),
    !exists("missing", envir = table, inherits = FALSE),
    identical(table, alias),
    identical(table$extra, "shared"),
    environmentName(table) == ""
)
