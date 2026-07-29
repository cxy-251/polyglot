# polyglot-covers: r.tooling.dot-c-copying-na-and-c-abi-boundaries

local({
    native_library <- normalizePath(Sys.getenv("POLYGLOT_R_NATIVE_LIBRARY"), mustWork = TRUE)
    dll <- dyn.load(native_library, local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)

    original <- c(1, 2, NA_real_)
    rejected <- tryCatch(
        .C(
            "polyglot_scale",
            values = original,
            length = as.integer(length(original)),
            factor = 3,
            PACKAGE = "polyglotnative"
        ),
        error = identity
    )
    result <- .C(
        "polyglot_scale",
        values = original,
        length = as.integer(length(original)),
        factor = 3,
        NAOK = TRUE,
        PACKAGE = "polyglotnative"
    )
    classify <- function(value) {
        .Call("C_polyglot_missing_kind", value, PACKAGE = "polyglotnative")
    }

    stopifnot(
        inherits(rejected, "error"),
        identical(result$values, c(3, 6, NA_real_)),
        identical(original, c(1, 2, NA_real_)),
        identical(result$length, 3L),
        identical(classify(1), 0L),
        identical(classify(NA_real_), 1L),
        identical(classify(NaN), 2L)
    )
})

# `.C` 以 typed pointer 参数工作并默认复制；NAOK 控制缺失浮点值。C 侧必须用 R 的 NA/NaN API。
