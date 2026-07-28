# polyglot-covers: r.tooling.external-pointer-release-and-finalizer-boundary

local({
    source("languages/r/support/native_helpers.R", local = TRUE)
    root <- tempfile("polyglot-r-native-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    dll <- dyn.load(build_polyglot_native(root), local = TRUE, now = TRUE)
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
