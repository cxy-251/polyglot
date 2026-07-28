# polyglot-family: files_paths_and_streams
# polyglot-concept: file_directory_metadata_and_links
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_103_file_paths_processes_and_environment.R
#
# 共同问题：文件、目录、metadata 和链接如何观察。
# 对照观察：`file.info` 向量化返回 metadata；符号链接能力按平台检测并以 `Sys.readlink` 观察。

local({
    root <- tempfile("polyglot-r-file-")
    dir.create(root)
    on.exit(unlink(root, recursive = TRUE, force = TRUE), add = TRUE)
    path <- file.path(root, "value.txt")
    writeLines("content", path)
    link <- file.path(root, "value-link")
    linked <- file.symlink(path, link)
    information <- file.info(c(root, path))

    stopifnot(
        isTRUE(information$isdir[[1L]]),
        isFALSE(information$isdir[[2L]]),
        information$size[[2L]] > 0,
        !linked || nzchar(Sys.readlink(link))
    )
})
