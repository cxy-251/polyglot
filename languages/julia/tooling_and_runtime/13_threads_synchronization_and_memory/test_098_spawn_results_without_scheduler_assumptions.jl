# polyglot-covers: julia.runtime.spawn-results-without-scheduler-assumptions

using Test
using Base.Threads

@testset "@spawn 返回 Task；结果可等待但线程选择和顺序不可断言" begin
    tasks = [Threads.@spawn (value^2, threadid()) for value in 1:8]
    results = fetch.(tasks)
    @test first.(results) == [value^2 for value in 1:8]
    @test all(id -> 1 <= id <= Threads.maxthreadid(), last.(results))
    @test all(istaskdone, tasks)
end
