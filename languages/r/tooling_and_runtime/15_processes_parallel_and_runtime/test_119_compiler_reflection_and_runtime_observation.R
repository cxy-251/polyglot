# polyglot-covers: r.tooling.compiler-reflection-and-runtime-observation

function_value <- function(x) x + 1L
compiled <- compiler::cmpfun(function_value)
call <- quote(function_value(2L))

stopifnot(
    identical(compiled(2L), 3L),
    is.function(compiled),
    identical(names(formals(function_value)), "x"),
    length(formals(function_value)) == 1L,
    identical(body(function_value), quote(x + 1L)),
    identical(as.character(call[[1L]]), "function_value"),
    is.matrix(gc())
)
