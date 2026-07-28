# polyglot-family: files_paths_and_streams
# polyglot-concept: path_normalization_and_resolution
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_103_file_paths_processes_and_environment.R
#
# 共同问题：相对路径、规范化和不存在路径怎样处理。
# 对照观察：`file.path` 只拼接；`normalizePath` 解析真实路径，`mustWork` 控制不存在目标是否失败。

local({
    root <- tempfile("polyglot-r-path-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    nested <- file.path(root, "nested")
    dir.create(nested)

    stopifnot(
        identical(normalizePath(file.path(root, ".", "nested")), normalizePath(nested)),
        inherits(
            tryCatch(normalizePath(file.path(root, "missing"), mustWork = TRUE), error = identity),
            "error"
        ),
        grepl("missing$", normalizePath(file.path(root, "missing"), mustWork = FALSE))
    )
})
