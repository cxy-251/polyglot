# polyglot-covers: r.language.on-exit-cleanup-and-interrupts

trace <- character()
work <- function() {
    on.exit(trace <<- c(trace, "first"), add = TRUE)
    on.exit(trace <<- c(trace, "second"), add = TRUE)
    stop("failure")
}

error <- tryCatch(work(), error = identity)

stopifnot(
    inherits(error, "error"),
    identical(trace, c("first", "second"))
)

interrupt_trace <- character()
interrupt_work <- function() {
    on.exit(interrupt_trace <<- c(interrupt_trace, "cleanup"), add = TRUE)
    stop(structure(
        list(message = "interrupted", call = NULL),
        class = c("interrupt", "condition")
    ))
}
captured <- tryCatch(interrupt_work(), interrupt = identity)
stopifnot(inherits(captured, "interrupt"), identical(interrupt_trace, "cleanup"))

# on.exit 的多个 action 按注册顺序执行；condition 类为 interrupt 也不会跳过函数退出清理。
