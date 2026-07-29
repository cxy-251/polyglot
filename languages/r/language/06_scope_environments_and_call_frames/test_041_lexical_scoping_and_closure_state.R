# polyglot-covers: r.language.lexical-scope-environments-and-superassignment

make_counter <- function() {
    value <- 0L
    function() {
        value <<- value + 1L
        value
    }
}

first <- make_counter()
second <- make_counter()

stopifnot(
    identical(c(first(), first(), second()), c(1L, 2L, 1L)),
    !identical(environment(first), environment(second)),
    identical(parent.env(environment(first)), environment(make_counter))
)

parent <- new.env(parent = emptyenv())
child <- new.env(parent = parent)
assign("shared", 1L, envir = parent)
assign("local", 2L, envir = child)
alias <- child
lockEnvironment(child, bindings = FALSE)

stopifnot(
    identical(get("local", envir = child, inherits = FALSE), 2L),
    identical(get("shared", envir = child, inherits = TRUE), 1L),
    !exists("shared", envir = child, inherits = FALSE),
    identical(parent.env(child), parent),
    identical(alias, child),
    environmentIsLocked(child),
    inherits(tryCatch(child$new <- 1L, error = identity), "error")
)

# `<<-` 沿 enclosure 搜索现有 binding；environment 本身采用引用语义，锁定 frame 不会复制它。
