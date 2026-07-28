# polyglot-covers: r.language.typeof-mode-storage-mode-and-class

integer <- 1:3
date <- as.Date("2026-07-28")

stopifnot(
    identical(typeof(integer), "integer"),
    identical(mode(integer), "numeric"),
    identical(storage.mode(integer), "integer"),
    identical(class(integer), "integer"),
    identical(typeof(date), "double"),
    identical(mode(date), "numeric"),
    identical(class(date), "Date")
)
