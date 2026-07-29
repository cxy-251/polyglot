# polyglot-covers: r.language.data-frame-list-mutation-and-joins

frame <- data.frame(id = 1:3, label = c("a", "b", "c"))

stopifnot(
    identical(frame[, "id"], 1:3),
    inherits(frame["id"], "data.frame"),
    identical(frame[2L, ], data.frame(id = 2L, label = "b", row.names = 2L)),
    identical(frame[frame$id > 1L, "label"], c("b", "c")),
    identical(frame[, "id", drop = FALSE], frame["id"])
)

value <- list(config = list(database = list(port = 5432L)), enabled = TRUE)
alias <- value
value[[c("config", "database", "port")]] <- 6432L
value["enabled"] <- list(FALSE)
stopifnot(
    identical(value$config$database$port, 6432L),
    identical(alias$config$database$port, 5432L),
    identical(value$enabled, FALSE)
)

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
