# polyglot-covers: r.language.data-frame-row-column-and-drop-semantics

frame <- data.frame(id = 1:3, label = c("a", "b", "c"))

stopifnot(
    identical(frame[, "id"], 1:3),
    inherits(frame["id"], "data.frame"),
    identical(frame[2L, ], data.frame(id = 2L, label = "b", row.names = 2L)),
    identical(frame[frame$id > 1L, "label"], c("b", "c")),
    identical(frame[, "id", drop = FALSE], frame["id"])
)
