# polyglot-covers: r.tooling.compiler-reflection-and-runtime-capabilities

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
    identical(as.character(getRversion()), "4.6.1"),
    is.logical(capabilities("cairo")),
    .Platform$OS.type %in% c("unix", "windows")
)

# cmpfun 不承诺性能；反射只锁定公开函数结构。版本与 capabilities 是不同层次的运行时观察。
