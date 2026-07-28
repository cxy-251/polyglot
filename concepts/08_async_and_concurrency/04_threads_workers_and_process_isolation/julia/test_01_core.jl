# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/julia/tooling_and_runtime/13_threads_synchronization_and_memory/
# polyglot-related+: test_098_spawn_results_without_scheduler_assumptions.jl
#
# 共同问题：thread 与 process 是否共享地址空间；结果怎样返回而不依赖调度位置。
# 对照观察：Threads.@spawn 在同一进程共享对象；子进程只有显式 IO/serialization 边界。

using Test
using Base.Threads

@testset "thread 共享进程而 child process 独立" begin
    parent_pid = getpid()
    thread_result = fetch(Threads.@spawn (getpid(), Threads.threadid()))
    @test thread_result[1] == parent_pid
    command = `$(Base.julia_cmd()) --startup-file=no --history-file=no -e "print(getpid())"`
    child_pid = parse(Int, read(command, String))
    @test child_pid != parent_pid
    @test thread_result[2] in 1:Threads.nthreads()
end
