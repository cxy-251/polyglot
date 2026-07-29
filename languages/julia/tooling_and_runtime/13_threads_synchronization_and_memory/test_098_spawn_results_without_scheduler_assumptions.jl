# polyglot-covers: julia.runtime.thread-scheduling-task-migration-and-owned-output

using Test
using Base.Threads

@testset "线程任务只断言结果与独占输出，不锁定调度和 threadid" begin
    tasks = [Threads.@spawn (value^2, threadid()) for value in 1:8]
    results = fetch.(tasks)
    @test first.(results) == [value^2 for value in 1:8]
    @test all(id -> 1 <= id <= Threads.maxthreadid(), last.(results))
    @test all(istaskdone, tasks)
    output = zeros(Int, 32)
    Threads.@threads for index in eachindex(output)
        output[index] = index^2
    end
    @test output == [index^2 for index in eachindex(output)]
    # 非 :static Task 在 yield 后可能迁移，不能把 threadid 当作稳定 buffer 索引。
end
