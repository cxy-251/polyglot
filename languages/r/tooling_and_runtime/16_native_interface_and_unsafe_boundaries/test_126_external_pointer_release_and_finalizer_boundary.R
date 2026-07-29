# polyglot-covers: r.tooling.external-pointer-release-and-finalizer-boundary

local({
    native_library <- normalizePath(Sys.getenv("POLYGLOT_R_NATIVE_LIBRARY"), mustWork = TRUE)
    dll <- dyn.load(native_library, local = TRUE, now = TRUE)
    # external pointer 仍保存 native finalizer 地址；DLL 保持加载到隔离测试进程退出。

    pointer <- .Call("C_polyglot_make_pointer", 42L, PACKAGE = "polyglotnative")
    value <- .Call("C_polyglot_read_pointer", pointer, PACKAGE = "polyglotnative")
    invisible(.Call("C_polyglot_release_pointer", pointer, PACKAGE = "polyglotnative"))
    error <- tryCatch(
        .Call("C_polyglot_read_pointer", pointer, PACKAGE = "polyglotnative"),
        error = identity
    )

    stopifnot(
        identical(typeof(pointer), "externalptr"),
        identical(value, 42L),
        inherits(error, "error")
    )
})

# finalizer 是兜底而非时序协议；测试显式 release，再验证 cleared external pointer 拒绝读取。
