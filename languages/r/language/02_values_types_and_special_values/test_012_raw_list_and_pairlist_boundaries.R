# polyglot-covers: r.language.object-kinds-language-objects-and-type-views

bytes <- charToRaw("R")
heterogeneous <- list(1L, "two", NULL)
arguments <- pairlist(first = 1L, second = quote(value))
symbol <- as.name("value")
call <- quote(sum(value, 1L))
expressions <- expression(value <- 2L, value + 1L)
integer <- 1:3
date <- as.Date("2026-07-28")

stopifnot(
    identical(bytes, as.raw(0x52)),
    identical(typeof(heterogeneous), "list"),
    length(heterogeneous) == 3L,
    identical(typeof(arguments), "pairlist"),
    identical(arguments[[2L]], quote(value)),
    identical(pairlist(), NULL),
    identical(typeof(symbol), "symbol"),
    identical(as.character(symbol), "value"),
    identical(typeof(call), "language"),
    identical(call[[1L]], as.name("sum")),
    identical(typeof(expressions), "expression"),
    length(expressions) == 2L,
    identical(typeof(integer), "integer"),
    identical(mode(integer), "numeric"),
    identical(storage.mode(integer), "integer"),
    identical(class(integer), "integer"),
    identical(typeof(date), "double"),
    identical(mode(date), "numeric"),
    identical(class(date), "Date")
)

# typeof 描述底层 R 对象种类；mode/storage.mode 是 S 兼容视图；class 决定对象分派。
