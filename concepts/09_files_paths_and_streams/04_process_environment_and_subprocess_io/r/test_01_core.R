# polyglot-family: files_paths_and_streams
# polyglot-concept: process_environment_and_subprocess_io
# polyglot-related: languages/r/tooling_and_runtime/15_processes_parallel_and_runtime/
# polyglot-related+: test_113_system2_output_error_and_exit_status.R
#
# 共同问题：子进程怎样继承环境、接收输入并返回 stdout、stderr 与退出码。
# 对照观察：`system2` 显式传入 env 和参数；捕获输出向量的 status attribute 表达非零退出。

success <- system2(
    file.path(R.home("bin"), "Rscript"),
    c("--vanilla", "-e", shQuote("cat(Sys.getenv('POLYGLOT_CHILD'))")),
    stdout = TRUE,
    stderr = TRUE,
    env = "POLYGLOT_CHILD=value"
)
failure <- suppressWarnings(system2(
    file.path(R.home("bin"), "Rscript"),
    c("--vanilla", "-e", shQuote("quit(status=9L)")),
    stdout = TRUE,
    stderr = TRUE
))

stopifnot(identical(success, "value"), identical(attr(failure, "status"), 9L))
