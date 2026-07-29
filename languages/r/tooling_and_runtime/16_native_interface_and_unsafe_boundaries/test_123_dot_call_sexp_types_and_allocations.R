# polyglot-covers: r.tooling.dot-call-sexp-protection-and-long-length-interface

local({
    native_library <- normalizePath(Sys.getenv("POLYGLOT_R_NATIVE_LIBRARY"), mustWork = TRUE)
    dll <- dyn.load(native_library, local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    result <- .Call("C_polyglot_double", c(1, 2, 3), PACKAGE = "polyglotnative")
    type_error <- tryCatch(
        .Call("C_polyglot_double", 1:3, PACKAGE = "polyglotnative"),
        error = identity
    )
    results <- lapply(seq_len(100L), function(index) {
        .Call("C_polyglot_double", as.double(index), PACKAGE = "polyglotnative")
    })
    length_value <- .Call("C_polyglot_length", seq_len(1000L), PACKAGE = "polyglotnative")

    stopifnot(
        identical(result, c(2, 4, 6)),
        identical(typeof(result), "double"),
        inherits(type_error, "error"),
        identical(unlist(results), as.double(seq_len(100L) * 2L)),
        identical(length_value, 1000),
        identical(typeof(length_value), "double")
    )
})

# `.Call` 传递 SEXP；分配结果必须在可能分配的 C 调用期间 PROTECT。XLENGTH 使用 R_xlen_t，
# 课程用小向量验证公开接口，不申请真正 long vector。
