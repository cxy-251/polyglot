# polyglot-covers: r.tooling.native-symbol-registration-and-lookup

local({
    native_library <- normalizePath(Sys.getenv("POLYGLOT_R_NATIVE_LIBRARY"), mustWork = TRUE)
    dll <- dyn.load(native_library, local = TRUE, now = TRUE)
    on.exit(dyn.unload(dll[["path"]]), add = TRUE)
    routines <- getDLLRegisteredRoutines(dll)

    stopifnot(
        "polyglot_scale" %in% names(routines$.C),
        "C_polyglot_double" %in% names(routines$.Call),
        identical(routines$.C$polyglot_scale$numParameters, 3L),
        identical(routines$.Call$C_polyglot_double$numParameters, 1L)
    )
})

# 注册表固定入口名、接口种类与参数数量；关闭 dynamic lookup 可把符号暴露收窄为显式 API。
