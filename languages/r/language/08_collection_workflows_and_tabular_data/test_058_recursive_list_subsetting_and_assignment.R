# polyglot-covers: r.language.recursive-list-subsetting-and-assignment

value <- list(config = list(database = list(port = 5432L)), enabled = TRUE)
alias <- value
value[[c("config", "database", "port")]] <- 6432L
value["enabled"] <- list(FALSE)

stopifnot(
    identical(value$config$database$port, 6432L),
    identical(alias$config$database$port, 5432L),
    identical(value$enabled, FALSE),
    identical(names(value), c("config", "enabled"))
)
